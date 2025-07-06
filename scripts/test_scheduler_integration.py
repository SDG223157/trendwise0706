#!/usr/bin/env python3
"""
Test script for news fetching optimization with scheduler integration

This script demonstrates how the system now automatically skips symbols
that are in the automated 346-symbol scheduler list.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_scheduler_integration():
    """Test the scheduler integration functionality"""
    print("🤖 Testing News Fetching Optimization with Scheduler Integration")
    print("=" * 70)
    
    try:
        from app.utils.analysis.stock_news_service import StockNewsService
        
        # Test symbols to demonstrate TradingView conversion
        test_symbols = [
            "AAPL",         # Plain symbol -> should convert to NASDAQ:AAPL and match
            "MSFT",         # Plain symbol -> should convert to NASDAQ:MSFT and match  
            "NASDAQ:AAPL",  # Already TradingView format -> should match directly
            "600519.SS",    # Yahoo Finance format -> should convert to SSE:600519 and match
            "0700.HK",      # Yahoo Finance format -> should convert to HKEX:700 and match
            "SOME_RANDOM_SYMBOL",  # Should NOT be in scheduler
            "TEST123"       # Should NOT be in scheduler
        ]
        
        print("🔍 Testing Scheduler Symbol Detection")
        print("-" * 40)
        
        for symbol in test_symbols:
            print(f"\n📊 Testing symbol: {symbol}")
            
            # First show TradingView conversion
            from app.utils.symbol_utils import normalize_ticker
            try:
                tv_symbol = normalize_ticker(symbol, purpose='search')
                print(f"  🔄 TradingView conversion: {symbol} → {tv_symbol}")
            except Exception as e:
                print(f"  ⚠️  TradingView conversion failed: {str(e)}")
                tv_symbol = symbol
            
            # Check if symbol is in scheduler
            scheduler_check = StockNewsService._check_if_symbol_in_scheduler(symbol)
            
            if scheduler_check['in_scheduler']:
                print(f"  ✅ In Scheduler: {scheduler_check['matching_variant']}")
                print(f"  🎯 Conversion method: {scheduler_check.get('conversion_used', 'unknown')}")
                print(f"  📋 Total scheduler symbols: {scheduler_check['total_scheduler_symbols']}")
                # Show first few variants for debugging
                variants = scheduler_check.get('symbol_variants', [])
                if len(variants) > 3:
                    print(f"  📝 First variants checked: {variants[:3]}...")
                else:
                    print(f"  📝 Variants checked: {variants}")
            else:
                print(f"  ❌ NOT in scheduler")
                if 'error' in scheduler_check:
                    print(f"  ⚠️  Error: {scheduler_check['error']}")
                else:
                    print(f"  📝 Conversion method: {scheduler_check.get('conversion_used', 'no_match')}")
        
        print("\n" + "=" * 70)
        print("🎯 Testing Auto-Check Logic")
        print("-" * 40)
        
        for symbol in test_symbols:
            print(f"\n🔄 Auto-check for: {symbol}")
            
            # Test the full auto-check logic
            result = StockNewsService.auto_check_and_fetch_news(
                symbol=symbol,
                force_check=False,
                use_smart_thresholds=True
            )
            
            print(f"  Status: {result['status']}")
            print(f"  Reason: {result['reason']}")
            print(f"  Message: {result['message']}")
            
            if 'optimization_details' in result:
                details = result['optimization_details']
                if 'automated_scheduler_protection' in details:
                    print(f"  🤖 Scheduler Protection: {details['automated_scheduler_protection']}")
                    print(f"  🔗 Scheduler Match: {details.get('scheduler_symbol_match', 'N/A')}")
        
        print("\n" + "=" * 70)
        print("🔨 Testing Force Override")
        print("-" * 40)
        
        # Test force override for a scheduler symbol
        scheduler_symbol = "AAPL"
        print(f"\n⚡ Force checking scheduler symbol: {scheduler_symbol}")
        
        result = StockNewsService.auto_check_and_fetch_news(
            symbol=scheduler_symbol,
            force_check=True,  # This should bypass scheduler check
            use_smart_thresholds=True
        )
        
        print(f"  Status: {result['status']}")
        print(f"  Reason: {result['reason']}")
        print(f"  Message: {result['message']}")
        
        if result['status'] != 'in_automated_scheduler':
            print("  ✅ Force override working - scheduler check bypassed")
        else:
            print("  ❌ Force override not working")
        
        print("\n" + "=" * 70)
        print("📊 System Summary")
        print("-" * 40)
        
        # Get scheduler status
        try:
            from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
            scheduler_symbols = news_fetch_scheduler.get_symbols()
            print(f"📋 Total symbols in automated scheduler: {len(scheduler_symbols)}")
            print(f"🎯 First 10 scheduler symbols: {scheduler_symbols[:10]}")
        except Exception as e:
            print(f"⚠️  Could not get scheduler info: {str(e)}")
        
        print("\n✅ Scheduler integration test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

def test_api_endpoints():
    """Test the API endpoints for scheduler integration"""
    print("\n🌐 Testing API Endpoints")
    print("=" * 70)
    
    try:
        import requests
        from urllib.parse import urljoin
        
        # Note: This assumes the app is running locally
        base_url = "http://localhost:5000"
        
        # Test symbols
        test_symbols = ["AAPL", "RANDOM_SYMBOL"]
        
        for symbol in test_symbols:
            print(f"\n🔍 Testing API for: {symbol}")
            
            # Test scheduler symbol check endpoint
            try:
                response = requests.post(
                    f"{base_url}/news/api/optimization/check-scheduler-symbol",
                    json={"symbol": symbol},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    scheduler_check = data['data']['scheduler_check']
                    print(f"  📊 Scheduler Check API: ✅")
                    print(f"  🎯 In Scheduler: {scheduler_check['in_scheduler']}")
                    if scheduler_check['in_scheduler']:
                        print(f"  🔗 Match: {scheduler_check['matching_variant']}")
                else:
                    print(f"  ❌ API Error: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                print(f"  ⚠️  App not running locally - skipping API test")
                break
            except Exception as e:
                print(f"  ❌ API Test Error: {str(e)}")
        
    except ImportError:
        print("⚠️  requests library not available - skipping API tests")

if __name__ == "__main__":
    print("🚀 Starting Scheduler Integration Tests")
    print("=" * 70)
    
    # Test the core functionality
    test_scheduler_integration()
    
    # Test API endpoints (optional)
    test_api_endpoints()
    
    print("\n🏁 All tests completed!")
    print("\nKey Benefits:")
    print("✅ Symbols in 346-scheduler list are automatically skipped")
    print("✅ Only symbols NOT in scheduler get daily limits applied")
    print("✅ Force override available when needed")
    print("✅ Complete integration with existing optimization system") 