ANALYZE_CONFIG = {
    'lookback_days': 365,
    'crossover_days': 365
}

# app/utils/config/analyze_config.py

import os

class AnalyzeConfig:
    # API Configuration
    APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
    
    # Analysis Parameters
    MAX_NEWS_ARTICLES = 10
    DEFAULT_DAYS = 5
    MIN_ARTICLES = 3
    
    # Sentiment Thresholds
    SENTIMENT_POSITIVE_THRESHOLD = 0.05
    SENTIMENT_NEGATIVE_THRESHOLD = -0.05
    
    # Cache Configuration
    CACHE_EXPIRY = 3600  # 1 hour