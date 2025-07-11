# app/utils/search/optimized_news_search.py

from typing import List, Dict, Tuple
from sqlalchemy import or_, and_, func, desc, text
from sqlalchemy.orm import Session
from ...models import NewsSearchIndex
import json
import re
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class OptimizedNewsSearch:
    """
    ⚡ STANDALONE AI SEARCH ENGINE ⚡
    
    Ultra-fast news search using the standalone news_search_index table with AI content.
    
    ✅ NO JOINS REQUIRED - All data in one table for maximum performance
    ✅ AI-ONLY SEARCH - Only returns articles with AI summaries and insights
    ✅ ADVANCED CACHING - Intelligent Redis caching with popular search tracking
    ✅ OPTIMIZED INDEXES - Custom database indexes for lightning-fast queries
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.cache = None
        self.cache_enabled = False
        
        # Initialize advanced caching
        try:
            from ..cache.news_cache import NewsCache
            self.cache = NewsCache()
            self.cache_enabled = self.cache.is_available()
            if self.cache_enabled:
                logger.debug("✅ OptimizedNewsSearch: Redis cache enabled - TURBO MODE!")
            else:
                logger.debug("ℹ️ OptimizedNewsSearch: Running without cache")
        except Exception as e:
            logger.debug(f"Cache initialization failed: {str(e)}")

    def is_cache_available(self) -> bool:
        """Check if advanced caching is available"""
        return self.cache_enabled and self.cache and self.cache.is_available()

    def search_by_symbols(
        self,
        symbols: List[str] = None,
        sentiment_filter: str = None,
        sort_order: str = 'LATEST',
        date_filter: str = None,
        region_filter: str = None,
        processing_filter: str = 'all',
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict], int, bool]:
        """
        ⚡ STANDALONE AI SYMBOL SEARCH ⚡
        
        Ultra-fast symbol search using only the news_search_index table.
        All AI content is directly available without expensive joins.
        
        Returns: (articles, total_count, has_more)
        """
        cache_key = None
        
        # 🎯 SMART CACHING: Try cache first for instant results
        if self.is_cache_available():
            try:
                cache_key = self._build_cache_key(
                    'standalone_symbol', symbols, sentiment_filter, sort_order,
                    date_filter, region_filter, processing_filter, page, per_page
                )
                cached_result = self.cache.get_json(cache_key)
                if cached_result:
                    logger.debug("🚀 INSTANT CACHE HIT - Symbol search in <1ms!")
                    return cached_result['articles'], cached_result['total'], cached_result['has_more']
            except Exception as e:
                logger.debug(f"Cache lookup failed: {str(e)}")

        # 🎯 STANDALONE QUERY: Only news_search_index table, no joins!
        query = self.session.query(NewsSearchIndex)
        
        # ✅ AI-ONLY FILTER: Only articles with AI summaries and insights
        query = query.filter(
            NewsSearchIndex.ai_summary.isnot(None),
            NewsSearchIndex.ai_insights.isnot(None),
            NewsSearchIndex.ai_summary != '',
            NewsSearchIndex.ai_insights != ''
        )
        
        # 🎯 SYMBOL FILTER: Fast JSON search without joins
        if symbols:
            symbol_conditions = []
            for symbol in symbols:
                # Search in the symbols_json field for fast symbol matching
                symbol_conditions.append(
                    NewsSearchIndex.symbols_json.like(f'%"{symbol}"%')
                )
            query = query.filter(or_(*symbol_conditions))

        # Apply filters using indexed columns
        query = self._apply_standalone_filters(query, sentiment_filter, date_filter, region_filter)
        
        # Special handling for "latest" in symbol search (when no specific symbols provided)
        if not symbols and hasattr(self, '_has_latest_keyword') and self._has_latest_keyword:
            from datetime import datetime, timedelta
            three_days_ago = datetime.now() - timedelta(days=3)
            query = query.filter(NewsSearchIndex.published_at >= three_days_ago)
            sort_order = 'LATEST'  # Ensure latest first
            logger.debug(f"🕐 'Latest' detected in symbol search - filtering to last 3 days")
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply sorting and pagination
        query = self._apply_sorting(query, sort_order)
        articles = query.offset((page - 1) * per_page).limit(per_page + 1).all()
        
        has_more = len(articles) > per_page
        if has_more:
            articles = articles[:-1]

        # 🚀 INSTANT CONVERSION: All data already in search index
        article_dicts = [article.to_dict() for article in articles]

        # 💾 CACHE RESULTS: Store for future instant access
        if self.is_cache_available() and cache_key:
            try:
                cache_data = {
                    'articles': article_dicts,
                    'total': total_count,
                    'has_more': has_more,
                    'cached_at': datetime.now().isoformat()
                }
                # Longer cache for popular symbols
                cache_expire = 600 if symbols and len(symbols) == 1 else 300
                self.cache.set_json(cache_key, cache_data, expire=cache_expire)
                logger.debug(f"💾 Cached standalone symbol search for {cache_expire}s")
            except Exception as e:
                logger.debug(f"Cache storage failed: {str(e)}")

        # Track popular searches
        if symbols:
            for symbol in symbols:
                self.cache_popular_search(f"symbol:{symbol}", total_count)

        return article_dicts, total_count, has_more

    def search_by_keywords(
        self,
        keywords: List[str],
        sentiment_filter: str = None,
        sort_order: str = 'LATEST',
        date_filter: str = None,
        page: int = 1,
        per_page: int = 20,
        force_latest_filter: bool = False
    ) -> Tuple[List[Dict], int, bool]:
        """
        ⚡ STANDALONE AI KEYWORD SEARCH ⚡
        
        Ultra-fast keyword search using only AI summaries and insights.
        No raw content search - pure AI-curated results for maximum relevance.
        
        Returns: (articles, total_count, has_more)
        """
        cache_key = None
        
        # 🎯 SMART CACHING: Popular keywords get instant results
        if self.is_cache_available():
            try:
                cache_key = self._build_cache_key(
                    'standalone_keyword', keywords, sentiment_filter, sort_order,
                    date_filter, page, per_page
                )
                cached_result = self.cache.get_json(cache_key)
                if cached_result:
                    logger.debug("🚀 INSTANT CACHE HIT - Keyword search in <1ms!")
                    return cached_result['articles'], cached_result['total'], cached_result['has_more']
            except Exception as e:
                logger.debug(f"Cache lookup failed: {str(e)}")
        
        # 🎯 STANDALONE QUERY: Only news_search_index table with AI content
        query = self.session.query(NewsSearchIndex)
        
        # ✅ AI-ONLY FILTER: Only articles with complete AI processing
        query = query.filter(
            NewsSearchIndex.ai_summary.isnot(None),
            NewsSearchIndex.ai_insights.isnot(None),
            NewsSearchIndex.ai_summary != '',
            NewsSearchIndex.ai_insights != ''
        )
        
        # 🧠 AI-FIRST KEYWORD SEARCH: Search AI summaries and insights primarily
        if keywords:
            keyword_conditions = []
            special_keywords = ['latest', 'recent', 'news', 'breaking', 'new']
            sentiment_sort_keywords = ['highest', 'lowest']
            has_special_keyword = any(kw.lower() in special_keywords for kw in keywords)
            has_sentiment_sort_keyword = any(kw.lower() in sentiment_sort_keywords for kw in keywords)
            
            # Detect sentiment sorting keywords and update sort_order
            if has_sentiment_sort_keyword:
                for keyword in keywords:
                    if keyword.lower() == 'highest':
                        sort_order = 'HIGHEST'
                        logger.debug(f"🔝 Detected 'highest' keyword - sorting by highest AI sentiment rating")
                    elif keyword.lower() == 'lowest':
                        sort_order = 'LOWEST'
                        logger.debug(f"🔻 Detected 'lowest' keyword - sorting by lowest AI sentiment rating")
            
            # Special handling for "latest" and similar keywords OR forced latest filter
            if has_special_keyword or force_latest_filter:
                # Check if "latest" keyword is specifically used (or forced by search route)
                has_latest_keyword = any(kw.lower() == 'latest' for kw in keywords) or force_latest_filter
                
                if has_latest_keyword:
                    # For "latest" keyword, show articles from last 3 days
                    from datetime import datetime, timedelta
                    three_days_ago = datetime.now() - timedelta(days=3)
                    query = query.filter(
                        NewsSearchIndex.published_at >= three_days_ago
                    )
                    # Override sort_order to ensure latest first
                    sort_order = 'LATEST'
                    logger.debug(f"🕐 'Latest' keyword detected (force_latest_filter={force_latest_filter}) - filtering to last 3 days and sorting by date")
                else:
                    # For other special keywords, use relaxed AI filtering
                    query = query.filter(
                        or_(
                            and_(
                                NewsSearchIndex.ai_summary.isnot(None),
                                NewsSearchIndex.ai_summary != ''
                            ),
                            NewsSearchIndex.title.isnot(None)  # Allow articles with just title
                        )
                    )
                    logger.debug(f"🕐 Special keyword detected, using relaxed AI filtering")
            else:
                # Normal AI-only filtering for other keywords
                pass  # Keep existing AI filtering
            
            for keyword in keywords:
                # Skip sentiment sorting keywords from content search
                if keyword.lower() in sentiment_sort_keywords:
                    logger.debug(f"🔄 Skipping sentiment sort keyword '{keyword}' from content search")
                    continue
                    
                if '"' in keyword:  # Exact phrase match
                    phrase = keyword.replace('"', '')
                    keyword_conditions.append(
                        or_(
                            NewsSearchIndex.title.like(f'%{phrase}%'),
                            NewsSearchIndex.ai_summary.like(f'%{phrase}%'),
                            NewsSearchIndex.ai_insights.like(f'%{phrase}%')
                        )
                    )
                else:  # Individual word match
                    # For special keywords like "latest", search mainly in title
                    if keyword.lower() in special_keywords:
                        keyword_conditions.append(
                            or_(
                                NewsSearchIndex.title.like(f'%{keyword}%'),
                                NewsSearchIndex.source.like(f'%{keyword}%')
                            )
                        )
                        logger.debug(f"🕐 Special keyword '{keyword}' - searching title/source")
                    else:
                        keyword_conditions.append(
                            or_(
                                NewsSearchIndex.title.like(f'%{keyword}%'),
                                NewsSearchIndex.ai_summary.like(f'%{keyword}%'),
                                NewsSearchIndex.ai_insights.like(f'%{keyword}%')
                            )
                        )
            
            if keyword_conditions:
                query = query.filter(and_(*keyword_conditions))

        # Apply filters
        query = self._apply_standalone_filters(query, sentiment_filter, date_filter)
        
        # Get results with pagination
        total_count = query.count()
        query = self._apply_sorting(query, sort_order)
        articles = query.offset((page - 1) * per_page).limit(per_page + 1).all()
        
        has_more = len(articles) > per_page
        if has_more:
            articles = articles[:-1]

        # 🚀 INSTANT CONVERSION: All AI data already available
        article_dicts = [article.to_dict() for article in articles]
        
        # 💾 INTELLIGENT CACHING: Popular keywords cached longer
        if self.is_cache_available() and cache_key:
            try:
                cache_data = {
                    'articles': article_dicts,
                    'total': total_count,
                    'has_more': has_more,
                    'cached_at': datetime.now().isoformat()
                }
                # Smart cache duration based on keyword popularity
                cache_expire = 600 if keywords and any(kw.lower() in ['latest', 'earnings', 'ai', 'technology', 'tesla', 'apple', 'bitcoin'] for kw in keywords) else 300
                self.cache.set_json(cache_key, cache_data, expire=cache_expire)
                logger.debug(f"💾 Cached standalone keyword search for {cache_expire}s")
            except Exception as e:
                logger.debug(f"Cache storage failed: {str(e)}")
        
        # Track popular keywords
        if keywords:
            for keyword in keywords:
                self.cache_popular_search(f"keyword:{keyword}", total_count)
        
        return article_dicts, total_count, has_more

    def get_recent_news(
        self,
        limit: int = 10,
        hours: int = 24,
        sentiment_filter: str = None
    ) -> List[Dict]:
        """
        ⚡ STANDALONE RECENT NEWS ⚡
        
        Get recent AI-enhanced news efficiently from standalone search index.
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        query = self.session.query(NewsSearchIndex).filter(
            NewsSearchIndex.published_at >= cutoff_time,
            # Only AI-enhanced articles
            NewsSearchIndex.ai_summary.isnot(None),
            NewsSearchIndex.ai_insights.isnot(None),
            NewsSearchIndex.ai_summary != '',
            NewsSearchIndex.ai_insights != ''
        )
        
        if sentiment_filter:
            query = self._apply_sentiment_filter_standalone(query, sentiment_filter)
        
        articles = query.order_by(desc(NewsSearchIndex.published_at)).limit(limit).all()
        
        return [article.to_dict() for article in articles]

    def advanced_search(
        self,
        keywords: List[str] = None,
        symbols: List[str] = None,
        sentiment: str = None,
        start_date: str = None,
        end_date: str = None,
        sources: List[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict], int]:
        """
        ⚡ STANDALONE ADVANCED SEARCH ⚡
        
        Advanced search with multiple filters using only the search index.
        """
        query = self.session.query(NewsSearchIndex)

        # ✅ AI-ONLY FILTER: Only complete AI-enhanced articles
        query = query.filter(
            NewsSearchIndex.ai_summary.isnot(None),
            NewsSearchIndex.ai_insights.isnot(None),
            NewsSearchIndex.ai_summary != '',
            NewsSearchIndex.ai_insights != ''
        )

        # AI-focused keyword search
        if keywords:
            keyword_filters = []
            for keyword in keywords:
                if '"' in keyword:  # Exact phrase match
                    phrase = keyword.replace('"', '')
                    keyword_filters.append(
                        or_(
                            NewsSearchIndex.title.like(f"%{phrase}%"),
                            NewsSearchIndex.ai_summary.like(f"%{phrase}%"),
                            NewsSearchIndex.ai_insights.like(f"%{phrase}%")
                        )
                    )
                else:  # Individual word match
                    keyword_filters.append(or_(
                        NewsSearchIndex.title.like(f"%{keyword}%"),
                        NewsSearchIndex.ai_summary.like(f"%{keyword}%"),
                        NewsSearchIndex.ai_insights.like(f"%{keyword}%")
                    ))
            query = query.filter(and_(*keyword_filters))

        # Symbol filter using JSON search
        if symbols:
            symbol_conditions = []
            for symbol in symbols:
                symbol_conditions.append(
                    NewsSearchIndex.symbols_json.like(f'%"{symbol}"%')
                )
            query = query.filter(or_(*symbol_conditions))

        # Apply other filters
        if sentiment:
            if sentiment.upper() in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']:
                # Map to AI sentiment rating for faster search
                sentiment_map = {'POSITIVE': [4, 5], 'NEGATIVE': [1, 2], 'NEUTRAL': [3]}
                rating_values = sentiment_map.get(sentiment.upper(), [])
                if rating_values:
                    query = query.filter(NewsSearchIndex.ai_sentiment_rating.in_(rating_values))

        if start_date:
            query = query.filter(NewsSearchIndex.published_at >= start_date)
        if end_date:
            query = query.filter(NewsSearchIndex.published_at <= end_date)

        if sources:
            query = query.filter(NewsSearchIndex.source.in_(sources))

        # Get total count and apply pagination
        total_count = query.count()
        query = query.order_by(desc(NewsSearchIndex.published_at))
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Convert to dict
        articles = [article.to_dict() for article in query.all()]
        
        return articles, total_count

    def _apply_standalone_filters(self, query, sentiment_filter=None, date_filter=None, region_filter=None):
        """Apply filters using only NewsSearchIndex table columns"""
        
        # Sentiment filter using AI sentiment rating (indexed)
        if sentiment_filter:
            if sentiment_filter.upper() == 'POSITIVE':
                query = query.filter(NewsSearchIndex.ai_sentiment_rating >= 4)
            elif sentiment_filter.upper() == 'NEGATIVE':
                query = query.filter(NewsSearchIndex.ai_sentiment_rating <= 2)
            elif sentiment_filter.upper() == 'NEUTRAL':
                query = query.filter(NewsSearchIndex.ai_sentiment_rating == 3)
            elif sentiment_filter.upper() == 'HIGHEST':
                query = query.filter(NewsSearchIndex.ai_sentiment_rating == 5)
            elif sentiment_filter.upper() == 'LOWEST':
                query = query.filter(NewsSearchIndex.ai_sentiment_rating == 1)

        # Date filter
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
                start_datetime = filter_date.replace(hour=0, minute=0, second=0)
                end_datetime = filter_date.replace(hour=23, minute=59, second=59)
                query = query.filter(NewsSearchIndex.published_at.between(start_datetime, end_datetime))
            except ValueError:
                pass  # Invalid date format

        # Region filter using symbols_json and source
        if region_filter:
            region_conditions = []
            
            # Get region-specific symbol patterns and search in JSON
            region_patterns = self._get_region_symbol_patterns(region_filter)
            if region_patterns:
                for pattern in region_patterns:
                    region_conditions.append(NewsSearchIndex.symbols_json.like(f'%{pattern}%'))
            
            # Source-based filtering
            region_sources = self._get_region_sources(region_filter)
            if region_sources:
                region_conditions.append(NewsSearchIndex.source.in_(region_sources))
            
            if region_conditions:
                query = query.filter(or_(*region_conditions))

        return query

    def _apply_sentiment_filter_standalone(self, query, sentiment_filter):
        """Apply sentiment filter using AI sentiment rating"""
        if sentiment_filter.upper() == 'POSITIVE':
            return query.filter(NewsSearchIndex.ai_sentiment_rating >= 4)
        elif sentiment_filter.upper() == 'NEGATIVE':
            return query.filter(NewsSearchIndex.ai_sentiment_rating <= 2)
        elif sentiment_filter.upper() == 'NEUTRAL':
            return query.filter(NewsSearchIndex.ai_sentiment_rating == 3)
        return query

    def _apply_sorting(self, query, sort_order='LATEST'):
        """Apply sorting using indexed columns"""
        if sort_order == 'HIGHEST':
            return query.order_by(
                NewsSearchIndex.ai_sentiment_rating.desc(),
                NewsSearchIndex.published_at.desc()
            )
        elif sort_order == 'LOWEST':
            return query.order_by(
                NewsSearchIndex.ai_sentiment_rating.asc(),
                NewsSearchIndex.published_at.desc()
            )
        else:  # LATEST
            return query.order_by(NewsSearchIndex.published_at.desc())

    def _get_region_symbol_patterns(self, region_filter):
        """Get comprehensive symbol patterns for region filtering"""
        region_patterns = {
            'CHINA': [
                # TradingView formats
                'SSE:', 'SZSE:',
                # Yahoo Finance formats  
                '.SS', '.SZ',
                # Bare number formats (common in Investing.com)
                '"6', '"00', '"30',  # JSON patterns for bare numbers
                # Combined patterns
                'SSE:6', 'SZSE:0', 'SZSE:3'
            ],
            'HK': [
                # TradingView formats
                'HKEX:',
                # Yahoo Finance formats
                '.HK',
                # Bare number formats (common in Investing.com)
                '"0', '"1', '"2', '"3', '"5', '"6', '"7', '"8', '"9',  # JSON patterns
                # Combined patterns
                'HKEX:0', 'HKEX:1', 'HKEX:2', 'HKEX:3', 'HKEX:5', 'HKEX:6', 'HKEX:7', 'HKEX:8', 'HKEX:9'
            ],
            'US': [
                # TradingView formats
                'NASDAQ:', 'NYSE:', 'AMEX:',
                # Note: US stocks don't have reliable number patterns
                # They use ticker symbols (AAPL, MSFT, etc.)
            ],
            'UK': [
                'LSE:', '.L', '.LN'
            ],
            'JP': [
                'TSE:', '.T', '.TO'
            ]
        }
        return region_patterns.get(region_filter.upper(), [])

    def _get_region_sources(self, region_filter):
        """Get comprehensive sources associated with specific regions"""
        region_sources = {
            'CHINA': [
                'China Daily', 'Xinhua', 'Global Times', 'SCMP', 
                'Caixin', 'Shanghai Daily', 'People\'s Daily',
                'China.org.cn', 'Sina Finance', 'Eastmoney',
                'Securities Times', 'China Securities Journal',
                '中国日报', '新华社', '环球时报'  # Chinese sources
            ],
            'HK': [
                'SCMP', 'South China Morning Post', 'Hong Kong Free Press',
                'HKEJ', 'Hong Kong Economic Journal', 'RTHK',
                'Ming Pao', 'Apple Daily', 'Oriental Daily',
                'AAStocks', 'ET Net', 'HK01', 'The Standard'
            ],
            'US': [
                'Reuters', 'Bloomberg', 'CNBC', 'Wall Street Journal',
                'MarketWatch', 'Yahoo Finance', 'Forbes', 'Fortune',
                'CNN Business', 'Fox Business', 'Seeking Alpha',
                'The Motley Fool', 'Investor\'s Business Daily', 'Barron\'s',
                'Associated Press', 'NPR', 'USA Today', 'Washington Post'
            ],
            'UK': [
                'BBC', 'Financial Times', 'Guardian', 'Telegraph',
                'Sky News', 'Independent', 'Evening Standard',
                'City AM', 'This is Money', 'The Times', 'Reuters UK'
            ],
            'JP': [
                'Nikkei', 'Japan Times', 'Kyodo News', 'NHK',
                'Asahi Shimbun', 'Mainichi Shimbun', 'Yomiuri Shimbun',
                'Japan Today', 'Tokyo Shimbun'
            ]
        }
        return region_sources.get(region_filter.upper(), [])

    def _build_cache_key(self, search_type, *args):
        """Build cache key for search results"""
        # Convert all arguments to strings and create hash-like key
        key_parts = [search_type] + [str(arg) for arg in args if arg is not None]
        return f"standalone_search:{'_'.join(key_parts)}"

    def cache_popular_search(self, search_term: str, result_count: int):
        """Track popular searches for optimization"""
        if self.is_cache_available():
            try:
                cache_key = f"popular_search:{search_term}"
                current_count = self.cache.get(cache_key) or 0
                self.cache.set(cache_key, int(current_count) + 1, expire=86400)  # 24 hour tracking
            except Exception as e:
                logger.debug(f"Failed to track popular search: {str(e)}")

    def get_search_stats(self) -> Dict:
        """Get comprehensive search statistics"""
        try:
            stats = {
                'total_ai_articles': self.session.query(NewsSearchIndex).filter(
                    NewsSearchIndex.ai_summary.isnot(None),
                    NewsSearchIndex.ai_insights.isnot(None),
                    NewsSearchIndex.ai_summary != '',
                    NewsSearchIndex.ai_insights != ''
                ).count(),
                'recent_ai_articles': self.session.query(NewsSearchIndex).filter(
                    NewsSearchIndex.published_at >= datetime.now() - timedelta(days=7),
                    NewsSearchIndex.ai_summary.isnot(None),
                    NewsSearchIndex.ai_insights.isnot(None),
                    NewsSearchIndex.ai_summary != '',
                    NewsSearchIndex.ai_insights != ''
                ).count(),
                'unique_sources': self.session.query(NewsSearchIndex.source).distinct().count(),
                'oldest_ai_article': self.session.query(func.min(NewsSearchIndex.published_at)).filter(
                    NewsSearchIndex.ai_summary.isnot(None)
                ).scalar(),
                'newest_ai_article': self.session.query(func.max(NewsSearchIndex.published_at)).filter(
                    NewsSearchIndex.ai_summary.isnot(None)
                ).scalar(),
                'cache_enabled': self.cache_enabled,
                'search_mode': 'STANDALONE_AI_SEARCH',
                'last_updated': datetime.now().isoformat()
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting search stats: {str(e)}")
            return {'error': str(e)}

    def clear_cache(self, pattern: str = None):
        """Clear search cache intelligently"""
        if self.cache_enabled:
            if pattern:
                self.cache.delete_pattern(pattern)
            else:
                # Clear standalone search caches
                patterns = [
                    'standalone_search:*',
                    'standalone_symbol:*', 
                    'standalone_keyword:*',
                    'popular_search:*'
                ]
                for pattern in patterns:
                    self.cache.delete_pattern(pattern)
                logger.info("🧹 Cleared all standalone search caches") 