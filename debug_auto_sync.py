#!/usr/bin/env python3
"""
Debug Auto-Sync Issues
Investigate why search index is empty despite AI processing working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from datetime import datetime

def debug_auto_sync():
    """Debug auto-sync functionality"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Auto-Sync Debug Analysis")
        print("=" * 50)
        
        # Get articles with AI content
        ai_articles = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_summary != ''
        ).all()
        
        print(f"📊 Found {len(ai_articles)} articles with AI content")
        print(f"📊 Search index entries: {NewsSearchIndex.query.count()}")
        
        if not ai_articles:
            print("❌ No articles with AI content found")
            return
        
        # Test auto-sync manually on one article
        test_article = ai_articles[0]
        print(f"\n🧪 Testing auto-sync on article {test_article.id}")
        print(f"   Title: {test_article.title[:100]}...")
        print(f"   AI Summary: {'✅' if test_article.ai_summary else '❌'}")
        print(f"   AI Insights: {'✅' if test_article.ai_insights else '❌'}")
        print(f"   AI Sentiment: {test_article.ai_sentiment_rating}")
        
        # Try to import and run the sync function
        try:
            from app.utils.search.search_index_sync import sync_article_to_search_index
            print("✅ Successfully imported sync_article_to_search_index")
            
            # Test the sync function
            print("🔄 Testing sync function...")
            sync_result = sync_article_to_search_index(test_article)
            
            if sync_result:
                print("✅ Sync function returned success")
                
                # Check if search index was actually updated
                search_entry = NewsSearchIndex.query.filter_by(
                    external_id=test_article.external_id
                ).first()
                
                if search_entry:
                    print("✅ Search index entry found!")
                    print(f"   Search ID: {search_entry.id}")
                    print(f"   Article ID: {search_entry.article_id}")
                    print(f"   Title: {search_entry.title}")
                    print(f"   AI Summary: {'✅' if search_entry.ai_summary else '❌'}")
                    print(f"   AI Insights: {'✅' if search_entry.ai_insights else '❌'}")
                else:
                    print("❌ No search index entry found after sync")
                    
            else:
                print("❌ Sync function returned failure")
                
        except ImportError as e:
            print(f"❌ Failed to import sync function: {e}")
            return
        except Exception as e:
            print(f"❌ Error testing sync function: {e}")
            return
        
        # Check all AI articles vs search index
        print(f"\n📋 Checking all AI articles vs search index:")
        
        synced_count = 0
        missing_count = 0
        
        for article in ai_articles:
            search_entry = NewsSearchIndex.query.filter_by(
                external_id=article.external_id
            ).first()
            
            if search_entry:
                synced_count += 1
            else:
                missing_count += 1
                if missing_count <= 5:  # Show first 5 missing
                    print(f"   ❌ Missing: Article {article.id} - {article.title[:60]}...")
        
        print(f"\n📊 Summary:")
        print(f"   AI Articles: {len(ai_articles)}")
        print(f"   Synced to search index: {synced_count}")
        print(f"   Missing from search index: {missing_count}")
        
        # Test bulk sync
        if missing_count > 0:
            print(f"\n🔄 Testing bulk sync for missing articles...")
            
            try:
                from app.utils.search.search_index_sync import bulk_sync_articles_to_search_index
                
                # Get articles that need syncing
                articles_to_sync = []
                for article in ai_articles:
                    search_entry = NewsSearchIndex.query.filter_by(
                        external_id=article.external_id
                    ).first()
                    if not search_entry:
                        articles_to_sync.append(article)
                
                print(f"   Found {len(articles_to_sync)} articles needing sync")
                
                if articles_to_sync:
                    bulk_result = bulk_sync_articles_to_search_index(articles_to_sync)
                    print(f"   Bulk sync result: {bulk_result}")
                    
                    # Check results
                    new_search_count = NewsSearchIndex.query.count()
                    print(f"   Search index entries after bulk sync: {new_search_count}")
                    
            except ImportError:
                print("   ❌ Bulk sync function not available")
            except Exception as e:
                print(f"   ❌ Bulk sync error: {e}")
        
        # Final recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if missing_count == 0:
            print("   ✅ All AI articles are properly synced to search index")
        elif sync_result:
            print("   ✅ Sync function works - consider running bulk sync")
            print("   💡 Run: python3 -c \"from app.utils.search.search_index_sync import bulk_sync_all; bulk_sync_all()\"")
        else:
            print("   ❌ Sync function is broken - check search_index_sync.py")
            print("   💡 Check foreign key constraints and database permissions")

if __name__ == "__main__":
    debug_auto_sync() 