#!/usr/bin/env python3
"""
Script to populate news search index table from existing news articles.
Run this after creating the search index table migration.
"""

import os
import sys
import logging
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from sqlalchemy import text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def populate_search_index(batch_size=1000):
    """
    Populate the news search index from existing news articles.
    
    Args:
        batch_size (int): Number of articles to process at once
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Get total count of articles
            total_count = NewsArticle.query.count()
            logger.info(f"📊 Total articles to process: {total_count}")
            
            if total_count == 0:
                logger.warning("⚠️ No articles found to process")
                return
            
            # Clear existing search index
            existing_count = NewsSearchIndex.query.count()
            if existing_count > 0:
                logger.info(f"🗑️ Clearing {existing_count} existing search index entries...")
                NewsSearchIndex.query.delete()
                db.session.commit()
            
            processed = 0
            skipped = 0
            errors = 0
            
            # Process articles in batches
            for offset in range(0, total_count, batch_size):
                logger.info(f"📦 Processing batch {offset//batch_size + 1} (articles {offset + 1} to {min(offset + batch_size, total_count)})")
                
                # Get batch of articles with their symbols
                articles = (NewsArticle.query
                           .options(db.joinedload(NewsArticle.symbols))
                           .offset(offset)
                           .limit(batch_size)
                           .all())
                
                batch_search_entries = []
                
                for article in articles:
                    try:
                        # Skip articles without required fields
                        if not article.external_id or not article.published_at:
                            logger.warning(f"⚠️ Skipping article {article.id}: missing external_id or published_at")
                            skipped += 1
                            continue
                        
                        # Create search index entry
                        search_entry = NewsSearchIndex.create_from_article(article)
                        batch_search_entries.append(search_entry)
                        processed += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing article {article.id}: {str(e)}")
                        errors += 1
                        continue
                
                # Bulk insert the batch
                if batch_search_entries:
                    try:
                        db.session.bulk_save_objects(batch_search_entries)
                        db.session.commit()
                        logger.info(f"✅ Saved {len(batch_search_entries)} search entries")
                    except Exception as e:
                        logger.error(f"❌ Error saving batch: {str(e)}")
                        db.session.rollback()
                        errors += len(batch_search_entries)
                
                # Progress update
                progress = ((offset + batch_size) / total_count) * 100
                logger.info(f"📈 Progress: {progress:.1f}% ({processed} processed, {skipped} skipped, {errors} errors)")
            
            # Final summary
            logger.info(f"🎉 Population complete!")
            logger.info(f"   ✅ Processed: {processed}")
            logger.info(f"   ⚠️ Skipped: {skipped}")
            logger.info(f"   ❌ Errors: {errors}")
            logger.info(f"   📊 Total in search index: {NewsSearchIndex.query.count()}")
            
        except Exception as e:
            logger.error(f"❌ Fatal error: {str(e)}")
            db.session.rollback()
            raise

def cleanup_old_articles(days_to_keep=90):
    """
    Clean up old articles from the main news_articles table after search index is populated.
    
    Args:
        days_to_keep (int): Number of days of articles to keep in the main table
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Count articles to be deleted
            old_articles_count = NewsArticle.query.filter(
                NewsArticle.published_at < cutoff_date
            ).count()
            
            if old_articles_count == 0:
                logger.info("✅ No old articles to cleanup")
                return
            
            logger.info(f"🗑️ Found {old_articles_count} articles older than {days_to_keep} days")
            
            # Confirm deletion
            confirm = input(f"Are you sure you want to delete {old_articles_count} old articles? (yes/no): ")
            if confirm.lower() != 'yes':
                logger.info("❌ Cleanup cancelled")
                return
            
            # Delete old articles (cascade will handle related records)
            deleted = NewsArticle.query.filter(
                NewsArticle.published_at < cutoff_date
            ).delete(synchronize_session=False)
            
            db.session.commit()
            logger.info(f"✅ Deleted {deleted} old articles")
            
            # Vacuum the database to reclaim space
            logger.info("🧹 Vacuuming database to reclaim space...")
            db.session.execute(text("VACUUM"))
            db.session.commit()
            logger.info("✅ Database vacuum complete")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {str(e)}")
            db.session.rollback()
            raise

def sync_search_index():
    """
    Sync search index with any new articles that might have been added.
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Find articles not in search index
            missing_articles = db.session.query(NewsArticle).filter(
                ~NewsArticle.id.in_(
                    db.session.query(NewsSearchIndex.article_id)
                )
            ).all()
            
            if not missing_articles:
                logger.info("✅ Search index is up to date")
                return
            
            logger.info(f"📦 Found {len(missing_articles)} articles to sync")
            
            synced = 0
            errors = 0
            
            for article in missing_articles:
                try:
                    # Skip articles without required fields
                    if not article.external_id or not article.published_at:
                        continue
                    
                    search_entry = NewsSearchIndex.create_from_article(article)
                    db.session.add(search_entry)
                    synced += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error syncing article {article.id}: {str(e)}")
                    errors += 1
            
            if synced > 0:
                db.session.commit()
                logger.info(f"✅ Synced {synced} articles to search index")
            
            if errors > 0:
                logger.warning(f"⚠️ {errors} articles failed to sync")
            
        except Exception as e:
            logger.error(f"❌ Error during sync: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description='Manage news search index')
    parser.add_argument('action', choices=['populate', 'cleanup', 'sync'], 
                       help='Action to perform')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for processing (default: 1000)')
    parser.add_argument('--keep-days', type=int, default=90,
                       help='Days to keep in main table during cleanup (default: 90)')
    
    args = parser.parse_args()
    
    if args.action == 'populate':
        logger.info("🚀 Starting search index population...")
        populate_search_index(batch_size=args.batch_size)
    elif args.action == 'cleanup':
        logger.info("🧹 Starting old articles cleanup...")
        cleanup_old_articles(days_to_keep=args.keep_days)
    elif args.action == 'sync':
        logger.info("🔄 Starting search index sync...")
        sync_search_index()
    
    logger.info("✅ Script completed successfully!") 