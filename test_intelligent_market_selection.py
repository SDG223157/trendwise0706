#!/usr/bin/env python3
"""
Test Intelligent Market Session Selection

This script demonstrates how the news fetch scheduler intelligently selects
the appropriate market session based on the current UTC time.
"""

import sys
import os
sys.path.insert(0, '.')

from datetime import datetime, time
from app.utils.scheduler.news_fetch_scheduler import NewsFetchScheduler

def test_time_based_selection():
    """Test the intelligent time-based market session selection"""
    print("🧠 Testing Intelligent Market Session Selection")
    print("=" * 50)
    print()
    
    # Create scheduler instance
    scheduler = NewsFetchScheduler()
    
    # Test current time
    current_session = scheduler._determine_current_market_session()
    current_time = datetime.now().strftime('%H:%M UTC')
    
    print(f"🕐 Current Time: {current_time}")
    print(f"🎯 Recommended Session: {current_session}")
    print()
    
    # Show what this means in terms of symbols
    if current_session == "CHINA_HK":
        symbols = scheduler._get_market_symbols("CHINA_HK")
        print(f"🇨🇳 China/Hong Kong Session Selected:")
        print(f"   • Total symbols: {len(symbols)}")
        print(f"   • Markets: CN, HK, GLOBAL")
        print(f"   • Articles per symbol: 2")
        print(f"   • Estimated articles: {len(symbols) * 2}")
    else:  # US session
        symbols = scheduler._get_market_symbols("US")
        print(f"🇺🇸 US Session Selected:")
        print(f"   • Total symbols: {len(symbols)}")
        print(f"   • Markets: US, GLOBAL")
        print(f"   • US stocks: 5 articles each")
        print(f"   • Global stocks: 2 articles each")
        print(f"   • Estimated articles: {(846 * 5) + (158 * 2)}")  # US + Global
    
    print()
    print("📅 Market Session Schedule:")
    print("   🇨🇳 China/Hong Kong Sessions:")
    print("     • 01:00 UTC - Market Open")
    print("     • 04:30 UTC - Mid-Session")
    print("     • 08:30 UTC - Market Close")
    print()
    print("   🇺🇸 US Sessions:")
    print("     • 14:00 UTC - Pre-Market")
    print("     • 17:30 UTC - Mid-Session")
    print("     • 21:30 UTC - After-Hours")
    print()
    
    print("🎯 Time-Based Selection Rules:")
    print("   • 00:30-02:00 UTC → China/HK session")
    print("   • 04:00-05:30 UTC → China/HK session")
    print("   • 08:00-09:30 UTC → China/HK session")
    print("   • 13:30-15:00 UTC → US session")
    print("   • 17:00-18:30 UTC → US session")
    print("   • 21:00-22:30 UTC → US session")
    print("   • Other times → Next upcoming session")
    print()
    
    print("✅ Benefits of Intelligent Selection:")
    print("   • Fetches relevant market data when most active")
    print("   • Reduces unnecessary API calls")
    print("   • Optimizes resource usage")
    print("   • Automatically adapts to global market hours")
    print()
    
    print("🚀 Usage:")
    print("   • Manual start: Automatically selects appropriate session")
    print("   • Scheduled runs: Follow predefined market times")
    print("   • API calls: Use 'auto' parameter for intelligent selection")
    
if __name__ == "__main__":
    test_time_based_selection() 