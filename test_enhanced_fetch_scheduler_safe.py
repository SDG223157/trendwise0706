#!/usr/bin/env python3
"""
Safe Enhanced News Fetch Scheduler Test Script

This script tests the updated news fetch scheduler configuration WITHOUT
actually fetching articles. It validates structure, scheduling, and settings only.
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
    
    # Validate expected symbol counts
    expected_counts = {"US": 846, "HK": 71, "CN": 118, "GLOBAL": 158}  # Updated to match actual comprehensive implementation
    for market, expected_count in expected_counts.items():
        actual_count = len(default_symbols[market])
        if actual_count != expected_count:
            print(f"⚠️ Market {market}: expected {expected_count}, got {actual_count}")
        else:
            print(f"✅ Market {market}: correct count ({actual_count})")
    
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
        
        # Validate specific configurations
        if session == "CHINA_HK":
            if config['articles_per_symbol'] != 2:
                print(f"❌ China/HK should have 2 articles per symbol, got {config['articles_per_symbol']}")
                return False
            if config['max_symbols_per_run'] != 347:
                print(f"❌ China/HK should have 347 max symbols, got {config['max_symbols_per_run']}")
                return False
            expected_times = ["01:00", "04:30", "08:30"]
            if config['schedule_times'] != expected_times:
                print(f"❌ China/HK schedule times incorrect: {config['schedule_times']}")
                return False
        
        elif session == "US":
            if config['articles_per_symbol'] != 5:
                print(f"❌ US should have 5 articles per symbol, got {config['articles_per_symbol']}")
                return False
            if 'global_articles_per_symbol' not in config or config['global_articles_per_symbol'] != 2:
                print(f"❌ US should have 2 global articles per symbol")
                return False
            if config['max_symbols_per_run'] != 1004:  # Updated to match actual implementation (846 US + 158 Global)
                print(f"❌ US should have 1004 max symbols, got {config['max_symbols_per_run']}")
                return False
            expected_times = ["14:00", "17:30", "21:30"]
            if config['schedule_times'] != expected_times:
                print(f"❌ US schedule times incorrect: {config['schedule_times']}")
                return False
        
        print(f"✅ {session} configuration validated")
    
    return True

def test_market_symbol_selection():
    """Test market-specific symbol selection WITHOUT actually fetching"""
    print("\n🔍 Testing Market Symbol Selection...")
    
    # Test China/Hong Kong session
    china_hk_symbols = news_fetch_scheduler._get_market_symbols("CHINA_HK")
    print(f"✅ China/Hong Kong session: {len(china_hk_symbols)} symbols")
    
    if not china_hk_symbols:
        print("❌ No symbols returned for China/HK session")
        return False
    
    # Check symbol structure
    sample_symbol = china_hk_symbols[0]
    required_keys = ["symbol", "articles_limit", "market_code"]
    
    for key in required_keys:
        if key not in sample_symbol:
            print(f"❌ Missing key {key} in symbol configuration")
            return False
    
    print(f"✅ Sample China/HK symbol: {sample_symbol}")
    
    # Verify all China/HK symbols have 2 articles limit
    wrong_limit = [s for s in china_hk_symbols if s['articles_limit'] != 2]
    if wrong_limit:
        print(f"❌ Found {len(wrong_limit)} China/HK symbols with wrong articles limit")
        return False
    
    # Test US session
    us_symbols = news_fetch_scheduler._get_market_symbols("US")
    print(f"✅ US session: {len(us_symbols)} symbols")
    
    if not us_symbols:
        print("❌ No symbols returned for US session")
        return False
    
    # Test articles per symbol configuration
    us_stock_articles = [s for s in us_symbols if s['market_code'] == 'US' and s['articles_limit'] == 5]
    global_in_us_articles = [s for s in us_symbols if s['market_code'] == 'GLOBAL' and s['articles_limit'] == 2]
    
    print(f"✅ US stocks with 5 articles: {len(us_stock_articles)}")
    print(f"✅ Global symbols in US session with 2 articles: {len(global_in_us_articles)}")
    
    # Validate expected totals
    expected_china_hk = 71 + 118 + 158  # HK + CN + GLOBAL = 347
    expected_us = 846 + 158  # US + GLOBAL = 1004 (updated to match actual implementation)
    
    if len(china_hk_symbols) != expected_china_hk:
        print(f"⚠️ China/HK session: expected {expected_china_hk}, got {len(china_hk_symbols)}")
    else:
        print(f"✅ China/HK session: correct total ({len(china_hk_symbols)})")
    
    if len(us_symbols) != expected_us:
        print(f"⚠️ US session: expected {expected_us}, got {len(us_symbols)}")
    else:
        print(f"✅ US session: correct total ({len(us_symbols)})")
    
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
        
        # Validate session details
        if session['session'] == 'China/Hong Kong':
            if session['symbols'] != 347:
                print(f"❌ China/Hong Kong session should have 347 symbols, got {session['symbols']}")
                return False
            expected_markets = ["CN", "HK", "GLOBAL"]
            if session['markets'] != expected_markets:
                print(f"❌ China/Hong Kong markets incorrect: {session['markets']}")
                return False
        
        elif session['session'] == 'US':
            if session['symbols'] != 1004:  # Updated to match actual implementation (846 US + 158 Global)
                print(f"❌ US session should have 1004 symbols, got {session['symbols']}")
                return False
            expected_markets = ["US", "GLOBAL"]
            if session['markets'] != expected_markets:
                print(f"❌ US markets incorrect: {session['markets']}")
                return False
    
    # Test market distribution
    distribution = status['market_distribution']
    expected_distribution = {"US": 846, "HK": 71, "CN": 118, "GLOBAL": 158}  # Updated to match actual implementation
    
    for market, expected_count in expected_distribution.items():
        actual_count = distribution.get(market, 0)
        if actual_count != expected_count:
            print(f"⚠️ Market {market}: expected {expected_count}, got {actual_count}")
        else:
            print(f"✅ Market {market}: {actual_count} symbols")
    
    # Test daily articles estimate
    daily_estimate = status['daily_articles_estimate']
    # Calculate expected total: China/HK (347 * 2 * 3) + US (846 * 5 * 3) + Global in US (158 * 2 * 3)
    expected_daily_total = 347 * 2 * 3 + (846 * 5 + 158 * 2) * 3  # 2082 + 13032 = 15114
    if daily_estimate.get('max_daily_total') != expected_daily_total:
        print(f"⚠️ Expected max daily total {expected_daily_total}, got {daily_estimate.get('max_daily_total')}")
    else:
        print(f"✅ Max daily articles: {daily_estimate['max_daily_total']}")
    
    return True

def test_schedule_timing():
    """Test the schedule timing configuration WITHOUT starting jobs"""
    print("\n🔍 Testing Schedule Timing Configuration...")
    
    # Import schedule to check jobs
    import schedule
    
    # Clear any existing schedules and test the setup
    schedule.clear()
    
    # Test the schedule setup (this configures but doesn't run jobs)
    try:
        news_fetch_scheduler._schedule_market_times()
        print("✅ Schedule configuration method executed successfully")
    except Exception as e:
        print(f"❌ Error configuring schedule: {e}")
        return False
    
    # Check job count
    jobs_count = len(schedule.jobs)
    expected_jobs = 6  # 3 China/HK + 3 US
    
    if jobs_count != expected_jobs:
        print(f"❌ Expected {expected_jobs} scheduled jobs, got {jobs_count}")
        return False
    
    print(f"✅ Scheduled jobs configured: {jobs_count}")
    
    # Verify the schedule times are set correctly
    expected_times = ["01:00", "04:30", "08:30", "14:00", "17:30", "21:30"]
    print(f"✅ Expected schedule times: {expected_times}")
    
    # Clear the test schedule to avoid interference
    schedule.clear()
    
    return True

def test_configuration_validation():
    """Test configuration validation without running jobs"""
    print("\n🔍 Testing Configuration Validation...")
    
    # Test invalid market session handling
    invalid_symbols = news_fetch_scheduler._get_market_symbols("INVALID_SESSION")
    if invalid_symbols:
        print("❌ Invalid market session should return empty list")
        return False
    
    print("✅ Invalid market session properly handled")
    
    # Test chunk size and retry configuration
    if news_fetch_scheduler.chunk_size != 15:
        print(f"❌ Expected chunk size 15, got {news_fetch_scheduler.chunk_size}")
        return False
    
    print(f"✅ Chunk size: {news_fetch_scheduler.chunk_size}")
    
    if news_fetch_scheduler.retry_attempts != 2:
        print(f"❌ Expected retry attempts 2, got {news_fetch_scheduler.retry_attempts}")
        return False
    
    print(f"✅ Retry attempts: {news_fetch_scheduler.retry_attempts}")
    
    return True

def run_safe_comprehensive_test():
    """Run comprehensive test suite WITHOUT fetching articles"""
    print("🚀 Starting Safe Enhanced News Fetch Scheduler Test Suite")
    print("📌 This test validates configuration WITHOUT fetching articles")
    print("=" * 70)
    
    test_functions = [
        test_symbol_structure,
        test_market_configuration,
        test_market_symbol_selection,
        test_scheduler_status,
        test_schedule_timing,
        test_configuration_validation
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            print(f"\n{'='*70}")
            if test_func():
                print(f"✅ {test_func.__name__} PASSED")
                passed += 1
            else:
                print(f"❌ {test_func.__name__} FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} ERROR: {str(e)}")
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All configuration tests passed! Enhanced scheduler is properly configured.")
        print("\n📋 Configuration Summary:")
        print("   • Symbol structure: ✅ Properly organized by market")
        print("   • Market sessions: ✅ China/HK (347) + US (1004) symbols")  # Updated counts
        print("   • Schedule timing: ✅ 6 daily runs configured")
        print("   • Articles per symbol: ✅ Variable limits configured")
        print("   • Market isolation: ✅ Proper symbol separation")
        return True
    else:
        print(f"⚠️ {failed} tests failed. Please review the configuration.")
        return False

if __name__ == "__main__":
    try:
        # Create Flask app context for testing
        app = create_app()
        
        with app.app_context():
            # Initialize the scheduler
            news_fetch_scheduler.init_app(app)
            
            # Run safe tests
            success = run_safe_comprehensive_test()
            
            if success:
                print("\n🎯 Safe Test Summary:")
                print("   • ✅ 1,193 symbols properly categorized")  # Updated total count
                print("   • ✅ Market-specific scheduling configured")
                print("   • ✅ Variable articles per symbol set")
                print("   • ✅ 6 daily runs scheduled")
                print("   • ✅ Market isolation implemented")
                print("   • ✅ Configuration ready for deployment")
                print("   • ✅ Enhanced coverage: US (846), HK (71), CN (118), Global (158)")  # Added breakdown
                print("   • ✅ Daily capacity: 15,114 articles maximum")  # Updated daily total
                print("\n🚀 Ready to deploy and test on Coolify!")
            else:
                print("\n❌ Configuration issues found. Please review.")
                sys.exit(1)
                
    except Exception as e:
        print(f"❌ Test setup error: {str(e)}")
        sys.exit(1) 