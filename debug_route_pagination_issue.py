#!/usr/bin/env python3
"""
Debug Route Pagination Issue

Trace exactly what happens in the search route when searching for "latest"
to identify why pagination shows 11,498 instead of 1,800.
"""

import sys
import os
sys.path.insert(0, '.')

def debug_route_pagination_issue():
    """Debug the route pagination logic step by step"""
    
    try:
        from app import create_app, db
        from app.models import NewsSearchIndex
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        from app.news.routes import _parse_unified_search_params
        from datetime import datetime, timedelta
        
        app = create_app()
        
        with app.app_context():
            print("🔍 DEBUGGING ROUTE PAGINATION ISSUE")
            print("=" * 50)
            
            print("🔧 STEP 1: SIMULATE ROUTE LOGIC")
            print("-" * 30)
            
            # Simulate exactly what the route does
            search_query = 'latest'
            symbol = ''
            keywords = ''
            
            # Mock request args
            mock_args = {}
            
            # Step 1: Parse search parameters (like the route does)
            search_params = _parse_unified_search_params(search_query, symbol, keywords, mock_args)
            print(f"✅ Search params parsed:")
            for key, value in search_params.items():
                print(f"   {key}: {value}")
                
            # Step 2: Check search index count
            search_index_count = NewsSearchIndex.query.count()
            print(f"\n📊 Search index count: {search_index_count}")
            
            # Step 3: Initialize OptimizedNewsSearch (like the route does)
            optimized_search = OptimizedNewsSearch(db.session)
            print(f"✅ OptimizedNewsSearch initialized")
            
            # Step 4: Determine search method (like the route does)
            search_type = search_params.get('search_type')
            print(f"🔍 Search type determined: {search_type}")
            
            # Step 5: Call the appropriate search method based on route logic
            page = 1
            per_page = 1  # Same as route
            
            if search_type == 'keyword':
                print(f"\n🧪 CALLING: search_by_keywords (force_latest_filter={search_params.get('has_latest', False)})")
                articles, total_count, has_more = optimized_search.search_by_keywords(
                    keywords=search_params.get('keywords', []),
                    sentiment_filter=search_params.get('sentiment_filter'),
                    sort_order=search_params.get('sort_order', 'LATEST'),
                    date_filter=search_params.get('date_filter'),
                    page=page,
                    per_page=per_page,
                    force_latest_filter=search_params.get('has_latest', False)
                )
            else:
                print(f"\n🧪 CALLING: search_by_symbols")
                # Set flag for "latest" keyword detection
                if search_params.get('has_latest'):
                    optimized_search._has_latest_keyword = True
                    
                articles, total_count, has_more = optimized_search.search_by_symbols(
                    symbols=search_params.get('symbols', []),
                    sentiment_filter=search_params.get('sentiment_filter'),
                    sort_order=search_params.get('sort_order', 'LATEST'),
                    date_filter=search_params.get('date_filter'),
                    region_filter=search_params.get('region_filter'),
                    processing_filter=search_params.get('processing_filter', 'all'),
                    page=page,
                    per_page=per_page
                )
            
            print(f"📊 ROUTE SEARCH RESULTS:")
            print(f"   Articles returned: {len(articles)}")
            print(f"   Total count: {total_count}")
            print(f"   Has more: {has_more}")
            
            # Step 6: Create SimplePagination object (like the route does)
            class SimplePagination:
                def __init__(self, items, total, page, per_page, has_more):
                    self.items = items
                    self.total = total
                    self.page = page
                    self.per_page = per_page
                    self.has_more = has_more
                    self.pages = (total + per_page - 1) // per_page if total else 1
                    self.has_prev = page > 1
                    self.has_next = has_more
                    self.prev_num = page - 1 if self.has_prev else None
                    self.next_num = page + 1 if self.has_next else None
            
            pagination = SimplePagination(
                items=articles,
                total=total_count,  # This is what shows up in the frontend!
                page=page,
                per_page=per_page,
                has_more=has_more
            )
            
            print(f"\n📋 PAGINATION OBJECT:")
            print(f"   pagination.total: {pagination.total}")
            print(f"   pagination.page: {pagination.page}")
            print(f"   pagination.pages: {pagination.pages}")
            print(f"   pagination.has_more: {pagination.has_more}")
            
            # Step 7: Diagnosis
            print(f"\n🎯 DIAGNOSIS:")
            
            if pagination.total == 11498:
                print("❌ ISSUE CONFIRMED: Route is creating pagination with 11,498 total")
                print("   - This means total_count from search method is 11,498")
                print("   - The search method is NOT returning 1,800 as expected")
                print("   - Our backend fix might not be taking effect in the route")
            elif pagination.total == 1800:
                print("✅ ROUTE IS WORKING: Pagination shows 1,800 total")
                print("   - Issue must be frontend caching or browser cache")
                print("   - Try hard refresh or check browser developer tools")
            else:
                print(f"⚠️  UNEXPECTED: Pagination shows {pagination.total} total")
                print("   - Different from both expected values")
                
            # Step 8: Check if there's any exception handling affecting results
            print(f"\n🔧 ADDITIONAL CHECKS:")
            
            # Test direct search method call
            try:
                print("Testing direct search_by_keywords call:")
                direct_articles, direct_total, direct_has_more = optimized_search.search_by_keywords(
                    keywords=['latest'],
                    force_latest_filter=True,
                    page=1,
                    per_page=1
                )
                print(f"   Direct call result: {direct_total} articles")
                
                if direct_total != total_count:
                    print(f"❌ INCONSISTENCY: Direct call returns {direct_total}, route logic returns {total_count}")
                else:
                    print(f"✅ CONSISTENT: Both calls return {total_count}")
                    
            except Exception as e:
                print(f"❌ Error in direct call: {str(e)}")
                
    except Exception as e:
        print(f"❌ Error in route debugging: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_route_pagination_issue() 