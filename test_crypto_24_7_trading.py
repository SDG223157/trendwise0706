#!/usr/bin/env python3
"""
Test Script for Crypto 24/7 Trading Functionality
Tests digital currency symbols to ensure they bypass trading day restrictions
Standalone version that doesn't require Flask app context
"""

import sys
import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Set

# Standalone crypto identification function (copied from trading_calendar.py)
def is_crypto_symbol(symbol: str) -> bool:
    """
    Determine if a symbol represents a cryptocurrency or digital currency.
    
    Args:
        symbol: The symbol to check
        
    Returns:
        True if it's a cryptocurrency symbol, False otherwise
    """
    if not symbol:
        return False
    
    symbol = symbol.upper().strip()
    
    # Direct crypto symbol patterns
    crypto_patterns = [
        r'^BINANCE:.*USDT$',        # Binance trading pairs (BINANCE:BTCUSDT)
        r'^BINANCE:.*USD$',         # Binance USD pairs
        r'^BINANCE:.*BTC$',         # Binance BTC pairs
        r'^BINANCE:.*ETH$',         # Binance ETH pairs
        r'^COINBASE:.*USD$',        # Coinbase pairs (COINBASE:BTCUSD)
        r'^KRAKEN:.*USD$',          # Kraken pairs (KRAKEN:BTCUSD)
        r'^BITSTAMP:.*USD$',        # Bitstamp pairs (BITSTAMP:BTCUSD)
        r'^.*-USD$',                # Generic crypto-USD pairs (BTC-USD, ETH-USD)
        r'^.*-USDT$',               # Tether pairs (BTC-USDT, ETH-USDT)
        r'^.*-BTC$',                # Bitcoin pairs (ETH-BTC, LTC-BTC)
        r'^.*-ETH$',                # Ethereum pairs (LINK-ETH, UNI-ETH)
    ]
    
    # Check against patterns
    for pattern in crypto_patterns:
        if re.match(pattern, symbol):
            return True
    
    # Known crypto symbols (base symbols without exchanges)
    crypto_symbols = {
        'BTC', 'BITCOIN', 'ETH', 'ETHEREUM', 'BNB', 'XRP', 'RIPPLE', 'ADA', 'CARDANO',
        'SOL', 'SOLANA', 'DOGE', 'DOGECOIN', 'DOT', 'POLKADOT', 'MATIC', 'POLYGON',
        'AVAX', 'AVALANCHE', 'SHIB', 'SHIBA', 'UNI', 'UNISWAP', 'LINK', 'CHAINLINK',
        'LTC', 'LITECOIN', 'BCH', 'BITCOIN CASH', 'ALGO', 'ALGORAND', 'XLM', 'STELLAR',
        'TRX', 'TRON', 'ATOM', 'COSMOS', 'VET', 'VECHAIN', 'FIL', 'FILECOIN',
        'ETC', 'ETHEREUM CLASSIC', 'THETA', 'ICP', 'INTERNET COMPUTER', 'NEAR',
        'FLOW', 'SAND', 'SANDBOX', 'MANA', 'DECENTRALAND', 'GALA', 'AXS', 'AXIE',
        'AAVE', 'COMP', 'COMPOUND', 'MKR', 'MAKER', 'SUSHI', 'SUSHISWAP', 'YFI',
        'YEARN', 'SNX', 'SYNTHETIX', 'CRV', 'CURVE', 'BAL', 'BALANCER', 'RUNE',
        'THORCHAIN', 'LUNA', 'TERRA', 'UST', 'USDC', 'USDT', 'TETHER', 'DAI',
        'BUSD', 'BINANCE USD', 'TUSD', 'PAXOS', 'GUSD', 'GEMINI USD'
    }
    
    # Check base symbol (remove exchange prefix if present)
    base_symbol = symbol.split(':')[-1] if ':' in symbol else symbol
    
    # Check if base symbol is a known crypto (before removing suffixes)
    if base_symbol in crypto_symbols:
        return True
    
    # Remove common suffixes for checking
    for suffix in ['USDT', 'USD', 'BTC', 'ETH', 'BUSD']:
        if base_symbol.endswith(suffix):
            base_symbol = base_symbol[:-len(suffix)]
            break
    
    # Check if base symbol (after removing suffixes) is a known crypto
    if base_symbol in crypto_symbols:
        return True
    
    # Check for common crypto exchange prefixes
    crypto_exchanges = ['BINANCE', 'COINBASE', 'KRAKEN', 'BITSTAMP', 'BITFINEX', 'HUOBI', 'KUCOIN', 'OKEX']
    if ':' in symbol:
        exchange = symbol.split(':')[0]
        if exchange in crypto_exchanges:
            return True
    
    return False

def has_crypto_symbols(symbols: List[str]) -> bool:
    """
    Check if any symbols in the list are crypto symbols.
    
    Args:
        symbols: List of symbols to check
        
    Returns:
        True if any symbol is a crypto symbol, False otherwise
    """
    return any(is_crypto_symbol(symbol) for symbol in symbols)

def test_crypto_symbol_identification():
    """Test crypto symbol identification function"""
    print("🧪 Testing Crypto Symbol Identification")
    print("=" * 50)
    
    # Test cases: (symbol, expected_result)
    test_cases = [
        # Binance symbols
        ('BINANCE:BTCUSDT', True),
        ('BINANCE:ETHUSDT', True),
        ('BINANCE:BNBUSDT', True),
        ('BINANCE:ADAUSDT', True),
        
        # Generic crypto-USD pairs
        ('BTC-USD', True),
        ('ETH-USD', True),
        ('DOGE-USD', True),
        ('SOL-USD', True),
        
        # Base crypto symbols
        ('BTC', True),
        ('ETH', True),
        ('BITCOIN', True),
        ('ETHEREUM', True),
        
        # Non-crypto symbols
        ('NASDAQ:AAPL', False),
        ('NYSE:MSFT', False),
        ('SSE:600519', False),
        ('HKEX:0700', False),
        ('COMEX:GC1!', False),  # Gold futures
        ('NYMEX:CL1!', False),  # Oil futures
        
        # Mixed cases
        ('COINBASE:BTCUSD', True),
        ('KRAKEN:ETHUSD', True),
        ('BITSTAMP:BTCUSD', True),
        ('USDT', True),  # Tether
        ('USDC', True),  # USD Coin
        
        # Edge cases
        ('', False),
        ('UNKNOWN', False),
        ('USD', False),  # Just USD is not crypto
    ]
    
    passed = 0
    failed = 0
    
    for symbol, expected in test_cases:
        result = is_crypto_symbol(symbol)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {symbol:<20} | Expected: {expected:<5} | Got: {result}")
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0

def test_crypto_symbol_list_detection():
    """Test crypto symbol detection in symbol lists"""
    print("\n🧪 Testing Crypto Symbol List Detection")
    print("=" * 50)
    
    test_cases = [
        # Pure crypto lists
        (['BTC-USD', 'ETH-USD', 'DOGE-USD'], True),
        (['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'], True),
        
        # Mixed crypto and traditional
        (['BTC-USD', 'NASDAQ:AAPL', 'NYSE:MSFT'], True),
        (['BINANCE:BTCUSDT', 'SSE:600519'], True),
        
        # Pure traditional
        (['NASDAQ:AAPL', 'NYSE:MSFT', 'SSE:600519'], False),
        (['COMEX:GC1!', 'NYMEX:CL1!'], False),
        
        # Edge cases
        ([], False),
        ([''], False),
        (['UNKNOWN'], False),
    ]
    
    passed = 0
    failed = 0
    
    for symbols, expected in test_cases:
        result = has_crypto_symbols(symbols)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {symbols} | Expected: {expected:<5} | Got: {result}")
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0

def test_scheduler_crypto_symbols():
    """Test that scheduler symbols include crypto symbols"""
    print("\n🧪 Testing Scheduler Crypto Symbols")
    print("=" * 50)
    
    # Simulated scheduler symbols (from the scheduler code)
    scheduler_crypto_symbols = [
        "BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:BNBUSDT", "BINANCE:ADAUSDT", "BINANCE:SOLUSDT", 
        "BINANCE:XRPUSDT", "BINANCE:DOTUSDT", "BINANCE:DOGENUSDT", "BINANCE:AVAXUSDT", "BINANCE:MATICUSDT", 
        "BINANCE:LINKUSDT", "BINANCE:LTCUSDT", "BINANCE:UNIUSDT", "BINANCE:ATOMUSDT", "BINANCE:XLMUSDT", 
        "BINANCE:VETUSDT", "BINANCE:FILUSDT", "BINANCE:TRXUSDT", "BINANCE:ETCUSDT", "BINANCE:THETAUSDT", 
        "BINANCE:ALGOUSDT", "BINANCE:ICPUSDT", "BINANCE:NEARUSDT", "BINANCE:FLOWUSDT", "BINANCE:SANDUSDT", 
        "BINANCE:MANAUSDT", "BINANCE:GALAUSDT", "BINANCE:AXSUSDT", "BINANCE:AAVEUSDT", "BINANCE:COMPUSDT", 
        "BINANCE:MKRUSDT", "BINANCE:SUSHIUSDT"
    ]
    
    crypto_count = 0
    non_crypto_count = 0
    
    for symbol in scheduler_crypto_symbols:
        if is_crypto_symbol(symbol):
            crypto_count += 1
        else:
            non_crypto_count += 1
            print(f"❌ {symbol} not detected as crypto")
    
    print(f"✅ {crypto_count} symbols correctly identified as crypto")
    print(f"❌ {non_crypto_count} symbols incorrectly identified as non-crypto")
    
    success = non_crypto_count == 0
    print(f"\n📊 Scheduler crypto detection: {'✅ PASS' if success else '❌ FAIL'}")
    return success

def main():
    """Run all tests"""
    print("🚀 Testing Crypto 24/7 Trading Functionality (Standalone)")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all tests
    test_results = []
    
    test_results.append(test_crypto_symbol_identification())
    test_results.append(test_crypto_symbol_list_detection())
    test_results.append(test_scheduler_crypto_symbols())
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED - Crypto symbol identification is working correctly!")
        print("\n📝 Next steps:")
        print("1. Deploy to Coolify to test full functionality")
        print("2. Test crypto news fetching on weekends/holidays")
        print("3. Verify scheduler bypasses trading day restrictions for crypto")
    else:
        print("❌ Some tests failed - Check the output above for details")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 