# app/utils/cache/enhanced_stock_cache.py

import pandas as pd
import numpy as np
import hashlib
import json
import pickle
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, timedelta
import logging

from app.utils.cache.stock_cache import StockCache

logger = logging.getLogger(__name__)

class EnhancedStockCache(StockCache):
    """Enhanced stock cache with analysis-specific optimizations"""
    
    def __init__(self):
        super().__init__()
        self.yfinance_prefix = "yfinance"
        self.analysis_prefix = "analysis" 
        self.visualization_prefix = "viz"
        self.performance_prefix = "perf"
        
    def _generate_params_hash(self, params: Dict) -> str:
        """Generate hash for parameters to create unique cache keys"""
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        return hashlib.md5(sorted_params.encode()).hexdigest()[:12]
    
    # ==================== YFINANCE DATA CACHING ====================
    
    def get_yfinance_data(self, ticker: str, period: str, interval: str = "1d") -> Optional[pd.DataFrame]:
        """Get cached yfinance data"""
        cache_key = f"{self.yfinance_prefix}:data:{ticker.upper()}:{period}:{interval}"
        cached_data = self.get_json(cache_key)
        
        if cached_data:
            try:
                # Reconstruct DataFrame from cached data
                df = pd.DataFrame(cached_data['data'])
                df.index = pd.to_datetime(cached_data['index'])
                df.columns = cached_data['columns']
                
                logger.debug(f"🎯 yfinance cache hit: {ticker} {period} {interval}")
                return df
            except Exception as e:
                logger.error(f"Error reconstructing yfinance data: {str(e)}")
                return None
        
        return None
    
    def set_yfinance_data(self, ticker: str, period: str, interval: str, data: pd.DataFrame, expire: int = 3600) -> bool:
        """Cache yfinance data (1 hour default)"""
        cache_key = f"{self.yfinance_prefix}:data:{ticker.upper()}:{period}:{interval}"
        
        try:
            # Convert DataFrame to cacheable format
            cache_data = {
                'data': data.to_dict('records'),
                'index': [str(idx) for idx in data.index],
                'columns': list(data.columns),
                'ticker': ticker.upper(),
                'period': period,
                'interval': interval,
                'cached_at': datetime.now().isoformat(),
                'rows': len(data)
            }
            
            success = self.set_json(cache_key, cache_data, expire)
            if success:
                logger.info(f"💾 Cached yfinance data: {ticker} {period} {interval} ({len(data)} rows)")
            return success
            
        except Exception as e:
            logger.error(f"Error caching yfinance data: {str(e)}")
            return False
    
    # ==================== MULTI-PERIOD ANALYSIS CACHING ====================
    
    def get_multi_period_analysis(self, ticker: str, period: str) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
        """Get cached multi-period analysis (daily, weekly, monthly)"""
        cache_key = f"{self.analysis_prefix}:multi:{ticker.upper()}:{period}"
        cached_data = self.get_json(cache_key)
        
        if cached_data:
            try:
                # Reconstruct all three DataFrames
                daily_df = self._reconstruct_dataframe(cached_data['daily'])
                weekly_df = self._reconstruct_dataframe(cached_data['weekly'])  
                monthly_df = self._reconstruct_dataframe(cached_data['monthly'])
                
                logger.debug(f"🎯 Multi-period analysis cache hit: {ticker} {period}")
                return daily_df, weekly_df, monthly_df
                
            except Exception as e:
                logger.error(f"Error reconstructing multi-period analysis: {str(e)}")
                return None
        
        return None
    
    def set_multi_period_analysis(self, ticker: str, period: str, 
                                daily_data: pd.DataFrame, weekly_data: pd.DataFrame, 
                                monthly_data: pd.DataFrame, expire: int = 1800) -> bool:
        """Cache multi-period analysis (30 minutes default)"""
        cache_key = f"{self.analysis_prefix}:multi:{ticker.upper()}:{period}"
        
        try:
            cache_data = {
                'daily': self._serialize_dataframe(daily_data),
                'weekly': self._serialize_dataframe(weekly_data),
                'monthly': self._serialize_dataframe(monthly_data),
                'ticker': ticker.upper(),
                'period': period,
                'cached_at': datetime.now().isoformat()
            }
            
            success = self.set_json(cache_key, cache_data, expire)
            if success:
                logger.info(f"💾 Cached multi-period analysis: {ticker} {period}")
            return success
            
        except Exception as e:
            logger.error(f"Error caching multi-period analysis: {str(e)}")
            return False
    
    # ==================== COMPLETE ANALYSIS CACHING ====================
    
    def get_complete_analysis(self, ticker: str, period: str, params: Dict = None) -> Optional[Dict]:
        """Get complete cached analysis result"""
        params = params or {}
        params_hash = self._generate_params_hash(params)
        cache_key = f"{self.analysis_prefix}:complete:{ticker.upper()}:{period}:{params_hash}"
        
        cached_result = self.get_json(cache_key)
        if cached_result:
            logger.debug(f"🎯 Complete analysis cache hit: {ticker} {period}")
            return cached_result
        
        return None
    
    def set_complete_analysis(self, ticker: str, period: str, params: Dict, result: Dict, expire: int = 900) -> bool:
        """Cache complete analysis result (15 minutes default)"""
        params_hash = self._generate_params_hash(params)
        cache_key = f"{self.analysis_prefix}:complete:{ticker.upper()}:{period}:{params_hash}"
        
        try:
            cache_data = {
                **result,  # Spread the result data
                'ticker': ticker.upper(),
                'period': period,
                'params': params,
                'cached_at': datetime.now().isoformat()
            }
            
            success = self.set_json(cache_key, cache_data, expire)
            if success:
                logger.info(f"💾 Cached complete analysis: {ticker} {period}")
            return success
            
        except Exception as e:
            logger.error(f"Error caching complete analysis: {str(e)}")
            return False
    
    # ==================== PLOTLY VISUALIZATION CACHING ====================
    
    def get_plotly_figure(self, ticker: str, period: str, chart_type: str = "dashboard", params: Dict = None) -> Optional[Dict]:
        """Get cached Plotly figure"""
        params = params or {}
        params_hash = self._generate_params_hash(params)
        cache_key = f"{self.visualization_prefix}:{chart_type}:{ticker.upper()}:{period}:{params_hash}"
        
        cached_figure = self.get_json(cache_key)
        if cached_figure:
            logger.debug(f"🎯 Plotly figure cache hit: {ticker} {period} {chart_type}")
            return cached_figure
        
        return None
    
    def set_plotly_figure(self, ticker: str, period: str, chart_type: str, params: Dict, 
                         figure_dict: Dict, expire: int = 600) -> bool:
        """Cache Plotly figure (10 minutes default)"""
        params_hash = self._generate_params_hash(params)
        cache_key = f"{self.visualization_prefix}:{chart_type}:{ticker.upper()}:{period}:{params_hash}"
        
        try:
            cache_data = {
                'figure': figure_dict,
                'ticker': ticker.upper(),
                'period': period,
                'chart_type': chart_type,
                'params': params,
                'cached_at': datetime.now().isoformat()
            }
            
            success = self.set_json(cache_key, cache_data, expire)
            if success:
                logger.info(f"💾 Cached Plotly figure: {ticker} {period} {chart_type}")
            return success
            
        except Exception as e:
            logger.error(f"Error caching Plotly figure: {str(e)}")
            return False
    
    # ==================== PERFORMANCE TRACKING ====================
    
    def track_analysis_performance(self, ticker: str, operation: str, duration: float, cache_hit: bool = False):
        """Track analysis performance metrics"""
        try:
            perf_key = f"{self.performance_prefix}:timing:{ticker.upper()}:{operation}"
            
            # Get existing performance data
            perf_data = self.get_json(perf_key) or {
                'operation': operation,
                'ticker': ticker.upper(),
                'total_requests': 0,
                'cache_hits': 0,
                'total_duration': 0,
                'min_duration': float('inf'),
                'max_duration': 0,
                'last_updated': None
            }
            
            # Update performance metrics
            perf_data['total_requests'] += 1
            if cache_hit:
                perf_data['cache_hits'] += 1
            perf_data['total_duration'] += duration
            perf_data['min_duration'] = min(perf_data['min_duration'], duration)
            perf_data['max_duration'] = max(perf_data['max_duration'], duration)
            perf_data['avg_duration'] = perf_data['total_duration'] / perf_data['total_requests']
            perf_data['cache_hit_rate'] = (perf_data['cache_hits'] / perf_data['total_requests']) * 100
            perf_data['last_updated'] = datetime.now().isoformat()
            
            # Cache performance data for 24 hours
            self.set_json(perf_key, perf_data, expire=86400)
            
        except Exception as e:
            logger.error(f"Error tracking performance: {str(e)}")
    
    def get_performance_stats(self, ticker: str = None) -> Dict:
        """Get performance statistics"""
        try:
            if ticker:
                # Get stats for specific ticker
                pattern = f"{self.performance_prefix}:timing:{ticker.upper()}:*"
            else:
                # Get all performance stats
                pattern = f"{self.performance_prefix}:timing:*"
            
            stats = {}
            # Note: This would require implementing scan_pattern method in base class
            # For now, return empty dict
            return stats
            
        except Exception as e:
            logger.error(f"Error getting performance stats: {str(e)}")
            return {}
    
    # ==================== CACHE MANAGEMENT ====================
    
    def invalidate_ticker_cache(self, ticker: str):
        """Invalidate all cache entries for a ticker"""
        ticker = ticker.upper()
        patterns = [
            f"{self.yfinance_prefix}:*:{ticker}:*",
            f"{self.analysis_prefix}:*:{ticker}:*", 
            f"{self.visualization_prefix}:*:{ticker}:*",
            f"{self.performance_prefix}:*:{ticker}:*"
        ]
        
        for pattern in patterns:
            try:
                self.delete_pattern(pattern)
                logger.info(f"💥 Invalidated cache pattern: {pattern}")
            except Exception as e:
                logger.error(f"Error invalidating cache pattern {pattern}: {str(e)}")
    
    def warm_popular_stocks(self, tickers: List[str], periods: List[str] = None):
        """Warm cache for popular stocks (would be called by background job)"""
        periods = periods or ["1y", "2y", "5y"]
        
        logger.info(f"🔥 Starting cache warming for {len(tickers)} tickers")
        
        for ticker in tickers:
            for period in periods:
                # Check if already cached
                if not self.get_yfinance_data(ticker, period):
                    logger.info(f"🔥 Warming cache for {ticker} {period}")
                    # This would trigger actual data fetching in background
                    # Implementation would depend on your background job system
    
    # ==================== HELPER METHODS ====================
    
    def _serialize_dataframe(self, df: pd.DataFrame) -> Dict:
        """Serialize DataFrame for caching"""
        return {
            'data': df.to_dict('records'),
            'index': [str(idx) for idx in df.index],
            'columns': list(df.columns),
            'rows': len(df)
        }
    
    def _reconstruct_dataframe(self, cached_data: Dict) -> pd.DataFrame:
        """Reconstruct DataFrame from cached data"""
        df = pd.DataFrame(cached_data['data'])
        df.index = pd.to_datetime(cached_data['index'])
        df.columns = cached_data['columns']
        return df
    
    def get_cache_stats(self) -> Dict:
        """Get overall cache statistics"""
        return {
            'cache_available': self.is_available(),
            'cache_prefixes': [
                self.yfinance_prefix,
                self.analysis_prefix, 
                self.visualization_prefix,
                self.performance_prefix
            ],
            'status': 'operational' if self.is_available() else 'unavailable'
        }

# Global enhanced stock cache instance
enhanced_stock_cache = EnhancedStockCache() 