#!/usr/bin/env python3
"""
Comprehensive Latest Search Debug

This script will trace exactly what's happening with the "latest" search
to identify why it's still showing 11,498 articles instead of ~1,809.
"""

import sys
import os
sys.path.insert(0, '.')

def debug_latest_search_comprehensive():
    """Comprehensive debugging of the latest search functionality"""
    
    try:
        from app import create_app, db
        from app.models import NewsSearchIndex
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        from app.news.routes import _parse_unified_search_params
        from datetime import datetime, timedelta
        from sqlalchemy import and_, or_
        
        app = create_app()
        
        with app.app_context():
            print("🔍 COMPREHENSIVE LATEST SEARCH DEBUG")
            print("=" * 60)
            
            # 1. Check current code implementation
            print("1. 📋 CHECKING CODE IMPLEMENTATION")
            print("-" * 35)
            
            # Read the current search file to see what code is actually there
            search_file = 'app/utils/search/optimized_news_search.py'
            try:
                with open(search_file, 'r') as f:
                    content = f.read()
                    
                if "filtering to last 3 days with AI-only articles" in content:
                    print("✅ Fix appears to be in the code")
                else:
                    print("❌ Fix not found in code - that's the problem!")
                    
                if "Special handling for \"latest\" keyword with strict AI filtering" in content:
                    print("✅ Latest keyword logic updated")
                else:
                    print("❌ Latest keyword logic not updated")
                    
            except Exception as e:
                print(f"❌ Error reading search file: {str(e)}")
            
            # 2. Test route parsing
            print("\n2. 🔧 TESTING ROUTE PARSING")
            print("-" * 25)
            
            mock_args = {}
            search_params = _parse_unified_search_params('latest', '', '', mock_args)
            
            print(f"Search params for 'latest':")
            for key, value in search_params.items():
                print(f"   {key}: {value}")
            
            has_latest = search_params.get('has_latest', False)
            print(f"\n✅ has_latest flag: {has_latest}")
            
            # 3. Test database queries manually
            print("\n3. 📊 TESTING DATABASE QUERIES")
            print("-" * 30)
            
            three_days_ago = datetime.now() - timedelta(days=3)
            
            # Query 1: All articles
            total_all = NewsSearchIndex.query.count()
            print(f"Total articles in search index: {total_all}")
            
            # Query 2: AI-only articles
            ai_only = NewsSearchIndex.query.filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None),
                NewsSearchIndex.ai_summary != '',
                NewsSearchIndex.ai_insights != ''
            ).count()
            print(f"Articles with AI processing: {ai_only}")
            
            # Query 3: Recent articles (3 days)
            recent_all = NewsSearchIndex.query.filter(
                NewsSearchIndex.published_at >= three_days_ago
            ).count()
            print(f"Articles from last 3 days (all): {recent_all}")
            
            # Query 4: Recent + AI articles (what "latest" should return)
            recent_ai = NewsSearchIndex.query.filter(
                NewsSearchIndex.published_at >= three_days_ago,
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None),
                NewsSearchIndex.ai_summary != '',
                NewsSearchIndex.ai_insights != ''
            ).count()
            print(f"Articles from last 3 days WITH AI: {recent_ai}")
            
            # 4. Test actual search method
            print("\n4. 🧪 TESTING ACTUAL SEARCH METHOD")
            print("-" * 35)
            
            search = OptimizedNewsSearch(db.session)
            
            # Test with force_latest_filter=True (like the route should call)
            print("Testing search_by_keywords with force_latest_filter=True:")
            articles, total, has_more = search.search_by_keywords(
                keywords=['latest'],
                page=1,
                per_page=5,
                force_latest_filter=True
            )
            
            print(f"   Results: {len(articles)} articles")
            print(f"   Total count: {total}")
            print(f"   Has more: {has_more}")
            
            # 5. Check what the query actually does step by step
            print("\n5. 🔬 STEP-BY-STEP QUERY ANALYSIS")
            print("-" * 35)
            
            # Simulate the exact same logic from search_by_keywords
            query = db.session.query(NewsSearchIndex)
            print(f"Initial query count: {query.count()}")
            
            # Step 1: AI-only filter (should always be applied)
            query = query.filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None),
                NewsSearchIndex.ai_summary != '',
                NewsSearchIndex.ai_insights != ''
            )
            print(f"After AI-only filter: {query.count()}")
            
            # Step 2: Check if latest keyword logic is triggered
            keywords = ['latest']
            force_latest_filter = True
            has_latest_keyword = any(kw.lower() == 'latest' for kw in keywords) or force_latest_filter
            
            print(f"has_latest_keyword: {has_latest_keyword}")
            
            if has_latest_keyword:
                # Step 3: Apply 3-day filter
                query = query.filter(
                    NewsSearchIndex.published_at >= three_days_ago
                )
                print(f"After 3-day filter: {query.count()}")
            
            # 6. Cache investigation
            print("\n6. 💾 CACHE INVESTIGATION")
            print("-" * 25)
            
            if search.is_cache_available():
                print("✅ Cache is available")
                # Try to clear cache again
                search.clear_cache('standalone_keyword:*')
                print("🧹 Cleared keyword search cache")
            else:
                print("❌ Cache not available")
            
            # 7. Final diagnosis
            print("\n7. 📋 DIAGNOSIS")
            print("-" * 15)
            
            if total == total_all:
                print("❌ PROBLEM: Search returning ALL articles (no filtering)")
                print("   - AI filter not being applied")
                print("   - Date filter not being applied") 
                print("   - Check if correct search method is being called")
            elif total == ai_only:
                print("❌ PROBLEM: AI filter working, but date filter not applied")
                print("   - 'latest' logic not being triggered")
                print("   - Check has_latest flag and force_latest_filter")
            elif total == recent_all:
                print("❌ PROBLEM: Date filter working, but AI filter bypassed")
                print("   - This was the original issue we tried to fix")
                print("   - AI filter being overridden by relaxed filtering")
            elif total == recent_ai:
                print("✅ WORKING: Both filters applied correctly!")
                print("   - Issue might be with pagination or caching")
            else:
                print(f"⚠️  UNEXPECTED: Getting {total} results")
                print(f"   - Expected: {recent_ai} (recent + AI)")
                print(f"   - Check for other filtering logic")
            
            # 8. Recommendations
            print("\n8. 🔧 RECOMMENDATIONS")
            print("-" * 20)
            
            if total != recent_ai:
                print("To fix this issue:")
                print("1. Restart the application completely")
                print("2. Clear all caches")
                print("3. Check if the fix was applied to the correct file")
                print("4. Verify no other search paths are being used")
                
    except Exception as e:
        print(f"❌ Error in comprehensive debug: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_latest_search_comprehensive() 