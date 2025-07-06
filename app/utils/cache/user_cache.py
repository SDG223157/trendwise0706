from .news_cache import NewsCache
from typing import Optional, Dict, List
import json
import logging

logger = logging.getLogger(__name__)

class UserCache(NewsCache):
    """Extended cache for user-related data"""
    
    def __init__(self):
        super().__init__()
        self.cache_prefix = "user"
        
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user data from cache by ID"""
        cache_key = f"{self.cache_prefix}:id:{user_id}"
        return self.get_json(cache_key)
    
    def set_user_by_id(self, user_id: int, user_data: Dict, expire: int = 1800) -> bool:
        """Cache user data by ID (30 minutes default)"""
        cache_key = f"{self.cache_prefix}:id:{user_id}"
        return self.set_json(cache_key, user_data, expire)
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user data from cache by email"""
        cache_key = f"{self.cache_prefix}:email:{email.lower()}"
        return self.get_json(cache_key)
    
    def set_user_by_email(self, email: str, user_data: Dict, expire: int = 1800) -> bool:
        """Cache user data by email (30 minutes default)"""
        cache_key = f"{self.cache_prefix}:email:{email.lower()}"
        return self.set_json(cache_key, user_data, expire)
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user data from cache by username"""
        cache_key = f"{self.cache_prefix}:username:{username.lower()}"
        return self.get_json(cache_key)
    
    def set_user_by_username(self, username: str, user_data: Dict, expire: int = 1800) -> bool:
        """Cache user data by username (30 minutes default)"""
        cache_key = f"{self.cache_prefix}:username:{username.lower()}"
        return self.set_json(cache_key, user_data, expire)
    
    def cache_user_complete(self, user_data: Dict, expire: int = 1800) -> bool:
        """Cache user data under all lookup keys"""
        success = True
        if user_data.get('id'):
            success &= self.set_user_by_id(user_data['id'], user_data, expire)
        if user_data.get('email'):
            success &= self.set_user_by_email(user_data['email'], user_data, expire)
        if user_data.get('username'):
            success &= self.set_user_by_username(user_data['username'], user_data, expire)
        return success
    
    def invalidate_user(self, user_id: int = None, email: str = None, username: str = None):
        """Invalidate user cache entries"""
        patterns = []
        if user_id:
            patterns.append(f"{self.cache_prefix}:id:{user_id}")
        if email:
            patterns.append(f"{self.cache_prefix}:email:{email.lower()}")
        if username:
            patterns.append(f"{self.cache_prefix}:username:{username.lower()}")
        
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def get_user_stats(self) -> Optional[Dict]:
        """Get cached user statistics"""
        cache_key = f"{self.cache_prefix}:stats"
        return self.get_json(cache_key)
    
    def set_user_stats(self, stats: Dict, expire: int = 300) -> bool:
        """Cache user statistics (5 minutes default)"""
        cache_key = f"{self.cache_prefix}:stats"
        return self.set_json(cache_key, stats, expire)
    
    def get_user_activities(self, user_id: int, page: int = 1) -> Optional[List[Dict]]:
        """Get cached user activities"""
        cache_key = f"{self.cache_prefix}:activities:{user_id}:page:{page}"
        return self.get_json(cache_key)
    
    def set_user_activities(self, user_id: int, activities: List[Dict], page: int = 1, expire: int = 600) -> bool:
        """Cache user activities (10 minutes default)"""
        cache_key = f"{self.cache_prefix}:activities:{user_id}:page:{page}"
        return self.set_json(cache_key, activities, expire)
    
    def get_admin_user_list(self, page: int = 1) -> Optional[Dict]:
        """Get cached admin user list"""
        cache_key = f"{self.cache_prefix}:admin_list:page:{page}"
        return self.get_json(cache_key)
    
    def set_admin_user_list(self, user_list: Dict, page: int = 1, expire: int = 300) -> bool:
        """Cache admin user list (5 minutes default)"""
        cache_key = f"{self.cache_prefix}:admin_list:page:{page}"
        return self.set_json(cache_key, user_list, expire)
    
    def invalidate_admin_caches(self):
        """Invalidate admin-related caches"""
        self.delete_pattern(f"{self.cache_prefix}:stats")
        self.delete_pattern(f"{self.cache_prefix}:admin_list:*")
        self.delete_pattern(f"{self.cache_prefix}:activities:*")

# Global instance
user_cache = UserCache() 