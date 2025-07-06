#!/usr/bin/env python3
"""
Robust AI Data Population Script for Search Index
Handles database locking and runs in smaller batches
"""

import os
import sys
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

def populate_search_index_robust():
    """Populate search index with AI data from news articles - robust version"""
    
    print("🔍 Starting robust AI data population...")
    print("=" * 60)
    
    try:
        # Database connection with extended timeout
        db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}?connect_timeout=60&read_timeout=60&write_timeout=60"
        engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=300)
        Session = sessionmaker(bind=engine)
        
        # Step 1: Verify environment
        print("🔍 Environment Check:")
        print(f"   • Database Host: {os.getenv('MYSQL_HOST')}")
        print(f"   • Database Name: {os.getenv('MYSQL_DATABASE')}")
        
        # Step 2: Check current data status
        with Session() as session:
            try:
                # Check articles with AI data
                ai_articles = session.execute(text("""
                    SELECT 
                        COUNT(*) as total_with_ai,
                        MIN(id) as min_id,
                        MAX(id) as max_id
                    FROM news_articles 
                    WHERE ai_summary IS NOT NULL 
                    AND ai_summary != ''
                    AND ai_insights IS NOT NULL 
                    AND ai_insights != ''
                """)).fetchone()
                
                # Check current search index
                search_entries = session.execute(text("""
                    SELECT COUNT(*) as total_entries
                    FROM news_search_index
                """)).fetchone()
                
                print(f"📊 Current Status:")
                print(f"   • Articles with AI data: {ai_articles.total_with_ai}")
                print(f"   • Search index entries: {search_entries.total_entries}")
                
                if ai_articles.total_with_ai == 0:
                    print("⚠️ No AI-processed articles found. Nothing to migrate.")
                    return True
                    
            except Exception as e:
                print(f"❌ Error checking data status: {str(e)}")
                return False
        
        # Step 3: Populate in small batches with retry logic
        batch_size = 5  # Small batches to avoid locking
        max_retries = 3
        total_processed = 0
        total_failed = 0
        
        print(f"\n🔄 Starting population in batches of {batch_size}...")
        
        # Get articles to process in batches
        offset = 0
        while True:
            batch_success = False
            
            for attempt in range(max_retries):
                try:
                    with Session() as session:
                        # Get batch of articles with ORM to access relationships
                        from app.models import NewsArticle, NewsSearchIndex
                        
                        articles = session.query(NewsArticle).filter(
                            NewsArticle.ai_summary.isnot(None),
                            NewsArticle.ai_summary != '',
                            NewsArticle.ai_insights.isnot(None),
                            NewsArticle.ai_insights != '',
                            ~NewsArticle.id.in_(
                                session.query(NewsSearchIndex.article_id).filter(
                                    NewsSearchIndex.article_id.isnot(None)
                                ).subquery()
                            )
                        ).order_by(NewsArticle.id).offset(offset).limit(batch_size).all()
                        
                        if not articles:
                            print(f"✅ No more articles to process")
                            batch_success = True
                            break
                        
                        # Process batch
                        for article in articles:
                            try:
                                # Create search index entry manually (without article_symbols table)
                                search_entry = NewsSearchIndex()
                                search_entry.article_id = article.id
                                search_entry.external_id = article.external_id
                                search_entry.title = article.title
                                search_entry.url = article.url
                                search_entry.published_at = article.published_at
                                search_entry.source = article.source
                                search_entry.ai_summary = article.ai_summary
                                search_entry.ai_insights = article.ai_insights
                                search_entry.ai_sentiment_rating = article.ai_sentiment_rating
                                search_entry.symbols_json = "[]"  # Empty for now, will be populated by simple extraction
                                # created_at and updated_at will be set automatically by the model
                                
                                # Add to session
                                session.add(search_entry)
                                
                                total_processed += 1
                                print(f"   ✅ Processed article {article.id}: {article.title[:50]}...")
                                
                            except Exception as e:
                                total_failed += 1
                                print(f"   ❌ Failed article {article.id}: {str(e)}")
                        
                        # Commit batch
                        session.commit()
                        batch_success = True
                        print(f"   📦 Batch complete: {len(articles)} articles processed")
                        
                        # Short delay between batches
                        time.sleep(0.5)
                        break
                        
                except OperationalError as e:
                    if "Lock wait timeout" in str(e):
                        print(f"   ⏱️ Lock timeout (attempt {attempt + 1}/{max_retries}), retrying...")
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise
                except Exception as e:
                    print(f"   ❌ Batch error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(1)
            
            if not batch_success:
                print(f"❌ Failed to process batch after {max_retries} attempts")
                break
            
            if not articles:  # No more articles to process
                break
                
            offset += batch_size
        
        # Step 4: Final verification
        print(f"\n🔍 Final verification...")
        with Session() as session:
            final_count = session.execute(text("""
                SELECT COUNT(*) as total_entries
                FROM news_search_index
            """)).fetchone()
            
            print(f"📊 Final Results:")
            print(f"   • Total processed: {total_processed}")
            print(f"   • Total failed: {total_failed}")
            print(f"   • Search index entries: {final_count.total_entries}")
            
            if final_count.total_entries > 0:
                print(f"✅ Search index populated successfully!")
                print(f"🔄 Next: Test search functionality")
                return True
            else:
                print(f"⚠️ Search index still empty - check for issues")
                return False
                
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        return False

if __name__ == "__main__":
    success = populate_search_index_robust()
    sys.exit(0 if success else 1) 