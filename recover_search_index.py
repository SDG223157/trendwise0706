#!/usr/bin/env python3
"""
Recovery Script for News Search Index

This script helps recover from the CASCADE deletion disaster that occurred
when clearing news_articles table deleted all news_search_index records.

DISASTER SUMMARY:
- news_articles: Cleared to 0 entries (intended)
- news_search_index: Accidentally cleared to 0 entries (CASCADE constraint)
- All AI-enhanced search data lost due to foreign key constraint

RECOVERY OPTIONS:
1. Restore from database backup (if available)
2. Re-populate from news scraping APIs
3. Manual data recovery if partial backups exist
"""

import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol, ArticleMetric
from sqlalchemy import text, func
import logging
from datetime import datetime, timedelta
import json
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def assess_damage():
    """Assess the current state of the database after the disaster"""
    
    print("💔 DISASTER ASSESSMENT")
    print("=" * 50)
    
    # Check current table counts
    articles_count = db.session.query(NewsArticle).count()
    search_index_count = db.session.query(NewsSearchIndex).count()
    symbols_count = db.session.query(ArticleSymbol).count()
    metrics_count = db.session.query(ArticleMetric).count()
    
    print(f"📊 Current Database State:")
    print(f"   📰 news_articles: {articles_count:,} entries")
    print(f"   🔍 news_search_index: {search_index_count:,} entries")
    print(f"   🏷️  article_symbols: {symbols_count:,} entries")
    print(f"   📈 article_metrics: {metrics_count:,} entries")
    
    # Check if we have any data left
    total_data = articles_count + search_index_count + symbols_count + metrics_count
    
    if total_data == 0:
        print("💀 COMPLETE DATA LOSS - All tables are empty")
        return "complete_loss"
    elif search_index_count == 0 and articles_count == 0:
        print("❌ SEARCH INDEX AND ARTICLES LOST - Buffer architecture failed")
        return "search_lost"
    elif search_index_count == 0:
        print("⚠️ SEARCH INDEX LOST - Articles may still exist")
        return "index_lost"
    else:
        print("✅ SOME DATA REMAINS - Partial recovery possible")
        return "partial_data"

def check_backup_options():
    """Check available backup and recovery options"""
    
    print("\n🔄 RECOVERY OPTIONS ASSESSMENT")
    print("=" * 50)
    
    recovery_options = []
    
    # Option 1: Database backup
    print("1. 💾 DATABASE BACKUP RECOVERY")
    print("   - Check if Coolify has automatic database backups")
    print("   - Look for MySQL dump files or snapshots")
    print("   - Recommended: Restore from most recent backup")
    recovery_options.append("database_backup")
    
    # Option 2: Application-level data recovery
    print("\n2. 🔄 APPLICATION DATA RECOVERY")
    print("   - Check if any cached data exists in Redis")
    print("   - Look for local data files or exports")
    print("   - Search for any saved search results")
    recovery_options.append("app_data_recovery")
    
    # Option 3: Re-scraping from sources
    print("\n3. 🌐 RE-SCRAPING FROM SOURCES")
    print("   - Re-fetch news from original APIs")
    print("   - Time-consuming but complete recovery")
    print("   - Requires API keys and rate limiting")
    recovery_options.append("rescrape_sources")
    
    # Option 4: Manual data entry
    print("\n4. 📝 MANUAL DATA ENTRY")
    print("   - Last resort for critical data")
    print("   - Very time-consuming")
    print("   - Only for most important articles")
    recovery_options.append("manual_entry")
    
    return recovery_options

def fix_schema_first():
    """Fix the database schema to prevent future CASCADE disasters"""
    
    print("\n🔧 SCHEMA FIX REQUIRED")
    print("=" * 50)
    
    print("Before any data recovery, we must fix the foreign key constraint")
    print("that caused this disaster to prevent it from happening again.")
    print()
    print("Required steps:")
    print("1. Run migration: flask db upgrade fix_search_cascade")
    print("2. This will remove CASCADE deletion from news_search_index")
    print("3. Make article_id nullable for standalone operation")
    print("4. Then proceed with data recovery")
    print()
    
    # Check if the fix migration exists
    try:
        # Try to check if the migration file exists
        import os
        migration_path = "migrations/versions/fix_search_index_cascade.py"
        if os.path.exists(migration_path):
            print("✅ Schema fix migration is ready")
            print("   Run: flask db upgrade fix_search_cascade")
        else:
            print("❌ Schema fix migration not found")
            print("   The fix migration needs to be created first")
    except Exception as e:
        print(f"⚠️ Cannot check migration status: {str(e)}")

def create_recovery_plan():
    """Create a step-by-step recovery plan"""
    
    print("\n🎯 RECOVERY PLAN")
    print("=" * 50)
    
    damage_level = assess_damage()
    
    if damage_level == "complete_loss":
        print("📋 COMPLETE LOSS RECOVERY PLAN:")
        print("   1. 🔧 Fix schema (remove CASCADE constraint)")
        print("   2. 💾 Restore from database backup (if available)")
        print("   3. 🌐 Re-scrape from news sources (if no backup)")
        print("   4. 🧠 Re-run AI processing on recovered articles")
        print("   5. 🔍 Rebuild search index")
        print("   6. ✅ Test search functionality")
        
    elif damage_level == "search_lost":
        print("📋 SEARCH INDEX RECOVERY PLAN:")
        print("   1. 🔧 Fix schema (remove CASCADE constraint)")
        print("   2. 💾 Restore search index from backup")
        print("   3. 🔄 Re-populate search index from articles (if backup unavailable)")
        print("   4. ✅ Test search functionality")
        
    elif damage_level == "index_lost":
        print("📋 INDEX REBUILD PLAN:")
        print("   1. 🔧 Fix schema (remove CASCADE constraint)")
        print("   2. 🔄 Rebuild search index from existing articles")
        print("   3. ✅ Test search functionality")
        
    else:
        print("📋 PARTIAL RECOVERY PLAN:")
        print("   1. 🔧 Fix schema (remove CASCADE constraint)")
        print("   2. 🔍 Assess what data is missing")
        print("   3. 💾 Restore missing data from backup")
        print("   4. ✅ Test search functionality")

def immediate_actions():
    """List immediate actions to take"""
    
    print("\n🚨 IMMEDIATE ACTIONS REQUIRED")
    print("=" * 50)
    
    print("1. 🛑 STOP ALL DATA OPERATIONS")
    print("   - Don't run any more scripts that modify the database")
    print("   - Don't clear any more tables")
    print("   - Preserve current state for analysis")
    print()
    
    print("2. 💾 CHECK FOR BACKUPS")
    print("   - Check Coolify backup settings")
    print("   - Look for automatic MySQL backups")
    print("   - Check if any manual backups exist")
    print()
    
    print("3. 🔧 FIX SCHEMA FIRST")
    print("   - Run: flask db upgrade fix_search_cascade")
    print("   - This prevents future CASCADE disasters")
    print("   - Make news_search_index truly standalone")
    print()
    
    print("4. 📞 CONTACT SUPPORT")
    print("   - Contact Coolify support about database backups")
    print("   - Ask about point-in-time recovery options")
    print("   - Request assistance with data recovery")

def main():
    """Main recovery assessment"""
    
    app = create_app()
    
    with app.app_context():
        print("💔 NEWS SEARCH INDEX DISASTER RECOVERY")
        print("=" * 60)
        print()
        
        # Assess the damage
        damage_level = assess_damage()
        
        # Check recovery options
        recovery_options = check_backup_options()
        
        # Fix schema requirements
        fix_schema_first()
        
        # Create recovery plan
        create_recovery_plan()
        
        # Immediate actions
        immediate_actions()
        
        print("\n" + "=" * 60)
        print("🎯 NEXT STEPS:")
        print("1. Fix the schema to prevent future disasters")
        print("2. Check for database backups on Coolify")
        print("3. Choose appropriate recovery method")
        print("4. Test thoroughly before resuming operations")
        print()
        print("💡 LESSON LEARNED:")
        print("Buffer architecture requires careful foreign key design")
        print("CASCADE constraints are dangerous for standalone tables")
        print("=" * 60)

if __name__ == '__main__':
    main() 