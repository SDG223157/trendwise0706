#!/usr/bin/env python3
"""
Fix: Frontend Cache Issue with Latest Search

The backend is working correctly (returning 1,802 articles) but the frontend
is still showing 11,498. This suggests a caching issue.
"""

import sys
import os
sys.path.insert(0, '.')

def fix_frontend_cache_issue():
    """Clear all caches and restart application"""
    
    try:
        from app import create_app, db
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        
        app = create_app()
        
        with app.app_context():
            print("🧹 CLEARING ALL CACHES")
            print("=" * 30)
            
            # Clear search cache
            search = OptimizedNewsSearch(db.session)
            if search.is_cache_available():
                search.clear_cache()
                print("✅ Cleared search cache")
            
            # Clear Redis cache patterns
            if search.cache and search.cache.is_available():
                patterns_to_clear = [
                    'standalone_search:*',
                    'standalone_symbol:*', 
                    'standalone_keyword:*',
                    'popular_search:*',
                    'news_cache:*',
                    'article_cache:*',
                    'pagination:*'
                ]
                
                for pattern in patterns_to_clear:
                    try:
                        deleted = search.cache.delete_pattern(pattern)
                        print(f"✅ Cleared pattern {pattern}: {deleted} keys")
                    except Exception as e:
                        print(f"⚠️  Could not clear {pattern}: {str(e)}")
            
            # Test the search one more time
            print("\n🧪 TESTING SEARCH AFTER CACHE CLEAR")
            print("-" * 40)
            
            articles, total, has_more = search.search_by_keywords(
                keywords=['latest'],
                page=1,
                per_page=1,
                force_latest_filter=True
            )
            
            print(f"Backend search results:")
            print(f"   Articles: {len(articles)}")
            print(f"   Total count: {total}")
            print(f"   Has more: {has_more}")
            
            if total == 1802:
                print("✅ Backend is working correctly!")
                print("🔧 Issue is in frontend display/caching")
                print("\n📋 NEXT STEPS:")
                print("1. Restart your application completely")
                print("2. Clear browser cache/hard refresh")
                print("3. Check browser developer tools for JS errors")
                print("4. Verify the search is using the correct API endpoint")
            else:
                print(f"❌ Backend still returning wrong count: {total}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_frontend_cache_issue() 