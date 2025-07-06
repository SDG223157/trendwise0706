from .news_cache import NewsCache
from typing import Optional, Dict, List, Any
import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseCache(NewsCache):
    """Extended cache for database query results and statistics"""
    
    def __init__(self):
        super().__init__()
        self.db_prefix = "db"
        self.count_prefix = "count"
        self.stats_prefix = "stats"
        
    def _generate_query_hash(self, query_params: Dict) -> str:
        """Generate a hash for query parameters"""
        query_str = json.dumps(query_params, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()[:12]
    
    # Count Query Caching
    def get_count_result(self, table: str, filters: Dict = None) -> Optional[int]:
        """Get cached count result"""
        filters = filters or {}
        query_hash = self._generate_query_hash({'table': table, 'filters': filters})
        cache_key = f"{self.count_prefix}:{table}:{query_hash}"
        
        result = self.get_json(cache_key)
        return result.get('count') if result else None
    
    def set_count_result(self, table: str, count: int, filters: Dict = None, expire: int = 1800) -> bool:
        """Cache count result (30 minutes default)"""
        filters = filters or {}
        query_hash = self._generate_query_hash({'table': table, 'filters': filters})
        cache_key = f"{self.count_prefix}:{table}:{query_hash}"
        
        data = {
            'count': count,
            'table': table,
            'filters': filters,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    # User Statistics Caching
    def get_user_statistics(self) -> Optional[Dict]:
        """Get cached user statistics"""
        cache_key = f"{self.stats_prefix}:users:overview"
        return self.get_json(cache_key)
    
    def set_user_statistics(self, stats: Dict, expire: int = 300) -> bool:
        """Cache user statistics (5 minutes default)"""
        cache_key = f"{self.stats_prefix}:users:overview"
        stats['cached_at'] = datetime.now().isoformat()
        return self.set_json(cache_key, stats, expire)
    
    # Article Statistics Caching
    def get_article_statistics(self, symbol: str = None) -> Optional[Dict]:
        """Get cached article statistics"""
        key_suffix = f":{symbol}" if symbol else ":global"
        cache_key = f"{self.stats_prefix}:articles{key_suffix}"
        return self.get_json(cache_key)
    
    def set_article_statistics(self, stats: Dict, symbol: str = None, expire: int = 1800) -> bool:
        """Cache article statistics (30 minutes default)"""
        key_suffix = f":{symbol}" if symbol else ":global"
        cache_key = f"{self.stats_prefix}:articles{key_suffix}"
        stats['cached_at'] = datetime.now().isoformat()
        return self.set_json(cache_key, stats, expire)
    
    # Symbol-specific Data Caching
    def get_symbol_processing_status(self, symbol: str) -> Optional[Dict]:
        """Get cached symbol processing status"""
        cache_key = f"{self.stats_prefix}:symbol_processing:{symbol}"
        return self.get_json(cache_key)
    
    def set_symbol_processing_status(self, symbol: str, status: Dict, expire: int = 1800) -> bool:
        """Cache symbol processing status (30 minutes default)"""
        cache_key = f"{self.stats_prefix}:symbol_processing:{symbol}"
        status['symbol'] = symbol
        status['cached_at'] = datetime.now().isoformat()
        return self.set_json(cache_key, status, expire)
    
    # Recent Articles Caching
    def get_recent_articles(self, symbol: str = None, limit: int = 20, hours: int = 24) -> Optional[List[Dict]]:
        """Get cached recent articles"""
        key_parts = [str(limit), f"{hours}h"]
        if symbol:
            key_parts.insert(0, symbol)
        key_suffix = ":".join(key_parts)
        cache_key = f"{self.db_prefix}:recent_articles:{key_suffix}"
        
        result = self.get_json(cache_key)
        return result.get('articles') if result else None
    
    def set_recent_articles(self, articles: List[Dict], symbol: str = None, limit: int = 20, 
                           hours: int = 24, expire: int = 600) -> bool:
        """Cache recent articles (10 minutes default)"""
        key_parts = [str(limit), f"{hours}h"]
        if symbol:
            key_parts.insert(0, symbol)
        key_suffix = ":".join(key_parts)
        cache_key = f"{self.db_prefix}:recent_articles:{key_suffix}"
        
        data = {
            'articles': articles,
            'symbol': symbol,
            'limit': limit,
            'hours': hours,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    # User Activity Caching
    def get_user_activities(self, user_id: int, page: int = 1, per_page: int = 20) -> Optional[Dict]:
        """Get cached user activities with pagination"""
        cache_key = f"{self.db_prefix}:user_activities:{user_id}:page_{page}:{per_page}"
        return self.get_json(cache_key)
    
    def set_user_activities(self, user_id: int, activities: List[Dict], total: int, 
                           page: int = 1, per_page: int = 20, expire: int = 600) -> bool:
        """Cache user activities (10 minutes default)"""
        cache_key = f"{self.db_prefix}:user_activities:{user_id}:page_{page}:{per_page}"
        
        data = {
            'activities': activities,
            'total': total,
            'page': page,
            'per_page': per_page,
            'user_id': user_id,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    # Admin Dashboard Data Caching
    def get_admin_dashboard_data(self) -> Optional[Dict]:
        """Get cached admin dashboard data"""
        cache_key = f"{self.stats_prefix}:admin_dashboard"
        return self.get_json(cache_key)
    
    def set_admin_dashboard_data(self, dashboard_data: Dict, expire: int = 300) -> bool:
        """Cache admin dashboard data (5 minutes default)"""
        cache_key = f"{self.stats_prefix}:admin_dashboard"
        dashboard_data['cached_at'] = datetime.now().isoformat()
        return self.set_json(cache_key, dashboard_data, expire)
    
    # Trending Data Caching
    def get_trending_symbols(self, period: str = "24h") -> Optional[List[Dict]]:
        """Get cached trending symbols"""
        cache_key = f"{self.stats_prefix}:trending_symbols:{period}"
        result = self.get_json(cache_key)
        return result.get('symbols') if result else None
    
    def set_trending_symbols(self, symbols: List[Dict], period: str = "24h", expire: int = 900) -> bool:
        """Cache trending symbols (15 minutes default)"""
        cache_key = f"{self.stats_prefix}:trending_symbols:{period}"
        
        data = {
            'symbols': symbols,
            'period': period,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    # Search Results Caching (complement to existing news search cache)
    def get_search_metadata(self, search_params: Dict) -> Optional[Dict]:
        """Get cached search metadata (total counts, facets, etc.)"""
        query_hash = self._generate_query_hash(search_params)
        cache_key = f"{self.db_prefix}:search_metadata:{query_hash}"
        return self.get_json(cache_key)
    
    def set_search_metadata(self, search_params: Dict, metadata: Dict, expire: int = 600) -> bool:
        """Cache search metadata (10 minutes default)"""
        query_hash = self._generate_query_hash(search_params)
        cache_key = f"{self.db_prefix}:search_metadata:{query_hash}"
        
        data = {
            'metadata': metadata,
            'search_params': search_params,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    # Symbol Lookup Caching
    def get_symbol_suggestions(self, query: str) -> Optional[List[Dict]]:
        """Get cached symbol suggestions"""
        cache_key = f"{self.db_prefix}:symbol_suggest:{query.lower()}"
        result = self.get_json(cache_key)
        return result.get('suggestions') if result else None
    
    def set_symbol_suggestions(self, query: str, suggestions: List[Dict], expire: int = 3600) -> bool:
        """Cache symbol suggestions (1 hour default)"""
        cache_key = f"{self.db_prefix}:symbol_suggest:{query.lower()}"
        
        data = {
            'suggestions': suggestions,
            'query': query,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    # Complex Query Results Caching
    def get_complex_query_result(self, query_name: str, params: Dict) -> Optional[Any]:
        """Get cached complex query result"""
        params_hash = self._generate_query_hash(params)
        cache_key = f"{self.db_prefix}:complex_query:{query_name}:{params_hash}"
        
        result = self.get_json(cache_key)
        return result.get('data') if result else None
    
    def set_complex_query_result(self, query_name: str, params: Dict, data: Any, expire: int = 1800) -> bool:
        """Cache complex query result (30 minutes default)"""
        params_hash = self._generate_query_hash(params)
        cache_key = f"{self.db_prefix}:complex_query:{query_name}:{params_hash}"
        
        cached_data = {
            'data': data,
            'query_name': query_name,
            'params': params,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, cached_data, expire)
    
    # Cache Invalidation Methods
    def invalidate_user_cache(self, user_id: int = None):
        """Invalidate user-related cache entries"""
        patterns = [f"{self.stats_prefix}:users:*"]
        if user_id:
            patterns.extend([
                f"{self.db_prefix}:user_activities:{user_id}:*",
                f"user:*:{user_id}*"
            ])
        
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def invalidate_article_cache(self, symbol: str = None):
        """Invalidate article-related cache entries"""
        patterns = [
            f"{self.stats_prefix}:articles:*",
            f"{self.db_prefix}:recent_articles:*"
        ]
        
        if symbol:
            patterns.extend([
                f"{self.stats_prefix}:symbol_processing:{symbol}",
                f"{self.db_prefix}:recent_articles:{symbol}:*"
            ])
        
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def invalidate_search_cache(self):
        """Invalidate search-related cache entries"""
        patterns = [
            f"{self.db_prefix}:search_metadata:*",
            f"{self.db_prefix}:symbol_suggest:*"
        ]
        
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def invalidate_admin_cache(self):
        """Invalidate admin dashboard cache"""
        patterns = [
            f"{self.stats_prefix}:admin_dashboard",
            f"{self.stats_prefix}:users:*",
            f"{self.stats_prefix}:articles:*"
        ]
        
        for pattern in patterns:
            self.delete_pattern(pattern)

# Global instance
db_cache = DatabaseCache() 