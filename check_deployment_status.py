#!/usr/bin/env python3
"""
Check deployment status and auto-sync functionality
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def check_deployment_status():
    """Check if the auto-sync fix is deployed and working"""
    
    print("🔍 DEPLOYMENT STATUS CHECK")
    print("=" * 50)
    
    try:
        # Database connection
        db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check news_articles with AI data
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total_articles,
                COUNT(CASE WHEN ai_summary IS NOT NULL AND ai_summary != '' THEN 1 END) as ai_processed,
                MAX(published_at) as latest_article,
                MAX(CASE WHEN ai_summary IS NOT NULL AND ai_summary != '' THEN published_at END) as latest_ai_processed
            FROM news_articles
        """)).fetchone()
        
        print(f"📰 NEWS_ARTICLES TABLE:")
        print(f"   • Total articles: {result.total_articles}")
        print(f"   • AI processed: {result.ai_processed}")
        print(f"   • Latest article: {result.latest_article}")
        print(f"   • Latest AI processed: {result.latest_ai_processed}")
        
        # Check search index
        search_result = session.execute(text("""
            SELECT 
                COUNT(*) as total_entries,
                COUNT(CASE WHEN ai_summary IS NOT NULL AND ai_summary != '' THEN 1 END) as with_ai_data
            FROM news_search_index
        """)).fetchone()
        
        print(f"\n🔍 NEWS_SEARCH_INDEX TABLE:")
        print(f"   • Total entries: {search_result.total_entries}")
        print(f"   • With AI data: {search_result.with_ai_data}")
        
        # Check for recent AI processing (last 1 hour)
        recent_ai = session.execute(text("""
            SELECT id, title, ai_summary IS NOT NULL as has_summary
            FROM news_articles 
            WHERE ai_summary IS NOT NULL 
            AND published_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            ORDER BY published_at DESC
            LIMIT 5
        """)).fetchall()
        
        print(f"\n🕐 RECENT AI PROCESSING (last hour):")
        if recent_ai:
            for article in recent_ai:
                print(f"   • Article {article.id}: {article.title[:60]}... (AI: {'✅' if article.has_summary else '❌'})")
        else:
            print("   • No recent AI processing detected")
        
        # Check if articles need syncing
        sync_needed = session.execute(text("""
            SELECT 
                a.id, a.title, a.ai_summary IS NOT NULL as has_ai,
                si.id IS NOT NULL as in_search_index
            FROM news_articles a
            LEFT JOIN news_search_index si ON a.id = si.article_id
            WHERE a.ai_summary IS NOT NULL AND a.ai_summary != ''
            AND si.id IS NULL
            LIMIT 10
        """)).fetchall()
        
        print(f"\n🔄 ARTICLES NEEDING SYNC:")
        if sync_needed:
            print(f"   • {len(sync_needed)} articles with AI data not in search index")
            for article in sync_needed:
                print(f"   • Article {article.id}: {article.title[:50]}...")
        else:
            print("   • All AI-processed articles are synced")
        
        session.close()
        
        print(f"\n📋 SUMMARY:")
        if result.ai_processed > 0 and search_result.total_entries == 0:
            print("   ⚠️  AI-processed articles exist but search index is empty")
            print("   🔄 Need to run population script on Coolify deployment")
        elif result.ai_processed == 0:
            print("   ⚠️  No AI-processed articles found")
            print("   🤖 Wait for AI scheduler to process articles")
        else:
            print("   ✅ System appears to be working correctly")
            
        print(f"\n🚀 NEXT STEPS:")
        print("   1. Ensure this script runs on Coolify deployment")
        print("   2. Run populate_search_index_ai_data.py on Coolify")
        print("   3. Monitor auto-sync for new articles")
        
    except Exception as e:
        print(f"❌ Error checking deployment status: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    check_deployment_status() 