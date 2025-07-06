
from datetime import datetime
from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import re
from typing import Dict, List, Optional
import logging
from apify_client import ApifyClient
import time
import random

class NewsFetcher:
    def __init__(self, api_token: str):
        """Initialize NewsFetcher with required resources"""
        self.client = ApifyClient(api_token)
        self.logger = logging.getLogger(__name__)
        
        

    def get_news(self, symbols: List[str], limit: int = 10, retries: int = 3) -> List[Dict]:
        """Fetch news from TradingView via Apify"""
        self.logger.debug(f"Fetching news for symbols: {symbols}")

        # Determine resultsLimit based on symbol regions
        results_limit = self._get_results_limit_for_symbols(symbols)
        self.logger.debug(f"Using resultsLimit: {results_limit} for symbols: {symbols}")

        run_input = {
            "symbols": symbols,
            "proxy": {"useApifyProxy": True},
            "resultsLimit": results_limit
        }

        for attempt in range(retries):
            try:
                run = self.client.actor("mscraper/tradingview-news-scraper").call(run_input=run_input)
                
                if not run or not run.get("defaultDatasetId"):
                    continue

                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                return items

            except Exception as e:
                self.logger.error(f"Error fetching news (attempt {attempt + 1}): {str(e)}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

        return []
    
    def _get_results_limit_for_symbols(self, symbols: List[str]) -> int:
        """
        Determine resultsLimit based on symbol regions:
        - China and Hong Kong symbols: 2 articles
        - Others: 5 articles
        """
        # Check if any symbol is from China or Hong Kong
        for symbol in symbols:
            if self._is_china_hk_symbol(symbol):
                self.logger.debug(f"China/HK symbol detected: {symbol}, using limit 2")
                return 2
        
        # Default limit for other regions
        self.logger.debug(f"Using default limit 5 for symbols: {symbols}")
        return 5
    
    def _is_china_hk_symbol(self, symbol: str) -> bool:
        """Check if symbol is from China or Hong Kong markets"""
        import re
        
        symbol = symbol.upper().strip()
        
        # China symbols patterns
        china_patterns = [
            r'^SSE:',           # Shanghai Stock Exchange (e.g., SSE:600519)
            r'^SZSE:',          # Shenzhen Stock Exchange (e.g., SZSE:000858)
            r'\.SS$',           # Yahoo Finance Shanghai format (e.g., 600519.SS)
            r'\.SZ$',           # Yahoo Finance Shenzhen format (e.g., 000858.SZ)
            r'^6\d{5}$',        # 6-digit Shanghai stocks starting with 6
            r'^[03]\d{5}$',     # 6-digit Shenzhen stocks starting with 0 or 3
        ]
        
        # Hong Kong symbols patterns
        hk_patterns = [
            r'^HKEX:',          # TradingView Hong Kong format (e.g., HKEX:700)
            r'\d+\.HK$',        # Yahoo Finance Hong Kong format (e.g., 0700.HK)
            r'^\d{3,5}$',       # Bare Hong Kong stock numbers (e.g., 700, 2318)
        ]
        
        # Check China patterns
        for pattern in china_patterns:
            if re.search(pattern, symbol):
                return True
        
        # Check Hong Kong patterns
        for pattern in hk_patterns:
            if re.search(pattern, symbol):
                return True
        
        return False
