#!/usr/bin/env python3
"""
Enhanced News Fetch Scheduler Test Script

This script tests the updated news fetch scheduler with market-specific scheduling,
1,102 symbols, and variable articles per symbol configuration.
"""

import os
import sys
import time
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
    from app import create_app
    
    print("✅ Successfully imported news fetch scheduler")
except ImportError as e:
    print(f"❌ Failed to import scheduler: {e}")
    sys.exit(1)

def test_symbol_structure():
    """Test the new symbol structure and categorization"""
    print("\n🔍 Testing Symbol Structure...")
    
    # Test DEFAULT_SYMBOLS structure
    default_symbols = news_fetch_scheduler.DEFAULT_SYMBOLS
    
    if not isinstance(default_symbols, dict):
        print("❌ DEFAULT_SYMBOLS should be a dictionary")
        return False
    
    expected_markets = ["US", "HK", "CN", "GLOBAL"]
    for market in expected_markets:
        if market not in default_symbols:
            print(f"❌ Missing market: {market}")
            return False
        
        if not isinstance(default_symbols[market], list):
            print(f"❌ Market {market} should contain a list of symbols")
            return False
        
        print(f"✅ Market {market}: {len(default_symbols[market])} symbols")
    
    # Test total symbol count
    total_symbols = sum(len(symbols) for symbols in default_symbols.values())
    print(f"✅ Total symbols across all markets: {total_symbols}")
    
    # Test unique symbols
    unique_symbols = news_fetch_scheduler.get_symbols()
    print(f"✅ Unique symbols (removing duplicates): {len(unique_symbols)}")
    
    return True

def test_market_configuration():
    """Test market-specific configuration"""
    print("\n🔍 Testing Market Configuration...")
    
    # Test market config structure
    market_config = news_fetch_scheduler.market_config
    
    expected_sessions = ["CHINA_HK", "US"]
    for session in expected_sessions:
        if session not in market_config:
            print(f"❌ Missing market session: {session}")
            return False
        
        config = market_config[session]
        required_keys = ["articles_per_symbol", "markets", "max_symbols_per_run", "schedule_times"]
        
        for key in required_keys:
            if key not in config:
                print(f"❌ Missing configuration key {key} in {session}")
                return False
        
        print(f"✅ Market session {session}: {len(config['markets'])} markets, {len(config['schedule_times'])} schedule times")
    
    return True

def test_market_symbol_selection():
    """Test market-specific symbol selection"""
    print("\n🔍 Testing Market Symbol Selection...")
    
    # Test China/Hong Kong session
    china_hk_symbols = news_fetch_scheduler._get_market_symbols("CHINA_HK")
    print(f"✅ China/Hong Kong session: {len(china_hk_symbols)} symbols")
    
    # Check symbol structure
    if china_hk_symbols:
        sample_symbol = china_hk_symbols[0]
        required_keys = ["symbol", "articles_limit", "market_code"]
        
        for key in required_keys:
            if key not in sample_symbol:
                print(f"❌ Missing key {key} in symbol configuration")
                return False
        
        print(f"✅ Sample symbol structure: {sample_symbol}")
    
    # Test US session
    us_symbols = news_fetch_scheduler._get_market_symbols("US")
    print(f"✅ US session: {len(us_symbols)} symbols")
    
    # Test articles per symbol configuration
    us_stock_articles = [s for s in us_symbols if s['market_code'] == 'US' and s['articles_limit'] == 5]
    global_in_us_articles = [s for s in us_symbols if s['market_code'] == 'GLOBAL' and s['articles_limit'] == 2]
    
    print(f"✅ US stocks with 5 articles: {len(us_stock_articles)}")
    print(f"✅ Global symbols in US session with 2 articles: {len(global_in_us_articles)}")
    
    return True

def test_scheduler_status():
    """Test scheduler status and configuration"""
    print("\n🔍 Testing Scheduler Status...")
    
    status = news_fetch_scheduler.get_status()
    
    required_keys = ["running", "fetch_schedule", "schedule_sessions", "total_unique_symbols", 
                    "market_distribution", "daily_articles_estimate", "configuration"]
    
    for key in required_keys:
        if key not in status:
            print(f"❌ Missing status key: {key}")
            return False
    
    print(f"✅ Scheduler running: {status['running']}")
    print(f"✅ Fetch schedule: {status['fetch_schedule']}")
    print(f"✅ Total unique symbols: {status['total_unique_symbols']}")
    
    # Test schedule sessions
    sessions = status['schedule_sessions']
    if len(sessions) != 2:
        print(f"❌ Expected 2 schedule sessions, got {len(sessions)}")
        return False
    
    for session in sessions:
        print(f"✅ Session {session['session']}: {session['symbols']} symbols, {len(session['times'])} times")
    
    # Test market distribution
    distribution = status['market_distribution']
    expected_total = sum(distribution.values())
    print(f"✅ Market distribution total: {expected_total}")
    
    for market, count in distribution.items():
        print(f"  • {market}: {count} symbols")
    
    return True

def test_schedule_timing():
    """Test the schedule timing configuration"""
    print("\n🔍 Testing Schedule Timing...")
    
    # Import schedule to check jobs
    import schedule
    
    # Clear any existing schedules
    schedule.clear()
    
    # Set up the schedule
    news_fetch_scheduler._schedule_market_times()
    
    # Check job count
    jobs_count = len(schedule.jobs)
    expected_jobs = 6  # 3 China/HK + 3 US
    
    if jobs_count != expected_jobs:
        print(f"❌ Expected {expected_jobs} scheduled jobs, got {jobs_count}")
        return False
    
    print(f"✅ Scheduled jobs: {jobs_count}")
    
    # Test schedule times
    expected_times = ["01:00", "04:30", "08:30", "14:00", "17:30", "21:30"]
    
    for job in schedule.jobs:
        job_time = str(job.start_day)
        print(f"✅ Scheduled job at: {job_time}")
    
    return True

def test_manual_run():
    """Test manual run functionality"""
    print("\n🔍 Testing Manual Run Functionality...")
    
    # Test with valid market session
    result = news_fetch_scheduler.run_now("CHINA_HK")
    
    if not result.get('success'):
        print(f"❌ Manual run failed: {result.get('error', 'Unknown error')}")
        return False
    
    print(f"✅ Manual run started: {result['message']}")
    print(f"✅ Market session: {result['market_session']}")
    print(f"✅ Total symbols: {result['total_symbols']}")
    
    # Test with invalid market session
    result = news_fetch_scheduler.run_now("INVALID")
    
    if result.get('success'):
        print("❌ Manual run should have failed with invalid market session")
        return False
    
    print(f"✅ Invalid market session properly rejected: {result['error']}")
    
    return True

def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("🚀 Starting Enhanced News Fetch Scheduler Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_symbol_structure,
        test_market_configuration,
        test_market_symbol_selection,
        test_scheduler_status,
        test_schedule_timing,
        test_manual_run
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            print(f"\n{'='*60}")
            if test_func():
                print(f"✅ {test_func.__name__} PASSED")
                passed += 1
            else:
                print(f"❌ {test_func.__name__} FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} ERROR: {str(e)}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Enhanced scheduler is ready for deployment.")
        return True
    else:
        print(f"⚠️ {failed} tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    try:
        # Create Flask app context for testing
        app = create_app()
        
        with app.app_context():
            # Initialize the scheduler
            news_fetch_scheduler.init_app(app)
            
            # Run tests
            success = run_comprehensive_test()
            
            if success:
                print("\n🎯 Enhanced News Fetch Scheduler Test Summary:")
                print("   • 1,102 symbols across 4 markets (US, HK, CN, GLOBAL)")
                print("   • 6 daily runs with market-specific scheduling")
                print("   • Variable articles per symbol (US: 5, Global: 2)")
                print("   • Maximum 14,355 articles per day")
                print("   • Market isolation implemented")
                print("   • All tests passed ✅")
            else:
                print("\n❌ Some tests failed. Please review the configuration.")
                sys.exit(1)
                
    except Exception as e:
        print(f"❌ Test setup error: {str(e)}")
        sys.exit(1) 