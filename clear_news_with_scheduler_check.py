#!/usr/bin/env python3
"""
Clear News Data with AI Scheduler Check
Safely clear news data even when AI scheduler is running by handling database locks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol
from sqlalchemy import text
import logging
import time
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_ai_scheduler_activity():
    """Check if AI scheduler is currently processing articles"""
    try:
        # Check for articles that were recently updated (likely being processed)
        recent_cutoff = datetime.now() - timedelta(minutes=10)
        
        # Look for articles with recent AI processing activity
        recent_ai_activity = NewsArticle.query.filter(
            NewsArticle.updated_at >= recent_cutoff
        ).count()
        
        # Check for articles in "processing" state (if we have such a field)
        processing_articles = NewsArticle.query.filter(
            NewsArticle.ai_summary.is_(None),
            NewsArticle.created_at >= recent_cutoff
        ).count()
        
        return {
            'recent_ai_updates': recent_ai_activity,
            'articles_being_processed': processing_articles,
            'scheduler_likely_active': recent_ai_activity > 0 or processing_articles > 0
        }
        
    except Exception as e:
        logger.error(f"Error checking scheduler activity: {str(e)}")
        return {'error': str(e)}

def wait_for_scheduler_pause(max_wait_minutes=5):
    """Wait for a natural pause in scheduler activity"""
    print(f"⏳ Waiting for AI scheduler to pause (max {max_wait_minutes} minutes)...")
    
    start_time = datetime.now()
    max_wait = timedelta(minutes=max_wait_minutes)
    
    while datetime.now() - start_time < max_wait:
        activity = check_ai_scheduler_activity()
        
        if not activity.get('scheduler_likely_active', True):
            print("✅ Scheduler activity paused - safe to proceed")
            return True
        
        print(f"   📊 Recent updates: {activity.get('recent_ai_updates', 0)}, Processing: {activity.get('articles_being_processed', 0)}")
        print("   ⏳ Waiting 30 seconds...")
        time.sleep(30)
    
    print(f"⚠️ Scheduler still active after {max_wait_minutes} minutes")
    return False

def force_clear_with_retries(max_retries=3):
    """Clear data with retries to handle database locks"""
    for attempt in range(max_retries):
        try:
            print(f"🔄 Clear attempt {attempt + 1}/{max_retries}...")
            
            # Use shorter timeouts to avoid hanging
            db.session.execute(text("SET SESSION innodb_lock_wait_timeout = 10"))
            
            # Clear in order with retries for each table
            tables_cleared = {}
            
            # 1. Clear article_symbols first
            try:
                symbols_deleted = ArticleSymbol.query.delete()
                db.session.flush()  # Flush but don't commit yet
                tables_cleared['article_symbols'] = symbols_deleted
                print(f"   ✅ Cleared {symbols_deleted} article symbols")
            except Exception as e:
                logger.warning(f"   ⚠️ Article symbols clear failed: {str(e)}")
                tables_cleared['article_symbols'] = 0
            
            # 2. Clear news_search_index
            try:
                search_deleted = NewsSearchIndex.query.delete()
                db.session.flush()
                tables_cleared['search_index'] = search_deleted
                print(f"   ✅ Cleared {search_deleted} search index entries")
            except Exception as e:
                logger.warning(f"   ⚠️ Search index clear failed: {str(e)}")
                tables_cleared['search_index'] = 0
            
            # 3. Clear news_articles (most likely to have locks)
            try:
                articles_deleted = NewsArticle.query.delete()
                db.session.flush()
                tables_cleared['news_articles'] = articles_deleted
                print(f"   ✅ Cleared {articles_deleted} news articles")
            except Exception as e:
                logger.warning(f"   ⚠️ News articles clear failed: {str(e)}")
                # If articles can't be cleared, rollback and try again
                db.session.rollback()
                if attempt < max_retries - 1:
                    print(f"   🔄 Retrying in 10 seconds...")
                    time.sleep(10)
                    continue
                else:
                    raise e
            
            # Commit all changes
            db.session.commit()
            
            return {
                'success': True,
                'articles_deleted': tables_cleared.get('news_articles', 0),
                'symbols_deleted': tables_cleared.get('article_symbols', 0),
                'search_deleted': tables_cleared.get('search_index', 0),
                'attempts_used': attempt + 1
            }
            
        except Exception as e:
            logger.error(f"   ❌ Attempt {attempt + 1} failed: {str(e)}")
            db.session.rollback()
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"   ⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                return {
                    'success': False,
                    'error': str(e),
                    'attempts_used': max_retries
                }
    
    return {'success': False, 'error': 'Max retries exceeded'}

def emergency_scheduler_stop():
    """Attempt to temporarily pause AI scheduler if possible"""
    print("🛑 Attempting to pause AI scheduler...")
    
    try:
        # Try to signal the scheduler to pause (if it supports this)
        # This would depend on your scheduler implementation
        
        # For now, we'll just wait and hope for a natural pause
        print("   📋 Note: Manual scheduler management may be needed")
        print("   💡 Consider stopping the scheduler service temporarily if clearing fails")
        
        return True
        
    except Exception as e:
        logger.error(f"Error attempting scheduler pause: {str(e)}")
        return False

def check_current_status():
    """Check current status safely"""
    try:
        # Use non-blocking queries
        news_articles = db.session.execute(text("SELECT COUNT(*) FROM news_articles")).scalar()
        search_index = db.session.execute(text("SELECT COUNT(*) FROM news_search_index")).scalar()
        
        try:
            article_symbols = db.session.execute(text("SELECT COUNT(*) FROM article_symbols")).scalar()
        except:
            article_symbols = 0
        
        return {
            'news_articles': news_articles,
            'search_index': search_index,
            'article_symbols': article_symbols
        }
        
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        return {'error': str(e)}

def show_fresh_start_instructions():
    """Show instructions for the fresh start workflow"""
    print("\n🚀 FRESH START WORKFLOW")
    print("=" * 50)
    print("\nNow that your tables are clean, follow these steps:")
    print("\n1️⃣ FETCH FRESH NEWS DATA:")
    print("   • Go to your TrendWise /news/fetch page")
    print("   • Enter symbols you want to track (e.g., AAPL, TSLA, GOOGL)")
    print("   • Click 'Fetch News' to get fresh articles")
    print("   • Articles will be saved to news_articles table")
    
    print("\n2️⃣ AI PROCESSING (Automatic):")
    print("   • Your AI scheduler will resume processing automatically")
    print("   • AI will generate summaries, insights, and sentiment ratings")
    print("   • Processing status visible in logs and admin interface")
    
    print("\n3️⃣ AUTO-SYNC (Automatic):")
    print("   • When AI processing completes, auto-sync triggers automatically")
    print("   • Articles with AI content sync to news_search_index table")
    print("   • Search functionality immediately available")

def main():
    """Main execution function"""
    print("🛑 Clear News Data (AI Scheduler Safe)")
    print("=" * 50)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Step 1: Check current status
        print("\n📊 Current Data Status:")
        status = check_current_status()
        
        if 'error' in status:
            print(f"❌ Error: {status['error']}")
            return
        
        print(f"   News articles: {status['news_articles']}")
        print(f"   Search index entries: {status['search_index']}")
        print(f"   Article symbols: {status['article_symbols']}")
        
        if status['news_articles'] == 0 and status['search_index'] == 0:
            print("\n✅ Tables are already empty!")
            show_fresh_start_instructions()
            return
        
        # Step 2: Check scheduler activity
        print("\n🔍 Checking AI Scheduler Activity...")
        activity = check_ai_scheduler_activity()
        
        if activity.get('scheduler_likely_active'):
            print(f"   ⚠️ AI scheduler appears active:")
            print(f"   • Recent AI updates: {activity.get('recent_ai_updates', 0)}")
            print(f"   • Articles being processed: {activity.get('articles_being_processed', 0)}")
            
            # Try to wait for a pause
            if not wait_for_scheduler_pause():
                print("\n🛑 Scheduler still active - attempting force clear with retries...")
        else:
            print("   ✅ No recent scheduler activity detected")
        
        # Step 3: Attempt to clear data
        total_records = status['news_articles'] + status['search_index'] + status['article_symbols']
        print(f"\n🚀 Clearing {total_records} total records across all news tables...")
        
        clear_result = force_clear_with_retries()
        
        if clear_result['success']:
            print(f"\n✅ Successfully cleared after {clear_result['attempts_used']} attempts:")
            print(f"   • {clear_result['articles_deleted']} news articles")
            print(f"   • {clear_result['search_deleted']} search index entries")
            print(f"   • {clear_result['symbols_deleted']} article symbols")
            
            # Verify clean state
            print(f"\n🔍 Verifying clean state...")
            verification = check_current_status()
            
            if not verification.get('error'):
                remaining = verification['news_articles'] + verification['search_index'] + verification['article_symbols']
                if remaining == 0:
                    print("✅ All tables successfully cleared!")
                    show_fresh_start_instructions()
                else:
                    print(f"⚠️ {remaining} records still remain - may need manual cleanup")
        else:
            print(f"\n❌ Failed to clear data after {clear_result['attempts_used']} attempts")
            print(f"Error: {clear_result.get('error', 'Unknown error')}")
            print("\n💡 Suggestions:")
            print("   • Stop the AI scheduler service temporarily")
            print("   • Wait for current AI processing cycle to complete")
            print("   • Try running the script again")
            print("   • Use database admin tools for manual cleanup if needed")

if __name__ == "__main__":
    main() 