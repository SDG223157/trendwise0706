#!/usr/bin/env python3
"""
Setup script for news search optimization system.

This script will:
1. Run database migrations to create the search index table
2. Populate the search index from existing articles
3. Verify the setup is working correctly
4. Provide usage instructions

Usage:
    python scripts/setup_search_optimization.py
"""

import os
import sys
import logging
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from app.utils.search.search_index_sync import SearchIndexSyncService
from app.utils.search.optimized_news_search import OptimizedNewsSearch
from flask_migrate import upgrade

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_banner():
    """Print setup banner"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TrendWise News Search Optimization Setup                  ║
║                                                                              ║
║  This script will set up an optimized search system for news articles       ║
║  using a dedicated search index table for faster performance.               ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

def run_migrations():
    """Run database migrations"""
    print("\n🔄 Running database migrations...")
    
    try:
        app = create_app()
        with app.app_context():
            upgrade()
            print("✅ Database migrations completed successfully")
            return True
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def check_existing_data():
    """Check existing data in the database"""
    print("\n📊 Checking existing data...")
    
    app = create_app()
    with app.app_context():
        try:
            main_count = NewsArticle.query.count()
            search_count = NewsSearchIndex.query.count()
            
            print(f"   📰 Main articles table: {main_count} articles")
            print(f"   🔍 Search index table: {search_count} articles")
            
            return main_count, search_count
        except Exception as e:
            print(f"❌ Error checking data: {str(e)}")
            return 0, 0

def populate_search_index():
    """Populate the search index table"""
    print("\n📦 Populating search index...")
    
    app = create_app()
    with app.app_context():
        try:
            sync_service = SearchIndexSyncService()
            
            # Get sync status first
            status = sync_service.full_sync_status()
            
            if status.get('error'):
                print(f"❌ Error getting sync status: {status['error']}")
                return False
            
            missing_count = status.get('missing_from_index', 0)
            
            if missing_count == 0:
                print("✅ Search index is already up to date")
                return True
            
            print(f"   📤 Syncing {missing_count} articles to search index...")
            
            # Sync new articles
            stats = sync_service.sync_new_articles(batch_size=1000)
            
            if stats.get('errors', 0) < 0:
                print("❌ Sync failed due to system error")
                return False
            
            print(f"✅ Search index populated successfully")
            print(f"   ➕ Added: {stats['added']} articles")
            print(f"   ✏️ Updated: {stats['updated']} articles")
            print(f"   ⚠️ Skipped: {stats['skipped']} articles")
            print(f"   ❌ Errors: {stats['errors']} articles")
            
            return True
            
        except Exception as e:
            print(f"❌ Error populating search index: {str(e)}")
            return False

def verify_search_functionality():
    """Verify that the search functionality is working"""
    print("\n🔍 Verifying search functionality...")
    
    app = create_app()
    with app.app_context():
        try:
            # Test optimized search
            search = OptimizedNewsSearch(db.session)
            
            # Get recent articles
            recent_articles = search.get_recent_news(limit=5)
            
            if recent_articles:
                print(f"✅ Search functionality working - found {len(recent_articles)} recent articles")
                
                # Show a sample article
                sample = recent_articles[0]
                print(f"   📰 Sample: {sample.get('title', 'No title')[:50]}...")
                
                # Test symbol search if we have symbols
                if sample.get('symbols'):
                    symbol = sample['symbols'][0]['symbol']
                    symbol_results, total, has_more = search.search_by_symbols(
                        symbols=[symbol], 
                        per_page=3
                    )
                    print(f"   🔍 Symbol search for '{symbol}': {len(symbol_results)} results")
                
                return True
            else:
                print("⚠️ No recent articles found - search index may be empty")
                return True
                
        except Exception as e:
            print(f"❌ Error verifying search: {str(e)}")
            return False

def show_usage_instructions():
    """Show usage instructions"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                SETUP COMPLETE                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

🎉 Your news search optimization system is now ready!

📖 WHAT WAS CREATED:
   • NewsSearchIndex table with optimized indexes
   • Search synchronization service
   • Optimized search functionality
   • Automatic fallback to original search if needed

🚀 HOW TO USE:

1. REGULAR SEARCH:
   Your existing search functionality will automatically use the optimized index
   when available, with fallback to the original search method.

2. SYNC NEW ARTICLES:
   When new articles are added, they'll automatically sync to the search index.
   For manual sync: python scripts/populate_search_index.py sync

3. CLEANUP OLD ARTICLES:
   To save space, you can remove old articles from the main table:
   python scripts/populate_search_index.py cleanup --keep-days 90

4. MAINTENANCE:
   Check sync status: python scripts/setup_search_optimization.py --status
   Re-populate index: python scripts/populate_search_index.py populate

⚡ PERFORMANCE BENEFITS:
   • Faster search queries (especially for symbol-based searches)
   • Reduced database load
   • Better scalability as news volume grows
   • Cached results for frequently searched terms

🔧 AUTOMATIC FEATURES:
   • New articles are automatically indexed
   • Search falls back to original method if index is unavailable
   • Optimized queries with proper indexing
   • JSON-based symbol storage for faster lookups

For more details, see the documentation in docs/
""")

def get_status():
    """Get current status of the search optimization system"""
    print("\n📊 Current Status:")
    
    app = create_app()
    with app.app_context():
        try:
            sync_service = SearchIndexSyncService()
            status = sync_service.full_sync_status()
            
            if status.get('error'):
                print(f"❌ Error getting status: {status['error']}")
                return
            
            print(f"   📰 Main table: {status['main_table_count']} articles")
            print(f"   🔍 Search index: {status['search_index_count']} articles")
            print(f"   📈 Sync percentage: {status['sync_percentage']:.1f}%")
            print(f"   🔄 Sync needed: {'Yes' if status['is_sync_needed'] else 'No'}")
            
            if status['is_sync_needed']:
                print(f"   ⚠️ Missing from index: {status['missing_from_index']}")
                print(f"   🗑️ Orphaned entries: {status['orphaned_entries']}")
            
            date_range = status.get('search_index_date_range', {})
            if date_range.get('oldest') and date_range.get('newest'):
                print(f"   📅 Date range: {date_range['oldest'][:10]} to {date_range['newest'][:10]}")
            
        except Exception as e:
            print(f"❌ Error getting status: {str(e)}")

def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup news search optimization')
    parser.add_argument('--status', action='store_true', help='Show current status only')
    parser.add_argument('--skip-migration', action='store_true', help='Skip database migration')
    parser.add_argument('--skip-populate', action='store_true', help='Skip populating search index')
    parser.add_argument('--coolify-mode', action='store_true', help='Run in Coolify deployment mode with SQLite')
    
    args = parser.parse_args()
    
    # Handle Coolify mode
    if args.coolify_mode:
        print("🚀 TrendWise Search Optimization Setup - Coolify Mode")
        print("📍 Configuring for SQLite database in Coolify environment")
        
        # Force SQLite configuration
        import os
        os.environ['DATABASE_URL'] = f'sqlite:///{os.getcwd()}/trendwise.db'
        os.environ['FLASK_ENV'] = 'production'
        
        # Unset MySQL variables that might interfere
        mysql_vars = ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
        for var in mysql_vars:
            if var in os.environ:
                del os.environ[var]
                print(f"   🚫 Removed {var} from environment")
                
        print(f"✅ Database URL: {os.environ['DATABASE_URL']}")
        print()
    
    if args.status:
        get_status()
        return
    
    print_banner()
    
    success = True
    
    # Step 1: Run migrations
    if not args.skip_migration:
        if not run_migrations():
            success = False
    
    # Step 2: Check existing data
    main_count, search_count = check_existing_data()
    
    if main_count == 0:
        print("⚠️ No articles found in the main table. Add some articles first.")
        return
    
    # Step 3: Populate search index
    if not args.skip_populate:
        if success and not populate_search_index():
            success = False
    
    # Step 4: Verify functionality
    if success:
        if not verify_search_functionality():
            success = False
    
    # Step 5: Show results
    if success:
        show_usage_instructions()
        get_status()
    else:
        print("""
❌ Setup encountered some issues. Please check the logs above and:
   1. Make sure your database is accessible
   2. Verify you have articles in the news_articles table
   3. Check for any permission issues
   4. Try running individual steps manually
""")

if __name__ == '__main__':
    main() 