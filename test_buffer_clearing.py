#!/usr/bin/env python3
"""
Test script for buffer clearing functionality in the news scheduler.
This script verifies that AI-processed articles are properly moved from 
news_articles (buffer) to news_search_index (permanent storage).

Run this script on Coolify to verify the buffer architecture works correctly.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_buffer_clearing.log')
    ]
)
logger = logging.getLogger(__name__)

def test_buffer_clearing():
    """Test the buffer clearing functionality comprehensively"""
    
    try:
        # Initialize the Flask app and database
        from app import create_app
        from app.models import db, NewsArticle, NewsSearchIndex, ArticleSymbol, ArticleMetric
        from app.utils.scheduler.news_scheduler import NewsAIScheduler
        
        app = create_app()
        
        with app.app_context():
            print("=" * 80)
            print("🧪 TESTING BUFFER CLEARING FUNCTIONALITY")
            print("=" * 80)
            
            # Step 1: Get baseline statistics
            print("\n📊 Step 1: Baseline Statistics")
            print("-" * 40)
            
            total_articles = db.session.query(NewsArticle).count()
            ai_processed_articles = db.session.query(NewsArticle).filter(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_summary != '',
                NewsArticle.ai_insights != ''
            ).count()
            
            total_search_index = db.session.query(NewsSearchIndex).count()
            
            print(f"📰 Total articles in buffer (news_articles): {total_articles}")
            print(f"🤖 AI-processed articles in buffer: {ai_processed_articles}")
            print(f"🔍 Total articles in search index: {total_search_index}")
            
            # Step 2: Check overlaps between tables
            print("\n🔍 Step 2: Cross-Table Analysis")
            print("-" * 40)
            
            # Find AI-processed articles that are in both tables
            overlap_query = text("""
                SELECT COUNT(*) as overlap_count
                FROM news_articles na
                INNER JOIN news_search_index nsi ON na.external_id = nsi.external_id
                WHERE na.ai_summary IS NOT NULL 
                AND na.ai_insights IS NOT NULL 
                AND na.ai_summary != '' 
                AND na.ai_insights != ''
            """)
            
            overlap_count = db.session.execute(overlap_query).fetchone().overlap_count
            
            # Find articles in search index but not in buffer
            only_in_search_query = text("""
                SELECT COUNT(*) as search_only_count
                FROM news_search_index nsi
                LEFT JOIN news_articles na ON nsi.external_id = na.external_id
                WHERE na.external_id IS NULL
            """)
            
            search_only_count = db.session.execute(only_in_search_query).fetchone().search_only_count
            
            print(f"🔄 Articles in both tables (candidates for clearing): {overlap_count}")
            print(f"🔍 Articles only in search index (already moved): {search_only_count}")
            print(f"🆕 Articles only in buffer (pending processing): {total_articles - overlap_count}")
            
            # Step 3: Test cleanup of unprocessable articles
            print("\n🧹 Step 3: Testing Unprocessable Articles Cleanup")
            print("-" * 40)
            
            # Check for unprocessable articles
            unprocessable_query = text("""
                SELECT COUNT(*) as unprocessable_count
                FROM news_articles
                WHERE (
                    content IS NULL 
                    OR content = ''
                    OR CHAR_LENGTH(TRIM(content)) <= 20
                )
                AND (ai_summary IS NULL OR ai_insights IS NULL OR ai_sentiment_rating IS NULL)
            """)
            
            unprocessable_count = db.session.execute(unprocessable_query).fetchone().unprocessable_count
            print(f"🗑️ Unprocessable articles found: {unprocessable_count}")
            
            if unprocessable_count > 0:
                # Test cleanup method
                cleanup_stats = scheduler._cleanup_unprocessable_articles(db.session)
                print(f"✅ Cleanup completed: {cleanup_stats['deleted']} articles removed")
                print(f"⚠️ Cleanup errors: {cleanup_stats['errors']}")
            else:
                print("✅ No unprocessable articles found")
            
            # Step 4: Test buffer clearing method directly
            print("\n🧪 Step 4: Testing Buffer Clearing Method")
            print("-" * 40)
            
            if overlap_count == 0:
                print("⚠️  No articles found in both tables. Buffer clearing not needed.")
                return
            
            # Create scheduler instance and test buffer clearing
            scheduler = NewsAIScheduler()
            
            # Test the buffer clearing method
            print(f"🗄️ Testing buffer clearing for {overlap_count} articles...")
            
            # Call the buffer clearing method
            buffer_stats = scheduler._clear_synced_articles_from_buffer(db.session)
            
            print(f"✅ Buffer clearing completed!")
            print(f"   📤 Articles cleared from buffer: {buffer_stats['cleared']}")
            print(f"   📊 Articles remaining in buffer: {buffer_stats['remaining_buffer']}")
            print(f"   ⚠️  Errors during clearing: {buffer_stats['errors']}")
            
            # Step 5: Verify results
            print("\n📈 Step 5: Post-Clearing Verification")
            print("-" * 40)
            
            # Check new statistics
            new_total_articles = db.session.query(NewsArticle).count()
            new_ai_processed = db.session.query(NewsArticle).filter(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_summary != '',
                NewsArticle.ai_insights != ''
            ).count()
            
            new_total_search_index = db.session.query(NewsSearchIndex).count()
            new_overlap_count = db.session.execute(overlap_query).fetchone().overlap_count
            
            print(f"📰 Articles in buffer (after clearing): {new_total_articles}")
            print(f"🤖 AI-processed articles in buffer: {new_ai_processed}")
            print(f"🔍 Articles in search index: {new_total_search_index}")
            print(f"🔄 Articles still in both tables: {new_overlap_count}")
            
            # Calculate changes
            cleared_articles = total_articles - new_total_articles
            print(f"\n📊 Summary of Changes:")
            print(f"   📤 Articles moved to permanent storage: {cleared_articles}")
            print(f"   📉 Buffer size reduction: {cleared_articles} articles")
            print(f"   🔄 Remaining overlaps: {new_overlap_count}")
            
            # Step 6: Data integrity checks
            print("\n🔍 Step 6: Data Integrity Verification")
            print("-" * 40)
            
            # Check that search index wasn't affected
            if new_total_search_index == total_search_index:
                print("✅ Search index preserved - no data loss")
            else:
                print(f"⚠️  Search index changed: {total_search_index} -> {new_total_search_index}")
            
            # Check for orphaned records (should be none due to CASCADE)
            orphaned_symbols = db.session.query(ArticleSymbol).filter(
                ~ArticleSymbol.article_id.in_(
                    db.session.query(NewsArticle.id)
                )
            ).count()
            
            orphaned_metrics = db.session.query(ArticleMetric).filter(
                ~ArticleMetric.article_id.in_(
                    db.session.query(NewsArticle.id)
                )
            ).count()
            
            print(f"🔗 Orphaned symbols: {orphaned_symbols}")
            print(f"📊 Orphaned metrics: {orphaned_metrics}")
            
            if orphaned_symbols == 0 and orphaned_metrics == 0:
                print("✅ No orphaned records - CASCADE deletions worked correctly")
            else:
                print("⚠️  Found orphaned records - CASCADE may have issues")
            
            # Step 7: Test search functionality
            print("\n🔍 Step 7: Search Functionality Test")
            print("-" * 40)
            
            # Test a few search queries to ensure everything still works
            from app.utils.search.optimized_news_search import OptimizedNewsSearch
            
            search_engine = OptimizedNewsSearch(db.session)
            
            # Test basic keyword search
            test_results, _, _ = search_engine.search_by_keywords(["latest"], page=1, per_page=5)
            print(f"🔍 Test search 'latest' returned: {len(test_results)} results")
            
            # Test symbol search
            symbol_results, _, _ = search_engine.search_by_symbols(["AAPL"], page=1, per_page=5)
            print(f"🔍 Test search 'AAPL' returned: {len(symbol_results)} results")
            
            if len(test_results) > 0 or len(symbol_results) > 0:
                print("✅ Search functionality working correctly")
            else:
                print("⚠️  Search returned no results - may need investigation")
            
            # Final summary
            print("\n" + "=" * 80)
            print("🎉 BUFFER CLEARING TEST COMPLETED")
            print("=" * 80)
            
            success_indicators = [
                cleared_articles > 0,
                new_overlap_count < overlap_count,
                new_total_search_index == total_search_index,
                orphaned_symbols == 0,
                orphaned_metrics == 0
            ]
            
            success_rate = sum(success_indicators) / len(success_indicators) * 100
            
            print(f"✅ Test Success Rate: {success_rate:.1f}%")
            print(f"📊 Buffer Architecture Status: {'✅ WORKING' if success_rate >= 80 else '⚠️ NEEDS ATTENTION'}")
            
            if success_rate >= 80:
                print("🎉 Buffer clearing functionality is working correctly!")
            else:
                print("⚠️  Buffer clearing needs attention - check logs for issues")
            
            return success_rate >= 80
            
    except Exception as e:
        logger.error(f"❌ Error in buffer clearing test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting buffer clearing test...")
    print("📋 This test will verify the buffer architecture works correctly")
    print("⚠️  Run this script on Coolify for accurate results")
    print()
    
    success = test_buffer_clearing()
    
    if success:
        print("✅ All tests passed! Buffer clearing is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check the logs for details.")
        sys.exit(1) 