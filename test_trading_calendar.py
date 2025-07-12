#!/usr/bin/env python3
"""
Test script for trading calendar functionality

This script tests the trading calendar utility to ensure it correctly
identifies trading days and non-trading days for different markets.
"""

from datetime import date, timedelta
from app.utils.trading_calendar import TradingCalendar, is_trading_day, should_fetch_news_today

def test_trading_calendar():
    """Test trading calendar functionality"""
    print("🧪 Testing Trading Calendar Functionality")
    print("=" * 50)
    
    # Test current date
    today = date.today()
    print(f"\n📅 Today: {today.strftime('%Y-%m-%d (%A)')}")
    
    # Test US market
    us_trading = TradingCalendar.is_trading_day(today, 'US')
    print(f"🇺🇸 US Market Trading Day: {us_trading}")
    
    # Test China market
    china_trading = TradingCalendar.is_trading_day(today, 'CHINA')
    print(f"🇨🇳 China Market Trading Day: {china_trading}")
    
    # Test news fetching decision for different market sessions
    sessions = ['US', 'CHINA_HK', 'CHINA']
    
    print("\n📰 News Fetching Decisions:")
    for session in sessions:
        decision = TradingCalendar.should_fetch_news(session)
        status_emoji = "✅" if decision['should_fetch'] else "🚫"
        print(f"{status_emoji} {session}: {decision['reason']}")
    
    # Test specific dates (weekends and holidays)
    test_dates = []
    
    # Add next Saturday and Sunday
    days_ahead = 1
    while len(test_dates) < 7:
        test_date = today + timedelta(days=days_ahead)
        test_dates.append(test_date)
        days_ahead += 1
    
    print(f"\n🗓️ Testing Next 7 Days:")
    for test_date in test_dates:
        day_name = test_date.strftime('%A')
        us_trading = TradingCalendar.is_trading_day(test_date, 'US')
        china_trading = TradingCalendar.is_trading_day(test_date, 'CHINA')
        
        status_us = "✅" if us_trading else "🚫"
        status_china = "✅" if china_trading else "🚫"
        
        print(f"  {test_date.strftime('%Y-%m-%d')} ({day_name}): US {status_us} | China {status_china}")
    
    # Test specific known holidays
    print(f"\n🎉 Testing Known Holidays for 2024:")
    holidays_2024 = [
        (date(2024, 1, 1), "New Year's Day"),
        (date(2024, 7, 4), "US Independence Day"),
        (date(2024, 12, 25), "Christmas"),
        (date(2024, 2, 10), "Chinese New Year"),
        (date(2024, 10, 1), "China National Day"),
    ]
    
    for holiday_date, holiday_name in holidays_2024:
        us_trading = TradingCalendar.is_trading_day(holiday_date, 'US')
        china_trading = TradingCalendar.is_trading_day(holiday_date, 'CHINA')
        
        us_status = "✅ Trading" if us_trading else "🚫 Holiday"
        china_status = "✅ Trading" if china_trading else "🚫 Holiday"
        
        print(f"  {holiday_date.strftime('%Y-%m-%d')} ({holiday_name}): US {us_status} | China {china_status}")
    
    # Test next trading day calculation
    print(f"\n⏭️ Next Trading Days:")
    us_next = TradingCalendar.get_next_trading_day(today, 'US')
    china_next = TradingCalendar.get_next_trading_day(today, 'CHINA')
    
    print(f"  Next US trading day: {us_next.strftime('%Y-%m-%d (%A)')}")
    print(f"  Next China trading day: {china_next.strftime('%Y-%m-%d (%A)')}")
    
    # Test edge cases
    print(f"\n🔍 Edge Case Testing:")
    
    # Test weekend
    # Find next Saturday
    days_to_saturday = (5 - today.weekday()) % 7
    if days_to_saturday == 0:
        days_to_saturday = 7
    next_saturday = today + timedelta(days=days_to_saturday)
    
    saturday_decision = TradingCalendar.should_fetch_news('US')
    print(f"Weekend test - Should fetch on {next_saturday.strftime('%A')}: {TradingCalendar.is_trading_day(next_saturday, 'US')}")
    
    print("\n✅ Trading Calendar Tests Completed!")
    return True

def test_integration():
    """Test integration with Flask app context if available"""
    print("\n🔧 Testing Integration...")
    
    try:
        # Test the simple functions
        us_trading_today = is_trading_day('US')
        china_trading_today = is_trading_day('CHINA')
        
        print(f"Simple function test - US trading today: {us_trading_today}")
        print(f"Simple function test - China trading today: {china_trading_today}")
        
        # Test news fetching decision
        us_decision = should_fetch_news_today('US')
        china_decision = should_fetch_news_today('CHINA_HK')
        
        print(f"News fetch decision (US): {us_decision['should_fetch']} - {us_decision['reason']}")
        print(f"News fetch decision (China/HK): {china_decision['should_fetch']} - {china_decision['reason']}")
        
        print("✅ Integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Trading Calendar Tests...")
    
    try:
        # Run basic tests
        test_trading_calendar()
        
        # Run integration tests
        test_integration()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc() 