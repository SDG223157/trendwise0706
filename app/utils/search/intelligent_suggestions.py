"""
Intelligent Search Suggestions Service

This service provides AI-powered search suggestions based on user input,
combining keyword extraction, semantic similarity, and user behavior analytics.
"""

import logging
import json
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import func, desc, and_, or_
from fuzzywuzzy import fuzz

from app import db
from app.models import (
    NewsKeyword, ArticleKeyword, NewsArticle, ArticleSymbol,
    SearchAnalytics, KeywordSimilarity, NewsSearchIndex
)
from app.utils.ai.keyword_extraction_service import keyword_extraction_service
from app.utils.cache.news_cache import NewsCache
from app.utils.search.acronym_expansion import acronym_expansion_service
import uuid

logger = logging.getLogger(__name__)

class IntelligentSuggestionService:
    """
    AI-powered search suggestion service with multiple suggestion strategies.
    
    Features:
    - Real-time keyword suggestions
    - Semantic similarity matching
    - User behavior analysis
    - Trending topics detection
    - Symbol and company name suggestions
    - Context-aware recommendations
    """
    
    def __init__(self):
        self.cache = None
        self.min_suggestion_relevance = 0.3
        self.max_suggestions = 10
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize cache
        try:
            self.cache = NewsCache()
        except Exception as e:
            logger.warning(f"Cache initialization failed: {str(e)}")
    
    def get_search_suggestions(
        self,
        query: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        limit: int = 10,
        include_context: bool = True
    ) -> List[Dict]:
        """
        Get intelligent search suggestions based on user input.
        
        Args:
            query: User's search query
            user_id: Optional user ID for personalization
            session_id: Browser session ID
            limit: Maximum number of suggestions
            include_context: Whether to include context information
            
        Returns:
            List of suggestion dictionaries with metadata
        """
        if not query or len(query.strip()) < 2:
            return self._get_popular_suggestions(limit)
        
        query = query.strip()
        
        # Check cache first
        cache_key = f"search_suggestions:{query.lower()}:{limit}"
        if self.cache:
            try:
                cached_suggestions = self.cache.get_json(cache_key)
                if cached_suggestions:
                    logger.debug(f"Cache hit for suggestions: {query}")
                    return self._add_suggestion_context(cached_suggestions, include_context)
            except Exception as e:
                logger.debug(f"Cache lookup failed: {str(e)}")
        
        # Generate suggestions using multiple strategies
        suggestions = []
        
        # 1. 🔑 ACRONYM EXPANSION: Handle short forms like "fed" → "federal reserve"
        acronym_suggestions = self._get_acronym_suggestions(query, limit // 3)
        suggestions.extend(acronym_suggestions)
        
        # 2. Keyword-based suggestions
        keyword_suggestions = self._get_keyword_suggestions(query, limit // 3)
        suggestions.extend(keyword_suggestions)
        
        # 3. Symbol suggestions
        symbol_suggestions = self._get_symbol_suggestions(query, limit // 6)
        suggestions.extend(symbol_suggestions)
        
        # 4. Semantic similarity suggestions
        semantic_suggestions = self._get_semantic_suggestions(query, limit // 6)
        suggestions.extend(semantic_suggestions)
        
        # 5. User behavior suggestions (if user_id provided)
        if user_id:
            user_suggestions = self._get_user_behavior_suggestions(query, user_id, limit // 6)
            suggestions.extend(user_suggestions)
        
        # 6. Trending suggestions
        trending_suggestions = self._get_trending_suggestions(query, limit // 6)
        suggestions.extend(trending_suggestions)
        
        # Remove duplicates and rank
        suggestions = self._deduplicate_and_rank(suggestions, limit)
        
        # Cache results
        if self.cache:
            try:
                self.cache.set_json(cache_key, suggestions, expire=self.cache_ttl)
            except Exception as e:
                logger.debug(f"Cache storage failed: {str(e)}")
        
        # Track analytics
        self._track_suggestion_request(query, user_id, session_id, len(suggestions))
        
        return self._add_suggestion_context(suggestions, include_context)
    
    def _get_acronym_suggestions(self, query: str, limit: int) -> List[Dict]:
        """Get suggestions based on acronym expansion"""
        suggestions = []
        
        try:
            # Use the acronym expansion service
            acronym_suggestions = acronym_expansion_service.get_acronym_suggestions(query, limit)
            
            # Add priority boost for acronym suggestions
            for suggestion in acronym_suggestions:
                suggestion['relevance_score'] = min(1.0, suggestion['relevance_score'] + 0.1)
                suggestions.append(suggestion)
                
            logger.info(f"Acronym expansion for '{query}': {len(suggestions)} suggestions")
            
        except Exception as e:
            logger.warning(f"Acronym suggestions failed: {str(e)}")
        
        return suggestions
    
    def _get_keyword_suggestions(self, query: str, limit: int) -> List[Dict]:
        """Get suggestions based on keyword matching"""
        suggestions = []
        
        try:
            # Use the keyword extraction service
            keyword_suggestions = keyword_extraction_service.get_keyword_suggestions(query, limit)
            
            for suggestion in keyword_suggestions:
                suggestions.append({
                    'text': suggestion['keyword'],
                    'type': 'keyword',
                    'category': suggestion['category'],
                    'relevance_score': suggestion['relevance_score'],
                    'frequency': suggestion['frequency'],
                    'source': 'keyword_extraction'
                })
        
        except Exception as e:
            logger.warning(f"Keyword suggestions failed: {str(e)}")
        
        return suggestions
    
    def _get_symbol_suggestions(self, query: str, limit: int) -> List[Dict]:
        """Get stock symbol suggestions"""
        suggestions = []
        
        try:
            query_upper = query.upper()
            
            # Direct symbol matches
            symbol_matches = db.session.query(
                ArticleSymbol.symbol,
                func.count(ArticleSymbol.article_id).label('article_count')
            ).filter(
                ArticleSymbol.symbol.ilike(f'%{query_upper}%')
            ).group_by(ArticleSymbol.symbol).order_by(
                func.count(ArticleSymbol.article_id).desc()
            ).limit(limit).all()
            
            for symbol, count in symbol_matches:
                suggestions.append({
                    'text': symbol,
                    'type': 'symbol',
                    'category': 'company',
                    'relevance_score': min(0.9, 0.5 + (count / 100)),
                    'frequency': count,
                    'source': 'symbol_match'
                })
        
        except Exception as e:
            logger.warning(f"Symbol suggestions failed: {str(e)}")
        
        return suggestions
    
    def _get_semantic_suggestions(self, query: str, limit: int) -> List[Dict]:
        """Get suggestions based on semantic similarity"""
        suggestions = []
        
        try:
            # Get similar keywords using fuzzy matching
            similar_keywords = db.session.query(NewsKeyword).filter(
                NewsKeyword.frequency >= 3  # Only suggest frequently used keywords
            ).all()
            
            # Calculate fuzzy similarity scores
            scored_keywords = []
            for keyword in similar_keywords:
                similarity = fuzz.ratio(query.lower(), keyword.keyword.lower())
                if similarity > 60:  # Threshold for similarity
                    scored_keywords.append((keyword, similarity))
            
            # Sort by similarity and relevance
            scored_keywords.sort(key=lambda x: (x[1], x[0].relevance_score), reverse=True)
            
            for keyword, similarity in scored_keywords[:limit]:
                suggestions.append({
                    'text': keyword.keyword,
                    'type': 'semantic',
                    'category': keyword.category,
                    'relevance_score': keyword.relevance_score,
                    'frequency': keyword.frequency,
                    'similarity': similarity / 100,
                    'source': 'semantic_match'
                })
        
        except Exception as e:
            logger.warning(f"Semantic suggestions failed: {str(e)}")
        
        return suggestions
    
    def _get_user_behavior_suggestions(self, query: str, user_id: int, limit: int) -> List[Dict]:
        """Get personalized suggestions based on user behavior"""
        suggestions = []
        
        try:
            # Get user's recent searches
            recent_searches = db.session.query(SearchAnalytics).filter(
                SearchAnalytics.user_id == user_id,
                SearchAnalytics.created_at >= datetime.utcnow() - timedelta(days=30)
            ).order_by(desc(SearchAnalytics.created_at)).limit(50).all()
            
            # Extract keywords from successful searches
            successful_keywords = set()
            for search in recent_searches:
                if search.result_clicked and search.selected_keywords:
                    try:
                        keywords = json.loads(search.selected_keywords)
                        successful_keywords.update(keywords)
                    except:
                        pass
            
            # Find similar keywords to user's successful searches
            if successful_keywords:
                similar_user_keywords = db.session.query(NewsKeyword).filter(
                    NewsKeyword.keyword.in_(successful_keywords)
                ).all()
                
                for keyword in similar_user_keywords:
                    if fuzz.ratio(query.lower(), keyword.keyword.lower()) > 40:
                        suggestions.append({
                            'text': keyword.keyword,
                            'type': 'personalized',
                            'category': keyword.category,
                            'relevance_score': keyword.relevance_score,
                            'frequency': keyword.frequency,
                            'source': 'user_behavior'
                        })
        
        except Exception as e:
            logger.warning(f"User behavior suggestions failed: {str(e)}")
        
        return suggestions
    
    def _get_trending_suggestions(self, query: str, limit: int) -> List[Dict]:
        """Get trending keyword suggestions"""
        suggestions = []
        
        try:
            trending_keywords = keyword_extraction_service.get_trending_keywords(days=7, limit=20)
            
            for trend in trending_keywords:
                if fuzz.ratio(query.lower(), trend['keyword'].lower()) > 30:
                    suggestions.append({
                        'text': trend['keyword'],
                        'type': 'trending',
                        'category': trend['category'],
                        'relevance_score': trend['relevance_score'],
                        'frequency': trend['frequency'],
                        'recent_count': trend['recent_count'],
                        'source': 'trending'
                    })
        
        except Exception as e:
            logger.warning(f"Trending suggestions failed: {str(e)}")
        
        return suggestions
    
    def _get_popular_suggestions(self, limit: int) -> List[Dict]:
        """Get popular suggestions when no query is provided"""
        suggestions = []
        
        try:
            # Get most frequently used keywords
            popular_keywords = db.session.query(NewsKeyword).filter(
                NewsKeyword.frequency >= 5
            ).order_by(
                NewsKeyword.frequency.desc(),
                NewsKeyword.relevance_score.desc()
            ).limit(limit).all()
            
            for keyword in popular_keywords:
                suggestions.append({
                    'text': keyword.keyword,
                    'type': 'popular',
                    'category': keyword.category,
                    'relevance_score': keyword.relevance_score,
                    'frequency': keyword.frequency,
                    'source': 'popular'
                })
        
        except Exception as e:
            logger.warning(f"Popular suggestions failed: {str(e)}")
        
        return suggestions
    
    def _deduplicate_and_rank(self, suggestions: List[Dict], limit: int) -> List[Dict]:
        """Remove duplicates and rank suggestions"""
        seen = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            text_lower = suggestion['text'].lower()
            if text_lower not in seen:
                seen.add(text_lower)
                unique_suggestions.append(suggestion)
        
        # Sort by relevance score, frequency, and type priority
        type_priority = {
            'acronym_expansion': 7,     # Highest priority for acronym expansions
            'related_term': 6,          # High priority for related terms
            'keyword': 5,
            'symbol': 4,
            'trending': 3,
            'personalized': 2,
            'semantic': 1,
            'popular': 0
        }
        
        unique_suggestions.sort(
            key=lambda x: (
                type_priority.get(x['type'], 0),
                x['relevance_score'],
                x['frequency']
            ),
            reverse=True
        )
        
        return unique_suggestions[:limit]
    
    def _add_suggestion_context(self, suggestions: List[Dict], include_context: bool) -> List[Dict]:
        """Add context information to suggestions"""
        if not include_context:
            return suggestions
        
        for suggestion in suggestions:
            try:
                # Add article count for this keyword
                keyword = suggestion['text']
                
                if suggestion['type'] == 'symbol':
                    # For symbols, count articles
                    article_count = db.session.query(func.count(ArticleSymbol.article_id)).filter(
                        ArticleSymbol.symbol == keyword
                    ).scalar()
                    suggestion['article_count'] = article_count
                else:
                    # For keywords, count articles containing this keyword
                    article_count = db.session.query(func.count(NewsSearchIndex.id)).filter(
                        or_(
                            NewsSearchIndex.title.ilike(f'%{keyword}%'),
                            NewsSearchIndex.ai_summary.ilike(f'%{keyword}%'),
                            NewsSearchIndex.ai_insights.ilike(f'%{keyword}%')
                        )
                    ).scalar()
                    suggestion['article_count'] = article_count
                
                # Add recent activity indicator
                recent_count = db.session.query(func.count(NewsSearchIndex.id)).filter(
                    NewsSearchIndex.created_at >= datetime.utcnow() - timedelta(days=7),
                    or_(
                        NewsSearchIndex.title.ilike(f'%{keyword}%'),
                        NewsSearchIndex.ai_summary.ilike(f'%{keyword}%'),
                        NewsSearchIndex.ai_insights.ilike(f'%{keyword}%')
                    )
                ).scalar()
                suggestion['recent_activity'] = recent_count
                
            except Exception as e:
                logger.debug(f"Error adding context to suggestion: {str(e)}")
                suggestion['article_count'] = 0
                suggestion['recent_activity'] = 0
        
        return suggestions
    
    def _track_suggestion_request(
        self,
        query: str,
        user_id: Optional[int],
        session_id: Optional[str],
        suggestions_count: int
    ):
        """Track suggestion request for analytics"""
        try:
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # This could be expanded to track suggestion requests
            # For now, we'll just log it
            logger.debug(f"Suggestion request: query='{query}', user_id={user_id}, "
                        f"session_id={session_id}, suggestions={suggestions_count}")
            
        except Exception as e:
            logger.debug(f"Error tracking suggestion request: {str(e)}")
    
    def track_suggestion_click(
        self,
        query: str,
        selected_suggestion: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ):
        """Track when a user clicks on a suggestion"""
        try:
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Store in search analytics
            analytics = SearchAnalytics(
                user_id=user_id,
                session_id=session_id,
                search_query=query,
                search_type='suggestion_click',
                selected_keywords=json.dumps([selected_suggestion]),
                result_clicked=True,
                created_at=datetime.utcnow()
            )
            db.session.add(analytics)
            db.session.commit()
            
            logger.debug(f"Tracked suggestion click: '{selected_suggestion}' for query '{query}'")
            
        except Exception as e:
            logger.error(f"Error tracking suggestion click: {str(e)}")
            db.session.rollback()
    
    def get_suggestion_analytics(
        self,
        days: int = 30,
        limit: int = 50
    ) -> Dict[str, any]:
        """Get analytics about suggestion usage"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Most popular suggestions
            popular_suggestions = db.session.query(
                SearchAnalytics.selected_keywords,
                func.count(SearchAnalytics.id).label('click_count')
            ).filter(
                SearchAnalytics.created_at >= cutoff_date,
                SearchAnalytics.search_type == 'suggestion_click',
                SearchAnalytics.selected_keywords.isnot(None)
            ).group_by(SearchAnalytics.selected_keywords).order_by(
                func.count(SearchAnalytics.id).desc()
            ).limit(limit).all()
            
            # Query patterns
            query_patterns = db.session.query(
                SearchAnalytics.search_query,
                func.count(SearchAnalytics.id).label('query_count')
            ).filter(
                SearchAnalytics.created_at >= cutoff_date
            ).group_by(SearchAnalytics.search_query).order_by(
                func.count(SearchAnalytics.id).desc()
            ).limit(limit).all()
            
            return {
                'popular_suggestions': [
                    {
                        'suggestion': suggestion,
                        'click_count': count
                    } for suggestion, count in popular_suggestions
                ],
                'query_patterns': [
                    {
                        'query': query,
                        'count': count
                    } for query, count in query_patterns
                ],
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting suggestion analytics: {str(e)}")
            return {
                'popular_suggestions': [],
                'query_patterns': [],
                'period_days': days
            }
    
    def improve_suggestions(self):
        """Analyze user behavior and improve suggestion algorithms"""
        try:
            # This is a placeholder for machine learning improvements
            # Could include:
            # - Analyzing successful vs unsuccessful searches
            # - Adjusting relevance scores based on user feedback
            # - Identifying new trending topics
            # - Calculating keyword similarity matrices
            
            logger.info("Suggestion improvement process started")
            
            # For now, just update keyword frequencies
            self._update_keyword_frequencies()
            
        except Exception as e:
            logger.error(f"Error improving suggestions: {str(e)}")
    
    def _update_keyword_frequencies(self):
        """Update keyword frequencies based on recent usage"""
        try:
            # Get recent search analytics
            recent_analytics = db.session.query(SearchAnalytics).filter(
                SearchAnalytics.created_at >= datetime.utcnow() - timedelta(days=7),
                SearchAnalytics.selected_keywords.isnot(None)
            ).all()
            
            keyword_usage = defaultdict(int)
            
            for analytics in recent_analytics:
                try:
                    keywords = json.loads(analytics.selected_keywords)
                    for keyword in keywords:
                        keyword_usage[keyword.lower()] += 1
                except:
                    pass
            
            # Update keyword frequencies
            for keyword_text, usage_count in keyword_usage.items():
                keyword = db.session.query(NewsKeyword).filter(
                    NewsKeyword.normalized_keyword == keyword_text
                ).first()
                
                if keyword:
                    # Boost relevance for frequently used keywords
                    boost_factor = min(0.2, usage_count / 100)
                    keyword.relevance_score = min(1.0, keyword.relevance_score + boost_factor)
                    keyword.last_seen = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Updated frequencies for {len(keyword_usage)} keywords")
            
        except Exception as e:
            logger.error(f"Error updating keyword frequencies: {str(e)}")
            db.session.rollback()

# Global instance
intelligent_suggestion_service = IntelligentSuggestionService() 