import re

# Comprehensive US Stock Exchange Mapping
# This mapping helps determine the correct exchange for US stocks
NASDAQ_STOCKS = {
    # Major Tech Stocks
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'AVGO', 
    'ADBE', 'CSCO', 'INTC', 'QCOM', 'AMD', 'INTU', 'AMAT', 'MU', 'NFLX', 
    'PYPL', 'WDAY', 'KLAC', 'LRCX', 'EA', 'ATVI', 'ISRG', 'VRTX', 'REGN', 
    'GILD', 'CMCSA', 'PEP', 'TMUS', 'COST',
    
    # Trump Media & Other Notable Stocks
    'DJT',  # Trump Media & Technology Group Corp. - NASDAQ
    
    # Other NASDAQ Stocks
    'ABNB', 'DOCU', 'ZM', 'ROKU', 'SHOP', 'SQ', 'TWLO', 'OKTA', 'DDOG',
    'CRWD', 'SNOW', 'PLTR', 'RBLX', 'HOOD', 'COIN', 'RIVN', 'LCID',
    'MRNA', 'BNTX', 'ZS', 'TEAM', 'SPLK', 'PANW', 'FTNT', 'CHTR',
    'DISH', 'SIRI', 'LULU', 'SBUX', 'MAR', 'BKNG', 'PCAR', 'FISV',
    'PAYX', 'FAST', 'CTAS', 'VRSK', 'CDNS', 'SNPS', 'ANSS', 'CTSH',
    'MCHP', 'ADI', 'XLNX', 'LAM', 'KLAC', 'MXIM', 'SWKS', 'QRVO',
    'MPWR', 'ALGN', 'IDXX', 'ILMN', 'MRTX', 'SGEN', 'BMRN', 'TECH',
    'EXAS', 'ARKG', 'ARKK', 'ARKQ', 'ARKW', 'PRNT', 'IZRL', 'FINX'
}

NYSE_STOCKS = {
    # Major NYSE Stocks
    'BRK.A', 'BRK.B', 'V', 'MA', 'JPM', 'BAC', 'WFC', 'MS', 'GS', 'BLK',
    'AXP', 'UNH', 'JNJ', 'LLY', 'PFE', 'MRK', 'ABT', 'TMO', 'DHR', 'BMY',
    'ABBV', 'WMT', 'PG', 'KO', 'MCD', 'NKE', 'DIS', 'HD', 'XOM', 'CVX',
    'RTX', 'HON', 'UPS', 'CAT', 'GE', 'BA', 'LMT', 'MMM', 'T', 'VZ',
    'CRM', 'ORCL', 'IBM', 'UBER', 'DASH', 'PGR', 'MET', 'ALL', 'PLD',
    'AMT', 'CCI', 'LIN', 'APD', 'ECL', 'NOC', 'GD', 'TDG', 'TGT', 'LOW',
    'DG', 'SPOT', 'UNP', 'CSX', 'FDX', 'VEEV', 'ZTS', 'EL', 'CL', 'K',
    'ACN', 'ADP', 'INFO', 'NEE', 'DUK', 'SO', 'TSM', 'ASML', 'UL', 'RY',
    'RIO', 'BHP', 'TD', 'NVO', 'TTE', 'BTI', 'DEO', 'SAP', 'SAN', 'EADSY',
    'PHG', 'SONY', 'VALE', 'ING', 'HSBC', 'BBD', 'SNY', 'SLB', 'NGG',
    'BMO', 'BCS', 'PTR', 'CS', 'UBS', 'SHEL', 'AZN', 'BP', 'GSK'
}

def get_us_stock_exchange(symbol: str) -> str:
    """
    Determine the correct US exchange for a stock symbol.
    
    Args:
        symbol (str): The stock symbol (e.g., 'AAPL', 'DJT')
        
    Returns:
        str: 'NASDAQ' or 'NYSE' based on the symbol lookup
    """
    symbol = symbol.upper().strip()
    
    if symbol in NASDAQ_STOCKS:
        return 'NASDAQ'
    elif symbol in NYSE_STOCKS:
        return 'NYSE'
    else:
        # Default fallback logic for unknown symbols
        # Tech-related patterns tend to be NASDAQ
        if any(pattern in symbol.lower() for pattern in ['tech', 'soft', 'data', 'net', 'sys', 'micro', 'cyber']):
            return 'NASDAQ'
        # Traditional/industrial patterns tend to be NYSE
        elif any(pattern in symbol.lower() for pattern in ['corp', 'inc', 'co', 'group', 'holdings']):
            return 'NYSE'
        else:
            # Final fallback: NASDAQ for shorter symbols, NYSE for longer ones
            return 'NASDAQ' if len(symbol) <= 4 else 'NYSE'

def normalize_ticker(symbol: str, purpose: str = 'analyze') -> str:
    """Convert between TradingView and Yahoo Finance symbols
    Args:
        symbol: The symbol to convert
        purpose: Either 'analyze' (convert to Yahoo) or 'search' (convert to TradingView)
    """
    # Handle Yahoo Finance indices to TradingView format
    if symbol.startswith('^') and purpose == 'search':
        yahoo_to_tv = {
            '^GSPC': 'SP:SPX',    # S&P 500
            '^DJI': 'DJ:DJI',     # Dow Jones
            '^IXIC': 'NASDAQ:IXIC',    # NASDAQ 100
            '^HSI': 'TVC:HSI',     # Hang Seng
            '^N225': 'TSE:NI225',  # Nikkei 225
            '^FTSE': 'LSE:UKX',    # FTSE 100
            '^GDAXI': 'XETR:DAX'  # DAX 40
        }
        return yahoo_to_tv.get(symbol, symbol)

    # Handle TradingView indices to Yahoo Finance format
    if symbol.startswith('TVC:') and purpose == 'analyze':
        tv_to_yahoo = {
            'TVC:HSI': '^HSI',     # Hang Seng Index
            'TVC:SSEC': '^SSEC',   # Shanghai Composite
            'TVC:SZSC': '^SZSC',   # Shenzhen Component
            'TVC:NDX': '^NDX',     # Nasdaq 100
            'TVC:SPX': '^GSPC',    # S&P 500
            'TVC:DJI': '^DJI'      # Dow Jones Industrial Average
        }
        return tv_to_yahoo.get(symbol, symbol.replace('TVC:', '^'))

    # Handle stock symbols based on purpose
    if purpose == 'search':
        # Convert Yahoo to TradingView format
        if symbol == 'BRK-A':  # Only handle hyphen format for Yahoo
            return 'NYSE:BRK.A'
        if re.match(r'^\d{4}\.HK$', symbol):
            return f"HKEX:{int(symbol.replace('.HK', ''))}"
        elif re.search(r'\.SS$', symbol):
            return f"SSE:{symbol.replace('.SS', '')}"
        elif re.search(r'\.SZ$', symbol):
            return f"SZSE:{symbol.replace('.SZ', '')}"
        elif re.search(r'\.T$', symbol):
            return f"TSE:{symbol.replace('.T', '')}"
        elif re.search(r'\.L$', symbol):
            return f"LSE:{symbol.replace('.L', '')}"
        # Handle US stocks - use proper exchange lookup
        elif re.match(r'^[A-Z]+$', symbol) and '.' not in symbol and ':' not in symbol:
            exchange = get_us_stock_exchange(symbol)
            return f"{exchange}:{symbol}"
    else:  # purpose == 'analyze'
        # Convert TradingView to Yahoo format
        if ':' in symbol:
            exchange, ticker = symbol.split(':')
            if exchange == 'NYSE' and ticker == 'BRK.A':
                return 'BRK-A'  # Use hyphen notation for Yahoo Finance
            if exchange == 'HKEX':
                return f"{int(ticker):04d}.HK"
            elif exchange == 'SSE':
                return f"{ticker}.SS"
            elif exchange == 'SZSE':
                return f"{ticker}.SZ"
            elif exchange == 'TSE':
                return f"{ticker}.T"
            elif exchange == 'LSE':
                return f"{ticker}.L"
            return ticker

    return symbol 