# app/utils/batch/news_batch.py

from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from ...models import NewsArticle, ArticleSymbol, ArticleMetric
import pandas as pd
from datetime import datetime
import logging

class NewsBatchProcessor:
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    def bulk_insert_articles(self, articles: List[Dict]) -> List[int]:
        """Bulk insert multiple articles"""
        try:
            # Create article instances
            article_instances = []
            for article_data in articles:
                article = NewsArticle(
                    title=article_data['title'],
                    content=article_data['content'],
                    url=article_data['url'],
                    published_at=article_data['published_at'],
                    source=article_data['source'],
                    sentiment_label=article_data['sentiment']['overall_sentiment'],
                    sentiment_score=article_data['sentiment']['confidence'],
                    brief_summary=article_data['summary']['brief'],
                    key_points=article_data['summary']['key_points'],
                    market_impact_summary=article_data['summary']['market_impact']
                )
                article_instances.append(article)

            # Bulk insert articles
            self.session.bulk_save_objects(article_instances)
            self.session.flush()

            # Get inserted IDs
            article_ids = [article.id for article in article_instances]

            # Create symbol and metric instances
            symbols = []
            metrics = []
            
            for article, article_id in zip(articles, article_ids):
                # Add symbols
                for symbol in article['symbols']:
                    symbols.append(ArticleSymbol(
                        article_id=article_id,
                        symbol=symbol
                    ))

                # Add metrics
                if 'metrics' in article:
                    for pct, context in zip(
                        article['metrics']['percentages'],
                        article['metrics']['percentage_contexts']
                    ):
                        metrics.append(ArticleMetric(
                            article_id=article_id,
                            metric_type='percentage',
                            value=pct,
                            context=context
                        ))

                    for amount, context in zip(
                        article['metrics']['currencies'],
                        article['metrics']['currency_contexts']
                    ):
                        try:
                            value = float(str(amount).replace(',', ''))
                            metrics.append(ArticleMetric(
                                article_id=article_id,
                                metric_type='currency',
                                value=value,
                                context=context
                            ))
                        except ValueError:
                            self.logger.warning(f"Invalid currency value: {amount}")

            # Bulk insert symbols and metrics
            self.session.bulk_save_objects(symbols)
            self.session.bulk_save_objects(metrics)
            self.session.commit()

            return article_ids

        except Exception as e:
            self.logger.error(f"Error in bulk insert: {e}")
            self.session.rollback()
            return []

    def export_to_csv(self, start_date: str, end_date: str, file_path: str):
        """Export articles to CSV file"""
        try:
            # Query articles
            articles = (self.session.query(NewsArticle)
                      .filter(NewsArticle.published_at.between(start_date, end_date))
                      .all())

            # Convert to DataFrame
            data = []
            for article in articles:
                row = article.to_dict()
                row['symbols'] = ','.join(row['symbols'])
                row['percentages'] = len(row['metrics']['percentages'])
                row['currencies'] = len(row['metrics']['currencies'])
                data.append(row)

            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)
            return True

        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            return False

    def import_from_csv(self, file_path: str) -> List[int]:
        """Import articles from CSV file"""
        try:
            df = pd.read_csv(file_path)
            articles = []

            for _, row in df.iterrows():
                article = {
                    'title': row['title'],
                    'content': row['content'],
                    'url': row['url'],
                    'published_at': row['published_at'],
                    'source': row['source'],
                    'sentiment': {
                        'overall_sentiment': row['sentiment_label'],
                        'confidence': row['sentiment_score']
                    },
                    'summary': {
                        'brief': row['brief_summary'],
                        'key_points': row['key_points'],
                        'market_impact': row['market_impact_summary']
                    },
                    'symbols': str(row['symbols']).split(',') if pd.notna(row['symbols']) else []
                }
                articles.append(article)

            return self.bulk_insert_articles(articles)

        except Exception as e:
            self.logger.error(f"Error importing from CSV: {e}")
            return []