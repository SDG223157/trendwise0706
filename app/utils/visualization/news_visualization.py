# app/utils/visualization/news_visualization.py

from typing import List, Dict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class NewsVisualizationService:
    @staticmethod
    def prepare_timeline_data(articles: List[Dict]) -> Dict:
        """Prepare data for sentiment timeline visualization"""
        if not articles:
            return {
                'dates': [],
                'scores': []
            }

        # Convert to DataFrame
        df = pd.DataFrame([{
            'date': datetime.strptime(a['published_at'], '%Y-%m-%d %H:%M:%S'),
            'score': a['sentiment']['score']
        } for a in articles])

        # Sort by date
        df = df.sort_values('date')

        # Group by date and calculate average sentiment
        daily = df.groupby(df['date'].dt.date)['score'].mean()

        return {
            'dates': [d.strftime('%Y-%m-%d') for d in daily.index],
            'scores': daily.values.tolist()
        }

    @staticmethod
    def calculate_sentiment_trends(articles: List[Dict]) -> Dict:
        """Calculate sentiment trends over time"""
        if not articles:
            return {
                'trend': 'No data',
                'volatility': 0,
                'momentum': 0
            }

        scores = [a['sentiment']['score'] for a in articles]
        
        # Calculate trend
        trend_slope = np.polyfit(range(len(scores)), scores, 1)[0]
        if trend_slope > 0.01:
            trend = 'Improving'
        elif trend_slope < -0.01:
            trend = 'Declining'
        else:
            trend = 'Stable'

        # Calculate volatility (standard deviation)
        volatility = np.std(scores)

        # Calculate momentum (recent vs overall average)
        recent_avg = np.mean(scores[-3:]) if len(scores) >= 3 else np.mean(scores)
        overall_avg = np.mean(scores)
        momentum = recent_avg - overall_avg

        return {
            'trend': trend,
            'volatility': float(volatility),
            'momentum': float(momentum)
        }

    @staticmethod
    def prepare_source_analysis(articles: List[Dict]) -> List[Dict]:
        """Analyze sentiment by news source"""
        if not articles:
            return []

        # Group by source
        sources = {}
        for article in articles:
            source = article['source']
            score = article['sentiment']['score']
            
            if source not in sources:
                sources[source] = {
                    'count': 0,
                    'total_score': 0,
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0
                }
            
            sources[source]['count'] += 1
            sources[source]['total_score'] += score
            
            if score > 0.05:
                sources[source]['positive'] += 1
            elif score < -0.05:
                sources[source]['negative'] += 1
            else:
                sources[source]['neutral'] += 1

        # Calculate averages and format results
        return [{
            'source': source,
            'article_count': stats['count'],
            'average_sentiment': stats['total_score'] / stats['count'],
            'sentiment_distribution': {
                'positive': stats['positive'],
                'negative': stats['negative'],
                'neutral': stats['neutral']
            }
        } for source, stats in sources.items()]