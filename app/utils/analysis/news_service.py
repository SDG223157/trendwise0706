# app/utils/analysis/news_service.py

import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import traceback
from app.utils.config.news_config import NewsConfig
from app.utils.data.news_service import NewsService
from .news_analyzer import NewsAnalyzer
from app.models import NewsArticle, ArticleSymbol  # Add at top
from sqlalchemy import func, or_  # Add this import
from app import db  # Add this import
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class NewsAnalysisService:
    def __init__(self):
        """Initialize the news analysis service"""
        self.logger = logging.getLogger(__name__)
        
        # Get API token from environment
        api_token = os.getenv("APIFY_API_TOKEN")
        if not api_token:
            self.logger.error("❌ APIFY_API_TOKEN environment variable is not set!")
            self.logger.error("Please set APIFY_API_TOKEN in your deployment environment")
            # Use a dummy token that will fail gracefully
            api_token = "MISSING_API_TOKEN"
        
        self.analyzer = NewsAnalyzer(api_token)
        self.db = NewsService()

    def get_news_by_date_range(self, start_date, end_date, symbol=None, page=1, per_page=20):
        try:
            return self.db.get_articles_by_date_range(
                start_date=start_date,
                end_date=end_date,
                symbol=symbol,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            self.logger.error(f"Error getting articles by date range: {str(e)}")
            return [], 0

    def get_sentiment_summary(self, days=7, symbol=None):
        """Get detailed sentiment analysis including daily breakdown"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            articles, total = self.db.get_articles_by_date_range(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                symbol=symbol
            )
            
            if not articles:
                return {
                    "average_sentiment": 0,
                    "daily_sentiment": {},
                    "highest_day": {"date": None, "value": 0},
                    "lowest_day": {"date": None, "value": 0},
                    "total_articles": 0
                }

            # Group articles by date
            daily_data = {}
            for article in articles:
                date_str = article['published_at'][:10]  # Extract YYYY-MM-DD
                sentiment = article['summary']['ai_sentiment_rating'] or 0
                
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'total_sentiment': 0,
                        'article_count': 0
                    }
                
                daily_data[date_str]['total_sentiment'] += sentiment
                daily_data[date_str]['article_count'] += 1

            # Calculate daily averages and find extremes
            daily_sentiment = {}
            max_sentiment = -float('inf')
            min_sentiment = float('inf')
            total_sentiment = 0
            total_articles = 0
            
            for date, data in daily_data.items():
                avg = data['total_sentiment'] / data['article_count']
                daily_sentiment[date] = {
                    'average_sentiment': avg,
                    'article_count': data['article_count']
                }
                
                total_sentiment += data['total_sentiment']
                total_articles += data['article_count']
                
                if avg > max_sentiment:
                    max_sentiment = avg
                    max_date = date
                    
                if avg < min_sentiment:
                    min_sentiment = avg
                    min_date = date

            return {
                "average_sentiment": total_sentiment / total_articles if total_articles else 0,
                "daily_sentiment": daily_sentiment,
                "highest_day": {
                    "date": max_date,
                    "value": round(max_sentiment, 1)
                },
                "lowest_day": {
                    "date": min_date,
                    "value": round(min_sentiment, 1)
                },
                "total_articles": total_articles
            }
            
        except Exception as e:
            self.logger.error(f"Error getting sentiment summary: {str(e)}")
            return {
                "average_sentiment": 0,
                "daily_sentiment": {},
                "highest_day": {"date": None, "value": 0},
                "lowest_day": {"date": None, "value": 0},
                "total_articles": 0
            }

    def search_articles(self, keyword=None, symbol=None, start_date=None, 
                       end_date=None, sentiment=None, page=1, per_page=20):
        """
        Search articles (renamed from search_news to match route expectations)
        """
        try:
            return self.db.search_articles(
                keyword=keyword,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                sentiment=sentiment,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            self.logger.error(f"Error searching articles: {str(e)}")
            return [], 0

    def close(self):
        """Clean up resources"""
        try:
            if hasattr(self.db, 'engine'):
                self.db.engine.dispose()
        except Exception as e:
            self.logger.error(f"Error closing resources: {str(e)}")
        
    def fetch_and_analyze_news(self, symbols, limit=10, timeout=30):
        """Fetch and analyze news for the given symbols with improved error handling"""
        try:
            self.logger.info(f"Starting news fetch for symbols: {symbols} with limit={limit}")
            
            if not symbols or not isinstance(symbols, list) or not isinstance(limit, int) or limit < 0:
                self.logger.error(f"Invalid input parameters: symbols={symbols}, limit={limit}")
                return []
            
            # Handle limit = 0 case (smart limiting - skip fetching)
            if limit == 0:
                self.logger.info(f"Limit is 0 for symbols {symbols} - skipping fetch (smart limiting)")
                return []

            # Connect with retries and longer timeouts
            session = requests.Session()
            retries = Retry(total=3, 
                          backoff_factor=0.5,
                          status_forcelist=[429, 500, 502, 503, 504])
            
            session.mount('https://', HTTPAdapter(max_retries=retries))
            
            # Normalize symbols (some exchanges need special handling)
            # For now, use symbols as-is since the NewsAnalyzer handles dual-source conversion
            normalized_symbols = symbols
            
            # 1. Fetch raw news from TradingView
            raw_articles = self.analyzer.get_news(symbols, limit)
            self.logger.info(f"Fetched {len(raw_articles)} raw articles from TradingView")
            
            if not raw_articles:
                return []
            
            # 2. Process and analyze articles
            analyzed_articles = []
            for idx, article in enumerate(raw_articles, 1):
                try:
                    if not article:
                        continue
                        
                    # Analyze article
                    analyzed = self.analyzer.analyze_article(article)
                    if not analyzed or not self._validate_article(analyzed):
                        continue
                    
                    # Save to database
                    article_id = self.db.save_article(analyzed)
                    if article_id:
                        analyzed['id'] = article_id
                        analyzed_articles.append(analyzed)
                    
                except Exception as e:
                    self.logger.error(f"Error processing article {idx}: {str(e)}")
                    continue
            
            return analyzed_articles
            
        except Exception as e:
            self.logger.error(f"Error in fetch_and_analyze_news: {str(e)}")
            return []

    def get_trending_topics(self, days: int = NewsConfig.TRENDING_DAYS) -> List[Dict]:
        """
        Get trending topics from recent news
        
        Args:
            days (int): Number of days to analyze
            
        Returns:
            List[Dict]: Trending topics with statistics
        """
        try:
            return self.db.get_trending_topics(days)
        except Exception as e:
            self.logger.error(f"Error getting trending topics: {str(e)}")
            return []
    
    def _validate_article(self, article: Dict) -> bool:
        """Validate required article fields"""
        required_fields = ['external_id', 'title', 'published_at']
        return all(article.get(field) for field in required_fields)

    def get_articles_by_date_range(
        self,
        start_date: str,
        end_date: str,
        symbol: str = None,
        page: int = 1,
        per_page: int = 20
    ):
        """Get articles within date range"""
        try:
            return self.db.search_articles(
                start_date=start_date,
                end_date=end_date,
                symbol=symbol,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            self.logger.error(f"Error getting articles by date range: {str(e)}")
            return [], 0

    def search_news(
        self,
        keyword: str = None,
        symbol: str = None,
        start_date: str = None,
        end_date: str = None,
        sentiment: str = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict], int]:
        """Search news articles with various filters"""
        try:
            return self.db.search_articles(
                keyword=keyword,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                sentiment=sentiment,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            self.logger.error(f"Error searching articles: {str(e)}")
            return [], 0

    def get_article_by_id(self, article_id: int) -> Optional[Dict]:
        """Get article by ID"""
        try:
            return self.db.get_article_by_id(article_id)
        except Exception as e:
            self.logger.error(f"Error getting article by ID: {str(e)}")
            return None

    def get_article_by_external_id(self, external_id: str) -> Optional[Dict]:
        """Get article by external ID"""
        try:
            return self.db.get_article_by_external_id(external_id)
        except Exception as e:
            self.logger.error(f"Error getting article by external ID: {str(e)}")
            return None

    def close(self):
        """Clean up resources"""
        try:
            self.db.close()
        except Exception as e:
            self.logger.error(f"Error closing resources: {str(e)}")

    def get_sentiment_timeseries(self, symbol: str, days: int, symbol_filter=None):
        """Get daily sentiment averages for a specific symbol or all articles"""
        # Get latest article date
        query = db.session.query(func.max(NewsArticle.published_at))
        if symbol.lower() == 'all':
            pass
        elif isinstance(symbol_filter, (list, tuple)):
            query = query.join(NewsArticle.symbols)
            query = query.filter(or_(*symbol_filter))
        else:
            query = query.join(NewsArticle.symbols)\
                .filter(func.upper(ArticleSymbol.symbol) == symbol.upper())
        latest_article = query.scalar()
            
        end_date = latest_article if latest_article else datetime.now()
        start_date = end_date - timedelta(days=days)

        # Base query for sentiment analysis
        query = db.session.query(
            func.date(NewsArticle.published_at).label('date'),
            func.avg(NewsArticle.ai_sentiment_rating).label('avg_sentiment'),
            func.count(NewsArticle.id).label('article_count')
        )

        # Apply symbol filter only if not "all"
        if symbol.lower() == 'all':
            pass
        elif isinstance(symbol_filter, (list, tuple)):
            query = query.join(NewsArticle.symbols)
            query = query.filter(or_(*symbol_filter))
        else:
            query = query.join(NewsArticle.symbols)\
                .filter(func.upper(ArticleSymbol.symbol) == symbol.upper())

        # Apply date range and other filters
        query = query.filter(
            NewsArticle.published_at >= start_date,
            NewsArticle.published_at <= end_date,
            NewsArticle.ai_sentiment_rating.isnot(None)
        ).group_by(func.date(NewsArticle.published_at)).order_by('date')

        results = query.all()

        # Process articles into daily buckets
        date_dict = {}
        for result in results:
            date_str = result[0].strftime('%Y-%m-%d')
            if date_str not in date_dict:
                date_dict[date_str] = {
                    'total_sentiment': 0,
                    'count': 0
                }
            date_dict[date_str]['total_sentiment'] += float(result[1]) if result[1] else 0
            date_dict[date_str]['count'] += result[2]

        # Calculate averages and format response
        result = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            daily_data = date_dict.get(date_str, {'total_sentiment': 0, 'count': 0})
            result[date_str] = {
                'average_sentiment': round(daily_data['total_sentiment'] / daily_data['count'], 2) if daily_data['count'] > 0 else 0,
                'article_count': daily_data['count']
            }
            current_date += timedelta(days=1)

        return result