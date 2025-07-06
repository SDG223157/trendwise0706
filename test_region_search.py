#!/usr/bin/env python3
"""
Test Region Search Functionality
Verify that China, Hong Kong, and US region searches work correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol

def test_region_search():
    """Test comprehensive region search functionality"""
    app = create_app()
    
    with app.app_context():
        print("🌍 Testing Region Search Functionality")
        print("=" * 70)
        
        # Test region detection
        print("\n1. TESTING REGION DETECTION:")
        test_queries = [
            "china latest news",
            "hong kong tech stocks",
            "us markets earnings",
            "chinese 600585 stock",
            "hk 0700 earnings",
            "american nasdaq stocks",
            "mainland chinese stocks",
            "hongkong markets"
        ]
        
        # Import region detection function
        from app.news.routes import detect_region_from_query, extract_region_from_query
        
        for query in test_queries:
            detected = detect_region_from_query(query)
            cleaned, region = extract_region_from_query(query)
            print(f"   '{query}' -> Region: {region or 'None'}, Cleaned: '{cleaned}'")
        
        # Test symbol distribution
        print("\n2. TESTING SYMBOL DISTRIBUTION:")
        
        # Count symbols by region patterns
        symbol_counts = {}
        
        # Check Chinese stocks
        china_patterns = [
            ('SSE:', 'Chinese (Shanghai)'),
            ('SZSE:', 'Chinese (Shenzhen)'),
            ('%.SS', 'Chinese (.SS)'),
            ('%.SZ', 'Chinese (.SZ)'),
        ]
        
        for pattern, name in china_patterns:
            if pattern.startswith('%'):
                # Like query for .SS, .SZ
                count = ArticleSymbol.query.filter(ArticleSymbol.symbol.like(pattern)).count()
            else:
                # Like query for SSE:, SZSE:
                count = ArticleSymbol.query.filter(ArticleSymbol.symbol.like(f'{pattern}%')).count()
            
            if count > 0:
                symbol_counts[name] = count
                print(f"   {name}: {count} articles")
        
        # Check Hong Kong stocks
        hk_patterns = [
            ('HKEX:', 'Hong Kong (HKEX)'),
            ('%.HK', 'Hong Kong (.HK)'),
        ]
        
        for pattern, name in hk_patterns:
            if pattern.startswith('%'):
                count = ArticleSymbol.query.filter(ArticleSymbol.symbol.like(pattern)).count()
            else:
                count = ArticleSymbol.query.filter(ArticleSymbol.symbol.like(f'{pattern}%')).count()
            
            if count > 0:
                symbol_counts[name] = count
                print(f"   {name}: {count} articles")
        
        # Check US stocks
        us_patterns = [
            ('NASDAQ:', 'US (NASDAQ)'),
            ('NYSE:', 'US (NYSE)'),
            ('AMEX:', 'US (AMEX)'),
        ]
        
        for pattern, name in us_patterns:
            count = ArticleSymbol.query.filter(ArticleSymbol.symbol.like(f'{pattern}%')).count()
            if count > 0:
                symbol_counts[name] = count
                print(f"   {name}: {count} articles")
        
        # Test optimized search with region filtering
        print("\n3. TESTING OPTIMIZED SEARCH WITH REGION FILTERING:")
        
        try:
            from app.utils.search.optimized_news_search import OptimizedNewsSearch
            search_service = OptimizedNewsSearch(db.session)
            
            # Test China region search
            print("\n   Testing CHINA region search:")
            china_results, china_total, china_has_more = search_service.search_by_symbols(
                symbols=[],
                region_filter='CHINA',
                per_page=5
            )
            print(f"   China results: {len(china_results)} articles, Total: {china_total}")
            if china_results:
                for i, article in enumerate(china_results[:2]):
                    print(f"      {i+1}. {article.get('title', 'No title')[:50]}...")
            
            # Test Hong Kong region search
            print("\n   Testing HK region search:")
            hk_results, hk_total, hk_has_more = search_service.search_by_symbols(
                symbols=[],
                region_filter='HK',
                per_page=5
            )
            print(f"   HK results: {len(hk_results)} articles, Total: {hk_total}")
            if hk_results:
                for i, article in enumerate(hk_results[:2]):
                    print(f"      {i+1}. {article.get('title', 'No title')[:50]}...")
            
            # Test US region search
            print("\n   Testing US region search:")
            us_results, us_total, us_has_more = search_service.search_by_symbols(
                symbols=[],
                region_filter='US',
                per_page=5
            )
            print(f"   US results: {len(us_results)} articles, Total: {us_total}")
            if us_results:
                for i, article in enumerate(us_results[:2]):
                    print(f"      {i+1}. {article.get('title', 'No title')[:50]}...")
            
        except Exception as e:
            print(f"   Error testing optimized search: {str(e)}")
        
        # Test full search with region keywords
        print("\n4. TESTING FULL SEARCH WITH REGION KEYWORDS:")
        
        try:
            from app.news.routes import _parse_unified_search_params
            
            # Test parsing of region queries
            test_search_queries = [
                ("china latest", "", ""),
                ("hong kong tech", "", ""),
                ("us earnings", "", ""),
                ("", "SSE:600585", ""),
                ("", "", "china mainland")
            ]
            
            for query, symbol, keywords in test_search_queries:
                search_params = _parse_unified_search_params(query, symbol, keywords, {})
                print(f"   Query: '{query}' Symbol: '{symbol}' Keywords: '{keywords}'")
                print(f"      -> Region: {search_params.get('region_filter')}")
                print(f"      -> Parsed symbols: {search_params.get('symbols', [])}")
                print(f"      -> Parsed keywords: {search_params.get('keywords', [])}")
                print("")
                
        except Exception as e:
            print(f"   Error testing search params: {str(e)}")
        
        print("\n" + "=" * 70)
        print("✅ REGION SEARCH TESTING COMPLETE")
        print("\n💡 EXAMPLE SEARCHES TO TRY:")
        print("• 'china latest' - Latest Chinese news")
        print("• 'hong kong tech' - Hong Kong tech news")
        print("• 'us earnings' - US earnings news")
        print("• 'chinese 600585' - Chinese stock 600585 news")
        print("• 'hk 0700' - Hong Kong stock 0700 news")
        print("• 'american nasdaq' - US NASDAQ news")

if __name__ == "__main__":
    test_region_search() 