# app/utils/cache/news_cache.py

from redis import Redis, ConnectionError, RedisError
import json
from typing import Optional, Any
import pickle
from datetime import timedelta
import os
import logging

logger = logging.getLogger(__name__)

class NewsCache:
    def __init__(self):
        """Initialize Redis cache connection with error handling"""
        self.redis_available = False
        self.redis = None
        self.binary_redis = None
        
        try:
            # Redis connection using environment variable or default
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            logger.info("🔄 Connecting to Redis using Coolify URL...")
            
            try:
                # Connect using the provided Redis URL
                self.redis = Redis.from_url(redis_url, decode_responses=True)
                self.binary_redis = Redis.from_url(redis_url, decode_responses=False)
                
                # Test connection
                self.redis.ping()
                self.redis_available = True
                logger.info("✅ Redis connected successfully using Coolify URL")
                
            except Exception as e:
                logger.debug(f"❌ Coolify Redis URL connection failed: {str(e)}")
                
                # Fallback to localhost for development
                try:
                    logger.info("🔄 Falling back to localhost for development...")
                    self.redis = Redis(host='localhost', port=6379, db=0, decode_responses=True)
                    self.binary_redis = Redis(host='localhost', port=6379, db=0)
                    
                    # Test connection
                    self.redis.ping()
                    self.redis_available = True
                    logger.info("✅ Redis connected successfully: localhost:6379")
                    
                except Exception as e2:
                    logger.debug(f"❌ localhost connection failed: {str(e2)}")
                    raise ConnectionError("Redis connection failed on both Coolify URL and localhost")
            
        except (ConnectionError, RedisError, Exception) as e:
            logger.warning(f"⚠️ Redis cache unavailable: {str(e)}. Operating without cache.")
            self.redis_available = False
            self.redis = None
            self.binary_redis = None

    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self.redis_available

    def get_json(self, key: str) -> Optional[Any]:
        """Get JSON data from cache with error handling"""
        if not self.redis_available:
            return None
            
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except (ConnectionError, RedisError, json.JSONDecodeError) as e:
            logger.debug(f"Cache get error for key {key}: {str(e)}")
            if "Authentication required" in str(e):
                logger.debug("Redis authentication required - disabling cache")
            self._handle_connection_error()
        return None

    def set_json(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set JSON data in cache with expiration and error handling"""
        if not self.redis_available:
            return False
            
        try:
            self.redis.set(key, json.dumps(value), ex=expire)
            return True
        except (ConnectionError, RedisError, json.JSONEncodeError) as e:
            logger.debug(f"Cache set error for key {key}: {str(e)}")
            if "Authentication required" in str(e):
                logger.debug("Redis authentication required - disabling cache")
            self._handle_connection_error()
            return False

    def get_object(self, key: str) -> Optional[Any]:
        """Get pickled object from cache with error handling"""
        if not self.redis_available:
            return None
            
        try:
            data = self.binary_redis.get(key)
            if data:
                return pickle.loads(data)
        except (ConnectionError, RedisError, pickle.PickleError) as e:
            logger.debug(f"Cache get object error for key {key}: {str(e)}")
            self._handle_connection_error()
        return None

    def set_object(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set pickled object in cache with expiration and error handling"""
        if not self.redis_available:
            return False
            
        try:
            self.binary_redis.set(key, pickle.dumps(value), ex=expire)
            return True
        except (ConnectionError, RedisError, pickle.PickleError) as e:
            logger.debug(f"Cache set object error for key {key}: {str(e)}")
            self._handle_connection_error()
            return False

    def build_key(self, *args) -> str:
        """Build cache key from arguments"""
        return ':'.join(str(arg) for arg in args)

    def delete_pattern(self, pattern: str) -> bool:
        """Delete all keys matching pattern with error handling"""
        if not self.redis_available:
            return False
            
        try:
            deleted_count = 0
            for key in self.redis.scan_iter(pattern):
                self.redis.delete(key)
                deleted_count += 1
            logger.debug(f"Deleted {deleted_count} cache keys matching pattern: {pattern}")
            return True
        except (ConnectionError, RedisError) as e:
            logger.debug(f"Cache delete pattern error for {pattern}: {str(e)}")
            self._handle_connection_error()
            return False
            
    def get_or_set(self, key: str, callback, expire: int = 3600):
        """Get from cache or set if not exists with error handling"""
        if not self.redis_available:
            return callback()
            
        try:
            data = self.get_json(key)
            if data is None:
                data = callback()
                if data is not None:
                    self.set_json(key, data, expire)
            return data
        except Exception as e:
            logger.debug(f"Cache get_or_set error for key {key}: {str(e)}")
            return callback()
    
    def _handle_connection_error(self):
        """Handle Redis connection errors by marking cache as unavailable"""
        if self.redis_available:
            logger.warning("🔄 Redis connection lost, disabling cache")
            self.redis_available = False
            
    def reconnect(self) -> bool:
        """Attempt to reconnect to Redis"""
        try:
            if self.redis:
                self.redis.ping()
                self.redis_available = True
                logger.info("✅ Redis cache reconnected successfully")
                return True
        except (ConnectionError, RedisError) as e:
            logger.debug(f"Redis reconnection failed: {str(e)}")
        return False