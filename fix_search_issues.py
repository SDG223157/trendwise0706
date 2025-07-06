#!/usr/bin/env python3
"""
Fix Search Issues
1. Symbol search without exchange prefix (e.g., 600585 instead of sse:600585)
2. Latest search not working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex

def test_current_search_issues():
    """Test the current search issues to confirm they exist"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing Current Search Issues")
        print("=" * 50)
        
        # Test 1: Symbol search without exchange prefix
        print("1. Testing bare symbol search (600585)...")
        
        # Check if articles exist with this symbol in different formats
        from app.models import ArticleSymbol
        
        # Check for various formats of 600585
        symbol_formats = ["600585", "SSE:600585", "600585.SS"]
        for symbol_format in symbol_formats:
            count = ArticleSymbol.query.filter_by(symbol=symbol_format).count()
            print(f"   Articles with symbol '{symbol_format}': {count}")
        
        # Test 2: Latest search
        print("\n2. Testing 'latest' keyword search...")
        
        # Check if search index has articles for latest search
        latest_articles = NewsSearchIndex.query.filter(
            NewsSearchIndex.ai_summary.like('%latest%') |
            NewsSearchIndex.ai_insights.like('%latest%') |
            NewsSearchIndex.title.like('%latest%')
        ).count()
        print(f"   Articles in search index with 'latest': {latest_articles}")
        
        # Check total articles vs AI articles
        total_articles = NewsArticle.query.count()
        ai_articles = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_summary != ''
        ).count()
        search_index_articles = NewsSearchIndex.query.count()
        
        print(f"\n📊 Current Status:")
        print(f"   Total articles: {total_articles}")
        print(f"   AI-processed articles: {ai_articles}")
        print(f"   Search index articles: {search_index_articles}")
        
        # Test 3: Check if symbol variants are working
        print("\n3. Testing symbol variant generation...")
        
        from app.utils.search.news_search import NewsSearch
        news_search = NewsSearch(db.session)
        
        test_symbols = ["600585", "SSE:600585", "600585.SS"]
        for symbol in test_symbols:
            variants = news_search.get_symbol_variants(symbol)
            print(f"   Symbol '{symbol}' variants: {variants}")

def create_improved_symbol_detection():
    """Create improved _is_likely_symbol function"""
    
    improved_function = '''
def _is_likely_symbol(text):
    """Determine if a text string is likely a stock symbol - IMPROVED VERSION"""
    import re
    
    # Stock symbol patterns - ENHANCED to include bare Chinese symbols
    patterns = [
        r'^[A-Z]{1,5}$',  # Simple 1-5 letter symbols (AAPL, MSFT)
        r'^[A-Z]+:[A-Z0-9]+$',  # Exchange:Symbol format (NASDAQ:AAPL, SSE:600585)
        r'^\d{4,6}\.HK$',  # Hong Kong format (0700.HK)
        r'^\d{6}\.S[SZ]$',  # Chinese format (600585.SS, 000001.SZ)
        r'^[A-Z]{1,4}\d*$',  # Mixed letter-number (QQQ, SPY)
        r'^\d{6}$',  # NEW: Bare Chinese symbols (600585, 000001)
        r'^\d{4}$',  # NEW: Bare Hong Kong symbols (0700, 2318)
        r'^\d{3,4}$',  # NEW: Short numeric symbols (700, 2318)
    ]
    
    return any(re.match(pattern, text.upper()) for pattern in patterns)
    '''
    
    print("🔧 Improved Symbol Detection Function:")
    print(improved_function)
    
def create_symbol_variant_enhancement():
    """Create enhanced symbol variant generation"""
    
    enhanced_function = '''
def get_symbol_variants(self, symbol: str) -> List[str]:
    """Get all possible variants for a symbol - ENHANCED for bare symbols"""
    variants = [symbol]
    
    # CRITICAL: Handle bare Chinese symbols (the main issue!)
    if re.match(r'^\d{6}$', symbol):  # 6-digit number like 600585
        if symbol.startswith('6'):  # Shanghai stocks
            variants.extend([f"SSE:{symbol}", f"{symbol}.SS"])
            logger.debug(f"🇨🇳 Bare Shanghai symbol detected: {symbol}")
        elif symbol.startswith(('0', '3')):  # Shenzhen stocks
            variants.extend([f"SZSE:{symbol}", f"{symbol}.SZ"])
            logger.debug(f"🇨🇳 Bare Shenzhen symbol detected: {symbol}")
    
    # CRITICAL: Handle bare Hong Kong symbols
    elif re.match(r'^\d{3,5}$', symbol):  # 3-5 digit numbers like 700, 2318
        # Pad with zeros for HK format
        padded = symbol.zfill(4)
        variants.extend([f"HKEX:{symbol}", f"HKEX:{padded}", f"{padded}.HK"])
        logger.debug(f"🇭🇰 Bare Hong Kong symbol detected: {symbol}")
    
    # Rest of existing logic...
    # [Include all existing symbol variant logic here]
    
    return list(set(variants))
    '''
    
    print("\n🔧 Enhanced Symbol Variant Generation:")
    print(enhanced_function)

def create_latest_search_fix():
    """Create fix for latest search issue"""
    
    fix_explanation = '''
🔍 "Latest" Search Issue Fix:

The issue is that the search now uses AI-only filtering:
    query = query.filter(
        NewsSearchIndex.ai_summary.isnot(None),
        NewsSearchIndex.ai_insights.isnot(None),
        NewsSearchIndex.ai_summary != '',
        NewsSearchIndex.ai_insights != ''
    )

This means only articles with complete AI processing are searchable.

SOLUTIONS:
1. Make "latest" a special keyword that sorts by published_at instead of content search
2. Allow partial AI content for "latest" searches  
3. Add fallback to search by title/source for popular keywords like "latest"

RECOMMENDED FIX:
Add special handling for common keywords like "latest", "news", "breaking":

if keyword.lower() in ['latest', 'news', 'breaking', 'recent']:
    # Sort by published_at instead of content search
    query = query.order_by(NewsSearchIndex.published_at.desc())
    # Don't filter by AI content for these special keywords
else:
    # Normal AI content search
    query = query.filter(AI content filters...)
    '''
    
    print("🔍 Latest Search Fix:")
    print(fix_explanation)

def main():
    """Main function to test and provide fixes"""
    test_current_search_issues()
    print("\n" + "="*60)
    create_improved_symbol_detection()
    print("\n" + "="*60)
    create_symbol_variant_enhancement()
    print("\n" + "="*60)
    create_latest_search_fix()
    
    print(f"\n💡 NEXT STEPS:")
    print("1. Update _is_likely_symbol function in app/news/routes.py")
    print("2. Update get_symbol_variants function in search classes")
    print("3. Add special keyword handling for 'latest' searches")
    print("4. Test with: '600585', 'latest', '0700'")

if __name__ == "__main__":
    main() 