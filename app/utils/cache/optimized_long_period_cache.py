"""
Optimized caching strategy for long-period stock analysis (10+ years)
Balances performance with data freshness for efficient rendering
"""

import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
import pandas as pd
from app.utils.cache.enhanced_stock_cache import enhanced_stock_cache

logger = logging.getLogger(__name__)

class LongPeriodAnalysisCache:
    """
    Specialized caching for long-period analysis with smart data partitioning
    """
    
    def __init__(self):
        self.cache = enhanced_stock_cache
        
    def get_partitioned_data(self, ticker: str, lookback_days: int, end_date: str) -> Tuple[Optional[pd.DataFrame], bool]:
        """
        Get historical data using partitioned caching strategy
        
        Strategy:
        1. Historical data (older than 2 days): Cache for 24 hours
        2. Recent data (last 2 days): Cache for 5 minutes  
        3. Combine cached historical + fresh recent data
        
        Returns:
        --------
        Tuple[pd.DataFrame, bool]: (data, was_fully_cached)
        """
        try:
            end_dt = pd.to_datetime(end_date)
            start_dt = end_dt - timedelta(days=lookback_days)
            
            # Split into historical (stable) and recent (changing) parts
            cutoff_date = end_dt - timedelta(days=2)
            
            # Try to get historical part (stable, long cache)
            historical_data = self._get_historical_partition(ticker, start_dt, cutoff_date)
            
            # Try to get recent part (volatile, short cache)  
            recent_data = self._get_recent_partition(ticker, cutoff_date, end_dt)
            
            # Combine cached parts
            if historical_data is not None and recent_data is not None:
                combined_data = pd.concat([historical_data, recent_data])
                combined_data = combined_data.sort_index()
                logger.info(f"📊 Partitioned cache hit for {ticker}: {len(combined_data)} rows")
                return combined_data, True
            
            # If either part missing, return None for full fetch
            return None, False
            
        except Exception as e:
            logger.error(f"Error in partitioned data retrieval: {str(e)}")
            return None, False
    
    def set_partitioned_data(self, ticker: str, data: pd.DataFrame, lookback_days: int, end_date: str):
        """
        Cache data using partitioned strategy
        """
        try:
            end_dt = pd.to_datetime(end_date)
            cutoff_date = end_dt - timedelta(days=2)
            
            # Split data
            historical_mask = data.index <= cutoff_date
            recent_mask = data.index > cutoff_date
            
            historical_data = data[historical_mask]
            recent_data = data[recent_mask]
            
            # Cache historical part (24 hours)
            if not historical_data.empty:
                self._set_historical_partition(ticker, historical_data, expire=86400)
            
            # Cache recent part (5 minutes)  
            if not recent_data.empty:
                self._set_recent_partition(ticker, recent_data, expire=300)
                
            logger.info(f"💾 Cached partitioned data for {ticker}: {len(historical_data)} historical + {len(recent_data)} recent")
            
        except Exception as e:
            logger.error(f"Error caching partitioned data: {str(e)}")
    
    def _get_historical_partition(self, ticker: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Optional[pd.DataFrame]:
        """Get cached historical data partition"""
        cache_key = f"stock:historical:{ticker}:{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}"
        cached_data = self.cache.get_json(cache_key)
        
        if cached_data:
            # Convert back to DataFrame
            df = pd.DataFrame(cached_data['data'])
            df.index = pd.to_datetime(cached_data['index'])
            logger.debug(f"🎯 Historical partition cache hit: {ticker}")
            return df
        return None
    
    def _set_historical_partition(self, ticker: str, data: pd.DataFrame, expire: int = 86400):
        """Cache historical data partition"""
        try:
            start_date = data.index.min().strftime('%Y%m%d')
            end_date = data.index.max().strftime('%Y%m%d')
            cache_key = f"stock:historical:{ticker}:{start_date}:{end_date}"
            
            cache_data = {
                'data': data.to_dict('records'),
                'index': data.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'cached_at': datetime.now().isoformat()
            }
            
            self.cache.set_json(cache_key, cache_data, expire)
            logger.debug(f"💾 Cached historical partition: {ticker}")
            
        except Exception as e:
            logger.error(f"Error caching historical partition: {str(e)}")
    
    def _get_recent_partition(self, ticker: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Optional[pd.DataFrame]:
        """Get cached recent data partition"""
        cache_key = f"stock:recent:{ticker}:{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}"
        cached_data = self.cache.get_json(cache_key)
        
        if cached_data:
            df = pd.DataFrame(cached_data['data'])
            df.index = pd.to_datetime(cached_data['index'])
            logger.debug(f"🎯 Recent partition cache hit: {ticker}")
            return df
        return None
    
    def _set_recent_partition(self, ticker: str, data: pd.DataFrame, expire: int = 300):
        """Cache recent data partition"""
        try:
            start_date = data.index.min().strftime('%Y%m%d')
            end_date = data.index.max().strftime('%Y%m%d')
            cache_key = f"stock:recent:{ticker}:{start_date}:{end_date}"
            
            cache_data = {
                'data': data.to_dict('records'),
                'index': data.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'cached_at': datetime.now().isoformat()
            }
            
            self.cache.set_json(cache_key, cache_data, expire)
            logger.debug(f"💾 Cached recent partition: {ticker}")
            
        except Exception as e:
            logger.error(f"Error caching recent partition: {str(e)}")

    def get_progressive_analysis(self, ticker: str, lookback_days: int, end_date: str) -> Optional[Dict]:
        """
        Get progressive analysis results for large datasets
        
        Progressive strategy:
        1. Return basic chart immediately if cached
        2. Return full analysis when ready
        3. Use incremental computation for technical indicators
        """
        cache_key = f"progressive:analysis:{ticker}:{lookback_days}:{end_date}"
        return self.cache.get_json(cache_key)
    
    def set_progressive_analysis(self, ticker: str, lookback_days: int, end_date: str, 
                               analysis_data: Dict, expire: int = 1800):
        """Cache progressive analysis results (30 minutes)"""
        cache_key = f"progressive:analysis:{ticker}:{lookback_days}:{end_date}"
        self.cache.set_json(cache_key, analysis_data, expire)

    def get_compressed_chart_data(self, ticker: str, lookback_days: int, end_date: str) -> Optional[Dict]:
        """
        Get compressed chart data for faster rendering
        
        For 10+ year data:
        1. Compress daily data to weekly for overview
        2. Keep daily data for recent 3 months
        3. Use smart sampling for middle periods
        """
        cache_key = f"compressed:chart:{ticker}:{lookback_days}:{end_date}"
        return self.cache.get_json(cache_key)
    
    def set_compressed_chart_data(self, ticker: str, lookback_days: int, end_date: str, 
                                chart_data: Dict, expire: int = 3600):
        """Cache compressed chart data (1 hour)"""
        cache_key = f"compressed:chart:{ticker}:{lookback_days}:{end_date}"
        self.cache.set_json(cache_key, chart_data, expire)

# Global instance
long_period_cache = LongPeriodAnalysisCache() 