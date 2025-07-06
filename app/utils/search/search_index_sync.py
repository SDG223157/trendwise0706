# app/utils/search/search_index_sync.py

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...models import NewsArticle, NewsSearchIndex
from ... import db

logger = logging.getLogger(__name__)

class SearchIndexSyncService:
    """
    Service to keep the news search index synchronized with the main news_articles table.
    
    This service handles:
    1. Adding new articles to the search index
    2. Updating existing articles in the search index
    3. Removing deleted articles from the search index
    4. Periodic cleanup of old articles
    """
    
    def __init__(self, session: Session = None):
        self.session = session or db.session
        self.logger = logger
    
    def sync_article(self, article: NewsArticle) -> bool:
        """
        Sync a single article to the search index.
        
        Args:
            article: The NewsArticle instance to sync
            
        Returns:
            bool: True if sync was successful, False otherwise
        """
        try:
            # Skip articles without required fields
            if not article.external_id or not article.published_at:
                self.logger.warning(f"⚠️ Skipping article {article.id}: missing external_id or published_at")
                return False
            
            # Check if article already exists in search index
            existing_entry = self.session.query(NewsSearchIndex).filter_by(
                external_id=article.external_id
            ).first()
            
            if existing_entry:
                # Update existing entry
                existing_entry.update_from_article(article)
                self.logger.debug(f"✏️ Updated search index for article {article.id}")
            else:
                # Create new entry
                search_entry = NewsSearchIndex.create_from_article(article)
                self.session.add(search_entry)
                self.logger.debug(f"➕ Added article {article.id} to search index")
            
            self.session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error syncing article {article.id} to search index: {str(e)}")
            self.session.rollback()
            return False
    
    def sync_multiple_articles(self, articles: List[NewsArticle]) -> Dict[str, int]:
        """
        Sync multiple articles to the search index efficiently.
        
        Args:
            articles: List of NewsArticle instances to sync
            
        Returns:
            Dict with counts of added, updated, skipped, and error articles
        """
        stats = {'added': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        if not articles:
            return stats
        
        try:
            # Get existing external_ids for efficient lookup
            external_ids = [article.external_id for article in articles if article.external_id]
            existing_entries = {}
            
            if external_ids:
                existing_query = self.session.query(NewsSearchIndex).filter(
                    NewsSearchIndex.external_id.in_(external_ids)
                )
                for entry in existing_query:
                    existing_entries[entry.external_id] = entry
            
            # Process each article
            for article in articles:
                try:
                    # Skip articles without required fields
                    if not article.external_id or not article.published_at:
                        stats['skipped'] += 1
                        continue
                    
                    if article.external_id in existing_entries:
                        # Update existing entry
                        existing_entries[article.external_id].update_from_article(article)
                        stats['updated'] += 1
                    else:
                        # Create new entry
                        search_entry = NewsSearchIndex.create_from_article(article)
                        self.session.add(search_entry)
                        stats['added'] += 1
                        
                except Exception as e:
                    self.logger.error(f"❌ Error processing article {article.id}: {str(e)}")
                    stats['errors'] += 1
            
            # Commit all changes
            self.session.commit()
            
            self.logger.info(f"📊 Bulk sync completed: {stats['added']} added, {stats['updated']} updated, "
                           f"{stats['skipped']} skipped, {stats['errors']} errors")
            
        except Exception as e:
            self.logger.error(f"❌ Error in bulk sync: {str(e)}")
            self.session.rollback()
            stats['errors'] = len(articles)
        
        return stats
    
    def sync_new_articles(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        Sync any new articles that aren't in the search index.
        
        Args:
            batch_size: Number of articles to process at once
            
        Returns:
            Dict with sync statistics
        """
        stats = {'added': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        try:
            # Find articles not in search index
            missing_articles_query = self.session.query(NewsArticle).filter(
                ~NewsArticle.id.in_(
                    self.session.query(NewsSearchIndex.article_id)
                )
            )
            
            total_missing = missing_articles_query.count()
            
            if total_missing == 0:
                self.logger.info("✅ Search index is up to date")
                return stats
            
            self.logger.info(f"📦 Found {total_missing} articles to sync")
            
            # Process in batches
            for offset in range(0, total_missing, batch_size):
                batch = missing_articles_query.offset(offset).limit(batch_size).all()
                batch_stats = self.sync_multiple_articles(batch)
                
                # Aggregate stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                self.logger.info(f"📈 Processed batch {offset//batch_size + 1}: "
                               f"{batch_stats['added']} added, {batch_stats['errors']} errors")
            
            self.logger.info(f"🎉 Sync completed: {stats['added']} articles added to search index")
            
        except Exception as e:
            self.logger.error(f"❌ Error syncing new articles: {str(e)}")
            stats['errors'] = -1  # Indicate system error
        
        return stats
    
    def remove_deleted_articles(self) -> int:
        """
        Remove articles from search index that no longer exist in the main table.
        
        Returns:
            int: Number of articles removed
        """
        try:
            # Find search index entries with no corresponding article
            orphaned_entries = self.session.query(NewsSearchIndex).filter(
                ~NewsSearchIndex.article_id.in_(
                    self.session.query(NewsArticle.id)
                )
            ).all()
            
            if not orphaned_entries:
                self.logger.info("✅ No orphaned search index entries found")
                return 0
            
            # Remove orphaned entries
            removed_count = 0
            for entry in orphaned_entries:
                self.session.delete(entry)
                removed_count += 1
            
            self.session.commit()
            
            self.logger.info(f"🗑️ Removed {removed_count} orphaned search index entries")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"❌ Error removing orphaned entries: {str(e)}")
            self.session.rollback()
            return -1
    
    def cleanup_old_articles(self, days_to_keep: int = 90) -> int:
        """
        Remove old articles from the main news_articles table while keeping search index.
        
        Args:
            days_to_keep: Number of days of articles to keep in the main table
            
        Returns:
            int: Number of articles removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Count old articles
            old_articles_count = self.session.query(NewsArticle).filter(
                NewsArticle.published_at < cutoff_date
            ).count()
            
            if old_articles_count == 0:
                self.logger.info("✅ No old articles to cleanup")
                return 0
            
            self.logger.info(f"🗑️ Found {old_articles_count} articles older than {days_to_keep} days")
            
            # Before deleting, make sure these articles are in the search index
            old_articles = self.session.query(NewsArticle).filter(
                NewsArticle.published_at < cutoff_date
            ).all()
            
            # Sync old articles to search index before deletion
            self.logger.info("📤 Syncing old articles to search index before deletion...")
            sync_stats = self.sync_multiple_articles(old_articles)
            
            if sync_stats['errors'] > 0:
                self.logger.warning(f"⚠️ {sync_stats['errors']} articles failed to sync. Proceeding with caution.")
            
            # Delete old articles (this will cascade to related tables)
            deleted_count = self.session.query(NewsArticle).filter(
                NewsArticle.published_at < cutoff_date
            ).delete(synchronize_session=False)
            
            self.session.commit()
            
            self.logger.info(f"✅ Deleted {deleted_count} old articles from main table")
            
            # Vacuum the database to reclaim space
            self.logger.info("🧹 Vacuuming database to reclaim space...")
            self.session.execute(text("VACUUM"))
            self.session.commit()
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"❌ Error during cleanup: {str(e)}")
            self.session.rollback()
            return -1
    
    def full_sync_status(self) -> Dict:
        """
        Get comprehensive sync status information.
        
        Returns:
            Dict with sync status details
        """
        try:
            main_table_count = self.session.query(NewsArticle).count()
            search_index_count = self.session.query(NewsSearchIndex).count()
            
            # Count articles missing from search index
            missing_from_index = self.session.query(NewsArticle).filter(
                ~NewsArticle.id.in_(
                    self.session.query(NewsSearchIndex.article_id)
                )
            ).count()
            
            # Count orphaned search index entries
            orphaned_entries = self.session.query(NewsSearchIndex).filter(
                ~NewsSearchIndex.article_id.in_(
                    self.session.query(NewsArticle.id)
                )
            ).count()
            
            # Get date ranges
            main_oldest = self.session.query(NewsArticle.published_at).order_by(
                NewsArticle.published_at.asc()
            ).first()
            main_newest = self.session.query(NewsArticle.published_at).order_by(
                NewsArticle.published_at.desc()
            ).first()
            
            index_oldest = self.session.query(NewsSearchIndex.published_at).order_by(
                NewsSearchIndex.published_at.asc()
            ).first()
            index_newest = self.session.query(NewsSearchIndex.published_at).order_by(
                NewsSearchIndex.published_at.desc()
            ).first()
            
            return {
                'main_table_count': main_table_count,
                'search_index_count': search_index_count,
                'missing_from_index': missing_from_index,
                'orphaned_entries': orphaned_entries,
                'sync_percentage': (search_index_count / main_table_count * 100) if main_table_count > 0 else 0,
                'main_table_date_range': {
                    'oldest': main_oldest[0].isoformat() if main_oldest and main_oldest[0] else None,
                    'newest': main_newest[0].isoformat() if main_newest and main_newest[0] else None
                },
                'search_index_date_range': {
                    'oldest': index_oldest[0].isoformat() if index_oldest and index_oldest[0] else None,
                    'newest': index_newest[0].isoformat() if index_newest and index_newest[0] else None
                },
                'is_sync_needed': missing_from_index > 0 or orphaned_entries > 0,
                'last_checked': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting sync status: {str(e)}")
            return {'error': str(e)}

# Convenience function for external use
def sync_article_to_search_index(article: NewsArticle) -> bool:
    """
    Convenience function to sync a single article to the search index.
    
    Args:
        article: The NewsArticle instance to sync
        
    Returns:
        bool: True if sync was successful
    """
    sync_service = SearchIndexSyncService()
    return sync_service.sync_article(article)

def sync_articles_to_search_index(articles: List[NewsArticle]) -> Dict[str, int]:
    """
    Convenience function to sync multiple articles to the search index.
    
    Args:
        articles: List of NewsArticle instances to sync
        
    Returns:
        Dict with sync statistics
    """
    sync_service = SearchIndexSyncService()
    return sync_service.sync_multiple_articles(articles) 