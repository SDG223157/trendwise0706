from typing import Dict, List, Optional
import logging
from apify_client import ApifyClient
import time
import re

class InvestingNewsScraperError(Exception):
    """Custom exception for Investing News Scraper errors"""
    pass

class InvestingNewsScraper:
    def __init__(self, api_token: str):
        """Initialize InvestingNewsScraper with Apify client"""
        if not api_token or api_token.strip() == "" or api_token == "MISSING_API_TOKEN":
            self.logger = logging.getLogger(__name__)
            self.logger.error("❌ Invalid or missing APIFY_API_TOKEN for Investing.com scraper")
            self.logger.error("Investing.com news fetching will be disabled")
            self.client = None
            return
            
        self.client = ApifyClient(api_token)
        self.logger = logging.getLogger(__name__)
        
    def convert_tradingview_to_investing_ticker(self, tradingview_ticker: str) -> str:
        """
        Convert TradingView ticker format to Investing.com format (Yahoo Finance symbol without exchange)
        
        This ensures the output matches Yahoo Finance symbol format without exchange suffix:
        - HKEX:0700 -> 0700 (Yahoo: 0700.HK)
        - NYSE:AAPL -> AAPL (Yahoo: AAPL)
        - SSE:600519 -> 600519 (Yahoo: 600519.SS)
        
        Args:
            tradingview_ticker: TradingView format ticker (e.g., "HKEX:700", "NYSE:AAPL", "SSE:600519")
            
        Returns:
            str: Yahoo Finance compatible symbol without exchange suffix (e.g., "700", "AAPL", "600519")
        """
        if not tradingview_ticker:
            return tradingview_ticker
            
        # Remove exchange prefix to get Yahoo Finance symbol part
        if ':' in tradingview_ticker:
            exchange, ticker = tradingview_ticker.split(':', 1)
            # Return ticker symbol as-is to match Yahoo Finance format without exchange suffix
            # Examples:
            # - HKEX:0700 → 0700 (Yahoo Finance: 0700.HK)  
            # - NYSE:AAPL → AAPL (Yahoo Finance: AAPL)
            # - SSE:600519 → 600519 (Yahoo Finance: 600519.SS)
            return ticker
        
        # If no exchange prefix, return as-is
        return tradingview_ticker
    
    def get_news(self, symbols: List[str], limit: int = 10, retries: int = 3) -> List[Dict]:
        """
        Fetch news from Investing.com via Apify with post-scraping filtering
        
        Note: The Apify Actor often returns more articles than requested via maxItems
        parameter due to fast scraping process. This method applies post-scraping
        filtering to ensure exact limit compliance.
        
        Args:
            symbols: List of symbols in TradingView format
            limit: Number of articles to fetch per symbol (strictly enforced)
            retries: Number of retry attempts
            
        Returns:
            List[Dict]: List of news articles (exactly 'limit' articles or fewer)
        """
        # Check if client is properly initialized
        if not self.client:
            self.logger.warning("⚠️ Investing.com scraper not initialized due to missing API token")
            return []
            
        self.logger.debug(f"Fetching Investing.com news for symbols: {symbols}")
        
        # Convert TradingView symbols to Investing format
        investing_tickers = []
        symbol_mapping = {}  # Track original -> converted mapping
        
        for symbol in symbols:
            investing_ticker = self.convert_tradingview_to_investing_ticker(symbol)
            investing_tickers.append(investing_ticker)
            symbol_mapping[investing_ticker] = symbol
            
        self.logger.debug(f"Converted to Investing.com format: {investing_tickers}")
        
        # Prepare run input for Investing News Scraper
        # Based on the user's example, it needs both "tickers" and "ids" arrays
        run_input = {
            "tickers": investing_tickers,
            "ids": ["26490"],  # Using default id from user's example
            "maxItems": limit,  # Control number of articles fetched
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyCountry": "US",
            },
        }
        
        # Debug logging to track limit parameter (Apify Actor may return more than requested)
        self.logger.debug(f"Investing scraper called with limit={limit}, tickers={investing_tickers}")
        
        all_articles = []
        
        for attempt in range(retries):
            try:
                self.logger.info(f"Starting Investing.com news fetch (attempt {attempt + 1}/{retries})")
                
                # Run the Actor
                run = self.client.actor("mscraper/investing-news-scraper").call(run_input=run_input)
                
                if not run or not run.get("defaultDatasetId"):
                    self.logger.warning(f"No dataset returned from Investing scraper (attempt {attempt + 1})")
                    continue
                
                # Fetch results
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                
                if items:
                    # Add source information and restore original symbol format
                    for item in items:
                        if isinstance(item, dict):
                            item['news_source'] = 'investing.com'
                            item['scraper_type'] = 'investing'
                            
                            # Try to map back to original TradingView format if ticker is available
                            article_ticker = item.get('ticker', '')
                            if article_ticker in symbol_mapping:
                                item['original_symbol'] = symbol_mapping[article_ticker]
                    
                    # POST-SCRAPING FILTERING: Apify Actor returns more articles than requested
                    # Apply strict limit here since maxItems parameter is not reliable
                    original_count = len(items)
                    if len(items) > limit:
                        items = items[:limit]  # Take only the first 'limit' articles
                        self.logger.info(f"🔧 POST-FILTER: Limited {original_count} articles to {limit} (Apify returned more than requested)")
                    
                    all_articles.extend(items)
                    self.logger.info(f"🔍 DEBUG: Final result after filtering: {len(items)} articles (limit was {limit})")
                    self.logger.info(f"Successfully fetched {len(items)} articles from Investing.com")
                    return all_articles
                else:
                    self.logger.warning(f"No articles returned from Investing scraper (attempt {attempt + 1})")
                    
            except Exception as e:
                self.logger.error(f"Error fetching Investing news (attempt {attempt + 1}): {str(e)}")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    raise InvestingNewsScraperError(f"Failed to fetch Investing news after {retries} attempts: {str(e)}")
        
        return all_articles
    
    def get_supported_exchanges(self) -> Dict[str, str]:
        """
        Get mapping of supported exchanges
        
        Returns:
            Dict[str, str]: Mapping of exchange codes to names
        """
        return {
            'HKEX': 'Hong Kong Stock Exchange',
            'NYSE': 'New York Stock Exchange', 
            'NASDAQ': 'NASDAQ',
            'SSE': 'Shanghai Stock Exchange',
            'SZSE': 'Shenzhen Stock Exchange',
            'TSE': 'Tokyo Stock Exchange',
            'LSE': 'London Stock Exchange',
            # Add more as needed
        }
    
    def validate_ticker_format(self, ticker: str) -> bool:
        """
        Validate if ticker is in correct format for Investing.com
        
        Args:
            ticker: Ticker symbol to validate
            
        Returns:
            bool: True if valid format
        """
        if not ticker or not isinstance(ticker, str):
            return False
            
        # Basic validation - should not contain exchange prefix
        return ':' not in ticker and len(ticker.strip()) > 0 