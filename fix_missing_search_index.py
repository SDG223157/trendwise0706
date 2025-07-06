#!/usr/bin/env python3
"""
Fix Missing Search Index Entries
Bulk sync all AI articles that are missing from search index
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from app.utils.search.search_index_sync import sync_article_to_search_index
import time

def fix_missing_search_index():
    """Bulk sync all AI articles missing from search index"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Fixing Missing Search Index Entries")
        print("=" * 50)
        
        # Get all articles with AI content
        ai_articles = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_summary != ''
        ).all()
        
        print(f"📊 Found {len(ai_articles)} articles with AI content")
        
        # Find missing articles
        missing_articles = []
        for article in ai_articles:
            search_entry = NewsSearchIndex.query.filter_by(
                external_id=article.external_id
            ).first()
            
            if not search_entry:
                missing_articles.append(article)
        
        print(f"📊 Found {len(missing_articles)} articles missing from search index")
        
        if not missing_articles:
            print("✅ All AI articles are already in search index!")
            return
        
        # Bulk sync missing articles
        print(f"\n🔄 Syncing {len(missing_articles)} missing articles...")
        
        success_count = 0
        error_count = 0
        
        for i, article in enumerate(missing_articles, 1):
            try:
                print(f"   [{i}/{len(missing_articles)}] Syncing article {article.id}...")
                
                # Sync the article
                sync_result = sync_article_to_search_index(article)
                
                if sync_result:
                    success_count += 1
                    print(f"   ✅ Synced: {article.title[:60]}...")
                else:
                    error_count += 1
                    print(f"   ❌ Failed: {article.title[:60]}...")
                
                # Small delay to avoid overwhelming the system
                time.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                print(f"   ❌ Error syncing article {article.id}: {str(e)}")
                continue
        
        # Final status
        print(f"\n📊 Bulk Sync Results:")
        print(f"   ✅ Successfully synced: {success_count}")
        print(f"   ❌ Failed to sync: {error_count}")
        print(f"   📊 Total processed: {success_count + error_count}")
        
        # Verify results
        final_search_count = NewsSearchIndex.query.count()
        print(f"   📊 Search index entries after sync: {final_search_count}")
        
        if success_count > 0:
            print(f"\n🎉 Successfully fixed {success_count} missing search index entries!")
            print("✅ Your search functionality should now work properly")
        else:
            print(f"\n❌ No articles were successfully synced")
            print("💡 Check logs for specific error details")

if __name__ == "__main__":
    fix_missing_search_index() 