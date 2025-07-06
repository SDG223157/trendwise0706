#!/usr/bin/env python3
"""
Test script for TradingView news scraper
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.analysis.news_analyzer import NewsAnalyzer
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_news_analyzer():
    """Test the TradingView news analyzer"""
    logger.info("Testing TradingView news analyzer...")
    
    # Use the API token from environment variable
    api_token = os.getenv("APIFY_API_TOKEN", "")
    
    analyzer = NewsAnalyzer(api_token)
    
    # Test with a few popular tickers
    test_symbols = ["NASDAQ:AAPL", "NYSE:TSLA", "HKEX:700"]
    
    logger.info(f"Fetching news for symbols: {test_symbols}")
    logger.info("This will fetch from TradingView...")
    
    try:
        # Fetch with small limit for testing
        articles = analyzer.get_news(test_symbols, limit=5)
        
        logger.info(f"Total articles fetched: {len(articles)}")
        
        # Show a sample of articles
        for i, article in enumerate(articles[:3]):
            logger.info(f"Article {i+1}:")
            logger.info(f"  Title: {article.get('title', 'N/A')[:100]}...")
            logger.info(f"  Source: {article.get('scraper_type', 'unknown')}")
            logger.info(f"  News Source: {article.get('news_source', 'N/A')}")
            
        return len(articles) > 0
        
    except Exception as e:
        logger.error(f"Error in news analyzer test: {str(e)}")
        return False

def test_tradingview_scraper():
    """Test TradingView scraper directly"""
    logger.info("Testing TradingView scraper...")
    
    api_token = os.getenv("APIFY_API_TOKEN", "")
    analyzer = NewsAnalyzer(api_token)
    
    test_symbols = ["NASDAQ:AAPL"]
    
    try:
        tv_articles = analyzer._fetch_tradingview_news(test_symbols, limit=2)
        logger.info(f"TradingView articles: {len(tv_articles)}")
        if tv_articles:
            logger.info(f"Sample TradingView article: {tv_articles[0].get('title', 'N/A')[:50]}...")
        return len(tv_articles) > 0
    except Exception as e:
        logger.error(f"TradingView scraper error: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("TRADINGVIEW NEWS SCRAPER TEST")
    logger.info("=" * 50)
    
    # Test 1: TradingView scraper
    tv_success = test_tradingview_scraper()
    
    logger.info("-" * 50)
    
    # Test 2: Integrated news analyzer
    analyzer_success = test_news_analyzer()
    
    logger.info("-" * 50)
    
    if tv_success and analyzer_success:
        logger.info("✓ All tests completed successfully!")
        logger.info("TradingView news scraper is working correctly.")
    else:
        logger.error("✗ Some tests failed!")
        logger.error("Please check the error messages above.")
    
    logger.info("=" * 50) 