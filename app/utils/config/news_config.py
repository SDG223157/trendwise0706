# app/utils/config/news_config.py
import os
class NewsConfig:
    # Database configuration
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'your_username',
        'password': 'your_password',
        'database': 'news_analysis'
    }
    
    # API configuration
    APIFY_TOKEN = os.getenv('APIFY_TOKEN')
    
    # Analysis configuration
    MAX_ARTICLES = 50
    DEFAULT_SUMMARY_LENGTH = 3
    MIN_WORD_LENGTH = 3
    
    # Trending topics configuration
    TRENDING_DAYS = 7
    MIN_TOPIC_MENTIONS = 2
    
    # Excluded words for topic analysis
    EXCLUDED_WORDS = {
        'this', 'that', 'with', 'from', 'what', 'where', 'when',
        'have', 'your', 'will', 'about', 'they', 'their'
    }
    
    # Market-related terms for impact analysis
    MARKET_TERMS = {
        'revenue', 'profit', 'earnings', 'growth', 'decline', 
        'market', 'stock', 'shares', 'price', 'trading',
        'valuation', 'forecast', 'guidance', 'outlook'
    }
    