"""
SP500 Historical Data Cache Service
Efficiently caches SP500 OHLC data to reduce Yahoo Finance API calls and improve performance
"""

import redis
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import hashlib
import numpy as np

logger = logging.getLogger(__name__)

class SP500DataCache:
    """
    Caches SP500 historical OHLC data to minimize API calls and improve performance
    """
    
    def __init__(self):
        self.redis_client = None
        self._connect_redis()
        
    def _connect_redis(self):
        """Initialize Redis connection with fallback handling"""
        try:
            import redis
            
            # Try localhost first (for development)
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ SP500 Data Cache: Redis connected successfully (localhost)")
                return
            except Exception:
                pass
                
            # Try Redis URL from environment
            import os
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ SP500 Data Cache: Redis connected successfully (URL)")
                return
                
            # No Redis available
            logger.warning("⚠️ SP500 Data Cache: Redis not available, using in-memory fallback")
            self.redis_client = None
                
        except Exception as e:
            logger.warning(f"⚠️ SP500 Data Cache: Redis connection failed: {str(e)}")
            self.redis_client = None
    
    def _generate_cache_key(self, start_date: str, end_date: str) -> str:
        """
        Generate a unique cache key for SP500 data based on date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Unique cache key string
        """
        # Create a shorter hash for the date range
        date_range = f"{start_date}:{end_date}"
        range_hash = hashlib.md5(date_range.encode()).hexdigest()[:8]
        
        return f"sp500:data:{start_date}:{end_date}:{range_hash}"
    
    def _normalize_dates(self, start_date: str, end_date: str) -> Tuple[str, str]:
        """
        Normalize dates to ensure consistent format
        
        Args:
            start_date: Start date string
            end_date: End date string
            
        Returns:
            Tuple of normalized date strings
        """
        try:
            # Parse and reformat dates to ensure consistency
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            return start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d')
        except ValueError:
            # Return as-is if parsing fails
            return start_date, end_date
    
    def get_sp500_data(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Retrieve cached SP500 data for the given date range with intelligent overlap handling
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with SP500 OHLC data or None if not found
        """
        if not self.redis_client:
            return None
            
        try:
            start_date, end_date = self._normalize_dates(start_date, end_date)
            
            # First, try exact match
            exact_key = self._generate_cache_key(start_date, end_date)
            cached_data = self.redis_client.get(exact_key)
            
            if cached_data:
                data = json.loads(cached_data)
                if self._is_cache_valid(data):
                    df = self._json_to_dataframe(data['ohlc_data'])
                    logger.info(f"✅ SP500 Data Cache HIT (exact): {exact_key} ({len(df)} rows)")
                    return df
                else:
                    self.redis_client.delete(exact_key)
                    logger.warning(f"🗑️ SP500 Data Cache: Removed invalid entry {exact_key}")
            
            # Try to find overlapping cached data that contains our range
            overlap_data = self._find_overlapping_cache(start_date, end_date)
            if overlap_data:
                logger.info(f"✅ SP500 Data Cache HIT (overlap): Found overlapping data")
                return overlap_data
                
            logger.info(f"❌ SP500 Data Cache MISS: {exact_key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ SP500 Data Cache: Error retrieving cache: {str(e)}")
            return None
    
    def _find_overlapping_cache(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Find cached data that overlaps with the requested date range
        
        Args:
            start_date: Requested start date
            end_date: Requested end date
            
        Returns:
            DataFrame subset that matches the requested range or None
        """
        try:
            # Search for SP500 data cache keys
            pattern = "sp500:data:*"
            keys = self.redis_client.keys(pattern)
            
            target_start = datetime.strptime(start_date, '%Y-%m-%d')
            target_end = datetime.strptime(end_date, '%Y-%m-%d')
            
            for key in keys:
                try:
                    cached_data = self.redis_client.get(key)
                    if not cached_data:
                        continue
                        
                    data = json.loads(cached_data)
                    if not self._is_cache_valid(data):
                        continue
                    
                    cached_start = datetime.strptime(data['start_date'], '%Y-%m-%d')
                    cached_end = datetime.strptime(data['end_date'], '%Y-%m-%d')
                    
                    # Check if cached data contains our target range
                    if cached_start <= target_start and cached_end >= target_end:
                        # Extract the subset we need
                        df = self._json_to_dataframe(data['ohlc_data'])
                        
                        # Filter to exact date range
                        df_filtered = df[
                            (df.index >= target_start) & 
                            (df.index <= target_end)
                        ]
                        
                        if not df_filtered.empty:
                            logger.info(f"📊 SP500 Data Cache: Extracted {len(df_filtered)} rows from larger cache")
                            return df_filtered
                            
                except Exception:
                    continue
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ SP500 Data Cache: Error finding overlapping cache: {str(e)}")
            return None
    
    def set_sp500_data(self, start_date: str, end_date: str, df: pd.DataFrame) -> bool:
        """
        Cache SP500 data for the given date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            df: DataFrame with SP500 OHLC data
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.redis_client or df is None or df.empty:
            return False
            
        try:
            start_date, end_date = self._normalize_dates(start_date, end_date)
            cache_key = self._generate_cache_key(start_date, end_date)
            
            # Prepare cache data
            cache_data = {
                'start_date': start_date,
                'end_date': end_date,
                'cached_at': datetime.now().isoformat(),
                'data_points': len(df),
                'ohlc_data': self._dataframe_to_json(df),
                'data_summary': {
                    'first_date': df.index[0].strftime('%Y-%m-%d') if not df.empty else None,
                    'last_date': df.index[-1].strftime('%Y-%m-%d') if not df.empty else None,
                    'first_close': float(df['Close'].iloc[0]) if not df.empty else None,
                    'last_close': float(df['Close'].iloc[-1]) if not df.empty else None,
                    'min_close': float(df['Close'].min()) if not df.empty else None,
                    'max_close': float(df['Close'].max()) if not df.empty else None
                }
            }
            
            # Determine expiration time
            expire_seconds = self._get_cache_expiration(end_date)
            
            # Store in Redis
            success = self.redis_client.setex(
                cache_key, 
                expire_seconds, 
                json.dumps(cache_data)
            )
            
            if success:
                logger.info(f"💾 SP500 Data Cache STORED: {cache_key} ({len(df)} rows, expires: {expire_seconds}s)")
                return True
            else:
                logger.error(f"❌ SP500 Data Cache: Failed to store {cache_key}")
                return False
                
        except Exception as e:
            logger.error(f"❌ SP500 Data Cache: Error storing cache: {str(e)}")
            return False
    
    def _dataframe_to_json(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Convert DataFrame to JSON-serializable format
        
        Args:
            df: DataFrame to convert
            
        Returns:
            Dictionary representation of DataFrame
        """
        return {
            'index': [dt.strftime('%Y-%m-%d') for dt in df.index],
            'data': {
                'Open': df['Open'].tolist(),
                'High': df['High'].tolist(),
                'Low': df['Low'].tolist(),
                'Close': df['Close'].tolist(),
                'Volume': df['Volume'].tolist() if 'Volume' in df.columns else []
            }
        }
    
    def _json_to_dataframe(self, json_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert JSON data back to DataFrame
        
        Args:
            json_data: Dictionary representation of DataFrame
            
        Returns:
            Reconstructed DataFrame
        """
        dates = [datetime.strptime(date_str, '%Y-%m-%d') for date_str in json_data['index']]
        
        data_dict = {
            'Open': json_data['data']['Open'],
            'High': json_data['data']['High'],
            'Low': json_data['data']['Low'],
            'Close': json_data['data']['Close']
        }
        
        if json_data['data']['Volume']:
            data_dict['Volume'] = json_data['data']['Volume']
        
        df = pd.DataFrame(data_dict, index=dates)
        return df
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """
        Validate cached data structure and freshness
        
        Args:
            cache_data: Cached data to validate
            
        Returns:
            True if cache data is valid
        """
        required_fields = ['start_date', 'end_date', 'cached_at', 'ohlc_data', 'data_points']
        
        # Check required fields
        if not all(field in cache_data for field in required_fields):
            return False
            
        # Check data points is reasonable
        data_points = cache_data.get('data_points', 0)
        if not isinstance(data_points, int) or data_points <= 0 or data_points > 10000:
            return False
            
        # Check dates are reasonable
        try:
            start_date = datetime.strptime(cache_data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(cache_data['end_date'], '%Y-%m-%d')
            cached_at = datetime.fromisoformat(cache_data['cached_at'].replace('Z', '+00:00'))
            
            # Date range should be reasonable (between 1 day and 5 years)
            date_range = (end_date - start_date).days
            if date_range < 1 or date_range > 1825:
                return False
                
            # Cache shouldn't be too old (max 30 days for safety)
            cache_age = (datetime.now() - cached_at.replace(tzinfo=None)).days
            if cache_age > 30:
                return False
                
        except (ValueError, TypeError):
            return False
            
        # Validate OHLC data structure
        ohlc_data = cache_data.get('ohlc_data', {})
        if not isinstance(ohlc_data, dict) or 'index' not in ohlc_data or 'data' not in ohlc_data:
            return False
            
        return True
    
    def _get_cache_expiration(self, end_date: str) -> int:
        """
        Determine appropriate cache expiration based on end date
        
        Args:
            end_date: End date string
            
        Returns:
            Expiration time in seconds
        """
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            now = datetime.now()
            days_ago = (now - end_dt).days
            
            # If end date is today or recent, shorter cache
            if days_ago <= 1:
                return 3600 * 4  # 4 hours (market data may update)
            elif days_ago <= 7:
                return 3600 * 12  # 12 hours
            elif days_ago <= 30:
                return 3600 * 24  # 24 hours
            else:
                # For historical data, much longer cache
                return 3600 * 24 * 7  # 7 days
                
        except ValueError:
            # Default expiration if date parsing fails
            return 3600 * 24  # 24 hours
    
    def get_cache_coverage(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Check what percentage of requested date range is covered by cache
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary with coverage statistics
        """
        if not self.redis_client:
            return {'coverage': 0, 'status': 'redis_unavailable'}
            
        try:
            # Try to get cached data
            cached_df = self.get_sp500_data(start_date, end_date)
            
            if cached_df is not None and not cached_df.empty:
                target_start = datetime.strptime(start_date, '%Y-%m-%d')
                target_end = datetime.strptime(end_date, '%Y-%m-%d')
                
                # Calculate business days in target range (approximate)
                target_days = (target_end - target_start).days
                business_days_approx = target_days * 5 / 7  # Rough estimate
                
                coverage_pct = min(100, (len(cached_df) / business_days_approx) * 100)
                
                return {
                    'coverage': coverage_pct,
                    'status': 'cached',
                    'cached_points': len(cached_df),
                    'estimated_target_points': int(business_days_approx)
                }
            else:
                return {
                    'coverage': 0,
                    'status': 'not_cached',
                    'cached_points': 0
                }
                
        except Exception as e:
            logger.error(f"❌ SP500 Data Cache: Error checking coverage: {str(e)}")
            return {'coverage': 0, 'status': 'error', 'error': str(e)}
    
    def invalidate_recent_cache(self, days_back: int = 7) -> int:
        """
        Invalidate recent SP500 data cache entries
        
        Args:
            days_back: Number of days back to invalidate
            
        Returns:
            Number of keys invalidated
        """
        if not self.redis_client:
            return 0
            
        try:
            pattern = "sp500:data:*"
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
            
            logger.info(f"🗑️ SP500 Data Cache: Invalidated {invalidated} recent entries")
            return invalidated
            
        except Exception as e:
            logger.error(f"❌ SP500 Data Cache: Error invalidating cache: {str(e)}")
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
            pattern = "sp500:data:*"
            keys = self.redis_client.keys(pattern)
            
            total_entries = len(keys)
            total_data_points = 0
            date_ranges = []
            
            # Sample some entries for statistics
            sample_size = min(20, total_entries)
            for key in keys[:sample_size]:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        data = json.loads(cached_data)
                        if self._is_cache_valid(data):
                            total_data_points += data.get('data_points', 0)
                            date_ranges.append({
                                'start': data['start_date'],
                                'end': data['end_date'],
                                'points': data.get('data_points', 0)
                            })
                except Exception:
                    pass
            
            return {
                'status': 'available',
                'total_entries': total_entries,
                'sampled_entries': len(date_ranges),
                'total_data_points': total_data_points,
                'avg_points_per_entry': total_data_points / len(date_ranges) if date_ranges else 0,
                'sample_date_ranges': date_ranges[:5]  # Show first 5 for debugging
            }
            
        except Exception as e:
            logger.error(f"❌ SP500 Data Cache: Error getting stats: {str(e)}")
            return {'status': 'error', 'error': str(e)}


# Global instance
sp500_data_cache = SP500DataCache() 