"""
Trading Calendar Utility

Provides functions to check if current day is a trading day for different markets.
Helps prevent unnecessary news fetching on weekends and holidays.
Supports 24/7 trading for digital currencies/cryptocurrencies.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Set
import re

logger = logging.getLogger(__name__)

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

class TradingCalendar:
    """Trading calendar utility for checking trading days across different markets"""
    
    # US Market Holidays (approximate - can be extended)
    US_HOLIDAYS_2024 = {
        date(2024, 1, 1),   # New Year's Day
        date(2024, 1, 15),  # Martin Luther King Jr. Day
        date(2024, 2, 19),  # Presidents' Day
        date(2024, 3, 29),  # Good Friday
        date(2024, 5, 27),  # Memorial Day
        date(2024, 6, 19),  # Juneteenth
        date(2024, 7, 4),   # Independence Day
        date(2024, 9, 2),   # Labor Day
        date(2024, 11, 28), # Thanksgiving
        date(2024, 12, 25), # Christmas
    }
    
    US_HOLIDAYS_2025 = {
        date(2025, 1, 1),   # New Year's Day
        date(2025, 1, 20),  # Martin Luther King Jr. Day
        date(2025, 2, 17),  # Presidents' Day
        date(2025, 4, 18),  # Good Friday
        date(2025, 5, 26),  # Memorial Day
        date(2025, 6, 19),  # Juneteenth
        date(2025, 7, 4),   # Independence Day
        date(2025, 9, 1),   # Labor Day
        date(2025, 11, 27), # Thanksgiving
        date(2025, 12, 25), # Christmas
    }
    
    # China Market Holidays (major ones - can be extended)
    CHINA_HOLIDAYS_2024 = {
        date(2024, 1, 1),   # New Year's Day
        date(2024, 2, 10),  # Chinese New Year (Spring Festival)
        date(2024, 2, 11),  # Chinese New Year
        date(2024, 2, 12),  # Chinese New Year
        date(2024, 4, 4),   # Qingming Festival
        date(2024, 4, 5),   # Qingming Festival
        date(2024, 5, 1),   # Labor Day
        date(2024, 6, 10),  # Dragon Boat Festival
        date(2024, 9, 15),  # Mid-Autumn Festival
        date(2024, 10, 1),  # National Day
        date(2024, 10, 2),  # National Day
        date(2024, 10, 3),  # National Day
    }
    
    CHINA_HOLIDAYS_2025 = {
        date(2025, 1, 1),   # New Year's Day
        date(2025, 1, 29),  # Chinese New Year (Spring Festival)
        date(2025, 1, 30),  # Chinese New Year
        date(2025, 1, 31),  # Chinese New Year
        date(2025, 4, 5),   # Qingming Festival
        date(2025, 5, 1),   # Labor Day
        date(2025, 5, 31),  # Dragon Boat Festival
        date(2025, 10, 1),  # National Day
        date(2025, 10, 2),  # National Day
        date(2025, 10, 3),  # National Day
        date(2025, 10, 6),  # Mid-Autumn Festival
    }
    
    @classmethod
    def _get_holidays_for_year(cls, market: str, year: int) -> Set[date]:
        """Get holidays for a specific market and year"""
        if market.upper() == 'US':
            if year == 2024:
                return cls.US_HOLIDAYS_2024
            elif year == 2025:
                return cls.US_HOLIDAYS_2025
        elif market.upper() in ['CHINA', 'CN', 'HK']:
            if year == 2024:
                return cls.CHINA_HOLIDAYS_2024
            elif year == 2025:
                return cls.CHINA_HOLIDAYS_2025
        
        # Return empty set for unknown markets or years
        return set()
    
    @classmethod
    def is_trading_day(cls, check_date: Optional[date] = None, market: str = 'US') -> bool:
        """
        Check if a given date is a trading day for the specified market.
        
        Args:
            check_date: Date to check (defaults to today)
            market: Market to check ('US', 'CHINA', 'CN', 'HK')
            
        Returns:
            True if it's a trading day, False otherwise
        """
        if check_date is None:
            check_date = date.today()
        
        # Check if it's a weekend
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if it's a holiday
        holidays = cls._get_holidays_for_year(market, check_date.year)
        if check_date in holidays:
            return False
        
        return True
    
    @classmethod
    def is_trading_day_for_markets(cls, check_date: Optional[date] = None, 
                                  markets: List[str] = None) -> Dict[str, bool]:
        """
        Check trading day status for multiple markets.
        
        Args:
            check_date: Date to check (defaults to today)
            markets: List of markets to check (defaults to ['US', 'CHINA'])
            
        Returns:
            Dictionary mapping market to trading day status
        """
        if check_date is None:
            check_date = date.today()
        
        if markets is None:
            markets = ['US', 'CHINA']
        
        results = {}
        for market in markets:
            results[market] = cls.is_trading_day(check_date, market)
        
        return results
    
    @classmethod
    def get_next_trading_day(cls, start_date: Optional[date] = None, 
                            market: str = 'US') -> date:
        """
        Get the next trading day after the given date.
        
        Args:
            start_date: Starting date (defaults to today)
            market: Market to check
            
        Returns:
            Next trading day
        """
        if start_date is None:
            start_date = date.today()
        
        check_date = start_date + timedelta(days=1)
        while not cls.is_trading_day(check_date, market):
            check_date += timedelta(days=1)
            # Safety check to avoid infinite loop
            if check_date > start_date + timedelta(days=30):
                logger.warning(f"Could not find next trading day within 30 days of {start_date}")
                break
        
        return check_date
    
    @classmethod
    def should_fetch_news(cls, market_session: str = 'US', symbols: List[str] = None) -> Dict[str, any]:
        """
        Determine if news should be fetched based on trading calendar.
        Supports 24/7 trading for cryptocurrency symbols.
        
        Args:
            market_session: Market session ('US', 'CHINA_HK', 'CHINA', 'HK')
            symbols: List of symbols to check (for crypto detection)
            
        Returns:
            Dictionary with decision and reasoning
        """
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')
        
        # 🪙 CRYPTO CHECK: Allow 24/7 trading for crypto symbols
        if symbols and has_crypto_symbols(symbols):
            crypto_count = sum(1 for symbol in symbols if is_crypto_symbol(symbol))
            return {
                'should_fetch': True,
                'date': today_str,
                'market_session': market_session,
                'relevant_markets': ['CRYPTO'],
                'trading_status': {'CRYPTO': True},
                'is_weekend': today.weekday() >= 5,
                'next_trading_day': None,
                'reason': f"Crypto symbols detected ({crypto_count}/{len(symbols)}) - 24/7 trading allowed",
                'crypto_symbols': [symbol for symbol in symbols if is_crypto_symbol(symbol)]
            }
        
        # Map session to relevant markets
        if market_session == 'CHINA_HK':
            relevant_markets = ['CHINA', 'HK']
        elif market_session in ['CHINA', 'CN']:
            relevant_markets = ['CHINA']
        elif market_session == 'HK':
            relevant_markets = ['HK']
        else:  # Default to US
            relevant_markets = ['US']
        
        # Check trading status for relevant markets
        trading_status = cls.is_trading_day_for_markets(today, relevant_markets)
        
        # If ANY relevant market is trading, allow fetching
        any_market_trading = any(trading_status.values())
        
        result = {
            'should_fetch': any_market_trading,
            'date': today_str,
            'market_session': market_session,
            'relevant_markets': relevant_markets,
            'trading_status': trading_status,
            'is_weekend': today.weekday() >= 5,
            'next_trading_day': None
        }
        
        if not any_market_trading:
            # Find next trading day for the primary market
            primary_market = relevant_markets[0]
            next_trading = cls.get_next_trading_day(today, primary_market)
            result['next_trading_day'] = next_trading.strftime('%Y-%m-%d')
            
            if today.weekday() >= 5:
                result['reason'] = f"Weekend - markets closed. Next trading day: {result['next_trading_day']}"
            else:
                result['reason'] = f"Holiday in {', '.join(relevant_markets)} - markets closed. Next trading day: {result['next_trading_day']}"
        else:
            trading_markets = [market for market, is_trading in trading_status.items() if is_trading]
            result['reason'] = f"Trading day for {', '.join(trading_markets)} - fetching allowed"
        
        return result


def is_trading_day(market: str = 'US') -> bool:
    """
    Simple function to check if today is a trading day.
    
    Args:
        market: Market to check ('US', 'CHINA', 'CN', 'HK')
        
    Returns:
        True if today is a trading day, False otherwise
    """
    return TradingCalendar.is_trading_day(market=market)


def should_fetch_news_today(market_session: str = 'US', symbols: List[str] = None) -> Dict[str, any]:
    """
    Simple function to check if news should be fetched today.
    Supports 24/7 trading for cryptocurrency symbols.
    
    Args:
        market_session: Market session to check
        symbols: List of symbols to check (for crypto detection)
        
    Returns:
        Dictionary with decision and reasoning
    """
    return TradingCalendar.should_fetch_news(market_session, symbols) 