"""
SP500 Score Cache Service
Efficiently caches SP500 scores for different time periods to improve analysis performance
"""

import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib

logger = logging.getLogger(__name__)

class SP500Cache:
    """
    Caches SP500 scores based on date ranges to avoid redundant calculations
    """
    
    def __init__(self):
        self.redis_client = None
        self._connect_redis()
        
    def _connect_redis(self):
        """Initialize Redis connection with fallback handling"""
        try:
            # Try to connect to Redis directly
            import redis
            
            # Try localhost first (for development)
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ SP500 Cache: Redis connected successfully (localhost)")
                return
            except Exception:
                pass
                
            # Try Redis URL from environment
            import os
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ SP500 Cache: Redis connected successfully (URL)")
                return
                
            # No Redis available
            logger.warning("⚠️ SP500 Cache: Redis not available, using in-memory fallback")
            self.redis_client = None
                
        except Exception as e:
            logger.warning(f"⚠️ SP500 Cache: Redis connection failed: {str(e)}")
            self.redis_client = None
    
    def _generate_cache_key(self, start_date: datetime, end_date: datetime, lookback_days: int = None) -> str:
        """
        Generate a unique cache key for SP500 score based on date range
        
        Args:
            start_date: Analysis start date
            end_date: Analysis end date  
            lookback_days: Optional lookback period for standard periods
            
        Returns:
            Unique cache key string
        """
        # Use date strings for human-readable keys
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        if lookback_days:
            # For standard lookback periods (e.g., 365 days)
            key = f"sp500:score:lookback:{lookback_days}:end:{end_str}"
        else:
            # For custom date ranges
            period_hash = hashlib.md5(f"{start_str}:{end_str}".encode()).hexdigest()[:8]
            key = f"sp500:score:range:{start_str}:{end_str}:{period_hash}"
            
        return key
    
    def get_sp500_score(self, start_date: datetime, end_date: datetime, lookback_days: int = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached SP500 score for the given date range
        
        Args:
            start_date: Analysis start date
            end_date: Analysis end date
            lookback_days: Optional lookback period for standard periods
            
        Returns:
            Cached SP500 data or None if not found
        """
        if not self.redis_client:
            return None
            
        try:
            cache_key = self._generate_cache_key(start_date, end_date, lookback_days)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                
                # Validate cache data
                if self._is_cache_valid(data):
                    logger.info(f"✅ SP500 Cache HIT: {cache_key} (score: {data['score']})")
                    return data
                else:
                    # Remove invalid cache entry
                    self.redis_client.delete(cache_key)
                    logger.warning(f"🗑️ SP500 Cache: Removed invalid entry {cache_key}")
                    
            logger.info(f"❌ SP500 Cache MISS: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ SP500 Cache: Error retrieving cache: {str(e)}")
            return None
    
    def set_sp500_score(self, start_date: datetime, end_date: datetime, score: float, 
                       additional_data: Dict[str, Any] = None, lookback_days: int = None) -> bool:
        """
        Cache SP500 score for the given date range
        
        Args:
            start_date: Analysis start date
            end_date: Analysis end date
            score: SP500 score to cache
            additional_data: Additional metadata to store
            lookback_days: Optional lookback period for standard periods
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._generate_cache_key(start_date, end_date, lookback_days)
            
            # Prepare cache data
            cache_data = {
                'score': score,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'lookback_days': lookback_days,
                'cached_at': datetime.now().isoformat(),
                'data_points': (end_date - start_date).days,
            }
            
            # Add additional data if provided
            if additional_data:
                cache_data.update(additional_data)
            
            # Determine expiration time
            expire_seconds = self._get_cache_expiration(end_date)
            
            # Store in Redis
            success = self.redis_client.setex(
                cache_key, 
                expire_seconds, 
                json.dumps(cache_data)
            )
            
            if success:
                logger.info(f"💾 SP500 Cache STORED: {cache_key} (score: {score}, expires: {expire_seconds}s)")
                return True
            else:
                logger.error(f"❌ SP500 Cache: Failed to store {cache_key}")
                return False
                
        except Exception as e:
            logger.error(f"❌ SP500 Cache: Error storing cache: {str(e)}")
            return False
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """
        Validate cached data structure and freshness
        
        Args:
            cache_data: Cached data to validate
            
        Returns:
            True if cache data is valid
        """
        required_fields = ['score', 'start_date', 'end_date', 'cached_at']
        
        # Check required fields
        if not all(field in cache_data for field in required_fields):
            return False
            
        # Check score is reasonable
        score = cache_data.get('score')
        if not isinstance(score, (int, float)) or score < 0 or score > 120:
            return False
            
        # Check dates are reasonable
        try:
            start_date = datetime.strptime(cache_data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(cache_data['end_date'], '%Y-%m-%d')
            cached_at = datetime.fromisoformat(cache_data['cached_at'].replace('Z', '+00:00'))
            
            # Data range should be reasonable (between 30 days and 2 years)
            date_range = (end_date - start_date).days
            if date_range < 30 or date_range > 730:
                return False
                
            # Cache shouldn't be too old (max 7 days for safety)
            cache_age = (datetime.now() - cached_at.replace(tzinfo=None)).days
            if cache_age > 7:
                return False
                
        except (ValueError, TypeError):
            return False
            
        return True
    
    def _get_cache_expiration(self, end_date: datetime) -> int:
        """
        Determine appropriate cache expiration based on end date
        
        Args:
            end_date: Analysis end date
            
        Returns:
            Expiration time in seconds
        """
        now = datetime.now()
        
        # If end date is recent (within last 7 days), shorter cache
        if (now - end_date).days <= 7:
            return 3600 * 6  # 6 hours (market may still be moving)
        
        # If end date is older, longer cache
        elif (now - end_date).days <= 30:
            return 3600 * 24  # 24 hours
        
        # For historical data, much longer cache
        else:
            return 3600 * 24 * 7  # 7 days
    
    def invalidate_recent_cache(self, days_back: int = 7) -> int:
        """
        Invalidate recent SP500 cache entries (useful after market close or data updates)
        
        Args:
            days_back: Number of days back to invalidate
            
        Returns:
            Number of keys invalidated
        """
        if not self.redis_client:
            return 0
            
        try:
            # Find all SP500 cache keys
            pattern = "sp500:score:*"
            keys = self.redis_client.keys(pattern)
            
            invalidated = 0
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for key in keys:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        data = json.loads(cached_data)
                        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
                        
                        # Invalidate if end date is recent
                        if end_date >= cutoff_date:
                            self.redis_client.delete(key)
                            invalidated += 1
                            
                except Exception:
                    # Delete malformed cache entries
                    self.redis_client.delete(key)
                    invalidated += 1
            
            logger.info(f"🗑️ SP500 Cache: Invalidated {invalidated} recent entries")
            return invalidated
            
        except Exception as e:
            logger.error(f"❌ SP500 Cache: Error invalidating cache: {str(e)}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.redis_client:
            return {'status': 'redis_unavailable'}
            
        try:
            pattern = "sp500:score:*"
            keys = self.redis_client.keys(pattern)
            
            total_entries = len(keys)
            valid_entries = 0
            
            # Sample some entries for validity check
            sample_size = min(10, total_entries)
            for key in keys[:sample_size]:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        data = json.loads(cached_data)
                        if self._is_cache_valid(data):
                            valid_entries += 1
                except Exception:
                    pass
            
            return {
                'status': 'available',
                'total_entries': total_entries,
                'sample_valid_ratio': valid_entries / sample_size if sample_size > 0 else 0,
                'estimated_valid_entries': int(total_entries * (valid_entries / sample_size)) if sample_size > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ SP500 Cache: Error getting stats: {str(e)}")
            return {'status': 'error', 'error': str(e)}


# Global instance
sp500_cache = SP500Cache() 