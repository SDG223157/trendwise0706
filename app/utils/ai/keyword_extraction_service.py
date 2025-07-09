"""
AI-Powered Keyword Extraction Service

This service analyzes news articles and extracts relevant keywords and concepts
for intelligent search suggestions using AI and NLP techniques.
"""

import logging
import re
import json
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime, timedelta
from collections import Counter
import requests
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk
from nltk.tree import Tree

from app import db
from app.models import NewsArticle, NewsKeyword, ArticleKeyword, KeywordSimilarity
from app.utils.cache.news_cache import NewsCache
import os

logger = logging.getLogger(__name__)

class KeywordExtractionService:
    """
    AI-powered service for extracting keywords and concepts from news articles.
    
    Features:
    - AI-based keyword extraction using OpenRouter API
    - Named Entity Recognition (NER)
    - Financial/market term identification
    - Semantic similarity calculation
    - Relevance scoring
    - Category classification
    """
    
    def __init__(self):
        self.cache = None
        self.stemmer = PorterStemmer()
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Initialize NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            nltk.download('maxent_ne_chunker', quiet=True)
            nltk.download('words', quiet=True)
        except Exception as e:
            logger.warning(f"NLTK download failed: {str(e)}")
        
        # Initialize cache
        try:
            self.cache = NewsCache()
        except Exception as e:
            logger.warning(f"Cache initialization failed: {str(e)}")
        
        # Financial/market terms for category detection
        self.financial_terms = {
            'earnings', 'revenue', 'profit', 'growth', 'decline', 'market', 'stock', 
            'shares', 'price', 'trading', 'valuation', 'forecast', 'guidance', 'outlook',
            'dividend', 'acquisition', 'merger', 'ipo', 'listing', 'financial', 'quarterly',
            'annual', 'results', 'performance', 'investment', 'investor', 'institutional',
            'retail', 'fund', 'portfolio', 'asset', 'liability', 'debt', 'equity',
            'capital', 'margin', 'volatility', 'risk', 'return', 'yield', 'bond',
            'commodity', 'futures', 'options', 'derivative', 'hedge', 'arbitrage'
        }
        
        # Technology terms
        self.technology_terms = {
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'neural network', 'algorithm', 'automation', 'robotics', 'blockchain',
            'cryptocurrency', 'bitcoin', 'ethereum', 'digital', 'cloud', 'saas',
            'software', 'hardware', 'semiconductor', 'chip', 'processor', 'gpu',
            'cpu', 'quantum', 'cybersecurity', 'data', 'analytics', 'big data',
            'iot', 'internet of things', 'mobile', 'app', 'platform', 'api',
            'infrastructure', 'network', 'connectivity', '5g', 'wireless'
        }
        
        # Industry terms
        self.industry_terms = {
            'automotive', 'electric vehicle', 'ev', 'autonomous', 'self-driving',
            'healthcare', 'pharmaceutical', 'biotech', 'medical', 'drug', 'vaccine',
            'energy', 'renewable', 'solar', 'wind', 'oil', 'gas', 'nuclear',
            'retail', 'e-commerce', 'consumer', 'fashion', 'luxury', 'brand',
            'manufacturing', 'industrial', 'aerospace', 'defense', 'construction',
            'real estate', 'property', 'hospitality', 'travel', 'airline',
            'telecommunications', 'media', 'entertainment', 'gaming', 'streaming'
        }
        
        # Stop words
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            self.stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    def extract_keywords_from_article(self, article: NewsArticle) -> List[Dict]:
        """
        Extract keywords from a single article using multiple techniques.
        
        Returns:
            List of keyword dictionaries with relevance scores and categories
        """
        if not article or not article.ai_summary:
            return []
        
        # Combine text sources
        text_sources = {
            'title': article.title or '',
            'ai_summary': article.ai_summary or '',
            'ai_insights': article.ai_insights or ''
        }
        
        # Extract keywords using different methods
        all_keywords = {}
        
        # 1. AI-powered extraction
        ai_keywords = self._extract_ai_keywords(text_sources)
        for keyword_data in ai_keywords:
            keyword = keyword_data['keyword'].lower()
            all_keywords[keyword] = keyword_data
        
        # 2. Named Entity Recognition
        ner_keywords = self._extract_ner_keywords(text_sources)
        for keyword_data in ner_keywords:
            keyword = keyword_data['keyword'].lower()
            if keyword in all_keywords:
                all_keywords[keyword]['relevance_score'] = max(
                    all_keywords[keyword]['relevance_score'],
                    keyword_data['relevance_score']
                )
            else:
                all_keywords[keyword] = keyword_data
        
        # 3. Financial term extraction
        financial_keywords = self._extract_financial_keywords(text_sources)
        for keyword_data in financial_keywords:
            keyword = keyword_data['keyword'].lower()
            if keyword in all_keywords:
                all_keywords[keyword]['relevance_score'] = max(
                    all_keywords[keyword]['relevance_score'],
                    keyword_data['relevance_score']
                )
            else:
                all_keywords[keyword] = keyword_data
        
        # 4. TF-IDF based extraction
        tfidf_keywords = self._extract_tfidf_keywords(text_sources, article.id)
        for keyword_data in tfidf_keywords:
            keyword = keyword_data['keyword'].lower()
            if keyword in all_keywords:
                all_keywords[keyword]['relevance_score'] = max(
                    all_keywords[keyword]['relevance_score'],
                    keyword_data['relevance_score']
                )
            else:
                all_keywords[keyword] = keyword_data
        
        # Filter and score keywords
        filtered_keywords = []
        for keyword, data in all_keywords.items():
            if (len(keyword) >= 2 and 
                keyword not in self.stop_words and 
                data['relevance_score'] > 0.1):
                filtered_keywords.append(data)
        
        # Sort by relevance and return top keywords
        filtered_keywords.sort(key=lambda x: x['relevance_score'], reverse=True)
        return filtered_keywords[:20]  # Limit to top 20 keywords per article
    
    def _extract_ai_keywords(self, text_sources: Dict[str, str]) -> List[Dict]:
        """Extract keywords using AI API"""
        try:
            if not self.openrouter_api_key:
                logger.warning("OpenRouter API key not available for AI keyword extraction")
                return []
            
            # Combine text
            combined_text = f"Title: {text_sources['title']}\n\nSummary: {text_sources['ai_summary']}\n\nInsights: {text_sources['ai_insights']}"
            
            prompt = f"""Analyze this financial news article and extract the most important keywords and concepts that users might search for.

Return ONLY a JSON array of objects with this exact format:
[
    {{"keyword": "keyword_text", "category": "category_name", "relevance": score}},
    ...
]

Categories should be one of: company, technology, financial, industry, concept, person, location
Relevance scores should be 0.0 to 1.0 (higher = more important for search)
Extract 5-15 keywords maximum.
Focus on searchable terms that users would actually type.

Article:
{combined_text[:8000]}"""

            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://trendwise.com",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "TrendWise AI Keyword Extraction"  # Optional. Site title for rankings on openrouter.ai.
            }
            
            data = {
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 750,  # Increased for DeepSeek V3's larger context
                "temperature": 0.1
            }
            
            response = requests.post(self.openrouter_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # Parse JSON response
                try:
                    # Extract JSON from response
                    json_start = content.find('[')
                    json_end = content.rfind(']') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        ai_keywords = json.loads(json_str)
                        
                        # Convert to our format
                        keywords = []
                        for item in ai_keywords:
                            if isinstance(item, dict) and 'keyword' in item:
                                keywords.append({
                                    'keyword': item['keyword'].strip(),
                                    'category': item.get('category', 'concept'),
                                    'relevance_score': float(item.get('relevance', 0.5)),
                                    'source': 'ai_extraction'
                                })
                        
                        logger.debug(f"Extracted {len(keywords)} AI keywords")
                        return keywords
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse AI keyword response: {str(e)}")
            
        except Exception as e:
            logger.warning(f"AI keyword extraction failed: {str(e)}")
        
        return []
    
    def _extract_ner_keywords(self, text_sources: Dict[str, str]) -> List[Dict]:
        """Extract named entities as keywords"""
        keywords = []
        
        try:
            # Combine text
            text = f"{text_sources['title']} {text_sources['ai_summary']} {text_sources['ai_insights']}"
            
            # Tokenize and tag
            tokens = word_tokenize(text)
            pos_tags = pos_tag(tokens)
            
            # Named entity recognition
            chunks = ne_chunk(pos_tags)
            
            entities = []
            for chunk in chunks:
                if isinstance(chunk, Tree):
                    entity = ' '.join([token for token, pos in chunk.leaves()])
                    entity_type = chunk.label()
                    entities.append((entity, entity_type))
            
            # Convert entities to keywords
            for entity, entity_type in entities:
                entity = entity.strip()
                if len(entity) >= 2 and entity.lower() not in self.stop_words:
                    category = 'company' if entity_type in ['ORGANIZATION', 'ORG'] else 'concept'
                    keywords.append({
                        'keyword': entity,
                        'category': category,
                        'relevance_score': 0.7,
                        'source': 'ner'
                    })
        
        except Exception as e:
            logger.warning(f"NER keyword extraction failed: {str(e)}")
        
        return keywords
    
    def _extract_financial_keywords(self, text_sources: Dict[str, str]) -> List[Dict]:
        """Extract financial and market-related keywords"""
        keywords = []
        
        # Combine text
        text = f"{text_sources['title']} {text_sources['ai_summary']} {text_sources['ai_insights']}".lower()
        
        # Check for financial terms
        for term in self.financial_terms:
            if term in text:
                # Calculate simple relevance based on frequency and position
                count = text.count(term)
                title_bonus = 0.2 if term in text_sources['title'].lower() else 0
                relevance = min(0.8, 0.3 + (count * 0.1) + title_bonus)
                
                keywords.append({
                    'keyword': term,
                    'category': 'financial',
                    'relevance_score': relevance,
                    'source': 'financial_terms'
                })
        
        # Check for technology terms
        for term in self.technology_terms:
            if term in text:
                count = text.count(term)
                title_bonus = 0.2 if term in text_sources['title'].lower() else 0
                relevance = min(0.8, 0.3 + (count * 0.1) + title_bonus)
                
                keywords.append({
                    'keyword': term,
                    'category': 'technology',
                    'relevance_score': relevance,
                    'source': 'technology_terms'
                })
        
        # Check for industry terms
        for term in self.industry_terms:
            if term in text:
                count = text.count(term)
                title_bonus = 0.2 if term in text_sources['title'].lower() else 0
                relevance = min(0.8, 0.3 + (count * 0.1) + title_bonus)
                
                keywords.append({
                    'keyword': term,
                    'category': 'industry',
                    'relevance_score': relevance,
                    'source': 'industry_terms'
                })
        
        return keywords
    
    def _extract_tfidf_keywords(self, text_sources: Dict[str, str], article_id: int) -> List[Dict]:
        """Extract keywords using TF-IDF-like scoring"""
        keywords = []
        
        try:
            # Combine text
            text = f"{text_sources['title']} {text_sources['ai_summary']} {text_sources['ai_insights']}"
            
            # Simple tokenization
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            
            # Filter stop words
            words = [word for word in words if word not in self.stop_words]
            
            # Count frequencies
            word_counts = Counter(words)
            
            # Calculate simple TF scores
            max_count = max(word_counts.values()) if word_counts else 1
            
            for word, count in word_counts.most_common(10):
                tf_score = count / max_count
                
                # Boost score if appears in title
                title_boost = 0.3 if word in text_sources['title'].lower() else 0
                
                relevance = min(0.9, tf_score + title_boost)
                
                if relevance > 0.2:
                    keywords.append({
                        'keyword': word,
                        'category': 'concept',
                        'relevance_score': relevance,
                        'source': 'tfidf'
                    })
        
        except Exception as e:
            logger.warning(f"TF-IDF keyword extraction failed: {str(e)}")
        
        return keywords
    
    def store_keywords(self, article: NewsArticle, keywords: List[Dict]) -> bool:
        """Store extracted keywords in the database"""
        try:
            for keyword_data in keywords:
                keyword_text = keyword_data['keyword'].strip()
                normalized_keyword = self.stemmer.stem(keyword_text.lower())
                category = keyword_data['category']
                relevance_score = keyword_data['relevance_score']
                
                # Get or create keyword
                keyword_obj = db.session.query(NewsKeyword).filter_by(
                    normalized_keyword=normalized_keyword,
                    category=category
                ).first()
                
                if keyword_obj:
                    # Update existing keyword
                    keyword_obj.frequency += 1
                    keyword_obj.last_seen = datetime.utcnow()
                    # Update relevance score (weighted average)
                    old_weight = keyword_obj.frequency - 1
                    keyword_obj.relevance_score = (
                        (keyword_obj.relevance_score * old_weight + relevance_score) / 
                        keyword_obj.frequency
                    )
                else:
                    # Create new keyword
                    keyword_obj = NewsKeyword(
                        keyword=keyword_text,
                        normalized_keyword=normalized_keyword,
                        category=category,
                        relevance_score=relevance_score,
                        frequency=1,
                        first_seen=datetime.utcnow(),
                        last_seen=datetime.utcnow()
                    )
                    db.session.add(keyword_obj)
                    db.session.flush()  # Get the ID
                
                # Create article-keyword relationship
                article_keyword = ArticleKeyword(
                    article_id=article.id,
                    keyword_id=keyword_obj.id,
                    relevance_in_article=relevance_score,
                    extraction_source=keyword_data.get('source', 'unknown')
                )
                db.session.add(article_keyword)
            
            db.session.commit()
            logger.debug(f"Stored {len(keywords)} keywords for article {article.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store keywords for article {article.id}: {str(e)}")
            db.session.rollback()
            return False
    
    def process_articles_batch(self, limit: int = 100, skip_processed: bool = True) -> Dict[str, int]:
        """Process a batch of articles for keyword extraction"""
        stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'keywords_extracted': 0
        }
        
        try:
            # Get articles that need processing
            query = db.session.query(NewsArticle).filter(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_summary != '',
                NewsArticle.ai_insights != ''
            )
            
            if skip_processed:
                # Skip articles that already have keywords
                processed_article_ids = db.session.query(ArticleKeyword.article_id).distinct()
                query = query.filter(~NewsArticle.id.in_(processed_article_ids))
            
            articles = query.limit(limit).all()
            
            logger.info(f"Processing {len(articles)} articles for keyword extraction")
            
            for article in articles:
                try:
                    # Extract keywords
                    keywords = self.extract_keywords_from_article(article)
                    
                    if keywords:
                        # Store keywords
                        if self.store_keywords(article, keywords):
                            stats['processed'] += 1
                            stats['keywords_extracted'] += len(keywords)
                        else:
                            stats['errors'] += 1
                    else:
                        stats['skipped'] += 1
                        logger.debug(f"No keywords extracted for article {article.id}")
                
                except Exception as e:
                    logger.error(f"Error processing article {article.id}: {str(e)}")
                    stats['errors'] += 1
            
            logger.info(f"Keyword extraction batch completed: {stats}")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            stats['errors'] = limit
        
        return stats
    
    def get_keyword_suggestions(self, query: str, limit: int = 10) -> List[Dict]:
        """Get intelligent keyword suggestions based on user input"""
        suggestions = []
        
        if not query or len(query) < 2:
            return suggestions
        
        query_lower = query.lower()
        
        try:
            # 1. Direct keyword matches
            direct_matches = db.session.query(NewsKeyword).filter(
                NewsKeyword.keyword.ilike(f'%{query}%')
            ).order_by(
                NewsKeyword.relevance_score.desc(),
                NewsKeyword.frequency.desc()
            ).limit(limit // 2).all()
            
            for keyword in direct_matches:
                suggestions.append({
                    'keyword': keyword.keyword,
                    'category': keyword.category,
                    'relevance_score': keyword.relevance_score,
                    'frequency': keyword.frequency,
                    'type': 'direct_match'
                })
            
            # 2. Semantic similarity matches (if we have similarity data)
            if len(suggestions) < limit:
                # Find keywords similar to query
                similar_keywords = self._find_similar_keywords(query_lower, limit - len(suggestions))
                suggestions.extend(similar_keywords)
            
            # 3. Category-based suggestions
            if len(suggestions) < limit:
                category_suggestions = self._get_category_suggestions(query_lower, limit - len(suggestions))
                suggestions.extend(category_suggestions)
            
        except Exception as e:
            logger.error(f"Error getting keyword suggestions: {str(e)}")
        
        return suggestions[:limit]
    
    def _find_similar_keywords(self, query: str, limit: int) -> List[Dict]:
        """Find keywords similar to the query"""
        suggestions = []
        
        try:
            # Simple similarity based on partial matching and stemming
            query_stem = self.stemmer.stem(query)
            
            similar_keywords = db.session.query(NewsKeyword).filter(
                NewsKeyword.normalized_keyword.ilike(f'%{query_stem}%')
            ).order_by(
                NewsKeyword.relevance_score.desc(),
                NewsKeyword.frequency.desc()
            ).limit(limit).all()
            
            for keyword in similar_keywords:
                suggestions.append({
                    'keyword': keyword.keyword,
                    'category': keyword.category,
                    'relevance_score': keyword.relevance_score,
                    'frequency': keyword.frequency,
                    'type': 'similar_match'
                })
        
        except Exception as e:
            logger.warning(f"Error finding similar keywords: {str(e)}")
        
        return suggestions
    
    def _get_category_suggestions(self, query: str, limit: int) -> List[Dict]:
        """Get suggestions based on category matching"""
        suggestions = []
        
        try:
            # Determine likely category of query
            category = self._classify_query_category(query)
            
            if category:
                category_keywords = db.session.query(NewsKeyword).filter(
                    NewsKeyword.category == category,
                    NewsKeyword.frequency >= 2  # Only suggest keywords that appear multiple times
                ).order_by(
                    NewsKeyword.relevance_score.desc(),
                    NewsKeyword.frequency.desc()
                ).limit(limit).all()
                
                for keyword in category_keywords:
                    suggestions.append({
                        'keyword': keyword.keyword,
                        'category': keyword.category,
                        'relevance_score': keyword.relevance_score,
                        'frequency': keyword.frequency,
                        'type': 'category_suggestion'
                    })
        
        except Exception as e:
            logger.warning(f"Error getting category suggestions: {str(e)}")
        
        return suggestions
    
    def _classify_query_category(self, query: str) -> Optional[str]:
        """Classify query into a category"""
        query_lower = query.lower()
        
        # Check against known term sets
        if any(term in query_lower for term in self.financial_terms):
            return 'financial'
        elif any(term in query_lower for term in self.technology_terms):
            return 'technology'
        elif any(term in query_lower for term in self.industry_terms):
            return 'industry'
        
        # Check for company patterns (all caps, common suffixes)
        if (query.isupper() and len(query) <= 5) or any(suffix in query_lower for suffix in ['inc', 'corp', 'ltd', 'llc']):
            return 'company'
        
        return 'concept'  # Default category
    
    def get_trending_keywords(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get trending keywords from recent articles"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get keywords from recent articles
            trending = db.session.query(
                NewsKeyword,
                db.func.count(ArticleKeyword.id).label('recent_count')
            ).join(ArticleKeyword).join(NewsArticle).filter(
                NewsArticle.created_at >= cutoff_date
            ).group_by(NewsKeyword.id).order_by(
                db.func.count(ArticleKeyword.id).desc(),
                NewsKeyword.relevance_score.desc()
            ).limit(limit).all()
            
            trending_keywords = []
            for keyword, recent_count in trending:
                trending_keywords.append({
                    'keyword': keyword.keyword,
                    'category': keyword.category,
                    'relevance_score': keyword.relevance_score,
                    'frequency': keyword.frequency,
                    'recent_count': recent_count,
                    'type': 'trending'
                })
            
            return trending_keywords
            
        except Exception as e:
            logger.error(f"Error getting trending keywords: {str(e)}")
            return []

# Global instance
keyword_extraction_service = KeywordExtractionService() 