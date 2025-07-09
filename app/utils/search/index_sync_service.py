"""
Automated News Search Index Synchronization Service

This service handles background synchronization between news_articles and news_search_index
tables to ensure search index stays current with minimal manual intervention.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app import db
from app.models import NewsArticle, NewsSearchIndex
import json

logger = logging.getLogger(__name__)

class NewsIndexSyncService:
    """
    Automated synchronization service for news search index.
    
    Features:
    - Incremental sync every 5 minutes
    - Full rebuild daily at 2 AM
    - Performance monitoring and metrics
    - Automatic error recovery
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.sync_stats = {
            'last_sync': None,
            'articles_synced': 0,
            'errors': 0,
            'performance_metrics': []
        }
        
    def start_scheduler(self):
        """Start the background scheduler with sync jobs"""
        try:
            # Incremental sync every 5 minutes
            self.scheduler.add_job(
                self.incremental_sync,
                IntervalTrigger(minutes=5),
                id='incremental_sync',
                replace_existing=True,
                max_instances=1
            )
            
            # Full rebuild daily at 2 AM
            self.scheduler.add_job(
                self.full_rebuild,
                CronTrigger(hour=2, minute=0),
                id='full_rebuild',
                replace_existing=True,
                max_instances=1
            )
            
            # Cleanup old entries weekly
            self.scheduler.add_job(
                self.cleanup_old_entries,
                CronTrigger(day_of_week='sun', hour=3, minute=0),
                id='cleanup_old_entries',
                replace_existing=True,
                max_instances=1
            )
            
            self.scheduler.start()
            logger.info("✅ News Index Sync Service started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start sync scheduler: {str(e)}")
            
    def stop_scheduler(self):
        """Stop the background scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("🛑 News Index Sync Service stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping sync scheduler: {str(e)}")
    
    def incremental_sync(self):
        """Sync only new/updated articles since last sync"""
        start_time = datetime.now()
        
        try:
            # Get cutoff time (last 10 minutes to ensure no gaps)
            cutoff_time = datetime.now() - timedelta(minutes=10)
            
            # Find new or updated articles
            new_articles = db.session.query(NewsArticle).filter(
                or_(
                    NewsArticle.created_at >= cutoff_time,
                    NewsArticle.updated_at >= cutoff_time
                ),
                # Only sync articles with AI content
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_summary != '',
                NewsArticle.ai_insights != ''
            ).all()
            
            synced_count = 0
            for article in new_articles:
                if self.sync_article_to_index(article):
                    synced_count += 1
            
            # Update stats
            duration = (datetime.now() - start_time).total_seconds()
            self.sync_stats['last_sync'] = datetime.now()
            self.sync_stats['articles_synced'] += synced_count
            self.sync_stats['performance_metrics'].append({
                'type': 'incremental',
                'duration': duration,
                'articles_processed': synced_count,
                'timestamp': datetime.now()
            })
            
            # Keep only last 100 metrics
            if len(self.sync_stats['performance_metrics']) > 100:
                self.sync_stats['performance_metrics'] = self.sync_stats['performance_metrics'][-100:]
            
            logger.info(f"✅ Incremental sync completed: {synced_count} articles in {duration:.2f}s")
            
        except Exception as e:
            self.sync_stats['errors'] += 1
            logger.error(f"❌ Incremental sync failed: {str(e)}")
    
    def full_rebuild(self):
        """Full rebuild of search index"""
        start_time = datetime.now()
        
        try:
            logger.info("🔄 Starting full search index rebuild...")
            
            # Clear existing index
            db.session.query(NewsSearchIndex).delete()
            
            # Get all articles with AI content
            articles = db.session.query(NewsArticle).filter(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_summary != '',
                NewsArticle.ai_insights != ''
            ).order_by(desc(NewsArticle.published_at)).all()
            
            synced_count = 0
            batch_size = 100
            
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i+batch_size]
                
                for article in batch:
                    if self.sync_article_to_index(article):
                        synced_count += 1
                
                # Commit batch
                db.session.commit()
                
                if i % 1000 == 0:
                    logger.info(f"🔄 Processed {i}/{len(articles)} articles...")
            
            # Update stats
            duration = (datetime.now() - start_time).total_seconds()
            self.sync_stats['last_sync'] = datetime.now()
            self.sync_stats['articles_synced'] += synced_count
            self.sync_stats['performance_metrics'].append({
                'type': 'full_rebuild',
                'duration': duration,
                'articles_processed': synced_count,
                'timestamp': datetime.now()
            })
            
            logger.info(f"✅ Full rebuild completed: {synced_count} articles in {duration:.2f}s")
            
        except Exception as e:
            self.sync_stats['errors'] += 1
            logger.error(f"❌ Full rebuild failed: {str(e)}")
            db.session.rollback()
    
    def sync_article_to_index(self, article: NewsArticle) -> bool:
        """Sync single article to search index"""
        try:
            # Check if article already exists in index
            existing = db.session.query(NewsSearchIndex).filter_by(
                external_id=article.external_id
            ).first()
            
            # Extract symbols as JSON
            symbols_json = json.dumps([symbol.symbol for symbol in article.symbols])
            
            if existing:
                # Update existing entry
                existing.title = article.title
                existing.url = article.url
                existing.published_at = article.published_at
                existing.source = article.source
                existing.ai_sentiment_rating = article.ai_sentiment_rating
                existing.symbols_json = symbols_json
                existing.ai_summary = article.ai_summary
                existing.ai_insights = article.ai_insights
                existing.updated_at = datetime.now()
            else:
                # Create new entry
                index_entry = NewsSearchIndex(
                    article_id=article.id,
                    external_id=article.external_id,
                    title=article.title,
                    url=article.url,
                    published_at=article.published_at,
                    source=article.source,
                    ai_sentiment_rating=article.ai_sentiment_rating,
                    symbols_json=symbols_json,
                    ai_summary=article.ai_summary,
                    ai_insights=article.ai_insights
                )
                db.session.add(index_entry)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to sync article {article.id}: {str(e)}")
            return False
    
    def cleanup_old_entries(self):
        """Remove old entries from search index"""
        try:
            # Remove entries older than 6 months
            cutoff_date = datetime.now() - timedelta(days=180)
            
            deleted_count = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.published_at < cutoff_date
            ).delete()
            
            db.session.commit()
            
            logger.info(f"🗑️ Cleaned up {deleted_count} old search index entries")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {str(e)}")
            db.session.rollback()
    
    def get_sync_status(self) -> Dict:
        """Get current sync status and metrics"""
        try:
            # Get counts
            total_articles = db.session.query(NewsArticle).filter(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_summary != '',
                NewsArticle.ai_insights != ''
            ).count()
            
            total_indexed = db.session.query(NewsSearchIndex).count()
            
            # Get recent performance metrics
            recent_metrics = self.sync_stats['performance_metrics'][-10:] if self.sync_stats['performance_metrics'] else []
            
            avg_duration = sum(m['duration'] for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0
            
            return {
                'scheduler_running': self.scheduler.running,
                'last_sync': self.sync_stats['last_sync'],
                'total_articles': total_articles,
                'total_indexed': total_indexed,
                'sync_percentage': round((total_indexed / total_articles * 100), 2) if total_articles > 0 else 0,
                'articles_synced': self.sync_stats['articles_synced'],
                'errors': self.sync_stats['errors'],
                'average_sync_duration': round(avg_duration, 2),
                'recent_metrics': recent_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get sync status: {str(e)}")
            return {'error': str(e)}
    
    def force_sync_article(self, article_id: int) -> bool:
        """Force sync a specific article"""
        try:
            article = db.session.query(NewsArticle).get(article_id)
            if not article:
                return False
            
            success = self.sync_article_to_index(article)
            if success:
                db.session.commit()
                logger.info(f"✅ Force synced article {article_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to force sync article {article_id}: {str(e)}")
            db.session.rollback()
            return False

# Global instance
sync_service = NewsIndexSyncService() 