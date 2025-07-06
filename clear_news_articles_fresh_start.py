#!/usr/bin/env python3
"""
Clear News Articles for Fresh Start
Safely clear all news data to start fresh with fetch → AI process → auto-sync workflow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_current_status():
    """Check current status before clearing"""
    try:
        # Get counts
        news_articles = NewsArticle.query.count()
        search_index = NewsSearchIndex.query.count()
        article_symbols = ArticleSymbol.query.count()
        
        # Get AI processed count
        ai_processed = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None)
        ).count()
        
        return {
            'news_articles': news_articles,
            'search_index': search_index,
            'article_symbols': article_symbols,
            'ai_processed': ai_processed
        }
        
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        return {'error': str(e)}

def clear_all_news_data():
    """
    Clear all news data for fresh start
    This will cascade to clear related tables due to foreign key constraints
    """
    try:
        logger.info("🗑️ Starting fresh data clear...")
        
        # Clear in correct order to handle foreign key constraints
        # 1. Clear article_symbols first
        symbols_deleted = ArticleSymbol.query.delete()
        logger.info(f"   Cleared {symbols_deleted} article symbols")
        
        # 2. Clear news_search_index 
        search_deleted = NewsSearchIndex.query.delete()
        logger.info(f"   Cleared {search_deleted} search index entries")
        
        # 3. Clear news_articles (main table)
        articles_deleted = NewsArticle.query.delete()
        logger.info(f"   Cleared {articles_deleted} news articles")
        
        # Commit all changes
        db.session.commit()
        
        logger.info("✅ All news data cleared successfully!")
        
        return {
            'articles_deleted': articles_deleted,
            'symbols_deleted': symbols_deleted,
            'search_deleted': search_deleted,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing data: {str(e)}")
        db.session.rollback()
        return {'error': str(e), 'success': False}

def verify_clean_state():
    """Verify that all tables are empty after clearing"""
    try:
        status = check_current_status()
        if 'error' in status:
            return status
            
        is_clean = (status['news_articles'] == 0 and 
                   status['search_index'] == 0 and 
                   status['article_symbols'] == 0)
        
        return {
            'is_clean': is_clean,
            'tables_status': status
        }
        
    except Exception as e:
        logger.error(f"Error verifying clean state: {str(e)}")
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
    print("   • Your AI scheduler runs every 4 hours automatically")
    print("   • Or manually trigger via /news/ai-status page")
    print("   • AI will generate summaries, insights, and sentiment ratings")
    print("   • Processing status visible in logs and admin interface")
    
    print("\n3️⃣ AUTO-SYNC (Automatic):")
    print("   • When AI processing completes, auto-sync triggers automatically")
    print("   • Articles with AI content sync to news_search_index table")
    print("   • Symbols preserved in symbols_json field")
    print("   • Search functionality immediately available")
    
    print("\n✅ VERIFICATION:")
    print("   • Check /news/search page for search functionality")
    print("   • Use /admin interface to monitor processing status")
    print("   • Run check_news_tables_status.py to verify data")
    
    print("\n🔄 ONGOING OPERATIONS:")
    print("   • New articles auto-fetch every 4 hours (via scheduler)")
    print("   • AI processing runs automatically on new articles")
    print("   • Auto-sync keeps search index updated")
    print("   • Full hands-off operation after initial setup")

def main():
    """Main execution function"""
    print("🗑️ Clear News Articles for Fresh Start")
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
        print(f"   AI processed: {status['ai_processed']}")
        
        # Step 2: Clear data directly (no confirmation needed)
        if status['news_articles'] > 0 or status['search_index'] > 0 or status['article_symbols'] > 0:
            total_records = status['news_articles'] + status['search_index'] + status['article_symbols']
            print(f"\n🚀 Clearing {total_records} total records across all news tables...")
            
            clear_result = clear_all_news_data()
            
            if clear_result['success']:
                print(f"✅ Successfully cleared:")
                print(f"   • {clear_result['articles_deleted']} news articles")
                print(f"   • {clear_result['search_deleted']} search index entries") 
                print(f"   • {clear_result['symbols_deleted']} article symbols")
                
                # Step 3: Verify clean state
                print(f"\n🔍 Verifying clean state...")
                verification = verify_clean_state()
                
                if verification.get('is_clean'):
                    print("✅ All tables successfully cleared!")
                    
                    # Step 4: Show fresh start instructions
                    show_fresh_start_instructions()
                    
                else:
                    print("⚠️ Some data may remain:")
                    for table, count in verification['tables_status'].items():
                        if count > 0:
                            print(f"   • {table}: {count} records")
            else:
                print(f"❌ Error clearing data: {clear_result.get('error', 'Unknown error')}")
                
        else:
            print("\n✅ Tables are already empty!")
            print("You're ready for fresh data fetching.")
            show_fresh_start_instructions()

if __name__ == "__main__":
    main() 