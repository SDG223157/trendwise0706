#!/usr/bin/env python3
"""
Populate AI data in news_search_index from news_articles table

This script migrates AI summary and insights data from the news_articles table
into the news_search_index table to enable standalone AI search.

After this migration:
- news_search_index becomes the primary search table with AI data
- news_articles can be used as a buffer table for new articles
- Search performance improves by eliminating joins
"""

import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from sqlalchemy import text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_ai_data():
    """Populate AI fields in news_search_index from news_articles"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Starting AI data migration to news_search_index...")
            
            # Get statistics before migration
            total_search_entries = db.session.query(NewsSearchIndex).count()
            ai_processed_articles = db.session.query(NewsArticle).filter(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_summary != '',
                NewsArticle.ai_insights != ''
            ).count()
            
            print(f"📊 Found {total_search_entries} entries in news_search_index")
            print(f"📊 Found {ai_processed_articles} AI-processed articles in news_articles")
            
            if ai_processed_articles == 0:
                print("⚠️ No AI-processed articles found. Nothing to migrate.")
                return True
            
            # Migrate AI data using efficient bulk update
            print("🔄 Migrating AI data...")
            
            # SQL query to update news_search_index with AI data from news_articles
            update_query = text("""
                UPDATE news_search_index nsi
                INNER JOIN news_articles na ON nsi.article_id = na.id
                SET 
                    nsi.ai_summary = na.ai_summary,
                    nsi.ai_insights = na.ai_insights,
                    nsi.updated_at = NOW()
                WHERE 
                    na.ai_summary IS NOT NULL 
                    AND na.ai_insights IS NOT NULL
                    AND na.ai_summary != ''
                    AND na.ai_insights != ''
            """)
            
            result = db.session.execute(update_query)
            db.session.commit()
            
            updated_count = result.rowcount
            print(f"✅ Updated {updated_count} entries in news_search_index with AI data")
            
            # Verify migration results
            print("🔍 Verifying migration results...")
            
            search_entries_with_ai = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None),
                NewsSearchIndex.ai_summary != '',
                NewsSearchIndex.ai_insights != ''
            ).count()
            
            print(f"✅ Verification: {search_entries_with_ai} entries now have AI data")
            
            # Show sample of migrated data
            sample_entries = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.ai_summary.isnot(None)
            ).limit(3).all()
            
            print("\n📝 Sample migrated entries:")
            for entry in sample_entries:
                print(f"  - ID: {entry.id}, Title: {entry.title[:50]}...")
                print(f"    AI Summary: {len(entry.ai_summary) if entry.ai_summary else 0} chars")
                print(f"    AI Insights: {len(entry.ai_insights) if entry.ai_insights else 0} chars")
            
            print(f"\n🎯 Migration Summary:")
            print(f"   • {updated_count} entries updated with AI data")
            print(f"   • {search_entries_with_ai} total entries now have AI content")
            print(f"   • Search table ready for standalone AI search")
            print(f"   • news_articles can now be used as buffer table")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during AI data migration: {str(e)}")
            db.session.rollback()
            return False

def verify_ai_data():
    """Verify the AI data migration was successful"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n🔍 Running AI data verification...")
            
            # Check search index entries with AI data
            total_entries = db.session.query(NewsSearchIndex).count()
            ai_entries = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None)
            ).count()
            
            # Check for orphaned entries (in search index but not in news_articles)
            orphaned_query = text("""
                SELECT COUNT(*) as orphaned_count
                FROM news_search_index nsi
                LEFT JOIN news_articles na ON nsi.article_id = na.id
                WHERE na.id IS NULL
            """)
            
            orphaned_result = db.session.execute(orphaned_query).fetchone()
            orphaned_count = orphaned_result.orphaned_count if orphaned_result else 0
            
            print(f"📊 Verification Results:")
            print(f"   • Total search index entries: {total_entries}")
            print(f"   • Entries with AI data: {ai_entries}")
            print(f"   • AI coverage: {(ai_entries/total_entries*100):.1f}%" if total_entries > 0 else "   • AI coverage: 0%")
            print(f"   • Orphaned entries: {orphaned_count}")
            
            if ai_entries > 0:
                print("✅ AI data migration verified successfully!")
                print("🚀 news_search_index is ready for standalone AI search")
                return True
            else:
                print("⚠️ No AI data found in search index")
                return False
                
        except Exception as e:
            print(f"❌ Error during verification: {str(e)}")
            return False

if __name__ == '__main__':
    print("🔄 AI Data Migration for news_search_index")
    print("=" * 50)
    
    success = populate_ai_data()
    
    if success:
        verify_ai_data()
        print("\n🎉 AI data migration completed successfully!")
        print("🔄 Next step: Update models and search logic to use standalone news_search_index")
    else:
        print("\n❌ AI data migration failed!")
        sys.exit(1) 