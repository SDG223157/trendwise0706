#!/usr/bin/env python3
"""
Investigate Sync Performance Issue

This script diagnoses the sync performance issue where:
- More search index entries than articles exist
- 0% sync rate for recent AI-processed articles
- Impossible sync coverage percentages
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path
sys.path.append(os.getcwd())

def investigate_sync_issue():
    """Investigate the sync performance and data consistency issues"""
    
    # Database connection
    db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        print("🔍 COMPREHENSIVE SYNC ISSUE INVESTIGATION")
        print("=" * 70)
        print(f"🕐 Investigation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. BASIC COUNTS VERIFICATION
        print("📊 STEP 1: Basic Table Counts")
        print("-" * 50)
        
        total_articles = session.execute(text('SELECT COUNT(*) FROM news_articles')).scalar()
        total_search_index = session.execute(text('SELECT COUNT(*) FROM news_search_index')).scalar()
        
        print(f"Total articles in news_articles: {total_articles:,}")
        print(f"Total entries in news_search_index: {total_search_index:,}")
        print(f"Search index to articles ratio: {total_search_index/total_articles:.2f}x")
        
        if total_search_index > total_articles:
            print("🚨 ANOMALY: More search index entries than articles!")
            print("   This suggests orphaned entries or duplicates in search index")
        
        # 2. AI-PROCESSED ARTICLES ANALYSIS
        print(f"\n🤖 STEP 2: AI-Processed Articles Analysis")
        print("-" * 50)
        
        ai_processed_total = session.execute(text('''
            SELECT COUNT(*) FROM news_articles 
            WHERE ai_summary IS NOT NULL 
            AND ai_insights IS NOT NULL 
            AND ai_sentiment_rating IS NOT NULL
            AND ai_summary != ''
            AND ai_insights != ''
        ''')).scalar()
        
        print(f"Total AI-processed articles: {ai_processed_total:,}")
        
        # Recent AI-processed articles
        recent_ai_processed = session.execute(text('''
            SELECT COUNT(*) FROM news_articles 
            WHERE ai_summary IS NOT NULL 
            AND ai_insights IS NOT NULL 
            AND ai_sentiment_rating IS NOT NULL
            AND ai_summary != ''
            AND ai_insights != ''
            AND created_at >= NOW() - INTERVAL 1 HOUR
        ''')).scalar()
        
        print(f"Recent AI-processed articles (1h): {recent_ai_processed:,}")
        
        # 3. ORPHANED SEARCH INDEX ENTRIES
        print(f"\n🔍 STEP 3: Orphaned Search Index Entries")
        print("-" * 50)
        
        orphaned_entries = session.execute(text('''
            SELECT COUNT(*) FROM news_search_index nsi
            LEFT JOIN news_articles na ON nsi.external_id = na.external_id
            WHERE na.external_id IS NULL
        ''')).scalar()
        
        print(f"Orphaned search index entries: {orphaned_entries:,}")
        
        if orphaned_entries > 0:
            print("🚨 ISSUE: Search index contains entries without corresponding articles")
            
            # Sample orphaned entries
            orphaned_sample = session.execute(text('''
                SELECT nsi.id, nsi.external_id, nsi.title, nsi.created_at
                FROM news_search_index nsi
                LEFT JOIN news_articles na ON nsi.external_id = na.external_id
                WHERE na.external_id IS NULL
                ORDER BY nsi.created_at DESC
                LIMIT 5
            ''')).fetchall()
            
            print("Sample orphaned entries:")
            for entry in orphaned_sample:
                print(f"  • Search ID {entry.id}: {entry.external_id} - {entry.title[:50]}...")
        
        # 4. DUPLICATE SEARCH INDEX ENTRIES
        print(f"\n🔄 STEP 4: Duplicate Search Index Entries")
        print("-" * 50)
        
        duplicate_count = session.execute(text('''
            SELECT COUNT(*) - COUNT(DISTINCT external_id) as duplicate_count
            FROM news_search_index
            WHERE external_id IS NOT NULL
        ''')).scalar()
        
        print(f"Duplicate external_ids in search index: {duplicate_count:,}")
        
        if duplicate_count > 0:
            print("🚨 ISSUE: Search index contains duplicate external_ids")
            
            # Sample duplicates
            duplicates_sample = session.execute(text('''
                SELECT external_id, COUNT(*) as count
                FROM news_search_index 
                WHERE external_id IS NOT NULL
                GROUP BY external_id 
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
                LIMIT 5
            ''')).fetchall()
            
            print("Sample duplicate external_ids:")
            for dup in duplicates_sample:
                print(f"  • {dup.external_id}: {dup.count} entries")
        
        # 5. UNSYNCED AI-PROCESSED ARTICLES
        print(f"\n⚠️ STEP 5: Unsynced AI-Processed Articles")
        print("-" * 50)
        
        unsynced_articles = session.execute(text('''
            SELECT COUNT(*) FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_sentiment_rating IS NOT NULL
            AND na.ai_summary != ''
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND na.external_id NOT IN (
                SELECT DISTINCT external_id FROM news_search_index 
                WHERE external_id IS NOT NULL
            )
        ''')).scalar()
        
        print(f"Total unsynced AI-processed articles: {unsynced_articles:,}")
        
        # Recent unsynced
        recent_unsynced = session.execute(text('''
            SELECT COUNT(*) FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_sentiment_rating IS NOT NULL
            AND na.ai_summary != ''
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND na.created_at >= NOW() - INTERVAL 1 HOUR
            AND na.external_id NOT IN (
                SELECT DISTINCT external_id FROM news_search_index 
                WHERE external_id IS NOT NULL
            )
        ''')).scalar()
        
        print(f"Recent unsynced AI-processed articles (1h): {recent_unsynced:,}")
        
        if unsynced_articles > 0:
            print("🚨 CRITICAL: AI-processed articles are not syncing to search index")
            
            # Sample unsynced articles
            unsynced_sample = session.execute(text('''
                SELECT na.id, na.title, na.external_id, na.created_at 
                FROM news_articles na
                WHERE na.ai_summary IS NOT NULL 
                AND na.ai_insights IS NOT NULL 
                AND na.ai_sentiment_rating IS NOT NULL
                AND na.ai_summary != ''
                AND na.ai_insights != ''
                AND na.external_id IS NOT NULL
                AND na.external_id NOT IN (
                    SELECT DISTINCT external_id FROM news_search_index 
                    WHERE external_id IS NOT NULL
                )
                ORDER BY na.created_at DESC
                LIMIT 5
            ''')).fetchall()
            
            print("Sample unsynced articles:")
            for article in unsynced_sample:
                print(f"  • ID {article.id}: {article.title[:60]}...")
                print(f"    External ID: {article.external_id}")
                print(f"    Created: {article.created_at}")
        
        # 6. SEARCH INDEX VALIDATION
        print(f"\n✅ STEP 6: Search Index Data Validation")
        print("-" * 50)
        
        # Check for invalid search index entries
        invalid_entries = session.execute(text('''
            SELECT COUNT(*) FROM news_search_index
            WHERE external_id IS NULL 
            OR external_id = ''
            OR title IS NULL
            OR title = ''
        ''')).scalar()
        
        print(f"Invalid search index entries: {invalid_entries:,}")
        
        # Check for entries with missing AI data
        missing_ai_data = session.execute(text('''
            SELECT COUNT(*) FROM news_search_index
            WHERE ai_summary IS NULL 
            OR ai_insights IS NULL
            OR ai_summary = ''
            OR ai_insights = ''
        ''')).scalar()
        
        print(f"Search index entries missing AI data: {missing_ai_data:,}")
        
        # 7. SYNC SERVICE STATUS CHECK
        print(f"\n🔄 STEP 7: Sync Service Status Check")
        print("-" * 50)
        
        # Check articles that should sync but haven't
        should_sync = session.execute(text('''
            SELECT COUNT(*) FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_sentiment_rating IS NOT NULL
            AND na.external_id IS NOT NULL
            AND na.published_at IS NOT NULL
        ''')).scalar()
        
        actually_synced = session.execute(text('''
            SELECT COUNT(DISTINCT na.external_id) FROM news_articles na
            INNER JOIN news_search_index nsi ON na.external_id = nsi.external_id
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_sentiment_rating IS NOT NULL
        ''')).scalar()
        
        print(f"Articles that should be synced: {should_sync:,}")
        print(f"Articles actually synced: {actually_synced:,}")
        
        if should_sync > 0:
            sync_efficiency = (actually_synced / should_sync) * 100
            print(f"Sync efficiency: {sync_efficiency:.1f}%")
            
            if sync_efficiency < 100:
                missing_syncs = should_sync - actually_synced
                print(f"🚨 SYNC GAP: {missing_syncs:,} articles should be synced but aren't")
        
        # 8. RECOMMENDATIONS
        print(f"\n💡 STEP 8: Diagnosis and Recommendations")
        print("-" * 50)
        
        print("🔍 DIAGNOSIS:")
        if orphaned_entries > 0:
            print(f"  • {orphaned_entries:,} orphaned search index entries (cleanup needed)")
        if duplicate_count > 0:
            print(f"  • {duplicate_count:,} duplicate search index entries (cleanup needed)")
        if unsynced_articles > 0:
            print(f"  • {unsynced_articles:,} AI-processed articles not syncing (sync service issue)")
        if recent_unsynced > 0:
            print(f"  • {recent_unsynced:,} recent articles stuck (immediate sync failure)")
        
        print(f"\n🛠️ IMMEDIATE ACTIONS NEEDED:")
        if orphaned_entries > 0:
            print("  1. Clean up orphaned search index entries")
        if duplicate_count > 0:
            print("  2. Remove duplicate search index entries")
        if unsynced_articles > 0:
            print("  3. Force sync of AI-processed articles")
        if recent_unsynced > 0:
            print("  4. Check AI scheduler logs for sync failures")
        
        print(f"\n📋 RECOMMENDED COMMANDS:")
        if orphaned_entries > 0 or duplicate_count > 0:
            print("  • python3 cleanup_search_index_issues.py")
        if unsynced_articles > 0:
            print("  • python3 force_sync_ai_articles.py")
        print("  • Check scheduler logs: tail -f logs/ai_scheduler.log")
        
    except Exception as e:
        print(f"❌ Error during investigation: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    investigate_sync_issue() 