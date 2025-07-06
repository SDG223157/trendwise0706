"""
Comprehensive company information caching system for yfinance data
Optimizes performance by caching rarely-changing company data
"""

import time
import logging
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import pandas as pd
from app.utils.cache.stock_cache import stock_cache

logger = logging.getLogger(__name__)

class CompanyInfoCache:
    """
    Specialized caching for company information from yfinance
    """
    
    def __init__(self):
        self.cache = stock_cache
        
        # Company info data categories with different cache durations
        self.cache_categories = {
            'basic_info': {
                'fields': [
                    'longName', 'shortName', 'symbol', 'sector', 'industry', 
                    'country', 'website', 'fullTimeEmployees', 'summary',
                    'city', 'state', 'zip', 'address1', 'phone', 'fax'
                ],
                'expire': 604800  # 7 days (rarely changes)
            },
            'financial_metrics': {
                'fields': [
                    'marketCap', 'enterpriseValue', 'forwardPE', 'trailingPE',
                    'priceToBook', 'debtToEquity', 'returnOnEquity', 'returnOnAssets',
                    'grossMargins', 'operatingMargins', 'profitMargins',
                    'revenueGrowth', 'earningsGrowth', 'currentRatio', 'quickRatio'
                ],
                'expire': 3600  # 1 hour (changes more frequently)
            },
            'market_data': {
                'fields': [
                    'currentPrice', 'previousClose', 'open', 'dayLow', 'dayHigh',
                    'regularMarketPreviousClose', 'regularMarketOpen', 
                    'regularMarketDayLow', 'regularMarketDayHigh', 'volume',
                    'averageVolume', 'averageVolume10days', 'marketCap'
                ],
                'expire': 300  # 5 minutes (real-time data)
            },
            'dividend_info': {
                'fields': [
                    'dividendRate', 'dividendYield', 'exDividendDate',
                    'payoutRatio', 'fiveYearAvgDividendYield', 'lastDividendValue',
                    'lastDividendDate', 'trailingAnnualDividendRate',
                    'trailingAnnualDividendYield'
                ],
                'expire': 86400  # 24 hours
            },
            'trading_info': {
                'fields': [
                    'beta', 'impliedSharesOutstanding', 'floatShares', 'sharesShort',
                    'sharesShortPriorMonth', 'shortRatio', 'shortPercentOfFloat',
                    'heldPercentInsiders', 'heldPercentInstitutions',
                    'fiftyTwoWeekLow', 'fiftyTwoWeekHigh', 'fiftyDayAverage',
                    'twoHundredDayAverage'
                ],
                'expire': 7200  # 2 hours
            },
            'business_info': {
                'fields': [
                    'businessSummary', 'longBusinessSummary', 'companyOfficers',
                    'maxAge', 'priceHint', 'currency', 'financialCurrency',
                    'exchange', 'exchangeTimezoneName', 'exchangeTimezoneShortName',
                    'gmtOffSetMilliseconds', 'market', 'messageBoardId'
                ],
                'expire': 604800  # 7 days
            }
        }
    
    def get_company_info(self, ticker: str, categories: List[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive company information with smart caching
        
        Parameters:
        -----------
        ticker : str
            Stock ticker symbol
        categories : List[str], optional
            Specific categories to retrieve. If None, gets all categories
            
        Returns:
        --------
        Dict[str, Any]
            Company information dictionary
        """
        ticker = ticker.upper()
        
        if categories is None:
            categories = list(self.cache_categories.keys())
        
        company_info = {}
        missing_categories = []
        
        # Check cache for each category
        for category in categories:
            cached_data = self._get_cached_category(ticker, category)
            if cached_data:
                company_info.update(cached_data)
                logger.debug(f"🎯 Company info cache hit for {ticker} {category}")
            else:
                missing_categories.append(category)
        
        # Fetch missing categories from yfinance
        if missing_categories:
            fresh_data = self._fetch_from_yfinance(ticker, missing_categories)
            if fresh_data:
                company_info.update(fresh_data)
                # Cache the fresh data by category
                self._cache_by_categories(ticker, fresh_data)
        
        return company_info
    
    def get_basic_company_info(self, ticker: str) -> Dict[str, Any]:
        """Get essential company information (most commonly used)"""
        return self.get_company_info(ticker, ['basic_info', 'financial_metrics'])
    
    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Get current market data (real-time pricing info)"""
        return self.get_company_info(ticker, ['market_data'])
    
    def get_financial_ratios(self, ticker: str) -> Dict[str, Any]:
        """Get financial ratios and metrics"""
        return self.get_company_info(ticker, ['financial_metrics', 'trading_info'])
    
    def refresh_company_info(self, ticker: str, categories: List[str] = None) -> Dict[str, Any]:
        """
        Force refresh company information (bypass cache)
        """
        ticker = ticker.upper()
        
        if categories is None:
            categories = list(self.cache_categories.keys())
        
        fresh_data = self._fetch_from_yfinance(ticker, categories)
        if fresh_data:
            self._cache_by_categories(ticker, fresh_data)
            return fresh_data
        
        return {}
    
    def _get_cached_category(self, ticker: str, category: str) -> Optional[Dict[str, Any]]:
        """Get cached data for a specific category"""
        cache_key = f"company:{category}:{ticker}"
        return self.cache.get_json(cache_key)
    
    def _cache_by_categories(self, ticker: str, data: Dict[str, Any]):
        """Cache data organized by categories"""
        for category, config in self.cache_categories.items():
            category_data = {}
            
            # Extract fields for this category
            for field in config['fields']:
                if field in data:
                    category_data[field] = data[field]
            
            if category_data:
                cache_key = f"company:{category}:{ticker}"
                
                # Add metadata
                category_data['_cached_at'] = datetime.now().isoformat()
                category_data['_category'] = category
                category_data['_ticker'] = ticker
                
                self.cache.set_json(cache_key, category_data, config['expire'])
                logger.debug(f"💾 Cached company {category} for {ticker} (expires in {config['expire']}s)")
    
    def _fetch_from_yfinance(self, ticker: str, categories: List[str]) -> Dict[str, Any]:
        """Fetch company information from yfinance"""
        start_time = time.time()
        
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            if not info:
                logger.warning(f"No company info found for {ticker}")
                return {}
            
            # Extract requested fields
            requested_fields = set()
            for category in categories:
                requested_fields.update(self.cache_categories[category]['fields'])
            
            # Filter to only requested fields that exist
            filtered_info = {}
            for field in requested_fields:
                if field in info:
                    filtered_info[field] = info[field]
            
            duration = time.time() - start_time
            logger.info(f"✅ Fetched company info for {ticker} in {duration:.2f}s ({len(filtered_info)} fields)")
            
            return filtered_info
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error fetching company info for {ticker}: {str(e)} (took {duration:.2f}s)")
            return {}
    
    def bulk_cache_company_info(self, tickers: List[str], batch_size: int = 10) -> Dict[str, bool]:
        """
        Bulk cache company information for multiple tickers
        Useful for warming the cache
        """
        results = {}
        
        logger.info(f"🔄 Bulk caching company info for {len(tickers)} tickers")
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            
            for ticker in batch:
                try:
                    company_info = self.get_company_info(ticker)
                    results[ticker] = bool(company_info)
                    
                    if company_info:
                        logger.debug(f"✅ Cached {ticker}: {len(company_info)} fields")
                    else:
                        logger.warning(f"❌ Failed to cache {ticker}")
                        
                except Exception as e:
                    logger.error(f"Error caching {ticker}: {str(e)}")
                    results[ticker] = False
                
                # Brief pause to avoid rate limiting
                time.sleep(0.1)
            
            # Longer pause between batches
            if i + batch_size < len(tickers):
                logger.info(f"📊 Processed {i + batch_size}/{len(tickers)} tickers, pausing...")
                time.sleep(1)
        
        successful = sum(results.values())
        logger.info(f"🏆 Bulk caching completed: {successful}/{len(tickers)} successful")
        
        return results
    
    def get_cache_stats(self, ticker: str = None) -> Dict[str, Any]:
        """Get cache statistics for company information"""
        stats = {
            'categories': {},
            'total_cached': 0,
            'cache_efficiency': {}
        }
        
        if ticker:
            # Stats for specific ticker
            ticker = ticker.upper()
            for category in self.cache_categories:
                cache_key = f"company:{category}:{ticker}"
                cached_data = self.cache.get_json(cache_key)
                stats['categories'][category] = {
                    'cached': bool(cached_data),
                    'fields': len(cached_data) if cached_data else 0,
                    'cached_at': cached_data.get('_cached_at') if cached_data else None
                }
                if cached_data:
                    stats['total_cached'] += 1
        
        return stats
    
    def clear_company_cache(self, ticker: str = None):
        """Clear company information cache"""
        if ticker:
            ticker = ticker.upper()
            for category in self.cache_categories:
                cache_key = f"company:{category}:{ticker}"
                self.cache.delete(cache_key)
            logger.info(f"🧹 Cleared company cache for {ticker}")
        else:
            # This would require iterating through all keys, which is expensive
            # Better to let cache expire naturally
            logger.warning("⚠️  Clear all company cache not implemented (use TTL expiration)")

# Global instance
company_info_cache = CompanyInfoCache() 