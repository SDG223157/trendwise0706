#!/usr/bin/env python3
"""
Test script to verify "latest" keyword functionality for 3-day filtering
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, NewsSearchIndex, NewsArticle
from app.utils.search.optimized_news_search import OptimizedNewsSearch
from datetime import datetime, timedelta

def test_latest_functionality():
    """Test that 'latest' keyword filters to articles from last 3 days"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing 'latest' keyword functionality...")
        
        # Check current search index
        total_articles = NewsSearchIndex.query.count()
        print(f"📊 Total articles in search index: {total_articles}")
        
        # Check articles from last 3 days
        three_days_ago = datetime.now() - timedelta(days=3)
        recent_articles = NewsSearchIndex.query.filter(
            NewsSearchIndex.published_at >= three_days_ago
        ).count()
        print(f"📅 Articles from last 3 days: {recent_articles}")
        
        # Check articles older than 3 days
        older_articles = NewsSearchIndex.query.filter(
            NewsSearchIndex.published_at < three_days_ago
        ).count()
        print(f"📅 Articles older than 3 days: {older_articles}")
        
        # Initialize search
        search = OptimizedNewsSearch(db.session)
        
        # Test 1: Search with "latest" keyword
        print("\n🔍 Test 1: Search with 'latest' keyword")
        search._has_latest_keyword = True
        articles, total, has_more = search.search_by_keywords(
            keywords=['latest'],
            sort_order='LATEST',
            page=1,
            per_page=10
        )
        
        print(f"Results: {len(articles)} articles found")
        print(f"Total count: {total}")
        
        # Verify all articles are from last 3 days
        all_recent = True
        for article in articles:
            if article.published_at < three_days_ago:
                all_recent = False
                print(f"❌ Found article older than 3 days: {article.title} ({article.published_at})")
        
        if all_recent:
            print("✅ All articles are from last 3 days")
        else:
            print("❌ Some articles are older than 3 days")
        
        # Test 2: Search without "latest" keyword (should show all articles)
        print("\n🔍 Test 2: Search without 'latest' keyword")
        search._has_latest_keyword = False
        articles_all, total_all, has_more_all = search.search_by_keywords(
            keywords=['news'],
            sort_order='LATEST',
            page=1,
            per_page=10
        )
        
        print(f"Results: {len(articles_all)} articles found")
        print(f"Total count: {total_all}")
        
        # Test 3: Symbol search with "latest" (no specific symbols)
        print("\n🔍 Test 3: Symbol search with 'latest' keyword")
        search._has_latest_keyword = True
        articles_symbol, total_symbol, has_more_symbol = search.search_by_symbols(
            symbols=[],
            sort_order='LATEST',
            page=1,
            per_page=10
        )
        
        print(f"Results: {len(articles_symbol)} articles found")
        print(f"Total count: {total_symbol}")
        
        # Verify all articles are from last 3 days
        all_recent_symbol = True
        for article in articles_symbol:
            if article.published_at < three_days_ago:
                all_recent_symbol = False
                print(f"❌ Found article older than 3 days: {article.title} ({article.published_at})")
        
        if all_recent_symbol:
            print("✅ All symbol search articles are from last 3 days")
        else:
            print("❌ Some symbol search articles are older than 3 days")
        
        # Test 4: Show sample articles
        print("\n📰 Sample articles from 'latest' search:")
        for i, article in enumerate(articles[:5]):
            print(f"{i+1}. {article.title}")
            print(f"   Published: {article.published_at}")
            print(f"   Symbols: {[s.symbol for s in article.symbols] if article.symbols else 'None'}")
            print()

if __name__ == "__main__":
    test_latest_functionality() 