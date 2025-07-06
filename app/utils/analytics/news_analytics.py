# app/utils/analytics/news_analytics.py

from typing import List, Dict, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, text
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from textblob import TextBlob
import logging
from app.models import NewsArticle, ArticleSymbol, ArticleMetric

class NewsAnalytics:
    def __init__(self, session: Session):
        """Initialize NewsAnalytics with database session"""
        self.session = session
        self.logger = logging.getLogger(__name__)
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
            self.logger.error(f"Error getting news by date range: {str(e)}")
            return [], 0
    def get_sentiment_summary(self, days=7):
        return {
            'total_articles': 0,
            'average_sentiment': 0,
            'sentiment_distribution': {
                'positive': 0,
                'negative': 0,
                'neutral': 0
            }
        }
    def get_sentiment_analysis(
        self, 
        symbol: Optional[str] = None, 
        days: int = 30,
        include_metrics: bool = True
    ) -> Dict:
        """
        Get detailed sentiment analysis for a symbol or all articles
        
        Args:
            symbol (str, optional): Stock symbol to analyze
            days (int): Number of days to analyze
            include_metrics (bool): Whether to include detailed metrics
            
        Returns:
            Dict: Sentiment analysis results
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Build base query
            query = self.session.query(NewsArticle)
            
            if symbol:
                query = query.join(ArticleSymbol).filter(ArticleSymbol.symbol == symbol)
            
            query = query.filter(NewsArticle.published_at >= start_date)
            articles = query.all()
            
            if not articles:
                self.logger.warning(f"No articles found for symbol {symbol} in last {days} days")
                return self._empty_sentiment_analysis()

            # Convert to DataFrame for analysis
            df = pd.DataFrame([{
                'date': article.published_at,
                'sentiment_score': article.sentiment_score,
                'sentiment_label': article.sentiment_label,
                'title': article.title
            } for article in articles])

            analysis = {
                'total_articles': len(articles),
                'sentiment_distribution': self._get_sentiment_distribution(df),
                'sentiment_metrics': self._calculate_sentiment_metrics(df),
                'timeline_analysis': self._analyze_timeline(df),
                'latest_sentiment': self._get_latest_sentiment(df)
            }

            if include_metrics:
                analysis.update({
                    'detailed_metrics': self._calculate_detailed_metrics(articles),
                    'key_statistics': self._calculate_key_statistics(df)
                })

            return analysis

        except Exception as e:
            self.logger.error(f"Error in get_sentiment_analysis: {str(e)}")
            return self._empty_sentiment_analysis()

    def get_symbol_correlations(self, symbol: str, days: int = 30) -> List[Dict]:
        """
        Analyze correlations between different symbols
        
        Args:
            symbol (str): Base symbol to analyze correlations for
            days (int): Number of days to analyze
            
        Returns:
            List[Dict]: List of correlated symbols with metrics
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get articles for base symbol
            base_articles = set(
                article.id for article in
                self.session.query(NewsArticle.id)
                .join(ArticleSymbol)
                .filter(
                    ArticleSymbol.symbol == symbol,
                    NewsArticle.published_at >= start_date
                )
            )
            
            if not base_articles:
                return []

            # Find co-occurring symbols
            correlations = []
            
            co_symbols = (
                self.session.query(
                    ArticleSymbol.symbol,
                    func.count(ArticleSymbol.article_id).label('count')
                )
                .filter(
                    ArticleSymbol.article_id.in_(base_articles),
                    ArticleSymbol.symbol != symbol
                )
                .group_by(ArticleSymbol.symbol)
                .having(func.count(ArticleSymbol.article_id) >= 2)
                .all()
            )

            for co_symbol, count in co_symbols:
                correlation = self._calculate_symbol_correlation(
                    symbol, co_symbol, start_date
                )
                if correlation:
                    correlations.append(correlation)

            return sorted(correlations, key=lambda x: x['correlation'], reverse=True)

        except Exception as e:
            self.logger.error(f"Error in get_symbol_correlations: {str(e)}")
            return []

    def get_trending_topics(self, days: int = 7) -> List[Dict]:
        """
        Get trending topics from recent news
        
        Args:
            days (int): Number of days to analyze
            
        Returns:
            List[Dict]: Trending topics with statistics
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            articles = (
                self.session.query(NewsArticle)
                .filter(NewsArticle.published_at >= start_date)
                .all()
            )

            topics = {}
            for article in articles:
                blob = TextBlob(article.title + " " + (article.brief_summary or ""))
                
                for phrase in blob.noun_phrases:
                    if len(phrase.split()) >= 2:  # Only multi-word phrases
                        if phrase not in topics:
                            topics[phrase] = {
                                'count': 0,
                                'sentiment_sum': 0,
                                'first_seen': article.published_at
                            }
                        
                        topics[phrase]['count'] += 1
                        topics[phrase]['sentiment_sum'] += article.sentiment_score
                        topics[phrase]['first_seen'] = min(
                            topics[phrase]['first_seen'], 
                            article.published_at
                        )

            # Process and sort topics
            trending = []
            for phrase, data in topics.items():
                if data['count'] >= 3:  # Minimum occurrence threshold
                    trending.append({
                        'topic': phrase,
                        'mentions': data['count'],
                        'avg_sentiment': data['sentiment_sum'] / data['count'],
                        'first_seen': data['first_seen'].strftime("%Y-%m-%d %H:%M:%S")
                    })

            return sorted(trending, key=lambda x: x['mentions'], reverse=True)[:20]

        except Exception as e:
            self.logger.error(f"Error in get_trending_topics: {str(e)}")
            return []

    def _empty_sentiment_analysis(self) -> Dict:
        """Return empty sentiment analysis structure"""
        return {
            'total_articles': 0,
            'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
            'sentiment_metrics': {'average': 0, 'volatility': 0},
            'timeline_analysis': {'trend': 'Insufficient data'},
            'latest_sentiment': None
        }

    def _get_sentiment_distribution(self, df: pd.DataFrame) -> Dict:
        """Calculate sentiment distribution"""
        distribution = df['sentiment_label'].value_counts()
        return {
            'positive': int(distribution.get('POSITIVE', 0)),
            'negative': int(distribution.get('NEGATIVE', 0)),
            'neutral': int(distribution.get('NEUTRAL', 0))
        }

    def _calculate_sentiment_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate basic sentiment metrics"""
        return {
            'average': float(df['sentiment_score'].mean()),
            'volatility': float(df['sentiment_score'].std()),
            'median': float(df['sentiment_score'].median()),
            'max': float(df['sentiment_score'].max()),
            'min': float(df['sentiment_score'].min())
        }

    def _analyze_timeline(self, df: pd.DataFrame) -> Dict:
        """Analyze sentiment timeline"""
        if len(df) < 2:
            return {'trend': 'Insufficient data'}

        df = df.sort_values('date')
        
        # Calculate trend
        z = np.polyfit(range(len(df)), df['sentiment_score'].values, 1)
        slope = z[0]

        # Calculate moving averages
        df['MA5'] = df['sentiment_score'].rolling(window=5, min_periods=1).mean()
        df['MA10'] = df['sentiment_score'].rolling(window=10, min_periods=1).mean()

        return {
            'trend': 'Improving' if slope > 0.01 else 'Declining' if slope < -0.01 else 'Stable',
            'slope': float(slope),
            'moving_averages': {
                'MA5': df['MA5'].tolist(),
                'MA10': df['MA10'].tolist()
            }
        }

    def _get_latest_sentiment(self, df: pd.DataFrame) -> Optional[Dict]:
        """Get latest sentiment data"""
        if df.empty:
            return None

        latest = df.sort_values('date', ascending=False).iloc[0]
        return {
            'score': float(latest['sentiment_score']),
            'label': latest['sentiment_label'],
            'title': latest['title'],
            'date': latest['date'].strftime("%Y-%m-%d %H:%M:%S")
        }

    def _calculate_detailed_metrics(self, articles: List[NewsArticle]) -> Dict:
        """Calculate detailed metrics from articles"""
        metric_data = {
            'percentage': {'values': [], 'contexts': []},
            'currency': {'values': [], 'contexts': []}
        }

        for article in articles:
            for metric in article.metrics:
                if metric.metric_type in metric_data:
                    metric_data[metric.metric_type]['values'].append(metric.metric_value)
                    metric_data[metric.metric_type]['contexts'].append(metric.metric_context)

        return metric_data

    def _calculate_key_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate key statistical measures"""
        return {
            'sentiment_percentiles': {
                'p25': float(df['sentiment_score'].quantile(0.25)),
                'p50': float(df['sentiment_score'].quantile(0.50)),
                'p75': float(df['sentiment_score'].quantile(0.75))
            },
            'daily_volatility': float(
                df.groupby(df['date'].dt.date)['sentiment_score'].std().mean()
            )
        }

    def _calculate_symbol_correlation(
        self, 
        base_symbol: str, 
        compare_symbol: str, 
        start_date: datetime
    ) -> Optional[Dict]:
        """Calculate correlation between two symbols"""
        try:
            # Get sentiment scores for both symbols
            base_scores = self._get_symbol_sentiment_scores(base_symbol, start_date)
            compare_scores = self._get_symbol_sentiment_scores(compare_symbol, start_date)

            if not base_scores or not compare_scores:
                return None

            # Calculate correlation
            correlation = np.corrcoef(base_scores, compare_scores)[0, 1]

            return {
                'symbol': compare_symbol,
                'correlation': float(correlation),
                'sample_size': len(base_scores)
            }

        except Exception as e:
            self.logger.error(f"Error calculating symbol correlation: {str(e)}")
            return None

    def _get_symbol_sentiment_scores(self, symbol: str, start_date: datetime) -> List[float]:
        """Get sentiment scores for a symbol"""
        articles = (
            self.session.query(NewsArticle.sentiment_score)
            .join(ArticleSymbol)
            .filter(
                ArticleSymbol.symbol == symbol,
                NewsArticle.published_at >= start_date
            )
            .order_by(NewsArticle.published_at)
            .all()
        )
        
        return [article.sentiment_score for article in articles]