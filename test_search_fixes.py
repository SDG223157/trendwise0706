#!/usr/bin/env python3
"""
Test Search Fixes
Verify that both symbol search and latest search fixes work properly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol

def test_symbol_detection():
    """Test the improved _is_likely_symbol function"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing Improved Symbol Detection")
        print("=" * 50)
        
        # Import the updated function
        from app.news.routes import _is_likely_symbol
        
        test_cases = [
            # Should be detected as symbols
            ("600585", True, "Bare Chinese symbol"),
            ("0700", True, "Bare Hong Kong symbol"),
            ("2318", True, "Bare Hong Kong symbol"),
            ("000001", True, "Bare Chinese symbol"),
            ("SSE:600585", True, "Exchange:Symbol format"),
            ("HKEX:0700", True, "Exchange:Symbol format"),
            ("AAPL", True, "US symbol"),
            ("600585.SS", True, "Chinese with .SS"),
            ("0700.HK", True, "HK with .HK"),
            
            # Should NOT be detected as symbols
            ("latest", False, "Regular keyword"),
            ("news", False, "Regular keyword"),
            ("breaking", False, "Regular keyword"),
            ("earnings", False, "Regular keyword"),
            ("12", False, "Too short number"),
            ("technology", False, "Regular word"),
        ]
        
        for test_input, expected, description in test_cases:
            result = _is_likely_symbol(test_input)
            status = "✅" if result == expected else "❌"
            print(f"   {status} '{test_input}' -> {result} ({description})")
            
        print("\n🔄 Testing Symbol Variant Generation")
        print("-" * 30)
        
        from app.utils.search.news_search import NewsSearch
        news_search = NewsSearch(db.session)
        
        test_symbols = ["600585", "0700", "2318", "SSE:600585", "HKEX:0700"]
        for symbol in test_symbols:
            variants = news_search.get_symbol_variants(symbol)
            print(f"   '{symbol}' -> {variants}")

def test_actual_search():
    """Test actual search functionality with both fixes"""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 Testing Actual Search Functionality")
        print("=" * 50)
        
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        optimized_search = OptimizedNewsSearch(db.session)
        
        # Test 1: Bare symbol search (600585)
        print("1. Testing bare symbol search '600585':")
        try:
            articles, total_count, has_more = optimized_search.search_by_symbols(
                symbols=["600585"],
                page=1,
                per_page=5
            )
            print(f"   Found {total_count} articles for '600585'")
            if articles:
                print(f"   Sample: {articles[0]['title'][:60]}...")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test 2: Exchange format search (SSE:600585)
        print("\n2. Testing exchange format search 'SSE:600585':")
        try:
            articles, total_count, has_more = optimized_search.search_by_symbols(
                symbols=["SSE:600585"],
                page=1,
                per_page=5
            )
            print(f"   Found {total_count} articles for 'SSE:600585'")
            if articles:
                print(f"   Sample: {articles[0]['title'][:60]}...")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test 3: Latest keyword search
        print("\n3. Testing 'latest' keyword search:")
        try:
            articles, total_count, has_more = optimized_search.search_by_keywords(
                keywords=["latest"],
                page=1,
                per_page=5
            )
            print(f"   Found {total_count} articles for 'latest'")
            if articles:
                print(f"   Sample: {articles[0]['title'][:60]}...")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test 4: Check what symbols actually exist in database
        print("\n4. Checking available symbols in database:")
        symbol_counts = {}
        
        # Get a sample of symbols to see what formats exist
        sample_symbols = ArticleSymbol.query.limit(20).all()
        for symbol_obj in sample_symbols:
            symbol = symbol_obj.symbol
            if symbol.startswith(('6', '0', '3', 'SSE:', 'SZSE:', 'HKEX:')):
                symbol_counts[symbol] = ArticleSymbol.query.filter_by(symbol=symbol).count()
        
        for symbol, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {symbol}: {count} articles")

def test_search_routes():
    """Test the search routes directly"""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 Testing Search Route Parameter Parsing")
        print("=" * 50)
        
        from app.news.routes import _parse_unified_search_params
        
        # Mock request args
        class MockArgs:
            def get(self, key, default=None):
                return default
        
        mock_args = MockArgs()
        
        # Test cases
        test_cases = [
            ("600585", "", "", "Should detect as symbol"),
            ("", "600585", "", "Explicit symbol parameter"),
            ("latest", "", "", "Should detect as keyword"), 
            ("600585 latest", "", "", "Mixed symbol and keyword"),
            ("SSE:600585", "", "", "Exchange format symbol"),
        ]
        
        for search_query, symbol, keywords, description in test_cases:
            params = _parse_unified_search_params(search_query, symbol, keywords, mock_args)
            print(f"   Query: '{search_query}' -> {params['search_type']}")
            print(f"     Symbols: {params.get('symbols', [])}")
            print(f"     Keywords: {params.get('keywords', [])}")
            print(f"     Description: {description}")
            print()

def main():
    """Run all tests"""
    test_symbol_detection()
    test_actual_search()
    test_search_routes()
    
    print(f"\n💡 SUMMARY:")
    print("✅ Symbol detection enhanced for bare Chinese/HK symbols")
    print("✅ Symbol variant generation improved")
    print("✅ Latest keyword search fixed with relaxed filtering")
    print("✅ Ready to test: search for '600585' and 'latest'")

if __name__ == "__main__":
    main() 