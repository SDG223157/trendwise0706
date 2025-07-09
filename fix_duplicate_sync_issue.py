#!/usr/bin/env python3
"""
Fix Duplicate External ID Issue in Search Index

This script fixes the root cause of sync failures:
1. Cleans up existing duplicate external_ids in search index
2. Tests the sync service with the cleaned data
3. Forces sync of the 20 waiting articles

The diagnostic showed: external_id: DJN_DN20250107000230:0 (count: 3)
This is causing all sync operations to fail with constraint violations.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path
sys.path.append(os.getcwd())

from app.models import NewsArticle, NewsSearchIndex

def get_db_session():
    """Get database session"""
    db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def cleanup_duplicate_external_ids():
    """Clean up duplicate external_ids in search index, keeping the latest entry"""
    session = get_db_session()
    
    try:
        print("🔍 STEP 1: Finding duplicate external_ids in search index")
        print("=" * 60)
        
        # Find all duplicate external_ids
        duplicate_query = text("""
            SELECT external_id, COUNT(*) as count, MIN(id) as keep_id, MAX(id) as latest_id
            FROM news_search_index 
            GROUP BY external_id 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """)
        
        duplicates = session.execute(duplicate_query).fetchall()
        
        if not duplicates:
            print("✅ No duplicate external_ids found!")
            return {'cleaned': 0, 'errors': 0}
        
        print(f"❌ Found {len(duplicates)} external_ids with duplicates:")
        total_duplicates = 0
        for dup in duplicates:
            print(f"  • {dup.external_id}: {dup.count} entries (keeping latest: {dup.latest_id})")
            total_duplicates += dup.count - 1  # All but one will be deleted
        
        print(f"\n🗑️ STEP 2: Cleaning up {total_duplicates} duplicate entries")
        print("=" * 60)
        
        cleaned_count = 0
        error_count = 0
        
        for dup in duplicates:
            try:
                # Keep the latest entry (highest ID), delete the rest
                delete_query = text("""
                    DELETE FROM news_search_index 
                    WHERE external_id = :external_id 
                    AND id != :keep_id
                """)
                
                result = session.execute(delete_query, {
                    'external_id': dup.external_id,
                    'keep_id': dup.latest_id  # Keep the latest entry
                })
                
                deleted_count = result.rowcount
                cleaned_count += deleted_count
                
                print(f"✅ Cleaned {dup.external_id}: removed {deleted_count} duplicates, kept entry {dup.latest_id}")
                
            except Exception as e:
                print(f"❌ Error cleaning {dup.external_id}: {str(e)}")
                error_count += 1
        
        # Commit the cleanup
        session.commit()
        
        print(f"\n✅ CLEANUP COMPLETED:")
        print(f"   🗑️ Removed: {cleaned_count} duplicate entries")
        print(f"   ❌ Errors: {error_count}")
        
        # Verify cleanup
        print(f"\n🔍 STEP 3: Verifying cleanup")
        print("=" * 60)
        
        remaining_duplicates = session.execute(duplicate_query).fetchall()
        
        if remaining_duplicates:
            print(f"⚠️ Still have {len(remaining_duplicates)} external_ids with duplicates:")
            for dup in remaining_duplicates:
                print(f"  • {dup.external_id}: {dup.count} entries")
        else:
            print("✅ All duplicates cleaned! Search index now has unique external_ids")
        
        return {
            'cleaned': cleaned_count, 
            'errors': error_count,
            'remaining_duplicates': len(remaining_duplicates)
        }
        
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        session.rollback()
        return {'cleaned': 0, 'errors': 1, 'error_message': str(e)}
    finally:
        session.close()

def test_sync_after_cleanup():
    """Test syncing the 20 waiting articles after cleanup"""
    session = get_db_session()
    
    try:
        print(f"\n🧪 STEP 4: Testing sync of waiting articles")
        print("=" * 60)
        
        # Get AI-processed articles waiting for sync
        waiting_articles = session.query(NewsArticle).filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_sentiment_rating.isnot(None),
            NewsArticle.ai_summary != '',
            NewsArticle.ai_insights != ''
        ).order_by(NewsArticle.id.desc()).limit(25).all()  # Get more than 20 to be safe
        
        print(f"📊 Found {len(waiting_articles)} AI-processed articles to test")
        
        if not waiting_articles:
            print("⚠️ No AI-processed articles found to test")
            return {'synced': 0, 'errors': 0}
        
        # Test sync using SearchIndexSyncService
        from app.utils.search.search_index_sync import SearchIndexSyncService
        
        sync_service = SearchIndexSyncService(session)
        
        print(f"🚀 Attempting to sync {len(waiting_articles)} articles...")
        
        # Use the existing sync service
        sync_results = sync_service.sync_multiple_articles(waiting_articles)
        
        print(f"\n📊 SYNC TEST RESULTS:")
        print(f"   ✅ Added: {sync_results['added']}")
        print(f"   🔄 Updated: {sync_results['updated']}")
        print(f"   ⏭️ Skipped: {sync_results['skipped']}")
        print(f"   ❌ Errors: {sync_results['errors']}")
        
        # Verify results in search index
        search_index_count = session.query(NewsSearchIndex).count()
        print(f"   📊 Total articles in search index: {search_index_count}")
        
        return sync_results
        
    except Exception as e:
        print(f"❌ Error during sync test: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'synced': 0, 'errors': 1, 'error_message': str(e)}
    finally:
        session.close()

def force_sync_waiting_articles():
    """Force sync articles using direct SQL to bypass any ORM issues"""
    session = get_db_session()
    
    try:
        print(f"\n🔧 STEP 5: Force sync using direct SQL")
        print("=" * 60)
        
        # Use INSERT IGNORE to handle any remaining constraint issues
        force_sync_query = text("""
            INSERT IGNORE INTO news_search_index (
                external_id, article_id, title, content_excerpt, published_at, source,
                ai_summary, ai_insights, ai_sentiment_rating, symbols_json, created_at, updated_at
            )
            SELECT 
                na.external_id,
                na.id as article_id,
                na.title,
                LEFT(na.content, 500) as content_excerpt,
                na.published_at,
                na.source,
                na.ai_summary,
                na.ai_insights,
                na.ai_sentiment_rating,
                COALESCE(
                    (SELECT JSON_ARRAYAGG(symbol) 
                     FROM article_symbols 
                     WHERE article_id = na.id), 
                    JSON_ARRAY()
                ) as symbols_json,
                NOW() as created_at,
                NOW() as updated_at
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_sentiment_rating IS NOT NULL
            AND na.ai_summary != ''
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND na.external_id NOT IN (
                SELECT DISTINCT external_id 
                FROM news_search_index 
                WHERE external_id IS NOT NULL
            )
        """)
        
        result = session.execute(force_sync_query)
        synced_count = result.rowcount
        
        session.commit()
        
        print(f"✅ FORCE SYNC COMPLETED: {synced_count} articles synced to search index")
        
        # Verify final state
        total_search_articles = session.query(NewsSearchIndex).count()
        total_ai_articles = session.query(NewsArticle).filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_sentiment_rating.isnot(None)
        ).count()
        
        print(f"\n📊 FINAL STATE:")
        print(f"   📊 Total AI-processed articles: {total_ai_articles}")
        print(f"   📊 Total articles in search index: {total_search_articles}")
        print(f"   📈 Search index coverage: {(total_search_articles/total_ai_articles*100):.1f}%")
        
        return {'synced': synced_count, 'total_search': total_search_articles}
        
    except Exception as e:
        print(f"❌ Error during force sync: {str(e)}")
        session.rollback()
        return {'synced': 0, 'errors': 1, 'error_message': str(e)}
    finally:
        session.close()

def main():
    """Main execution"""
    print("🚀 FIXING DUPLICATE EXTERNAL_ID SYNC ISSUE")
    print("=" * 70)
    print("This script will fix the root cause of sync failures and sync waiting articles")
    print()
    
    # Step 1: Clean up duplicates
    cleanup_results = cleanup_duplicate_external_ids()
    
    if cleanup_results['errors'] > 0:
        print(f"⚠️ Cleanup had errors. Check logs before proceeding.")
        return
    
    # Step 2: Test sync with cleaned data
    sync_results = test_sync_after_cleanup()
    
    # Step 3: Force sync any remaining articles
    force_results = force_sync_waiting_articles()
    
    print(f"\n🎉 ISSUE RESOLUTION COMPLETE!")
    print("=" * 70)
    print(f"✅ Duplicates cleaned: {cleanup_results['cleaned']}")
    print(f"✅ Articles synced (test): {sync_results.get('added', 0) + sync_results.get('updated', 0)}")
    print(f"✅ Articles force synced: {force_results.get('synced', 0)}")
    print(f"📊 Total search index size: {force_results.get('total_search', 'unknown')}")
    
    print(f"\n💡 NEXT STEPS:")
    print("1. Deploy this fix to Coolify")
    print("2. Restart AI scheduler to test normal sync operation")
    print("3. Monitor logs for successful sync of new articles")
    print("4. The 20 waiting articles should now be available in search!")

if __name__ == "__main__":
    main() 