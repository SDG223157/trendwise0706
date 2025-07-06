#!/usr/bin/env python3
"""
Fix Auto-Sync in AI Scheduler
Debug and fix the auto-sync mechanism that should run after AI processing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from app.utils.scheduler.news_scheduler import NewsAIScheduler
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_scheduler_auto_sync():
    """Test the auto-sync mechanism in the AI scheduler"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing AI Scheduler Auto-Sync")
        print("=" * 50)
        
        # Get an article without AI content to test on
        test_article = NewsArticle.query.filter(
            NewsArticle.ai_summary.is_(None)
        ).first()
        
        if not test_article:
            print("❌ No articles without AI content found for testing")
            return
            
        print(f"🧪 Testing on article {test_article.id}")
        print(f"   Title: {test_article.title[:100]}...")
        print(f"   Content length: {len(test_article.content) if test_article.content else 0}")
        
        # Initialize scheduler
        scheduler = NewsAIScheduler()
        scheduler.init_app(app)
        
        # Test the process_single_article method
        print(f"\n🤖 Processing article with AI...")
        
        try:
            with scheduler.get_db_session() as session:
                # Process the article
                success = scheduler.process_single_article(session, test_article)
                
                if success:
                    print("✅ AI processing completed successfully")
                    
                    # Check if auto-sync worked
                    search_entry = NewsSearchIndex.query.filter_by(
                        external_id=test_article.external_id
                    ).first()
                    
                    if search_entry:
                        print("✅ Auto-sync worked! Search index entry created")
                        print(f"   Search ID: {search_entry.id}")
                        print(f"   Article ID: {search_entry.article_id}")
                    else:
                        print("❌ Auto-sync failed - no search index entry found")
                        
                        # Try manual sync to see if that works
                        print("🔄 Testing manual sync...")
                        
                        # Refresh the article to get updated AI content
                        db.session.refresh(test_article)
                        
                        from app.utils.search.search_index_sync import sync_article_to_search_index
                        manual_sync_result = sync_article_to_search_index(test_article)
                        
                        if manual_sync_result:
                            print("✅ Manual sync worked - issue is in scheduler's auto-sync")
                            print("💡 Problem: Session mismatch between scheduler and sync function")
                        else:
                            print("❌ Manual sync also failed")
                            
                else:
                    print("❌ AI processing failed")
                    
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            logger.error(f"Error during testing: {str(e)}", exc_info=True)

def fix_scheduler_auto_sync():
    """Create a fixed version of the scheduler auto-sync"""
    print("\n🔧 Creating Fixed Auto-Sync Mechanism")
    print("=" * 50)
    
    # The fix is to use Flask-SQLAlchemy session instead of scheduler's session
    # for the sync function call
    
    fix_code = """
    # 🔄 AUTO-SYNC TO SEARCH INDEX: Fixed version
    try:
        from flask import current_app
        from app import db
        from app.utils.search.search_index_sync import sync_article_to_search_index
        
        # Get article using Flask-SQLAlchemy session instead of scheduler session
        with current_app.app_context():
            updated_article = NewsArticle.query.get(article_id)
            if updated_article:
                sync_success = sync_article_to_search_index(updated_article)
                if sync_success:
                    logger.info(f"✅ Auto-synced article {article_id} to search index")
                else:
                    logger.warning(f"⚠️ Failed to auto-sync article {article_id} to search index")
    except Exception as e:
        logger.error(f"❌ Error auto-syncing article {article_id} to search index: {str(e)}")
    """
    
    print("💡 The issue is likely a database session mismatch.")
    print("💡 The scheduler uses its own session, but sync function expects Flask-SQLAlchemy session.")
    print("\n🔧 Recommended fix:")
    print("   1. Update scheduler to use Flask-SQLAlchemy session for sync calls")
    print("   2. Or modify sync function to accept scheduler session")
    print("   3. Or run manual bulk sync for now and fix scheduler later")
    
    print(f"\n📝 Fixed auto-sync code:")
    print(fix_code)

def main():
    """Main function"""
    test_scheduler_auto_sync()
    fix_scheduler_auto_sync()
    
    print(f"\n💡 IMMEDIATE ACTION REQUIRED:")
    print("   1. Run: python3 fix_missing_search_index.py (to sync existing articles)")
    print("   2. Consider updating scheduler code to fix auto-sync for future articles")
    print("   3. Test search functionality after bulk sync")

if __name__ == "__main__":
    main() 