#!/usr/bin/env python3
"""
Debug Script: Latest Search Issue Analysis

This script will test the "latest" search functionality to understand why
it's showing all articles instead of filtering to the last 3 days.
"""

import sys
import os
sys.path.insert(0, '.')

def test_latest_search_issue():
    """Test the latest search functionality to identify the issue"""
    
    try:
        from app import create_app, db
        from app.models import NewsSearchIndex
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        from datetime import datetime, timedelta
        
        app = create_app()
        
        with app.app_context():
            print("🔍 DEBUGGING 'LATEST' SEARCH ISSUE")
            print("=" * 50)
            
            # 1. Check database state
            total_articles = NewsSearchIndex.query.count()
            print(f"📊 Total articles in search index: {total_articles}")
            
            # 2. Check article date distribution
            three_days_ago = datetime.now() - timedelta(days=3)
            one_week_ago = datetime.now() - timedelta(days=7)
            one_month_ago = datetime.now() - timedelta(days=30)
            
            recent_3_days = NewsSearchIndex.query.filter(
                NewsSearchIndex.published_at >= three_days_ago
            ).count()
            
            recent_week = NewsSearchIndex.query.filter(
                NewsSearchIndex.published_at >= one_week_ago
            ).count()
            
            recent_month = NewsSearchIndex.query.filter(
                NewsSearchIndex.published_at >= one_month_ago
            ).count()
            
            print(f"📅 Articles from last 3 days: {recent_3_days}")
            print(f"📅 Articles from last 7 days: {recent_week}")
            print(f"📅 Articles from last 30 days: {recent_month}")
            print(f"📅 Articles older than 30 days: {total_articles - recent_month}")
            
            # 3. Test AI filtering
            ai_complete = NewsSearchIndex.query.filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None),
                NewsSearchIndex.ai_summary != '',
                NewsSearchIndex.ai_insights != ''
            ).count()
            
            print(f"🤖 Articles with complete AI processing: {ai_complete}")
            
            # 4. Test recent articles with AI processing
            recent_with_ai = NewsSearchIndex.query.filter(
                NewsSearchIndex.published_at >= three_days_ago,
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None),
                NewsSearchIndex.ai_summary != '',
                NewsSearchIndex.ai_insights != ''
            ).count()
            
            print(f"🤖 Recent articles (3 days) with AI: {recent_with_ai}")
            
            # 5. Test the actual search functionality
            print("\n🧪 TESTING SEARCH FUNCTIONALITY")
            print("-" * 30)
            
            search = OptimizedNewsSearch(db.session)
            
            # Test 1: Normal keyword search
            print("Test 1: Normal keyword search (without 'latest')")
            articles1, total1, has_more1 = search.search_by_keywords(
                keywords=['news'],
                page=1,
                per_page=5
            )
            print(f"   Results: {len(articles1)} articles, total: {total1}")
            
            # Test 2: Search with "latest" keyword (should trigger 3-day filter)
            print("Test 2: Search with 'latest' keyword")
            articles2, total2, has_more2 = search.search_by_keywords(
                keywords=['latest'],
                page=1,
                per_page=5,
                force_latest_filter=True
            )
            print(f"   Results: {len(articles2)} articles, total: {total2}")
            
            # Test 3: Check if articles are actually from last 3 days
            if articles2:
                print("   Article dates from 'latest' search:")
                for i, article in enumerate(articles2[:3]):
                    pub_date = article.get('published_at', 'Unknown')
                    print(f"     {i+1}. {pub_date}")
            
            # 6. Test manual date filtering
            print("\nTest 3: Manual date filtering (should match 'latest' results)")
            manual_query = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.published_at >= three_days_ago,
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None),
                NewsSearchIndex.ai_summary != '',
                NewsSearchIndex.ai_insights != ''
            )
            manual_count = manual_query.count()
            manual_articles = manual_query.order_by(NewsSearchIndex.published_at.desc()).limit(5).all()
            
            print(f"   Manual filter count: {manual_count}")
            print(f"   Manual filter results: {len(manual_articles)} articles")
            
            # 7. Check if the issue is in the route parsing
            print("\n🔧 CHECKING ROUTE PARSING")
            print("-" * 25)
            
            from app.news.routes import _parse_unified_search_params
            
            # Simulate the search route parsing
            mock_args = {}
            search_params = _parse_unified_search_params('latest', '', '', mock_args)
            
            print(f"Parsed search params for 'latest':")
            for key, value in search_params.items():
                print(f"   {key}: {value}")
            
            # 8. Summary
            print("\n📋 DIAGNOSIS SUMMARY")
            print("-" * 20)
            
            if recent_3_days == 0:
                print("❌ ISSUE: No articles from last 3 days!")
                print("   - All articles are older than 3 days")
                print("   - 'latest' search correctly filters but finds nothing")
                print("   - Solution: Either update article dates or change filter period")
            elif recent_with_ai == 0:
                print("❌ ISSUE: No recent articles have AI processing!")
                print("   - Recent articles exist but lack AI summaries/insights")
                print("   - AI-only filter excludes all recent articles")
                print("   - Solution: Process recent articles with AI")
            elif total2 == total1:
                print("❌ ISSUE: 'latest' filter not being applied!")
                print("   - Same results for normal vs 'latest' search")
                print("   - Check force_latest_filter parameter passing")
            elif total2 == recent_with_ai:
                print("✅ 'latest' search is working correctly!")
                print(f"   - Shows {total2} recent articles with AI processing")
                print("   - May appear to show 'all' if most articles are recent")
            else:
                print("⚠️  Unexpected result pattern")
                print(f"   - Total articles: {total_articles}")
                print(f"   - Recent with AI: {recent_with_ai}")
                print(f"   - Latest search results: {total2}")
            
    except Exception as e:
        print(f"❌ Error running diagnostic: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_latest_search_issue() 