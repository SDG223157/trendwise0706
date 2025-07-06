#!/usr/bin/env python3
"""
News Optimization Test Script

This script demonstrates and tests the enhanced news fetching optimization system.
Run this to see how the intelligent thresholds and caching work.

Usage:
    python scripts/test_news_optimization.py [symbol]
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_news_optimization(symbol='AAPL'):
    """Test the news optimization system for a given symbol"""
    try:
        # Import after path setup
        from app.utils.analysis.stock_news_service import StockNewsService, NewsOptimizationConfig
        from app import create_app, db
        
        print(f"🔍 Testing News Optimization for {symbol}")
        print("=" * 50)
        
        # Create app context
        app = create_app()
        with app.app_context():
            
            # Test 1: Check current optimization status
            print("\n📊 1. Current System Status:")
            print(f"   News fetching enabled: {StockNewsService.is_news_fetching_enabled()}")
            
            # Test 2: Check smart thresholds for the symbol
            print(f"\n🎯 2. Smart Thresholds for {symbol}:")
            thresholds = NewsOptimizationConfig.get_threshold_for_stock(symbol)
            for key, value in thresholds.items():
                print(f"   {key}: {value}h")
            
            # Test 3: Check recent news status (with smart thresholds)
            print(f"\n📰 3. Recent News Status (Smart Thresholds):")
            status_smart = StockNewsService.check_recent_news_status(
                symbol, use_smart_thresholds=True
            )
            print(f"   Should fetch: {status_smart['should_fetch']}")
            print(f"   Reason: {status_smart.get('fetch_reason', 'N/A')}")
            print(f"   Recent articles: {status_smart['total_recent_articles']}")
            print(f"   Latest article age: {status_smart['latest_article_age_hours']}h")
            
            # Test 4: Check recent news status (without smart thresholds)
            print(f"\n📰 4. Recent News Status (Default Thresholds):")
            status_default = StockNewsService.check_recent_news_status(
                symbol, use_smart_thresholds=False
            )
            print(f"   Should fetch: {status_default['should_fetch']}")
            print(f"   Reason: {status_default.get('fetch_reason', 'N/A')}")
            
            # Test 5: Run auto check and fetch
            print(f"\n🤖 5. Auto Check and Fetch Test:")
            auto_result = StockNewsService.auto_check_and_fetch_news(symbol)
            print(f"   Status: {auto_result['status']}")
            print(f"   Message: {auto_result['message']}")
            print(f"   Reason: {auto_result.get('reason', 'N/A')}")
            
            # Test 6: Check daily fetch allowance (NEW)
            print(f"\n🛡️  6. Daily Fetch Allowance:")
            allowance = StockNewsService.check_daily_fetch_allowance(symbol)
            print(f"   Allow fetch: {allowance['allow_fetch']}")
            print(f"   Reason: {allowance['reason']}")
            print(f"   Details: {allowance['details']}")
            
            # Test 7: Get fetch record stats (NEW)
            print(f"\n📝 7. Daily Fetch Records:")
            fetch_stats = StockNewsService.get_fetch_record_stats(symbol)
            if 'error' not in fetch_stats:
                print(f"   Total attempts today: {fetch_stats.get('total_attempts', 0)}")
                if fetch_stats.get('results_summary'):
                    for result_type, count in fetch_stats['results_summary'].items():
                        print(f"   {result_type}: {count}")
                print(f"   First attempt: {fetch_stats.get('first_attempt', 'None')}")
                print(f"   Last attempt: {fetch_stats.get('last_attempt', 'None')}")
            else:
                print(f"   Error: {fetch_stats['error']}")
            
            # Test 8: Get optimization stats
            print(f"\n📈 8. Optimization Statistics:")
            stats = StockNewsService.get_news_optimization_stats([symbol])
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
            # Test 9: Configuration details
            print(f"\n⚙️  9. Configuration Details:")
            print(f"   Recent news threshold: {NewsOptimizationConfig.RECENT_NEWS_THRESHOLD}h")
            print(f"   Stale news threshold: {NewsOptimizationConfig.STALE_NEWS_THRESHOLD}h")
            print(f"   Minimal news threshold: {NewsOptimizationConfig.MINIMAL_NEWS_THRESHOLD}h")
            print(f"   Cache duration: {NewsOptimizationConfig.NEWS_CHECK_CACHE_DURATION}s")
            
            is_high_freq = symbol.upper() in NewsOptimizationConfig.HIGH_FREQUENCY_STOCKS
            print(f"   Is high-frequency stock: {is_high_freq}")
            
            print("\n✅ Test completed successfully!")
            
            # Return comprehensive results
            return {
                'symbol': symbol,
                'system_enabled': StockNewsService.is_news_fetching_enabled(),
                'smart_thresholds': thresholds,
                'status_smart': status_smart,
                'status_default': status_default,
                'auto_result': auto_result,
                'stats': stats,
                'is_high_frequency': is_high_freq,
                'allowance': allowance,
                'fetch_stats': fetch_stats,
                'test_time': datetime.now().isoformat()
            }
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_multiple_symbols():
    """Test optimization for multiple symbols"""
    symbols = ['AAPL', 'MSFT', 'SPY', 'BTC-USD']
    results = {}
    
    print("🔍 Testing Multiple Symbols")
    print("=" * 50)
    
    for symbol in symbols:
        print(f"\n--- Testing {symbol} ---")
        result = test_news_optimization(symbol)
        if result:
            results[symbol] = result
            
            # Quick summary
            should_fetch = result['status_smart']['should_fetch']
            reason = result['status_smart'].get('fetch_reason', 'N/A')
            print(f"✨ {symbol}: {'FETCH' if should_fetch else 'SKIP'} - {reason}")
    
    return results

def test_fetch_record_behavior():
    """Test daily fetch record tracking behavior"""
    print("\n📝 Fetch Record Behavior Test")
    print("=" * 40)
    
    try:
        from app.utils.analysis.stock_news_service import StockNewsService, FetchRecordTracker
        from app import create_app
        
        app = create_app()
        with app.app_context():
            symbol = 'TEST'
            tracker = FetchRecordTracker()
            
            print(f"🧪 Testing fetch record tracking for {symbol}")
            
            # Clear any existing records first
            tracker.clear_daily_record(symbol)
            
            # Test 1: Initial state
            print("\n1️⃣ Initial State:")
            allowance = tracker.should_allow_fetch(symbol)
            print(f"   Allow fetch: {allowance['allow_fetch']}")
            print(f"   Reason: {allowance['reason']}")
            
            # Test 2: Record first failed attempt
            print("\n2️⃣ Recording First Failed Attempt:")
            tracker.record_fetch_attempt(symbol, 'no_news', 0, 'No articles found')
            allowance = tracker.should_allow_fetch(symbol)
            print(f"   Allow fetch: {allowance['allow_fetch']}")
            print(f"   Attempts: {allowance.get('attempts_today', 0)}")
            
            # Test 3: Record second failed attempt
            print("\n3️⃣ Recording Second Failed Attempt:")
            tracker.record_fetch_attempt(symbol, 'no_news', 0, 'Still no articles')
            allowance = tracker.should_allow_fetch(symbol)
            print(f"   Allow fetch: {allowance['allow_fetch']}")
            print(f"   Reason: {allowance['reason']}")
            
            # Test 4: Try to exceed limit
            print("\n4️⃣ Attempting Third Fetch (Should Block):")
            tracker.record_fetch_attempt(symbol, 'no_news', 0, 'Third attempt')
            allowance = tracker.should_allow_fetch(symbol)
            print(f"   Allow fetch: {allowance['allow_fetch']}")
            print(f"   Reason: {allowance['reason']}")
            
            # Test 5: Force override
            print("\n5️⃣ Force Override Test:")
            force_allowance = tracker.should_allow_fetch(symbol, force=True)
            print(f"   Allow fetch (forced): {force_allowance['allow_fetch']}")
            print(f"   Reason: {force_allowance['reason']}")
            
            # Test 6: Get daily stats
            print("\n6️⃣ Daily Statistics:")
            stats = tracker.get_daily_stats(symbol)
            print(f"   Total attempts: {stats['total_attempts']}")
            print(f"   Results summary: {stats['results_summary']}")
            
            # Clean up
            tracker.clear_daily_record(symbol)
            print("\n🧹 Cleaned up test records")
            
    except Exception as e:
        print(f"❌ Error testing fetch records: {str(e)}")

def demonstrate_cache_behavior():
    """Demonstrate caching behavior"""
    print("\n🗄️  Cache Behavior Demonstration")
    print("=" * 40)
    
    try:
        from app.utils.analysis.stock_news_service import StockNewsService
        from app import create_app
        import time
        
        app = create_app()
        with app.app_context():
            symbol = 'AAPL'
            
            # First call (should hit database)
            print("📊 First call (cache miss):")
            start_time = time.time()
            result1 = StockNewsService.check_recent_news_status(symbol)
            time1 = time.time() - start_time
            print(f"   Time: {time1:.3f}s")
            print(f"   Reason: {result1.get('fetch_reason', 'N/A')}")
            
            # Second call (should hit cache)
            print("\n📋 Second call (cache hit):")
            start_time = time.time()
            result2 = StockNewsService.check_recent_news_status(symbol)
            time2 = time.time() - start_time
            print(f"   Time: {time2:.3f}s")
            print(f"   Reason: {result2.get('fetch_reason', 'N/A')}")
            
            print(f"\n⚡ Cache speedup: {time1/time2:.1f}x faster")
            
            # Clear cache
            print("\n🧹 Clearing cache...")
            StockNewsService.clear_news_check_cache(symbol)
            
            # Third call (cache miss again)
            print("\n📊 Third call (cache cleared):")
            start_time = time.time()
            result3 = StockNewsService.check_recent_news_status(symbol)
            time3 = time.time() - start_time
            print(f"   Time: {time3:.3f}s")
            
    except Exception as e:
        print(f"❌ Error demonstrating cache: {str(e)}")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'
    
    print("🚀 News Optimization Test Suite")
    print("=" * 60)
    
    # Test single symbol
    result = test_news_optimization(symbol)
    
    # Test multiple symbols
    if len(sys.argv) <= 1:  # Only if no specific symbol provided
        print("\n" + "=" * 60)
        test_multiple_symbols()
        
        # Test fetch record behavior
        print("\n" + "=" * 60)
        test_fetch_record_behavior()
        
        # Demonstrate cache behavior
        print("\n" + "=" * 60)
        demonstrate_cache_behavior()
    
    print("\n🎉 All tests completed!")
    print("\nℹ️  Check your application logs for detailed optimization messages.")
    print("🆕 The system now includes daily fetch record tracking to prevent duplicate attempts!") 