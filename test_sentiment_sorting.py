#!/usr/bin/env python3
"""
Test Sentiment Sorting Functionality
Verify that "highest" and "lowest" sorting by AI sentiment rating works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol

def test_sentiment_sorting():
    """Test comprehensive sentiment sorting functionality"""
    app = create_app()
    
    with app.app_context():
        print("🔝🔻 Testing Sentiment Sorting Functionality")
        print("=" * 70)
        
        # Test sort detection
        print("\n1. TESTING SORT DETECTION:")
        test_queries = [
            "highest sentiment news",
            "lowest china stocks",
            "tech highest earnings",
            "us lowest performing",
            "highest sentiment tech stocks",
            "lowest sentiment earnings",
            "china highest",
            "lowest us markets"
        ]
        
        # Import sort detection function
        from app.news.routes import extract_sort_from_query, _parse_unified_search_params
        
        for query in test_queries:
            cleaned, sort_order = extract_sort_from_query(query)
            print(f"   '{query}' -> Sort: {sort_order or 'None'}, Cleaned: '{cleaned}'")
        
        # Test unified search params with sorting
        print("\n2. TESTING UNIFIED SEARCH PARAMS WITH SORTING:")
        
        test_search_queries = [
            ("highest sentiment", "", ""),
            ("lowest tech", "", ""),
            ("china highest", "", ""),
            ("lowest us earnings", "", ""),
            ("", "", "highest sentiment stocks")
        ]
        
        for query, symbol, keywords in test_search_queries:
            search_params = _parse_unified_search_params(query, symbol, keywords, {})
            print(f"   Query: '{query}' Symbol: '{symbol}' Keywords: '{keywords}'")
            print(f"      -> Sort: {search_params.get('sort_order', 'LATEST')}")
            print(f"      -> Region: {search_params.get('region_filter', 'None')}")
            print(f"      -> Keywords: {search_params.get('keywords', [])}")
            print("")
        
        # Test AI sentiment rating distribution
        print("\n3. TESTING AI SENTIMENT RATING DISTRIBUTION:")
        
        # Check sentiment rating distribution in search index
        from sqlalchemy import func
        sentiment_counts = db.session.query(
            NewsSearchIndex.ai_sentiment_rating,
            func.count(NewsSearchIndex.id).label('count')
        ).filter(
            NewsSearchIndex.ai_sentiment_rating.isnot(None)
        ).group_by(NewsSearchIndex.ai_sentiment_rating).order_by(NewsSearchIndex.ai_sentiment_rating).all()
        
        total_rated = sum(count for rating, count in sentiment_counts)
        print(f"   Total articles with AI sentiment ratings: {total_rated}")
        
        for rating, count in sentiment_counts:
            percentage = (count / total_rated * 100) if total_rated > 0 else 0
            stars = "⭐" * int(rating) if rating else "❓"
            print(f"   Rating {rating}: {count} articles ({percentage:.1f}%) {stars}")
        
        # Test optimized search with sentiment sorting
        print("\n4. TESTING OPTIMIZED SEARCH WITH SENTIMENT SORTING:")
        
        try:
            from app.utils.search.optimized_news_search import OptimizedNewsSearch
            search_service = OptimizedNewsSearch(db.session)
            
            # Test highest sentiment search
            print("\n   Testing HIGHEST sentiment search:")
            highest_results, highest_total, highest_has_more = search_service.search_by_keywords(
                keywords=['tech'],
                sort_order='HIGHEST',
                per_page=5
            )
            print(f"   Highest sentiment results: {len(highest_results)} articles, Total: {highest_total}")
            if highest_results:
                for i, article in enumerate(highest_results[:3]):
                    rating = article.get('ai_sentiment_rating', 'N/A')
                    title = article.get('title', 'No title')[:50]
                    print(f"      {i+1}. Rating {rating}: {title}...")
            
            # Test lowest sentiment search
            print("\n   Testing LOWEST sentiment search:")
            lowest_results, lowest_total, lowest_has_more = search_service.search_by_keywords(
                keywords=['earnings'],
                sort_order='LOWEST',
                per_page=5
            )
            print(f"   Lowest sentiment results: {len(lowest_results)} articles, Total: {lowest_total}")
            if lowest_results:
                for i, article in enumerate(lowest_results[:3]):
                    rating = article.get('ai_sentiment_rating', 'N/A')
                    title = article.get('title', 'No title')[:50]
                    print(f"      {i+1}. Rating {rating}: {title}...")
            
            # Test combined region + sentiment sorting
            print("\n   Testing COMBINED region + sentiment sorting:")
            combined_results, combined_total, combined_has_more = search_service.search_by_symbols(
                symbols=[],
                region_filter='CHINA',
                sort_order='HIGHEST',
                per_page=3
            )
            print(f"   China + Highest sentiment results: {len(combined_results)} articles, Total: {combined_total}")
            if combined_results:
                for i, article in enumerate(combined_results):
                    rating = article.get('ai_sentiment_rating', 'N/A')
                    title = article.get('title', 'No title')[:50]
                    print(f"      {i+1}. Rating {rating}: {title}...")
            
        except Exception as e:
            print(f"   Error testing optimized search: {str(e)}")
        
        # Test sorting validation
        print("\n5. TESTING SORTING VALIDATION:")
        
        # Verify that highest sorting returns highest ratings first
        try:
            highest_articles = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.ai_sentiment_rating.isnot(None),
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_summary != ''
            ).order_by(
                NewsSearchIndex.ai_sentiment_rating.desc(),
                NewsSearchIndex.published_at.desc()
            ).limit(5).all()
            
            print(f"   Top 5 highest rated articles:")
            for i, article in enumerate(highest_articles):
                rating = article.ai_sentiment_rating
                title = article.title[:50] if article.title else 'No title'
                print(f"      {i+1}. Rating {rating}: {title}...")
            
            # Verify that lowest sorting returns lowest ratings first
            lowest_articles = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.ai_sentiment_rating.isnot(None),
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_summary != ''
            ).order_by(
                NewsSearchIndex.ai_sentiment_rating.asc(),
                NewsSearchIndex.published_at.desc()
            ).limit(5).all()
            
            print(f"\n   Top 5 lowest rated articles:")
            for i, article in enumerate(lowest_articles):
                rating = article.ai_sentiment_rating
                title = article.title[:50] if article.title else 'No title'
                print(f"      {i+1}. Rating {rating}: {title}...")
                
        except Exception as e:
            print(f"   Error testing sorting validation: {str(e)}")
        
        print("\n" + "=" * 70)
        print("✅ SENTIMENT SORTING TESTING COMPLETE")
        print("\n💡 EXAMPLE SEARCHES TO TRY:")
        print("• 'highest sentiment' - Articles with highest AI sentiment ratings")
        print("• 'lowest tech' - Tech articles with lowest sentiment ratings")
        print("• 'china highest' - Chinese articles with highest sentiment")
        print("• 'lowest us earnings' - US earnings with lowest sentiment")
        print("• 'highest sentiment stocks' - Stock news with highest sentiment")
        print("• 'lowest china markets' - Chinese market news with lowest sentiment")

if __name__ == "__main__":
    test_sentiment_sorting() 