# app/utils/cache/stock_cache.py

from .news_cache import NewsCache
from typing import Optional, Dict, List
import pandas as pd
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StockCache(NewsCache):
    """Extended cache for stock and financial data"""
    
    def __init__(self):
        super().__init__()
        self.stock_prefix = "stock"
        self.financial_prefix = "financial"
        self.analysis_prefix = "analysis"
        
    # Stock Price Data Caching
    def get_stock_data(self, ticker: str, start_date: str, end_date: str) -> Optional[Dict]:
        """Get cached stock price data"""
        cache_key = f"{self.stock_prefix}:price:{ticker}:{start_date}:{end_date}"
        return self.get_json(cache_key)
    
    def set_stock_data(self, ticker: str, start_date: str, end_date: str, data: pd.DataFrame, expire: int = 3600) -> bool:
        """Cache stock price data (1 hour default)"""
        cache_key = f"{self.stock_prefix}:price:{ticker}:{start_date}:{end_date}"
        # Convert DataFrame to cacheable format
        cache_data = {
            'data': data.to_dict('records'),
            'index': [str(idx) for idx in data.index],
            'columns': list(data.columns),
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, cache_data, expire)
    
    # Financial Metrics Caching
    def get_financial_data(self, ticker: str, metric: str, start_year: str, end_year: str) -> Optional[Dict]:
        """Get cached financial data"""
        cache_key = f"{self.financial_prefix}:data:{ticker}:{metric}:{start_year}:{end_year}"
        return self.get_json(cache_key)
    
    def set_financial_data(self, ticker: str, metric: str, start_year: str, end_year: str, data: pd.Series, expire: int = 7200) -> bool:
        """Cache financial data (2 hours default)"""
        cache_key = f"{self.financial_prefix}:data:{ticker}:{metric}:{start_year}:{end_year}"
        # Convert Series to cacheable format
        cache_data = {
            'values': data.tolist(),
            'years': data.index.tolist(),
            'name': data.name,
            'ticker': ticker,
            'metric': metric,
            'start_year': start_year,
            'end_year': end_year,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, cache_data, expire)
    
    def get_financial_metric(self, ticker: str, metric: str, start_year: str, end_year: str) -> Optional[Dict]:
        """Get cached financial metric data"""
        cache_key = f"{self.financial_prefix}:metric:{ticker}:{metric}:{start_year}:{end_year}"
        return self.get_json(cache_key)
    
    def set_financial_metric(self, ticker: str, metric: str, start_year: str, end_year: str, data: Dict, expire: int = 86400) -> bool:
        """Cache financial metric data (24 hours default)"""
        cache_key = f"{self.financial_prefix}:metric:{ticker}:{metric}:{start_year}:{end_year}"
        return self.set_json(cache_key, data, expire)
    
    # Company Information Caching
    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Get cached company information"""
        cache_key = f"{self.stock_prefix}:info:{ticker}"
        return self.get_json(cache_key)
    
    def set_company_info(self, ticker: str, info: Dict, expire: int = 86400) -> bool:
        """Cache company information (24 hours default)"""
        cache_key = f"{self.stock_prefix}:info:{ticker}"
        return self.set_json(cache_key, info, expire)
    
    # Stock Analysis Results Caching
    def get_analysis_result(self, ticker: str, analysis_type: str, params_hash: str) -> Optional[Dict]:
        """Get cached analysis result"""
        cache_key = f"{self.analysis_prefix}:{analysis_type}:{ticker}:{params_hash}"
        return self.get_json(cache_key)
    
    def set_analysis_result(self, ticker: str, analysis_type: str, params_hash: str, result: Dict, expire: int = 3600) -> bool:
        """Cache analysis result (1 hour default)"""
        cache_key = f"{self.analysis_prefix}:{analysis_type}:{ticker}:{params_hash}"
        return self.set_json(cache_key, result, expire)
    
    # Market Data Caching
    def get_market_data(self, market_type: str, date: str = None) -> Optional[Dict]:
        """Get cached market data (indices, sector performance, etc.)"""
        date_key = date or datetime.now().strftime('%Y-%m-%d')
        cache_key = f"{self.stock_prefix}:market:{market_type}:{date_key}"
        return self.get_json(cache_key)
    
    def set_market_data(self, market_type: str, data: Dict, date: str = None, expire: int = 1800) -> bool:
        """Cache market data (30 minutes default)"""
        date_key = date or datetime.now().strftime('%Y-%m-%d')
        cache_key = f"{self.stock_prefix}:market:{market_type}:{date_key}"
        return self.set_json(cache_key, data, expire)
    
    # Symbol Lookup and Validation Caching
    def get_symbol_validation(self, symbol: str) -> Optional[Dict]:
        """Get cached symbol validation result"""
        cache_key = f"{self.stock_prefix}:validate:{symbol.upper()}"
        return self.get_json(cache_key)
    
    def set_symbol_validation(self, symbol: str, is_valid: bool, info: Dict = None, expire: int = 43200) -> bool:
        """Cache symbol validation (12 hours default)"""
        cache_key = f"{self.stock_prefix}:validate:{symbol.upper()}"
        data = {
            'symbol': symbol.upper(),
            'is_valid': is_valid,
            'info': info or {},
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    # Historical Data Table Existence Caching
    def get_table_exists(self, table_name: str) -> Optional[bool]:
        """Get cached table existence check"""
        cache_key = f"{self.stock_prefix}:table_exists:{table_name}"
        result = self.get_json(cache_key)
        return result.get('exists') if result else None
    
    def set_table_exists(self, table_name: str, exists: bool, expire: int = 3600) -> bool:
        """Cache table existence check (1 hour default)"""
        cache_key = f"{self.stock_prefix}:table_exists:{table_name}"
        data = {'exists': exists, 'checked_at': datetime.now().isoformat()}
        return self.set_json(cache_key, data, expire)
    
    # Performance Ratios Caching
    def get_performance_ratios(self, ticker: str, period: str) -> Optional[Dict]:
        """Get cached performance ratios"""
        cache_key = f"{self.analysis_prefix}:ratios:{ticker}:{period}"
        return self.get_json(cache_key)
    
    def set_performance_ratios(self, ticker: str, period: str, ratios: Dict, expire: int = 7200) -> bool:
        """Cache performance ratios (2 hours default)"""
        cache_key = f"{self.analysis_prefix}:ratios:{ticker}:{period}"
        return self.set_json(cache_key, ratios, expire)
    
    # Trending Stocks Caching
    def get_trending_stocks(self, category: str = 'general') -> Optional[List[Dict]]:
        """Get cached trending stocks"""
        cache_key = f"{self.stock_prefix}:trending:{category}"
        return self.get_json(cache_key)
    
    def set_trending_stocks(self, stocks: List[Dict], category: str = 'general', expire: int = 900) -> bool:
        """Cache trending stocks (15 minutes default)"""
        cache_key = f"{self.stock_prefix}:trending:{category}"
        return self.set_json(cache_key, stocks, expire)
    
    # Bulk Cache Operations
    def invalidate_ticker_cache(self, ticker: str):
        """Invalidate all cache entries for a specific ticker"""
        patterns = [
            f"{self.stock_prefix}:price:{ticker}:*",
            f"{self.stock_prefix}:info:{ticker}",
            f"{self.financial_prefix}:metric:{ticker}:*",
            f"{self.analysis_prefix}:*:{ticker}:*"
        ]
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        if not self.is_available():
            return {'cache_available': False}
        
        try:
            # This would require Redis info commands
            # Simplified version for now
            return {
                'cache_available': True,
                'cache_type': 'redis',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {'cache_available': False, 'error': str(e)}

# Global instance
stock_cache = StockCache() 