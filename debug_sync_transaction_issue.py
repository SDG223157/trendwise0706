#!/usr/bin/env python3
"""
Debug Sync Transaction Issue

This script investigates why sync operations report success but fewer articles 
actually make it to the database (e.g., logs show 4 synced but only 3 in DB).

Potential causes:
1. Transaction rollback after sync
2. Database constraint violations
3. Foreign key constraint issues
4. Duplicate detection problems
5. Session commit issues
"""

import os
import sys
from datetime import datetime, timedelta
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

def analyze_recent_sync_transactions():
    """Analyze recent sync transactions to identify failures"""
    session = get_db_session()
    
    try:
        print("🔍 DEBUGGING SYNC TRANSACTION ISSUES")
        print("=" * 70)
        
        # Get the most recent AI-processed articles
        recent_processed = session.query(NewsArticle).filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_sentiment_rating.isnot(None)
        ).order_by(NewsArticle.id.desc()).limit(20).all()
        
        print(f"\n📊 STEP 1: Recent AI-processed articles (last 20)")
        print("-" * 50)
        print(f"Total AI-processed articles found: {len(recent_processed)}")
        
        if not recent_processed:
            print("❌ No AI-processed articles found!")
            return
            
        # Check which ones are in search index
        processed_ids = [article.id for article in recent_processed]
        
        search_index_articles = session.query(NewsSearchIndex).filter(
            NewsSearchIndex.article_id.in_(processed_ids)
        ).all()
        
        synced_ids = [article.article_id for article in search_index_articles]
        missing_ids = [id for id in processed_ids if id not in synced_ids]
        
        print(f"\n📊 STEP 2: Sync status analysis")
        print("-" * 50)
        print(f"Articles in search index: {len(synced_ids)}")
        print(f"Articles missing from search index: {len(missing_ids)}")
        
        if missing_ids:
            print(f"\n❌ STEP 3: Missing articles analysis")
            print("-" * 50)
            
            missing_articles = session.query(NewsArticle).filter(
                NewsArticle.id.in_(missing_ids)
            ).all()
            
            for article in missing_articles:
                print(f"Missing ID {article.id}: {article.title[:60]}...")
                
                # Check validation criteria
                validation_issues = []
                
                if not article.external_id:
                    validation_issues.append("❌ Missing external_id")
                if not article.published_at:
                    validation_issues.append("❌ Missing published_at")
                if not article.content or len(article.content.strip()) == 0:
                    validation_issues.append("❌ Empty content")
                if not article.ai_summary:
                    validation_issues.append("❌ Missing AI summary")
                if not article.ai_insights:
                    validation_issues.append("❌ Missing AI insights")
                if article.ai_sentiment_rating is None:
                    validation_issues.append("❌ Missing AI sentiment")
                
                if validation_issues:
                    print(f"  Validation issues: {', '.join(validation_issues)}")
                else:
                    print(f"  ✅ All validation criteria met - should sync!")
                    
        # Check for potential constraint violations
        print(f"\n🔍 STEP 4: Constraint violation analysis")
        print("-" * 50)
        
        # Check for duplicate external_ids in search index
        duplicate_external_ids = session.execute(text("""
            SELECT external_id, COUNT(*) as count 
            FROM news_search_index 
            WHERE external_id IN (
                SELECT external_id 
                FROM news_articles 
                WHERE id IN :ids
            )
            GROUP BY external_id 
            HAVING COUNT(*) > 1
        """), {"ids": tuple(processed_ids)}).fetchall()
        
        if duplicate_external_ids:
            print(f"❌ Found {len(duplicate_external_ids)} duplicate external_ids in search index:")
            for dup in duplicate_external_ids:
                print(f"  external_id: {dup[0]} (count: {dup[1]})")
        else:
            print("✅ No duplicate external_ids found")
            
        # Check for foreign key constraint issues
        print(f"\n🔍 STEP 5: Foreign key constraint analysis")
        print("-" * 50)
        
        # Check if articles still exist in news_articles after sync
        still_in_buffer = session.query(NewsArticle).filter(
            NewsArticle.id.in_(processed_ids)
        ).count()
        
        print(f"Articles still in buffer (news_articles): {still_in_buffer}")
        print(f"Articles in search index: {len(synced_ids)}")
        
        if still_in_buffer > 0:
            print("⚠️  Some processed articles still in buffer - buffer clearing might have failed")
        
        # Check the latest sync attempt details
        print(f"\n🔍 STEP 6: Latest sync attempt analysis")
        print("-" * 50)
        
        # Get the 10 most recent articles that should have been synced
        latest_processed = session.query(NewsArticle).filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_sentiment_rating.isnot(None)
        ).order_by(NewsArticle.id.desc()).limit(10).all()
        
        if latest_processed:
            print(f"Latest 10 AI-processed articles:")
            for article in latest_processed:
                in_search_index = article.id in synced_ids
                status = "✅ SYNCED" if in_search_index else "❌ MISSING"
                print(f"  ID {article.id}: {status} - {article.title[:50]}...")
                
            synced_count = sum(1 for article in latest_processed if article.id in synced_ids)
            print(f"\nSync success rate: {synced_count}/{len(latest_processed)} ({synced_count/len(latest_processed)*100:.1f}%)")
            
        # Check for any database errors that might not be logged
        print(f"\n🔍 STEP 7: Database integrity check")
        print("-" * 50)
        
        # Check if there are any NULL values in required fields
        null_checks = session.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN external_id IS NULL THEN 1 ELSE 0 END) as null_external_id,
                SUM(CASE WHEN published_at IS NULL THEN 1 ELSE 0 END) as null_published_at,
                SUM(CASE WHEN content IS NULL OR content = '' THEN 1 ELSE 0 END) as null_content
            FROM news_search_index
            WHERE article_id IN :ids
        """), {"ids": tuple(processed_ids) if processed_ids else (0,)}).fetchone()
        
        if null_checks:
            print(f"Search index integrity:")
            print(f"  Total records: {null_checks[0]}")
            print(f"  NULL external_id: {null_checks[1]}")
            print(f"  NULL published_at: {null_checks[2]}")
            print(f"  NULL/empty content: {null_checks[3]}")
            
        print(f"\n💡 DIAGNOSIS:")
        print("=" * 50)
        if len(missing_ids) > 0:
            print(f"❌ ISSUE CONFIRMED: {len(missing_ids)} articles missing from search index")
            print(f"   This explains why only {len(synced_ids)} articles synced instead of expected number")
        else:
            print("✅ All recent articles are properly synced to search index")
            
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    analyze_recent_sync_transactions() 