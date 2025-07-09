#!/usr/bin/env python3
"""
Debug AI Processing vs Search Index Sync Discrepancy

This script diagnoses why AI-processed articles aren't making it to the search index.
It shows the validation differences between AI processing and search index sync.
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path
sys.path.append(os.getcwd())

from app.models import NewsArticle

def get_db_session():
    """Get database session"""
    db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()

def analyze_sync_discrepancy():
    """Analyze why AI-processed articles aren't syncing to search index"""
    print("🔍 DEBUGGING AI PROCESSING vs SEARCH INDEX SYNC DISCREPANCY")
    print("=" * 70)
    
    with get_db_session() as session:
        # 1. Count articles that meet AI processing criteria
        print("\n📊 STEP 1: Articles that meet AI processing criteria")
        print("-" * 50)
        
        ai_processable_query = text("""
            SELECT COUNT(*) as count
            FROM news_articles 
            WHERE content IS NOT NULL 
            AND content != ''
            AND CHAR_LENGTH(TRIM(content)) > 20
            AND (ai_summary IS NULL OR ai_insights IS NULL OR ai_sentiment_rating IS NULL)
        """)
        
        ai_processable_count = session.execute(ai_processable_query).fetchone().count
        print(f"Articles ready for AI processing: {ai_processable_count}")
        
        # 2. Count articles that have been AI processed
        print("\n🤖 STEP 2: Articles that have been AI processed")
        print("-" * 45)
        
        ai_processed_query = text("""
            SELECT COUNT(*) as count
            FROM news_articles 
            WHERE ai_summary IS NOT NULL 
            AND ai_insights IS NOT NULL 
            AND ai_summary != '' 
            AND ai_insights != ''
        """)
        
        ai_processed_count = session.execute(ai_processed_query).fetchone().count
        print(f"Articles with complete AI processing: {ai_processed_count}")
        
        # 3. Count articles that meet basic search index sync criteria  
        print("\n🔄 STEP 3: Articles that meet BASIC search index sync criteria")
        print("-" * 55)
        
        sync_eligible_query = text("""
            SELECT COUNT(*) as count
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
        """)
        
        sync_eligible_count = session.execute(sync_eligible_query).fetchone().count
        print(f"Articles eligible for search index sync: {sync_eligible_count}")
        
        # 4. Count articles that fail external_id validation
        print("\n❌ STEP 4: Articles that FAIL external_id validation")
        print("-" * 50)
        
        no_external_id_query = text("""
            SELECT COUNT(*) as count
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NULL
        """)
        
        no_external_id_count = session.execute(no_external_id_query).fetchone().count
        print(f"AI-processed articles WITHOUT external_id: {no_external_id_count}")
        
        # 5. Count articles that fail published_at validation
        print("\n📅 STEP 5: Articles that FAIL published_at validation")
        print("-" * 50)
        
        no_published_at_query = text("""
            SELECT COUNT(*) as count
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND na.published_at IS NULL
        """)
        
        no_published_at_count = session.execute(no_published_at_query).fetchone().count
        print(f"AI-processed articles WITHOUT published_at: {no_published_at_count}")
        
        # 6. Count articles fully validated for sync
        print("\n✅ STEP 6: Articles that pass FULL validation for sync")
        print("-" * 52)
        
        fully_validated_query = text("""
            SELECT COUNT(*) as count
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND na.published_at IS NOT NULL
            AND TRIM(na.ai_summary) != ''
            AND TRIM(na.ai_insights) != ''
        """)
        
        fully_validated_count = session.execute(fully_validated_query).fetchone().count
        print(f"Articles passing FULL validation: {fully_validated_count}")
        
        # 7. Count articles already in search index
        print("\n🗄️ STEP 7: Articles already in search index")
        print("-" * 40)
        
        in_search_index_query = text("""
            SELECT COUNT(DISTINCT na.external_id) as count
            FROM news_articles na
            INNER JOIN news_search_index nsi ON na.external_id = nsi.external_id
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND nsi.ai_summary IS NOT NULL
            AND nsi.ai_insights IS NOT NULL
        """)
        
        in_search_index_count = session.execute(in_search_index_query).fetchone().count
        print(f"Articles already synced to search index: {in_search_index_count}")
        
        # 8. Show sample failing articles
        print("\n🔍 STEP 8: Sample articles that fail validation")
        print("-" * 45)
        
        failing_articles_query = text("""
            SELECT id, title, external_id, published_at, 
                   LENGTH(ai_summary) as summary_len,
                   LENGTH(ai_insights) as insights_len,
                   CASE 
                       WHEN external_id IS NULL THEN 'Missing external_id'
                       WHEN published_at IS NULL THEN 'Missing published_at'
                       WHEN TRIM(ai_summary) = '' THEN 'Empty AI summary after trim'
                       WHEN TRIM(ai_insights) = '' THEN 'Empty AI insights after trim'
                       ELSE 'Unknown issue'
                   END as failure_reason
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND (
                na.external_id IS NULL 
                OR na.published_at IS NULL
                OR TRIM(na.ai_summary) = ''
                OR TRIM(na.ai_insights) = ''
            )
            LIMIT 10
        """)
        
        failing_articles = session.execute(failing_articles_query).fetchall()
        
        if failing_articles:
            print("Sample failing articles:")
            for article in failing_articles:
                print(f"  • ID {article.id}: {article.title[:50]}...")
                print(f"    Reason: {article.failure_reason}")
                print(f"    external_id: {article.external_id}")
                print(f"    published_at: {article.published_at}")
                print(f"    AI content lengths: summary={article.summary_len}, insights={article.insights_len}")
                print()
        else:
            print("No failing articles found!")
        
        # 9. Show the discrepancy calculation
        print("\n📊 DISCREPANCY ANALYSIS")
        print("=" * 25)
        print(f"✅ Articles with AI processing: {ai_processed_count}")
        print(f"❌ Articles failing validation: {ai_processed_count - fully_validated_count}")
        print(f"✅ Articles passing validation: {fully_validated_count}")
        print(f"🗄️ Articles in search index: {in_search_index_count}")
        print(f"🔄 Articles needing sync: {fully_validated_count - in_search_index_count}")
        
        # 10. Show breakdown of validation failures
        print("\n🔍 VALIDATION FAILURE BREAKDOWN")
        print("=" * 35)
        print(f"📝 Missing external_id: {no_external_id_count}")
        print(f"📅 Missing published_at: {no_published_at_count}")
        
        empty_content_query = text("""
            SELECT COUNT(*) as count
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND na.published_at IS NOT NULL
            AND (TRIM(na.ai_summary) = '' OR TRIM(na.ai_insights) = '')
        """)
        
        empty_content_count = session.execute(empty_content_query).fetchone().count
        print(f"🗂️ Empty content after trim: {empty_content_count}")
        
        print("\n💡 CONCLUSION:")
        print("-" * 12)
        if no_external_id_count > 0:
            print(f"❗ MAIN ISSUE: {no_external_id_count} AI-processed articles are missing external_id")
            print("   This prevents them from being synced to search index.")
        if no_published_at_count > 0:
            print(f"❗ SECONDARY ISSUE: {no_published_at_count} articles are missing published_at")
        if empty_content_count > 0:
            print(f"❗ CONTENT ISSUE: {empty_content_count} articles have empty AI content after trimming")
            
        if no_external_id_count == 0 and no_published_at_count == 0 and empty_content_count == 0:
            print("✅ No validation issues found. The sync process should be working correctly.")
        else:
            print("\n🔧 RECOMMENDED FIXES:")
            print("1. Ensure all fetched articles have external_id set")
            print("2. Ensure all fetched articles have published_at set")
            print("3. Add validation to prevent empty AI content generation")

if __name__ == "__main__":
    analyze_sync_discrepancy() 