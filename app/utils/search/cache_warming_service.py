"""
Cache Warming Service for News Search

This service proactively caches popular searches to improve search performance
and reduce database load for common queries.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from sqlalchemy import func, desc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app import db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol
from app.utils.search.optimized_news_search import OptimizedNewsSearch
from app.utils.cache.news_cache import NewsCache
import json

logger = logging.getLogger(__name__)

class CacheWarmingService:
    """
    Proactive cache warming service for news search.
    
    Features:
    - Warm popular symbol searches
    - Warm trending keyword searches
    - Warm recent news queries
    - Performance monitoring
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.cache = None
        self.cache_enabled = False
        self.warming_stats = {
            'last_warming': None,
            'caches_warmed': 0,
            'errors': 0,
            'performance_metrics': []
        }
        
        # Initialize cache
        try:
            self.cache = NewsCache()
            self.cache_enabled = self.cache.is_available()
            if self.cache_enabled:
                logger.info("✅ Cache warming service initialized with Redis")
            else:
                logger.warning("⚠️ Cache warming service: Redis not available")
        except Exception as e:
            logger.error(f"❌ Cache warming service initialization failed: {str(e)}")
    
    def start_scheduler(self):
        """Start the cache warming scheduler"""
        if not self.cache_enabled:
            logger.warning("⚠️ Cache warming disabled - Redis not available")
            return
            
        try:
            # Warm popular searches every 15 minutes
            self.scheduler.add_job(
                self.warm_popular_searches,
                IntervalTrigger(minutes=15),
                id='warm_popular_searches',
                replace_existing=True,
                max_instances=1
            )
            
            # Warm trending symbols every 30 minutes
            self.scheduler.add_job(
                self.warm_trending_symbols,
                IntervalTrigger(minutes=30),
                id='warm_trending_symbols',
                replace_existing=True,
                max_instances=1
            )
            
            # Warm recent news every 10 minutes
            self.scheduler.add_job(
                self.warm_recent_news,
                IntervalTrigger(minutes=10),
                id='warm_recent_news',
                replace_existing=True,
                max_instances=1
            )
            
            # Full warming cycle every 2 hours
            self.scheduler.add_job(
                self.full_warming_cycle,
                IntervalTrigger(hours=2),
                id='full_warming_cycle',
                replace_existing=True,
                max_instances=1
            )
            
            self.scheduler.start()
            logger.info("✅ Cache warming scheduler started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start cache warming scheduler: {str(e)}")
    
    def stop_scheduler(self):
        """Stop the cache warming scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("🛑 Cache warming scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping cache warming scheduler: {str(e)}")
    
    def warm_popular_searches(self):
        """Warm cache for popular search queries"""
        if not self.cache_enabled:
            return
            
        start_time = datetime.now()
        warmed_count = 0
        
        try:
            # Get most popular symbols from last 7 days
            popular_symbols = self.get_popular_symbols(days=7, limit=20)
            
            # Get trending keywords
            trending_keywords = self.get_trending_keywords(days=3, limit=15)
            
            # Warm symbol searches
            for symbol in popular_symbols:
                if self.warm_symbol_search(symbol):
                    warmed_count += 1
            
            # Warm keyword searches
            for keyword in trending_keywords:
                if self.warm_keyword_search(keyword):
                    warmed_count += 1
            
            # Warm mixed searches (popular combinations)
            popular_combinations = self.get_popular_search_combinations(limit=10)
            for combo in popular_combinations:
                if self.warm_mixed_search(combo):
                    warmed_count += 1
            
            # Update stats
            duration = (datetime.now() - start_time).total_seconds()
            self.warming_stats['last_warming'] = datetime.now()
            self.warming_stats['caches_warmed'] += warmed_count
            self.warming_stats['performance_metrics'].append({
                'type': 'popular_searches',
                'duration': duration,
                'caches_warmed': warmed_count,
                'timestamp': datetime.now()
            })
            
            logger.info(f"✅ Popular searches warmed: {warmed_count} caches in {duration:.2f}s")
            
        except Exception as e:
            self.warming_stats['errors'] += 1
            logger.error(f"❌ Popular searches warming failed: {str(e)}")
    
    def warm_trending_symbols(self):
        """Warm cache for trending stock symbols"""
        if not self.cache_enabled:
            return
            
        start_time = datetime.now()
        warmed_count = 0
        
        try:
            # Get symbols with most articles in last 24 hours
            trending_symbols = db.session.query(
                ArticleSymbol.symbol,
                func.count(ArticleSymbol.article_id).label('article_count')
            ).join(NewsArticle).filter(
                NewsArticle.published_at >= datetime.now() - timedelta(hours=24),
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None)
            ).group_by(ArticleSymbol.symbol).order_by(desc('article_count')).limit(25).all()
            
            # Warm cache for each trending symbol
            for symbol, count in trending_symbols:
                # Warm different filter combinations
                filters = [
                    {'sentiment_filter': None, 'sort_order': 'LATEST'},
                    {'sentiment_filter': 'POSITIVE', 'sort_order': 'LATEST'},
                    {'sentiment_filter': 'NEGATIVE', 'sort_order': 'LATEST'},
                    {'sentiment_filter': None, 'sort_order': 'HIGHEST'}
                ]
                
                for filter_combo in filters:
                    if self.warm_symbol_search(symbol, **filter_combo):
                        warmed_count += 1
            
            # Update stats
            duration = (datetime.now() - start_time).total_seconds()
            self.warming_stats['caches_warmed'] += warmed_count
            self.warming_stats['performance_metrics'].append({
                'type': 'trending_symbols',
                'duration': duration,
                'caches_warmed': warmed_count,
                'timestamp': datetime.now()
            })
            
            logger.info(f"✅ Trending symbols warmed: {warmed_count} caches in {duration:.2f}s")
            
        except Exception as e:
            self.warming_stats['errors'] += 1
            logger.error(f"❌ Trending symbols warming failed: {str(e)}")
    
    def warm_recent_news(self):
        """Warm cache for recent news queries"""
        if not self.cache_enabled:
            return
            
        start_time = datetime.now()
        warmed_count = 0
        
        try:
            # Warm general recent news queries
            recent_queries = [
                {'keywords': ['latest'], 'sort_order': 'LATEST'},
                {'keywords': ['earnings'], 'sort_order': 'LATEST'},
                {'keywords': ['ai', 'artificial intelligence'], 'sort_order': 'LATEST'},
                {'keywords': ['technology'], 'sort_order': 'LATEST'},
                {'keywords': ['merger'], 'sort_order': 'LATEST'},
                {'keywords': ['acquisition'], 'sort_order': 'LATEST'},
                {'keywords': ['dividend'], 'sort_order': 'LATEST'},
                {'keywords': ['cryptocurrency'], 'sort_order': 'LATEST'},
                {'keywords': ['bitcoin'], 'sort_order': 'LATEST'},
                {'keywords': ['tesla'], 'sort_order': 'LATEST'},
                {'keywords': ['apple'], 'sort_order': 'LATEST'},
                {'keywords': ['microsoft'], 'sort_order': 'LATEST'},
                {'keywords': ['google'], 'sort_order': 'LATEST'},
                {'keywords': ['amazon'], 'sort_order': 'LATEST'},
                {'keywords': ['nvidia'], 'sort_order': 'LATEST'}
            ]
            
            for query in recent_queries:
                if self.warm_keyword_search(query['keywords'], sort_order=query['sort_order']):
                    warmed_count += 1
            
            # Update stats
            duration = (datetime.now() - start_time).total_seconds()
            self.warming_stats['caches_warmed'] += warmed_count
            self.warming_stats['performance_metrics'].append({
                'type': 'recent_news',
                'duration': duration,
                'caches_warmed': warmed_count,
                'timestamp': datetime.now()
            })
            
            logger.info(f"✅ Recent news warmed: {warmed_count} caches in {duration:.2f}s")
            
        except Exception as e:
            self.warming_stats['errors'] += 1
            logger.error(f"❌ Recent news warming failed: {str(e)}")
    
    def full_warming_cycle(self):
        """Complete warming cycle for comprehensive cache coverage"""
        if not self.cache_enabled:
            return
            
        start_time = datetime.now()
        
        try:
            logger.info("🔄 Starting full cache warming cycle...")
            
            # Run all warming methods
            self.warm_popular_searches()
            self.warm_trending_symbols()
            self.warm_recent_news()
            
            # Warm additional specific queries
            self.warm_high_value_queries()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Full warming cycle completed in {duration:.2f}s")
            
        except Exception as e:
            self.warming_stats['errors'] += 1
            logger.error(f"❌ Full warming cycle failed: {str(e)}")
    
    def warm_symbol_search(self, symbol: str, **kwargs) -> bool:
        """Warm cache for a specific symbol search"""
        try:
            search = OptimizedNewsSearch(db.session)
            
            # Default parameters
            params = {
                'symbols': [symbol],
                'sentiment_filter': kwargs.get('sentiment_filter'),
                'sort_order': kwargs.get('sort_order', 'LATEST'),
                'date_filter': kwargs.get('date_filter'),
                'region_filter': kwargs.get('region_filter'),
                'processing_filter': kwargs.get('processing_filter', 'all'),
                'page': 1,
                'per_page': 20
            }
            
            # Execute search to warm cache
            results = search.search_by_symbols(**params)
            
            # Also warm page 2 if there are enough results
            if len(results[0]) >= 20:
                params['page'] = 2
                search.search_by_symbols(**params)
            
            logger.debug(f"🔥 Warmed symbol search cache: {symbol}")
            return True
            
        except Exception as e:
            logger.debug(f"❌ Failed to warm symbol search {symbol}: {str(e)}")
            return False
    
    def warm_keyword_search(self, keywords: List[str], **kwargs) -> bool:
        """Warm cache for a specific keyword search"""
        try:
            search = OptimizedNewsSearch(db.session)
            
            # Default parameters
            params = {
                'keywords': keywords,
                'sentiment_filter': kwargs.get('sentiment_filter'),
                'sort_order': kwargs.get('sort_order', 'LATEST'),
                'date_filter': kwargs.get('date_filter'),
                'page': 1,
                'per_page': 20
            }
            
            # Execute search to warm cache
            results = search.search_by_keywords(**params)
            
            # Also warm page 2 if there are enough results
            if len(results[0]) >= 20:
                params['page'] = 2
                search.search_by_keywords(**params)
            
            logger.debug(f"🔥 Warmed keyword search cache: {keywords}")
            return True
            
        except Exception as e:
            logger.debug(f"❌ Failed to warm keyword search {keywords}: {str(e)}")
            return False
    
    def warm_mixed_search(self, combo: Dict) -> bool:
        """Warm cache for mixed symbol + keyword searches"""
        try:
            search = OptimizedNewsSearch(db.session)
            
            # Execute advanced search
            results = search.advanced_search(
                keywords=combo.get('keywords'),
                symbols=combo.get('symbols'),
                sentiment=combo.get('sentiment'),
                page=1,
                per_page=20
            )
            
            logger.debug(f"🔥 Warmed mixed search cache: {combo}")
            return True
            
        except Exception as e:
            logger.debug(f"❌ Failed to warm mixed search {combo}: {str(e)}")
            return False
    
    def warm_high_value_queries(self):
        """Warm cache for high-value queries that are expensive to compute"""
        high_value_queries = [
            # High sentiment queries
            {'sentiment_filter': 'POSITIVE', 'sort_order': 'HIGHEST'},
            {'sentiment_filter': 'NEGATIVE', 'sort_order': 'LOWEST'},
            
            # Regional queries
            {'region_filter': 'US', 'sort_order': 'LATEST'},
            {'region_filter': 'CHINA', 'sort_order': 'LATEST'},
            {'region_filter': 'EUROPE', 'sort_order': 'LATEST'},
            
            # Date-based queries
            {'date_filter': 'today', 'sort_order': 'LATEST'},
            {'date_filter': 'week', 'sort_order': 'LATEST'},
            {'date_filter': 'month', 'sort_order': 'LATEST'},
        ]
        
        for query in high_value_queries:
            try:
                search = OptimizedNewsSearch(db.session)
                search.search_by_symbols(symbols=None, **query)
                logger.debug(f"🔥 Warmed high-value query: {query}")
            except Exception as e:
                logger.debug(f"❌ Failed to warm high-value query {query}: {str(e)}")
    
    def get_popular_symbols(self, days: int = 7, limit: int = 20) -> List[str]:
        """Get most popular symbols from recent searches"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get symbols with most articles
            popular = db.session.query(
                ArticleSymbol.symbol,
                func.count(ArticleSymbol.article_id).label('count')
            ).join(NewsArticle).filter(
                NewsArticle.published_at >= cutoff_date,
                NewsArticle.ai_summary.isnot(None)
            ).group_by(ArticleSymbol.symbol).order_by(desc('count')).limit(limit).all()
            
            return [symbol for symbol, count in popular]
            
        except Exception as e:
            logger.error(f"❌ Failed to get popular symbols: {str(e)}")
            return []
    
    def get_trending_keywords(self, days: int = 3, limit: int = 15) -> List[str]:
        """Get trending keywords from recent articles"""
        # Common trending keywords to warm
        trending_keywords = [
            'earnings', 'ai', 'artificial intelligence', 'technology', 'merger',
            'acquisition', 'dividend', 'cryptocurrency', 'bitcoin', 'tesla',
            'apple', 'microsoft', 'google', 'amazon', 'nvidia', 'meta',
            'breakthrough', 'innovation', 'partnership', 'agreement'
        ]
        
        return trending_keywords[:limit]
    
    def get_popular_search_combinations(self, limit: int = 10) -> List[Dict]:
        """Get popular search combinations"""
        combinations = [
            {'symbols': ['AAPL'], 'keywords': ['earnings']},
            {'symbols': ['TSLA'], 'keywords': ['ai', 'artificial intelligence']},
            {'symbols': ['MSFT'], 'keywords': ['technology']},
            {'symbols': ['GOOGL'], 'keywords': ['ai']},
            {'symbols': ['AMZN'], 'keywords': ['earnings']},
            {'symbols': ['NVDA'], 'keywords': ['ai', 'artificial intelligence']},
            {'symbols': ['META'], 'keywords': ['technology']},
            {'symbols': ['NFLX'], 'keywords': ['streaming']},
            {'symbols': ['UBER'], 'keywords': ['technology']},
            {'symbols': ['ZOOM'], 'keywords': ['technology']}
        ]
        
        return combinations[:limit]
    
    def get_warming_status(self) -> Dict:
        """Get current warming status and metrics"""
        try:
            status = {
                'scheduler_running': self.scheduler.running if self.scheduler else False,
                'cache_enabled': self.cache_enabled,
                'last_warming': self.warming_stats['last_warming'],
                'caches_warmed': self.warming_stats['caches_warmed'],
                'errors': self.warming_stats['errors'],
                'recent_metrics': self.warming_stats['performance_metrics'][-10:] if self.warming_stats['performance_metrics'] else []
            }
            
            # Add cache statistics if available
            if self.cache_enabled and self.cache:
                try:
                    cache_info = self.cache.get_cache_info()
                    status['cache_info'] = cache_info
                except:
                    pass
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Failed to get warming status: {str(e)}")
            return {'error': str(e)}

# Global instance
cache_warming_service = CacheWarmingService() 