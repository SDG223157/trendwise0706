#!/usr/bin/env python3
"""
Automated News AI Processing Scheduler

This service automatically processes news articles with AI summaries and insights
every 4 hours without manual intervention. It replaces the need to manually
click "Update AI Summaries" by running continuously in the background.

Features:
- Runs every 4 hours automatically
- Processes up to 20 articles per run
- Generates AI summaries, insights, and sentiment ratings
- Built-in rate limiting and error handling
- Web-based management interface
"""

import os
import threading
import time
import logging
import schedule
import requests
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from flask import current_app
from openai import OpenAI

# Import models for auto-sync functionality  
from app.models import NewsArticle

# 🔑 AUTOMATIC KEYWORD EXTRACTION: Import the auto keyword extraction service
from app.utils.keywords.auto_keyword_extraction import AutoKeywordExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsAIScheduler:
    """Automated scheduler for processing news articles with AI summaries and insights"""
    
    def __init__(self):
        """Initialize the scheduler"""
        self.running = False
        self.scheduler_thread = None
        self.flask_app = None
        self.engine = None
        self.Session = None
        self.max_articles_per_run = 10
        self.content_truncate_limit = 10000  # Increased for DeepSeek V3's 16,384 token context
        
    def init_app(self, app):
        """Initialize with Flask app context"""
        self.flask_app = app
        
        # Create database engine
        db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        logger.info("📅 News AI Scheduler initialized successfully")
        
    def start(self):
        """Start the automated scheduler"""
        if self.running:
            logger.warning("⚠️ Scheduler is already running")
            return
            
        if not os.getenv('OPENROUTER_API_KEY'):
            logger.error("❌ OPENROUTER_API_KEY is required for AI processing")
            raise ValueError("OPENROUTER_API_KEY is required for AI processing")
            
        self.running = True
        
        # Clear any existing scheduled jobs
        schedule.clear()
        
        # Schedule the job to run every 10 minutes with proper context
        schedule.every(10).minutes.do(self._run_scheduled_job)
        
        # Optional: Also run daily at midnight for maintenance
        schedule.every().day.at("00:00").do(self._run_scheduled_job)
        
        # Start the scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("🤖 Automated news AI processing scheduler started successfully!")
        logger.info("⏰ Will process articles every 10 minutes automatically")
        
        # Run immediately when scheduler starts
        logger.info("⚡ Running initial AI processing job immediately...")
        initial_thread = threading.Thread(
            target=self._run_initial_job, 
            daemon=False, 
            name="NewsAISchedulerInitial"
        )
        initial_thread.start()
        logger.info("⚡ Initial AI processing job started in background")
        
    def stop(self):
        """Stop the automated scheduler"""
        if not self.running:
            logger.warning("⚠️ Scheduler is not running")
            return
            
        self.running = False
        schedule.clear()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            # Give the thread time to finish current job
            self.scheduler_thread.join(timeout=5)
            
        logger.info("🛑 Automated news AI processing scheduler stopped")
        
    def _run_scheduler(self):
        """Internal method to run the scheduler loop"""
        logger.info("📅 Scheduler thread started")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {str(e)}")
                time.sleep(60)  # Continue after error
                
        logger.info("📅 Scheduler thread stopped")
        
    def _run_scheduled_job(self):
        """Run the scheduled AI processing job with proper Flask app context"""
        try:
            logger.info("⏰ Scheduled AI processing job triggered (every 10 minutes)")
            
            # Ensure we have proper Flask app context
            if hasattr(self, 'flask_app') and self.flask_app:
                with self.flask_app.app_context():
                    self.run_processing_job()
                    logger.info("⏰ Scheduled AI processing job completed")
            else:
                # Fallback: try to get or create app context
                try:
                    from flask import current_app
                    self.run_processing_job()
                    logger.info("⏰ Scheduled AI processing job completed")
                except RuntimeError:
                    # No app context available, create one
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        self.run_processing_job()
                        logger.info("⏰ Scheduled AI processing job completed")
                        
        except Exception as e:
            logger.error(f"❌ Error in scheduled AI processing job: {str(e)}", exc_info=True)
    
    def _run_initial_job(self):
        """Run the initial AI processing job when scheduler starts"""
        try:
            logger.info("⚡ Initial AI processing job triggered (scheduler start)")
            
            # Ensure we have proper Flask app context
            if hasattr(self, 'flask_app') and self.flask_app:
                with self.flask_app.app_context():
                    self.run_processing_job()
                    logger.info("⚡ Initial AI processing job completed")
            else:
                # Fallback: try to get or create app context
                try:
                    from flask import current_app
                    self.run_processing_job()
                    logger.info("⚡ Initial AI processing job completed")
                except RuntimeError:
                    # No app context available, create one
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        self.run_processing_job()
                        logger.info("⚡ Initial AI processing job completed")
                        
        except Exception as e:
            logger.error(f"❌ Error in initial AI processing job: {str(e)}", exc_info=True)
        
    @contextmanager
    def get_db_session(self):
        """Get database session with proper cleanup"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            
    def get_unprocessed_articles(self, session):
        """Get articles that need AI processing - must have both missing AI fields AND substantial content"""
        query = text("""
            SELECT id, title, content, url, published_at, ai_summary, ai_insights, ai_sentiment_rating
            FROM news_articles 
            WHERE content IS NOT NULL 
            AND content != ''
            AND CHAR_LENGTH(TRIM(content)) > 20
            AND (ai_summary IS NULL OR ai_insights IS NULL OR ai_sentiment_rating IS NULL)
            ORDER BY id DESC
            LIMIT :limit
        """)
        
        result = session.execute(query, {"limit": self.max_articles_per_run})
        return result.fetchall()
        
    def get_total_unprocessed_count(self, session):
        """Get total count of ALL articles that need AI processing (no limit)"""
        query = text("""
            SELECT COUNT(*) as total_count
            FROM news_articles 
            WHERE content IS NOT NULL 
            AND content != ''
            AND CHAR_LENGTH(TRIM(content)) > 20
            AND (ai_summary IS NULL OR ai_insights IS NULL OR ai_sentiment_rating IS NULL)
        """)
        
        result = session.execute(query)
        return result.fetchone().total_count
    
    def _cleanup_unprocessable_articles(self, session):
        """
        Delete articles that don't meet AI processing requirements to avoid repeated checking.
        
        Requirements for AI processing:
        - Content must not be NULL or empty
        - Content must have more than 20 characters (substantial content)
        
        Articles that fail these checks will never be processable and should be removed.
        
        Returns:
            dict: Statistics about the cleanup operation
        """
        try:
            # Import here to avoid circular imports
            from ...models import NewsArticle, ArticleSymbol, ArticleMetric
            
            # Find articles that don't meet AI processing requirements
            unprocessable_query = text("""
                SELECT id, title, content, external_id
                FROM news_articles
                WHERE (
                    content IS NULL 
                    OR content = ''
                    OR CHAR_LENGTH(TRIM(content)) <= 20
                )
                AND (ai_summary IS NULL OR ai_insights IS NULL OR ai_sentiment_rating IS NULL)
                LIMIT 100
            """)
            
            unprocessable_articles = session.execute(unprocessable_query).fetchall()
            
            stats = {
                'deleted': 0,
                'errors': 0,
                'total_candidates': len(unprocessable_articles)
            }
            
            if not unprocessable_articles:
                logger.debug("🔍 No unprocessable articles found for cleanup")
                return stats
            
            logger.info(f"🗑️ Found {len(unprocessable_articles)} articles that don't meet AI processing requirements")
            
            deleted_count = 0
            
            for article_data in unprocessable_articles:
                try:
                    # Get the full article object
                    article = session.query(NewsArticle).get(article_data.id)
                    if not article:
                        continue
                    
                    # Log the reason for deletion
                    reason = "empty content"
                    if article.content is None:
                        reason = "NULL content"
                    elif article.content == '':
                        reason = "empty content"
                    elif len(article.content.strip()) <= 20:
                        reason = f"insufficient content ({len(article.content.strip())} chars)"
                    
                    # Delete the article (CASCADE will handle related records)
                    session.delete(article)
                    deleted_count += 1
                    
                    logger.debug(f"🗑️ Deleted unprocessable article {article_data.id}: '{article_data.title[:50]}...' (reason: {reason})")
                    
                except Exception as e:
                    logger.error(f"❌ Error deleting unprocessable article {article_data.id}: {str(e)}")
                    stats['errors'] += 1
                    continue
            
            # Commit the cleanup
            session.commit()
            
            stats['deleted'] = deleted_count
            
            if deleted_count > 0:
                logger.info(f"✅ Cleanup completed: {deleted_count} unprocessable articles removed from buffer")
                logger.info(f"🧹 These articles will no longer be checked for AI processing")
                
                # Log sample of deleted articles
                if len(unprocessable_articles) > 0:
                    sample_articles = unprocessable_articles[:3]
                    logger.info("🗑️ Sample unprocessable articles removed:")
                    for article in sample_articles:
                        content_len = len(article.content.strip()) if article.content else 0
                        logger.info(f"   • {article.title[:60]}... (content: {content_len} chars)")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error in unprocessable articles cleanup: {str(e)}")
            session.rollback()  # Rollback on error to maintain data integrity
            return {
                'deleted': 0,
                'errors': 1,
                'total_candidates': 0,
                'error_message': str(e)
            }
    
    def _batch_sync_missing_articles(self, session):
        """
        Batch sync AI-processed articles that are missing from search index.
        This prevents frequent individual syncs and database lock issues.
        
        Returns:
            dict: Statistics about the sync operation
        """
        try:
            # Import here to avoid circular imports
            from ...utils.search.search_index_sync import SearchIndexSyncService
            from ...models import NewsSearchIndex
            
            # 🔍 IMPROVED DUPLICATE DETECTION: Use more robust query to find truly missing articles
            missing_articles_query = text("""
                SELECT DISTINCT na.id, na.external_id, na.title
                FROM news_articles na
                WHERE na.ai_summary IS NOT NULL 
                AND na.ai_insights IS NOT NULL 
                AND na.ai_summary != '' 
                AND na.ai_insights != ''
                AND na.external_id IS NOT NULL
                AND na.external_id NOT IN (
                    SELECT DISTINCT nsi.external_id 
                    FROM news_search_index nsi 
                    WHERE nsi.external_id IS NOT NULL
                )
                LIMIT 50
            """)
            
            missing_articles_data = session.execute(missing_articles_query).fetchall()
            
            # Count already synced articles for reporting with exact match
            already_synced_query = text("""
                SELECT COUNT(DISTINCT na.external_id) as synced_count
                FROM news_articles na
                WHERE na.ai_summary IS NOT NULL 
                AND na.ai_insights IS NOT NULL 
                AND na.ai_summary != '' 
                AND na.ai_insights != ''
                AND na.external_id IS NOT NULL
                AND na.external_id IN (
                    SELECT DISTINCT nsi.external_id 
                    FROM news_search_index nsi 
                    WHERE nsi.external_id IS NOT NULL
                )
            """)
            
            already_synced_count = session.execute(already_synced_query).fetchone().synced_count
            
            # 🔍 DUPLICATE CHECK: Double-check to ensure no duplicates will be created
            if missing_articles_data:
                external_ids_to_check = [row.external_id for row in missing_articles_data]
                existing_in_index = session.query(NewsSearchIndex.external_id).filter(
                    NewsSearchIndex.external_id.in_(external_ids_to_check)
                ).all()
                existing_external_ids = {row.external_id for row in existing_in_index}
                
                # Filter out articles that are already in index
                truly_missing = [
                    row for row in missing_articles_data 
                    if row.external_id not in existing_external_ids
                ]
                
                logger.info(f"🔍 Duplicate check: {len(missing_articles_data)} initially found, "
                           f"{len(existing_external_ids)} already exist, "
                           f"{len(truly_missing)} truly missing")
                
                missing_articles_data = truly_missing
            
            stats = {
                'synced': 0,
                'already_synced': already_synced_count,
                'errors': 0,
                'total_missing': len(missing_articles_data),
                'duplicates_prevented': 0
            }
            
            if not missing_articles_data:
                logger.info("✅ No AI-processed articles need syncing to search index")
                return stats
            
            logger.info(f"🔄 Found {len(missing_articles_data)} AI-processed articles that truly need syncing")
            
            # Get full article objects for sync - with additional validation
            article_ids = [row.id for row in missing_articles_data]
            articles_to_sync = session.query(NewsArticle).filter(
                NewsArticle.id.in_(article_ids)
            ).all()
            
            # Final validation: ensure articles have required fields
            validated_articles = []
            for article in articles_to_sync:
                if (article.external_id and article.published_at and 
                    article.ai_summary and article.ai_insights and
                    article.ai_summary.strip() and article.ai_insights.strip()):
                    validated_articles.append(article)
                else:
                    logger.warning(f"⚠️ Skipping article {article.id}: missing required fields")
            
            if validated_articles:
                logger.info(f"📦 Batch syncing {len(validated_articles)} validated articles to search index...")
                
                # Use SearchIndexSyncService for efficient batch sync
                sync_service = SearchIndexSyncService(session)
                sync_results = sync_service.sync_multiple_articles(validated_articles)
                
                stats['synced'] = sync_results['added']  # Only count additions, not updates
                stats['errors'] = sync_results['errors']
                stats['duplicates_prevented'] = sync_results['updated']  # Updates mean duplicates were prevented
                
                logger.info(f"✅ Batch sync completed: {stats['synced']} new articles synced, "
                           f"{stats['duplicates_prevented']} duplicates prevented, {stats['errors']} errors")
                
                # Log sample of synced articles
                if len(missing_articles_data) > 0:
                    sample_articles = missing_articles_data[:3]
                    logger.info("📰 Sample synced articles:")
                    for article in sample_articles:
                        logger.info(f"   • {article.title[:80]}...")
            else:
                logger.info("⚠️ No validated articles to sync after filtering")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error in batch sync: {str(e)}")
            return {
                'synced': 0,
                'already_synced': 0,
                'errors': 1,
                'total_missing': 0,
                'error_message': str(e)
            }
    
    def _clear_synced_articles_from_buffer(self, session):
        """
        Clear AI-processed articles from news_articles table after they've been synced to search index.
        This transforms news_articles into a buffer table for incoming articles.
        
        Returns:
            dict: Statistics about the buffer clearing operation
        """
        try:
            # Import here to avoid circular imports
            from ...models import NewsSearchIndex, ArticleSymbol, ArticleMetric, NewsArticle
            
            # 🔍 SAFETY CHECK: Find AI-processed articles that are confirmed to be in search index
            synced_articles_query = text("""
                SELECT DISTINCT na.id, na.external_id, na.title
                FROM news_articles na
                INNER JOIN news_search_index nsi ON na.external_id = nsi.external_id
                WHERE na.ai_summary IS NOT NULL 
                AND na.ai_insights IS NOT NULL 
                AND na.ai_summary != '' 
                AND na.ai_insights != ''
                AND na.external_id IS NOT NULL
                AND nsi.ai_summary IS NOT NULL
                AND nsi.ai_insights IS NOT NULL
                LIMIT 100
            """)
            
            synced_articles_data = session.execute(synced_articles_query).fetchall()
            
            # Count remaining buffer articles
            remaining_buffer_query = text("""
                SELECT COUNT(*) as remaining_count
                FROM news_articles na
                WHERE na.external_id IS NOT NULL
                AND (na.ai_summary IS NULL OR na.ai_insights IS NULL 
                     OR na.ai_summary = '' OR na.ai_insights = '')
            """)
            
            remaining_buffer_count = session.execute(remaining_buffer_query).fetchone().remaining_count
            
            stats = {
                'cleared': 0,
                'already_cleared': 0,
                'remaining_buffer': remaining_buffer_count,
                'errors': 0,
                'total_candidates': len(synced_articles_data)
            }
            
            if not synced_articles_data:
                logger.info("🔍 No AI-processed articles found in both tables to clear from buffer")
                return stats
            
            logger.info(f"🗄️ Found {len(synced_articles_data)} AI-processed articles confirmed in search index")
            
            # 🛡️ SAFETY: Additional verification before deletion
            article_ids_to_clear = []
            for article_data in synced_articles_data:
                # Double-check the article exists in search index with AI content
                search_entry = session.query(NewsSearchIndex).filter_by(
                    external_id=article_data.external_id
                ).filter(
                    NewsSearchIndex.ai_summary.isnot(None),
                    NewsSearchIndex.ai_insights.isnot(None),
                    NewsSearchIndex.ai_summary != '',
                    NewsSearchIndex.ai_insights != ''
                ).first()
                
                if search_entry:
                    article_ids_to_clear.append(article_data.id)
                else:
                    logger.warning(f"⚠️ Skipping article {article_data.id}: not properly synced to search index")
            
            if not article_ids_to_clear:
                logger.info("⚠️ No articles passed safety verification for buffer clearing")
                return stats
            
            logger.info(f"🗄️ Clearing {len(article_ids_to_clear)} verified articles from buffer...")
            
            # 🗑️ CAREFUL DELETION: Handle foreign key relationships
            cleared_count = 0
            
            for article_id in article_ids_to_clear:
                try:
                    # Get the article for logging
                    article = session.query(NewsArticle).get(article_id)
                    if not article:
                        continue
                    
                    # Delete the main article (CASCADE will handle related records)
                    # Note: ArticleSymbol and ArticleMetric have CASCADE delete constraints
                    session.delete(article)
                    cleared_count += 1
                    
                    logger.debug(f"🗑️ Cleared article {article_id}: '{article.title[:50]}...' (CASCADE will handle related records)")
                    
                except Exception as e:
                    logger.error(f"❌ Error clearing article {article_id}: {str(e)}")
                    stats['errors'] += 1
                    continue
            
            # Commit the buffer clearing
            session.commit()
            
            stats['cleared'] = cleared_count
            
            # Update remaining buffer count after clearing
            final_remaining = session.execute(remaining_buffer_query).fetchone().remaining_count
            stats['remaining_buffer'] = final_remaining
            
            logger.info(f"✅ Buffer clearing completed: {cleared_count} articles moved to permanent storage")
            logger.info(f"🗄️ news_articles buffer now contains: {final_remaining} articles pending AI processing")
            
            # Log sample of cleared articles
            if len(synced_articles_data) > 0:
                sample_articles = synced_articles_data[:3]
                logger.info("📰 Sample articles moved to permanent storage:")
                for article in sample_articles:
                    logger.info(f"   • {article.title[:80]}...")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error in buffer clearing: {str(e)}")
            session.rollback()  # Rollback on error to maintain data integrity
            return {
                'cleared': 0,
                'already_cleared': 0,
                'remaining_buffer': 0,
                'errors': 1,
                'total_candidates': 0,
                'error_message': str(e)
            }
        
    def run_processing_job(self):
        """Main processing job - processes unprocessed articles with AI"""
        if not self.running:
            logger.info("🔄 Processing job triggered but scheduler is stopped")
            return
            
        logger.info("🤖 Starting automated AI processing job...")
        
        try:
            with self.get_db_session() as session:
                # 🔄 BATCH AUTO-SYNC: First check if AI-processed articles need syncing to search index
                logger.info("🔄 Step 1: Checking for AI-processed articles that need syncing to search index...")
                sync_stats = self._batch_sync_missing_articles(session)
                
                if sync_stats['synced'] > 0:
                    logger.info(f"✅ Batch sync completed: {sync_stats['synced']} new articles synced to search index")
                    if sync_stats.get('duplicates_prevented', 0) > 0:
                        logger.info(f"🛡️ Duplicates prevented: {sync_stats['duplicates_prevented']} articles were already synced")
                elif sync_stats['already_synced'] > 0:
                    logger.info(f"✅ Search index up-to-date: {sync_stats['already_synced']} AI-processed articles already synced")
                else:
                    logger.info("🔍 No AI-processed articles found needing sync")
                
                # 🗄️ BUFFER CLEARING: Clear AI-processed articles from news_articles after successful sync
                logger.info("🗄️ Step 1.5: Clearing AI-processed articles from buffer (news_articles table)...")
                buffer_stats = self._clear_synced_articles_from_buffer(session)
                
                if buffer_stats['cleared'] > 0:
                    logger.info(f"✅ Buffer clearing completed: {buffer_stats['cleared']} articles moved to permanent storage")
                    logger.info(f"🗄️ Buffer now contains: {buffer_stats['remaining_buffer']} articles pending processing")
                elif buffer_stats['already_cleared'] > 0:
                    logger.info(f"✅ Buffer clean: {buffer_stats['already_cleared']} articles already in permanent storage only")
                else:
                    logger.info("🔍 No AI-processed articles found to clear from buffer")
                
                # 🧹 CLEANUP: Remove articles that don't meet AI processing requirements
                logger.info("🧹 Step 1.6: Cleaning up unprocessable articles from buffer...")
                cleanup_stats = self._cleanup_unprocessable_articles(session)
                
                if cleanup_stats['deleted'] > 0:
                    logger.info(f"✅ Cleanup completed: {cleanup_stats['deleted']} unprocessable articles removed")
                    logger.info(f"🧹 These articles will no longer consume processing resources")
                elif cleanup_stats['total_candidates'] > 0:
                    logger.info(f"⚠️ Found {cleanup_stats['total_candidates']} unprocessable articles but failed to clean up")
                else:
                    logger.info("🔍 No unprocessable articles found needing cleanup")
                
                # 🤖 PROCESS NEW ARTICLES: Now proceed with AI processing of new articles
                logger.info("🤖 Step 2: Processing new articles that need AI processing...")
                
                # Get articles that need processing
                articles = self.get_unprocessed_articles(session)
                
                if not articles:
                    logger.info("✅ No articles need AI processing")
                    return
                    
                logger.info(f"📄 Found {len(articles)} articles to process")
                
                processed_count = 0
                failed_count = 0
                
                for article in articles:
                    try:
                        if not self.running:
                            logger.info("🛑 Processing stopped - scheduler was stopped")
                            break
                            
                        success = self.process_single_article(session, article)
                        if success:
                            processed_count += 1
                            logger.info(f"✅ Successfully processed article {article.id}")
                        else:
                            failed_count += 1
                            logger.warning(f"⚠️ Failed to process article {article.id}")
                            
                        # Rate limiting - wait between articles
                        time.sleep(2)
                        
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"❌ Error processing article {article.id}: {str(e)}")
                        continue
                        
                # Summary
                logger.info(f"🎯 Processing job completed:")
                logger.info(f"   🔄 Batch sync: {sync_stats['synced']} new articles synced to search index")
                if sync_stats.get('duplicates_prevented', 0) > 0:
                    logger.info(f"   🛡️ Duplicates prevented: {sync_stats['duplicates_prevented']} articles")
                logger.info(f"   🗄️ Buffer clearing: {buffer_stats['cleared']} articles moved to permanent storage")
                logger.info(f"   🧹 Cleanup: {cleanup_stats['deleted']} unprocessable articles removed")
                logger.info(f"   ✅ AI processing: {processed_count} articles processed")
                logger.info(f"   ❌ Failed: {failed_count} articles") 
                logger.info(f"   📊 Total processed: {len(articles)} articles")
                logger.info(f"   📊 Search index coverage: {sync_stats['already_synced']} articles already synced")
                
        except Exception as e:
            logger.error(f"❌ Error in processing job: {str(e)}")
            
    def process_single_article(self, session, article):
        """Process a single article with AI summaries and insights"""
        try:
            article_id = article.id
            content = article.content
            title = article.title
            
            # Validate content
            if not content or len(content.strip()) < 10:
                logger.warning(f"⚠️ Article {article_id} has insufficient content")
                return False
                
            # Truncate content if too long
            if len(content) > self.content_truncate_limit:
                content = content[:self.content_truncate_limit] + "..."
                logger.info(f"📝 Truncated content for article {article_id} to {self.content_truncate_limit} chars")
                
            generated_data = {}
            
            # Generate AI Summary if missing
            if not article.ai_summary:
                summary = self.generate_ai_summary(title, content)
                if summary:
                    generated_data['ai_summary'] = summary
                    logger.info(f"✓ Generated AI summary for article {article_id}")
                else:
                    logger.warning(f"⚠️ Failed to generate AI summary for article {article_id}")
                    
            # Generate AI Insights if missing  
            if not article.ai_insights:
                insights = self.generate_ai_insights(title, content)
                if insights:
                    generated_data['ai_insights'] = insights
                    logger.info(f"✓ Generated AI insights for article {article_id}")
                else:
                    logger.warning(f"⚠️ Failed to generate AI insights for article {article_id}")
                    
            # Generate AI Sentiment if missing
            if article.ai_sentiment_rating is None:
                sentiment = self.generate_ai_sentiment(title, content)
                if sentiment is not None:
                    generated_data['ai_sentiment_rating'] = sentiment
                    logger.info(f"✓ Generated AI sentiment for article {article_id}: {sentiment}")
                else:
                    logger.warning(f"⚠️ Failed to generate AI sentiment for article {article_id}")
                    
            # Update database if we generated any content
            if generated_data:
                self.update_article_ai_data(session, article_id, generated_data)
                
                # 🔑 AUTOMATIC KEYWORD EXTRACTION: Extract keywords after AI processing
                try:
                    # Initialize keyword extractor
                    keyword_extractor = AutoKeywordExtractor()
                    
                    # Extract keywords for this article using the buffer table (news_articles)
                    extraction_result = keyword_extractor.extract_keywords_for_article(article_id)
                    
                    if extraction_result.get('success'):
                        keywords_count = extraction_result.get('keywords_extracted', 0)
                        logger.info(f"✓ Extracted {keywords_count} keywords for article {article_id}")
                    else:
                        logger.warning(f"⚠️ Keyword extraction failed for article {article_id}: {extraction_result.get('message', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"❌ Error extracting keywords for article {article_id}: {str(e)}")
                    # Don't fail the whole process if keyword extraction fails
                    pass
                
                # 🔄 BATCH SYNC: Individual sync removed - now handled by batch sync at start of processing
                # This prevents frequent individual syncs and database lock issues
                logger.debug(f"✅ Article {article_id} AI processing completed, will be synced in next batch")
                
                return True
            else:
                logger.warning(f"⚠️ No AI data generated for article {article_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error processing article {article.id}: {str(e)}")
            return False
            
    def update_article_ai_data(self, session, article_id, data):
        """Update article with generated AI data"""
        set_clauses = []
        params = {"article_id": article_id}
        
        if 'ai_summary' in data:
            set_clauses.append("ai_summary = :ai_summary")
            params['ai_summary'] = data['ai_summary']
            
        if 'ai_insights' in data:
            set_clauses.append("ai_insights = :ai_insights") 
            params['ai_insights'] = data['ai_insights']
            
        if 'ai_sentiment_rating' in data:
            set_clauses.append("ai_sentiment_rating = :ai_sentiment_rating")
            params['ai_sentiment_rating'] = data['ai_sentiment_rating']
            
        if set_clauses:
            query = text(f"""
                UPDATE news_articles 
                SET {', '.join(set_clauses)}
                WHERE id = :article_id
            """)
            session.execute(query, params)
            
    def generate_ai_summary(self, title, content):
        """Generate AI summary for an article"""
        try:
            prompt = f"""Analyze this news article and create a structured summary using EXACTLY this format:

**Key Concepts/Keywords**

- [Extract 3-5 key financial/market concepts, company names, or important terms]
- [Each item should be a specific concept, not generic placeholders]

**Key Points**

- [Extract 3-5 main factual points from the article]
- [Focus on concrete facts, numbers, events, or developments]

**Context**

- [Provide 2-4 background context items that help understand the significance]
- [Include market conditions, historical context, or related developments]

IMPORTANT: Replace ALL bracketed placeholders with actual content from the article. Do not use generic terms like "Keyword 1" or "Point 1". CRITICAL: Always include blank lines before and after bullet point lists for proper markdown rendering.

Title: {title}
Content: {content}"""
            
            return self.call_openrouter_api(prompt)
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}")
            return None
            
    def generate_ai_insights(self, title, content):
        """Generate AI insights for an article"""
        try:
            prompt = f"""Analyze this news article and create structured financial insights using EXACTLY this format:

**Key Insights**

- [Extract 3-5 key financial insights, market trends, or strategic implications]
- [Focus on actionable insights for investors and traders]

**Market Implications**

- [Identify 2-4 specific market implications or potential impacts]
- [Consider effects on sectors, competitors, or broader markets]

**Conclusion**

- [Provide a clear, concise conclusion summarizing the overall significance]

IMPORTANT: Replace ALL bracketed placeholders with actual insights from the article. Do not use generic terms like "Insight 1" or "Implication 1". CRITICAL: Always include blank lines before and after bullet point lists for proper markdown rendering.

Title: {title}
Content: {content}"""
            
            return self.call_openrouter_api(prompt)
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
            return None
            
    def generate_ai_sentiment(self, title, content):
        """Generate AI sentiment rating for an article"""
        try:
            prompt = f"""
            Analyze the sentiment of this news article and provide a numerical rating from -100 to +100 where:
            -100 = Extremely bearish/negative
            -50 = Moderately bearish/negative  
            0 = Neutral
            +50 = Moderately bullish/positive
            +100 = Extremely bullish/positive

            Title: {title}
            Content: {content}

            Respond with only the numerical rating (integer between -100 and +100):
            """
            
            response = self.call_openrouter_api(prompt)
            if response:
                # Extract number from response
                try:
                    # Look for number in response
                    import re
                    numbers = re.findall(r'-?\d+', response.strip())
                    if numbers:
                        sentiment = int(numbers[0])
                        # Clamp to valid range
                        sentiment = max(-100, min(100, sentiment))
                        return sentiment
                except ValueError:
                    pass
                    
            return None
            
        except Exception as e:
            logger.error(f"Error generating AI sentiment: {str(e)}")
            return None
            
    def call_openrouter_api(self, prompt, max_tokens=500):  # Increased for DeepSeek V3's larger context
        """Call OpenRouter API for AI generation using OpenAI client"""
        try:
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                logger.error("OPENROUTER_API_KEY not found")
                return None
                
            # Create OpenAI client for OpenRouter
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key
            )
            
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://trendwise.com",  # Optional. Site URL for rankings on openrouter.ai.
                    "X-Title": "TrendWise News AI Scheduler"  # Optional. Site title for rankings on openrouter.ai.
                },
                model="anthropic/claude-3.7-sonnet",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,
                timeout=30
            )
            
            content = completion.choices[0].message.content.strip()
            return content if content else None
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {str(e)}")
            return None
            
    def get_status(self):
        """Get current scheduler status"""
        next_run = None
        jobs_count = len(schedule.jobs)
        
        if jobs_count > 0:
            # Get next scheduled run time
            next_job = schedule.next_run()
            if next_job:
                next_run = next_job.isoformat()
                
        return {
            "running": self.running,
            "next_run": next_run,
            "jobs_count": jobs_count,
            "api_key_configured": bool(os.getenv('OPENROUTER_API_KEY')),
            "max_articles_per_run": self.max_articles_per_run
        }

# Global instance
news_scheduler = NewsAIScheduler() 