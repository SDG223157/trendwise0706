# app/utils/search/news_search.py

from typing import List, Dict, Tuple
from sqlalchemy import or_, and_, func, desc, distinct
from sqlalchemy.orm import Session
from ...models import NewsArticle, ArticleSymbol, ArticleMetric
import re
from datetime import datetime, timedelta
from textblob import TextBlob
import logging

logger = logging.getLogger(__name__)

class NewsSearch:
    def __init__(self, session: Session):
        self.session = session
        # Initialize cache if available
        self.cache = None
        self.cache_enabled = False
        
        try:
            from ..cache.news_cache import NewsCache
            self.cache = NewsCache()
            self.cache_enabled = self.cache.is_available()
            if self.cache_enabled:
                logger.debug("✅ NewsSearch initialized with Redis cache")
            else:
                logger.debug("ℹ️ NewsSearch initialized without Redis cache")
        except ImportError as e:
            logger.debug(f"Cache module not available: {str(e)}")
        except Exception as e:
            logger.warning(f"Cache initialization failed: {str(e)}")

    def is_cache_available(self) -> bool:
        """Check if cache is available"""
        return self.cache_enabled and self.cache and self.cache.is_available()

    def advanced_search(
        self,
        keywords: List[str] = None,
        symbols: List[str] = None,
        sentiment: str = None,
        min_sentiment_score: float = None,
        start_date: str = None,
        end_date: str = None,
        sources: List[str] = None,
        metric_type: str = None,
        metric_min_value: float = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict], int]:
        """Advanced search with multiple filters"""
        query = self.session.query(NewsArticle)

        # ALWAYS filter to only show articles with AI processing (both summary and insights)
        # This ensures users only see high-quality, AI-enhanced content
        query = query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_summary != '',
            NewsArticle.ai_insights != ''
        )

        # Keyword search (with phrase support)
        if keywords:
            keyword_filters = []
            for keyword in keywords:
                if '"' in keyword:  # Exact phrase match
                    phrase = keyword.replace('"', '')
                    keyword_filters.append(
                        NewsArticle.content.like(f"%{phrase}%")
                    )
                else:  # Individual word match
                    keyword_filters.append(or_(
                        NewsArticle.content.like(f"%{keyword}%"),
                        NewsArticle.title.like(f"%{keyword}%")
                    ))
            query = query.filter(and_(*keyword_filters))

        # Symbol filter
        if symbols:
            query = query.join(ArticleSymbol).filter(
                ArticleSymbol.symbol.in_(symbols)
            )

        # Sentiment filter
        if sentiment:
            query = query.filter(NewsArticle.sentiment_label == sentiment)
        if min_sentiment_score is not None:
            query = query.filter(NewsArticle.sentiment_score >= min_sentiment_score)

        # Date range filter
        if start_date:
            query = query.filter(NewsArticle.published_at >= start_date)
        if end_date:
            query = query.filter(NewsArticle.published_at <= end_date)

        # Source filter
        if sources:
            query = query.filter(NewsArticle.source.in_(sources))

        # Metric filter
        if metric_type and metric_min_value is not None:
            query = query.join(ArticleMetric).filter(and_(
                ArticleMetric.metric_type == metric_type,
                ArticleMetric.value >= metric_min_value
            ))

        # Get total count
        total_count = query.count()

        # Add pagination
        query = query.order_by(desc(NewsArticle.published_at))
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Execute query and convert to dict
        articles = [article.to_dict() for article in query.all()]
        
        return articles, total_count

    def find_similar_articles(
        self,
        article_id: int,
        max_results: int = 5
    ) -> List[Dict]:
        """Find articles similar to the given article"""
        # Get the original article
        original = self.session.query(NewsArticle).get(article_id)
        if not original:
            return []

        # Create TextBlob for original article
        original_blob = TextBlob(original.content)

        # Get articles from the same time period
        time_window = timedelta(days=7)
        candidates = (self.session.query(NewsArticle)
                    .filter(
                        NewsArticle.id != article_id,
                        NewsArticle.published_at.between(
                            original.published_at - time_window,
                            original.published_at + time_window
                        )
                    )
                    .all())

        # Calculate similarity scores
        similarities = []
        for candidate in candidates:
            candidate_blob = TextBlob(candidate.content)
            
            # Calculate similarity score based on multiple factors
            content_similarity = original_blob.similarity(candidate_blob)
            sentiment_similarity = 1 - abs(
                original.sentiment_score - candidate.sentiment_score
            )
            
            # Combine scores (you can adjust weights)
            total_score = (content_similarity * 0.7 + sentiment_similarity * 0.3)
            
            similarities.append((candidate, total_score))

        # Sort by similarity score and get top results
        similar_articles = sorted(
            similarities,
            key=lambda x: x[1],
            reverse=True
        )[:max_results]

        return [article[0].to_dict() for article in similar_articles]

    def get_trending_entities(
        self,
        days: int = 7,
        min_occurrences: int = 3
    ) -> Dict[str, List[Dict]]:
        """Get trending entities (companies, people, topics)"""
        # Get recent articles
        start_date = datetime.now() - timedelta(days=days)
        articles = (self.session.query(NewsArticle)
                   .filter(NewsArticle.published_at >= start_date)
                   .all())

        entities = {
            'companies': {},
            'people': {},
            'topics': {}
        }

        for article in articles:
            blob = TextBlob(article.content)
            
            # Extract noun phrases and classify them
            for phrase in blob.noun_phrases:
                if self._is_company(phrase):
                    entities['companies'][phrase] = entities['companies'].get(phrase, 0) + 1
                elif self._is_person(phrase):
                    entities['people'][phrase] = entities['people'].get(phrase, 0) + 1
                else:
                    entities['topics'][phrase] = entities['topics'].get(phrase, 0) + 1

        # Format results
        result = {}
        for category, items in entities.items():
            # Filter by minimum occurrences and sort by count
            trending = [
                {'entity': entity, 'occurrences': count}
                for entity, count in items.items()
                if count >= min_occurrences
            ]
            result[category] = sorted(
                trending,
                key=lambda x: x['occurrences'],
                reverse=True
            )[:10]  # Top 10 for each category

        return result

    # app/utils/search/news_search.py (continued)

    def _is_company(self, phrase: str) -> bool:
        """Simple heuristic to identify company names"""
        company_indicators = [
            'Inc', 'Corp', 'Ltd', 'LLC', 'Company', 'Technologies',
            'Holdings', 'Group', 'International', 'Incorporated',
            'Corporation', 'Limited', 'Bank', 'Partners'
        ]
        return any(indicator in phrase for indicator in company_indicators)

    def _is_person(self, phrase: str) -> bool:
        """Simple heuristic to identify person names"""
        # Check for common titles
        titles = ['Mr', 'Mrs', 'Ms', 'Dr', 'CEO', 'President', 'Director']
        if any(title in phrase for title in titles):
            return True
        
        # Check for name-like patterns (two or more capitalized words)
        words = phrase.split()
        if len(words) >= 2 and all(word[0].isupper() for word in words if word):
            return True
            
        return False

    def search_by_topic(self, topic: str, days: int = 30) -> List[Dict]:
        """Search articles by topic with relevant context"""
        start_date = datetime.now() - timedelta(days=days)
        
        # Search for articles containing the topic
        query = self.session.query(
            NewsArticle,
            func.ts_rank(
                func.to_tsvector('english', NewsArticle.content),
                func.plainto_tsquery('english', topic)
            ).label('relevance')
        ).filter(
            NewsArticle.published_at >= start_date,
            or_(
                NewsArticle.content.ilike(f'%{topic}%'),
                NewsArticle.title.ilike(f'%{topic}%')
            )
        ).order_by(desc('relevance'))

        articles = query.all()
        results = []

        for article, relevance in articles:
            # Extract relevant context around the topic
            context = self._extract_context(article.content, topic)
            
            article_dict = article.to_dict()
            article_dict['relevance'] = float(relevance)
            article_dict['topic_context'] = context
            results.append(article_dict)

        return results

    def _extract_context(self, text: str, topic: str, window: int = 100) -> str:
        """Extract context around a topic mention"""
        # Find all occurrences of the topic
        pattern = re.compile(topic, re.IGNORECASE)
        matches = list(pattern.finditer(text))
        
        contexts = []
        for match in matches:
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            
            # Get the context and highlight the topic
            context = text[start:end]
            if start > 0:
                context = f"...{context}"
            if end < len(text):
                context = f"{context}..."
                
            contexts.append(context)
            
        return contexts

    def get_topic_trends(self, topics: List[str], days: int = 30) -> Dict[str, List[Dict]]:
        """Analyze trends for specific topics over time"""
        start_date = datetime.now() - timedelta(days=days)
        results = {}
        
        for topic in topics:
            # Get daily mentions and sentiment
            daily_stats = (
                self.session.query(
                    func.date(NewsArticle.published_at).label('date'),
                    func.count().label('mentions'),
                    func.avg(NewsArticle.sentiment_score).label('avg_sentiment')
                )
                .filter(
                    NewsArticle.published_at >= start_date,
                    or_(
                        NewsArticle.content.ilike(f'%{topic}%'),
                        NewsArticle.title.ilike(f'%{topic}%')
                    )
                )
                .group_by(func.date(NewsArticle.published_at))
                .order_by(func.date(NewsArticle.published_at))
                .all()
            )
            
            results[topic] = [{
                'date': stats.date.strftime('%Y-%m-%d'),
                'mentions': stats.mentions,
                'sentiment': float(stats.avg_sentiment) if stats.avg_sentiment else 0
            } for stats in daily_stats]
            
        return results

    def get_related_topics(self, topic: str, min_correlation: float = 0.3) -> List[Dict]:
        """Find topics that frequently appear together"""
        # Get articles containing the main topic
        base_articles = set(
            article.id for article in
            self.session.query(NewsArticle.id)
            .filter(or_(
                NewsArticle.content.ilike(f'%{topic}%'),
                NewsArticle.title.ilike(f'%{topic}%')
            ))
        )
        
        if not base_articles:
            return []

        # Extract and count all noun phrases from these articles
        related = {}
        total_articles = len(base_articles)
        
        articles = (
            self.session.query(NewsArticle)
            .filter(NewsArticle.id.in_(base_articles))
        )
        
        for article in articles:
            blob = TextBlob(article.content)
            for phrase in blob.noun_phrases:
                if phrase.lower() != topic.lower():
                    related[phrase] = related.get(phrase, 0) + 1
        
        # Calculate correlation scores
        correlations = []
        for phrase, count in related.items():
            correlation = count / total_articles
            if correlation >= min_correlation:
                correlations.append({
                    'topic': phrase,
                    'correlation': correlation,
                    'occurrences': count
                })
        
        return sorted(correlations, key=lambda x: x['correlation'], reverse=True)

    def get_source_stats(self, start_date: str, end_date: str) -> List[Dict]:
        """Get statistics by news source"""
        stats = (
            self.session.query(
                NewsArticle.source,
                func.count().label('article_count'),
                func.avg(NewsArticle.sentiment_score).label('avg_sentiment'),
                func.count(distinct(ArticleSymbol.symbol)).label('unique_symbols')
            )
            .outerjoin(ArticleSymbol)
            .filter(NewsArticle.published_at.between(start_date, end_date))
            .group_by(NewsArticle.source)
            .order_by(desc('article_count'))
        )
        
        return [{
            'source': stat.source,
            'article_count': stat.article_count,
            'avg_sentiment': float(stat.avg_sentiment) if stat.avg_sentiment else 0,
            'unique_symbols': stat.unique_symbols
        } for stat in stats]

    def optimized_symbol_search(
        self,
        symbols: List[str] = None,
        sentiment_filter: str = None,
        sort_order: str = 'LATEST',
        date_filter: str = None,
        region_filter: str = None,
        processing_filter: str = 'all',
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict], int, bool]:  # Added has_more flag
        """
        Optimized search specifically for symbol-based queries
        Returns: (articles, total_count, has_more)
        """
        cache_key = None
        cached_result = None
        
        # Try cache first if available  
        if self.is_cache_available():
            try:
                cache_key = self._build_cache_key(
                    'symbol_search', symbols, sentiment_filter, sort_order, 
                    date_filter, region_filter, processing_filter, page, per_page
                )
                cached_result = self.cache.get_json(cache_key)
                if cached_result:
                    logger.debug(f"🎯 Cache hit for search query")
                    return cached_result['articles'], cached_result['total'], cached_result['has_more']
            except Exception as e:
                logger.debug(f"Cache lookup failed: {str(e)}")
                # Continue without cache

        # Build optimized query
        query = self.session.query(NewsArticle)
        
        # Apply symbol filter using optimized approach
        if symbols:
            symbol_conditions = []
            for symbol in symbols:
                # Use exact match first, then fallback to variants
                symbol_conditions.append(ArticleSymbol.symbol == symbol)
            
            # Use EXISTS subquery for better performance
            subquery = self.session.query(ArticleSymbol.article_id).filter(
                or_(*symbol_conditions)
            ).subquery()
            
            query = query.filter(NewsArticle.id.in_(subquery))

        # Apply other filters efficiently
        query = self._apply_filters(query, sentiment_filter, date_filter, 
                                   region_filter, processing_filter)

        # Apply sorting with optimized ORDER BY
        query = self._apply_sorting(query, sort_order)

        # Efficient pagination without full count for better performance
        articles = query.offset((page - 1) * per_page).limit(per_page + 1).all()
        
        has_more = len(articles) > per_page
        if has_more:
            articles = articles[:-1]  # Remove extra item
        
        # Get accurate total count for proper pagination
        if page == 1:
            # For first page, get actual total count
            count_query = self.session.query(NewsArticle)
            
            # Apply same filters for count
            if symbols:
                symbol_conditions = []
                for symbol in symbols:
                    symbol_conditions.append(ArticleSymbol.symbol == symbol)
                
                count_subquery = self.session.query(ArticleSymbol.article_id).filter(
                    or_(*symbol_conditions)
                ).subquery()
                
                count_query = count_query.filter(NewsArticle.id.in_(count_subquery))
            
            count_query = self._apply_filters(count_query, sentiment_filter, date_filter, 
                                           region_filter, processing_filter)
            
            total_count = count_query.count()
        else:
            # For subsequent pages, estimate based on has_more
            if has_more:
                total_count = page * per_page + 1  # At least this many
            else:
                total_count = (page - 1) * per_page + len(articles)

        # Convert to dict
        article_dicts = [article.to_dict() for article in articles]
        
        # Cache results if cache is available
        if self.is_cache_available() and cache_key:
            try:
                cache_data = {
                    'articles': article_dicts,
                    'total': total_count,
                    'has_more': has_more
                }
                success = self.cache.set_json(cache_key, cache_data, expire=300)  # 5 minute cache
                if success:
                    logger.debug(f"💾 Cached search results for 5 minutes")
            except Exception as e:
                logger.debug(f"Cache storage failed: {str(e)}")
        
        return article_dicts, total_count, has_more

    def _apply_filters(self, query, sentiment_filter=None, date_filter=None, 
                      region_filter=None, processing_filter='all'):
        """Apply filters efficiently using indexes"""
        
        # ALWAYS filter to only show articles with AI processing (both summary and insights)
        # This ensures users only see high-quality, AI-enhanced content
        query = query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_summary != '',
            NewsArticle.ai_insights != ''
        )
        
        # Sentiment filter
        if sentiment_filter:
            if sentiment_filter.upper() in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']:
                query = query.filter(NewsArticle.sentiment_label == sentiment_filter.lower())
            elif sentiment_filter.upper() in ['HIGHEST', 'LOWEST']:
                # Use indexed ai_sentiment_rating
                if sentiment_filter.upper() == 'HIGHEST':
                    query = query.filter(NewsArticle.ai_sentiment_rating >= 4)
                else:
                    query = query.filter(NewsArticle.ai_sentiment_rating <= 2)

        # Date filter
        if date_filter:
            try:
                from datetime import datetime, timedelta
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
                start_datetime = filter_date.replace(hour=0, minute=0, second=0)
                end_datetime = filter_date.replace(hour=23, minute=59, second=59)
                query = query.filter(NewsArticle.published_at.between(start_datetime, end_datetime))
            except ValueError:
                pass  # Invalid date format

        # Region filter using symbols and sources
        if region_filter:
            region_conditions = []
            
            # Get region-specific symbol patterns
            region_symbol_patterns = self._get_region_symbol_patterns(region_filter)
            if region_symbol_patterns:
                logger.debug(f"🏷️ Region {region_filter} symbol patterns: {region_symbol_patterns}")
                # Use EXISTS subquery to find articles with symbols matching region patterns
                symbol_subquery = self.session.query(ArticleSymbol.article_id).filter(
                    or_(*[ArticleSymbol.symbol.like(pattern) for pattern in region_symbol_patterns])
                ).subquery()
                region_conditions.append(NewsArticle.id.in_(symbol_subquery))
            
            # Source-based filtering as backup
            region_sources = self._get_region_sources(region_filter)
            if region_sources:
                region_conditions.append(NewsArticle.source.in_(region_sources))
            
            # Apply region conditions with OR logic
            if region_conditions:
                query = query.filter(or_(*region_conditions))

        return query

    def _apply_sorting(self, query, sort_order='LATEST'):
        """Apply sorting using indexed columns"""
        if sort_order == 'HIGHEST':
            return query.order_by(
                NewsArticle.ai_sentiment_rating.desc(),
                NewsArticle.published_at.desc()
            )
        elif sort_order == 'LOWEST':
            return query.order_by(
                NewsArticle.ai_sentiment_rating.asc(),
                NewsArticle.published_at.desc()
            )
        else:  # LATEST
            return query.order_by(NewsArticle.published_at.desc())

    def _get_region_symbol_patterns(self, region_filter):
        """Get symbol patterns for region filter including bare number formats for Investing.com compatibility"""
        region_patterns = {
            'CHINA': [
                '%.SS',      # Shanghai Stock Exchange (e.g., 600298.SS)
                '%.SZ',      # Shenzhen Stock Exchange (e.g., 000001.SZ)
                'SSE:%',     # TradingView Shanghai format (e.g., SSE:600298)
                'SZSE:%',    # TradingView Shenzhen format (e.g., SZSE:000001)
                '6%',        # Bare Chinese stock numbers starting with 6 (Shanghai)
                '0%',        # Bare Chinese stock numbers starting with 0 (Shenzhen)
                '3%',        # Bare Chinese stock numbers starting with 3 (Shenzhen)
            ],
            'HK': [
                '%.HK',      # Hong Kong Stock Exchange (e.g., 0700.HK)
                'HKEX:%',    # TradingView Hong Kong format (e.g., HKEX:700)
                '0%',        # Bare HK stock numbers (e.g., 0700, 0005)
                '1%',        # Bare HK stock numbers (e.g., 1398, 1299)
                '2%',        # Bare HK stock numbers (e.g., 2318)
                '3%',        # Bare HK stock numbers (e.g., 3988)
                '5%',        # Bare HK stock numbers (e.g., 5000)
                '6%',        # Bare HK stock numbers (e.g., 6823)
                '7%',        # Bare HK stock numbers (e.g., 7000)
                '8%',        # Bare HK stock numbers (e.g., 8000)
                '9%',        # Bare HK stock numbers (e.g., 9988)
            ],
            'US': [
                'NASDAQ:%',  # NASDAQ stocks
                'NYSE:%',    # NYSE stocks
                # Note: Plain symbols without exchange prefix are harder to identify as US
                # We could add specific US stock patterns if needed
            ],
        }
        return region_patterns.get(region_filter.upper(), [])

    def _get_region_sources(self, region_filter):
        """Get sources for region filter"""
        region_mapping = {
            'US': ['Bloomberg', 'CNBC', 'Reuters', 'WSJ', 'SeekingAlpha', 'Yahoo Finance', 'MarketWatch', 'Forbes', 'Barron\'s'],
            'CHINA': ['Xinhua', 'SCMP', 'Caixin', 'China Daily', 'Shanghai Daily', 'Global Times', 'People\'s Daily', 'China.org.cn'],
            'HK': ['HKEJ', 'SCMP', 'RTHK', 'South China Morning Post'],
        }
        return region_mapping.get(region_filter.upper(), [])

    def _build_cache_key(self, *args):
        """Build cache key from arguments"""
        return ':'.join(str(arg) for arg in args if arg is not None)

    def get_symbol_variants(self, symbol: str) -> List[str]:
        """Get all possible variants for a symbol, including bare number format for Investing.com compatibility"""
        import re
        variants = [symbol]
        
        # CRITICAL: Handle bare Chinese symbols (MAIN FIX for 600585 issue!)
        if re.match(r'^\d{6}$', symbol):  # 6-digit number like 600585
            if symbol.startswith('6'):  # Shanghai stocks
                variants.extend([f"SSE:{symbol}", f"{symbol}.SS"])
                logger.debug(f"🇨🇳 Bare Shanghai symbol detected: {symbol}, adding SSE variants")
            elif symbol.startswith(('0', '3')):  # Shenzhen stocks
                variants.extend([f"SZSE:{symbol}", f"{symbol}.SZ"])
                logger.debug(f"🇨🇳 Bare Shenzhen symbol detected: {symbol}, adding SZSE variants")
                
        # CRITICAL: Handle bare Hong Kong symbols
        elif re.match(r'^\d{3,5}$', symbol):  # 3-5 digit numbers like 700, 2318
            # Pad with zeros for HK format if needed
            if len(symbol) == 3:
                padded = "0" + symbol  # 700 -> 0700
            else:
                padded = symbol.zfill(4)  # General padding
            variants.extend([f"HKEX:{symbol}", f"HKEX:{padded}", f"{padded}.HK"])
            logger.debug(f"🇭🇰 Bare Hong Kong symbol detected: {symbol}, adding HK variants")
        
        # Enhanced gold symbol handling
        gold_symbols = ['COMEX:GC1!', 'COMEX:GC', 'TVC:GOLD', 'FXCM:GOLD', 'GC=F', 'XAUUSD', 'GOLD']
        if symbol.upper() in [s.upper() for s in gold_symbols] or 'GOLD' in symbol.upper() or 'GC' in symbol.upper():
            # Add all gold variants for comprehensive search
            variants.extend(gold_symbols)
            logger.debug(f"🥇 Gold symbol detected: {symbol}, adding variants: {gold_symbols}")
        
        # Enhanced silver symbol handling  
        silver_symbols = ['COMEX:SI1!', 'COMEX:SI', 'TVC:SILVER', 'FXCM:SILVER', 'SI=F', 'XAGUSD', 'SILVER']
        if symbol.upper() in [s.upper() for s in silver_symbols] or 'SILVER' in symbol.upper() or 'SI' in symbol.upper():
            variants.extend(silver_symbols)
            logger.debug(f"🥈 Silver symbol detected: {symbol}, adding variants: {silver_symbols}")
        
        # Add exchange prefixes for common symbols (only if not already handled above)
        if ':' not in symbol and not re.match(r'^\d+$', symbol):
            exchanges = ['NASDAQ', 'NYSE', 'HKEX', 'SSE', 'SZSE', 'LSE', 'TSE', 'COMEX', 'NYMEX', 'TVC', 'FXCM']
            for exchange in exchanges:
                variants.append(f"{exchange}:{symbol}")
        
        # Handle special conversions and ADD BARE NUMBER FORMAT for Investing.com compatibility
        if symbol.endswith('.HK'):
            base = symbol[:-3]
            variants.append(f"HKEX:{base}")
            variants.append(base)  # Add bare number format (e.g., "0700")
            logger.debug(f"🇭🇰 HK symbol detected: {symbol}, adding bare format: {base}")
        elif symbol.endswith('.SS'):
            base = symbol[:-3]
            variants.append(f"SSE:{base}")
            variants.append(base)  # Add bare number format (e.g., "600438")
            logger.debug(f"🇨🇳 Shanghai symbol detected: {symbol}, adding bare format: {base}")
        elif symbol.endswith('.SZ'):
            base = symbol[:-3]
            variants.append(f"SZSE:{base}")
            variants.append(base)  # Add bare number format (e.g., "000001")
            logger.debug(f"🇨🇳 Shenzhen symbol detected: {symbol}, adding bare format: {base}")
        elif symbol.endswith('.T'):
            base = symbol[:-2]
            variants.append(f"TSE:{base}")
            variants.append(base)  # Add bare number format (e.g., "7203")
            logger.debug(f"🇯🇵 Tokyo symbol detected: {symbol}, adding bare format: {base}")
        elif symbol.endswith('.L'):
            base = symbol[:-2]
            variants.append(f"LSE:{base}")
            variants.append(base)  # Add bare format (e.g., "SHEL")
            logger.debug(f"🇬🇧 London symbol detected: {symbol}, adding bare format: {base}")
        elif symbol.endswith('=F'):
            # Handle futures symbols
            base = symbol[:-2]
            variants.extend([f"COMEX:{base}", f"NYMEX:{base}", f"COMEX:{base}1!", f"NYMEX:{base}1!"])
        
        # CRITICAL: Handle TradingView format to bare number conversion
        # This is essential for finding Investing.com articles when searching with TradingView format
        if ':' in symbol:
            exchange, base = symbol.split(':', 1)
            if exchange.upper() in ['SSE', 'SZSE', 'HKEX', 'TSE', 'LSE']:
                variants.append(base)  # Add bare number format
                logger.debug(f"🔄 TradingView format detected: {symbol}, adding bare format: {base}")
            
        # Remove duplicates and return
        return list(set(variants))

    def clear_cache(self, pattern: str = None):
        """Clear search cache"""
        if self.cache_enabled:
            if pattern:
                self.cache.delete_pattern(pattern)
            else:
                self.cache.delete_pattern('symbol_search:*')