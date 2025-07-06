# Region-Based Results Limits for TradingView Scraper

## Overview
The TradingView scraper now dynamically adjusts the `resultsLimit` parameter based on the geographic region of the symbols being scraped. This optimization helps manage API usage while ensuring adequate coverage for different markets.

## Implementation Details

### Limit Configuration
- **China and Hong Kong symbols**: 2 articles per symbol
- **Other symbols (US, UK, Japan, Europe, etc.)**: 5 articles per symbol

### Symbol Detection Patterns

#### China Symbols
- **TradingView format**: `SSE:600519`, `SZSE:000858`
- **Yahoo Finance format**: `600519.SS`, `000858.SZ`
- **6-digit numbers**: `600519` (Shanghai), `000858` (Shenzhen), `300750` (Shenzhen)

#### Hong Kong Symbols
- **TradingView format**: `HKEX:700`
- **Yahoo Finance format**: `0700.HK`
- **3-5 digit numbers**: `700`, `2318`, `09988`

#### Other Symbols
- **US symbols**: `NASDAQ:AAPL`, `NYSE:TSLA`, `AAPL`
- **UK symbols**: `LSE:SHEL`
- **Japan symbols**: `TSE:7203`
- **European symbols**: `ASML`

### Algorithm Logic
1. **Mixed Symbol Lists**: If any symbol in the batch is from China or Hong Kong, use limit 2 for the entire batch
2. **Pure Other Symbols**: If no China/HK symbols are present, use limit 5
3. **Single Symbol**: Apply region-specific limit directly

## Modified Files

### 1. `app/utils/analysis/get_news.py`
- Added `_get_results_limit_for_symbols()` method
- Added `_is_china_hk_symbol()` method for region detection
- Modified `get_news()` to use dynamic limits

### 2. `app/utils/analysis/news_analyzer.py`
- Added `_get_results_limit_for_symbols()` method
- Added `_is_china_hk_symbol()` method for region detection
- Modified `_fetch_tradingview_news()` to use dynamic limits

## Technical Implementation

### Region Detection Code
```python
def _is_china_hk_symbol(self, symbol: str) -> bool:
    """Check if symbol is from China or Hong Kong markets"""
    import re
    
    symbol = symbol.upper().strip()
    
    # China symbols patterns
    china_patterns = [
        r'^SSE:',           # Shanghai Stock Exchange
        r'^SZSE:',          # Shenzhen Stock Exchange
        r'\.SS$',           # Yahoo Finance Shanghai format
        r'\.SZ$',           # Yahoo Finance Shenzhen format
        r'^6\d{5}$',        # 6-digit Shanghai stocks
        r'^[03]\d{5}$',     # 6-digit Shenzhen stocks
    ]
    
    # Hong Kong symbols patterns
    hk_patterns = [
        r'^HKEX:',          # TradingView Hong Kong format
        r'\d+\.HK$',        # Yahoo Finance Hong Kong format
        r'^\d{3,5}$',       # Bare Hong Kong stock numbers
    ]
    
    # Check patterns using re.search()
    for pattern in china_patterns + hk_patterns:
        if re.search(pattern, symbol):
            return True
    
    return False
```

### Dynamic Limit Selection
```python
def _get_results_limit_for_symbols(self, symbols: List[str]) -> int:
    """
    Determine resultsLimit based on symbol regions:
    - China and Hong Kong symbols: 2 articles
    - Others: 5 articles
    """
    # Check if any symbol is from China or Hong Kong
    for symbol in symbols:
        if self._is_china_hk_symbol(symbol):
            return 2
    
    # Default limit for other regions
    return 5
```

## Testing Results
All test cases pass with 100% success rate:

### China Symbols
- ✅ SSE:600519 → 2 articles
- ✅ SZSE:000858 → 2 articles
- ✅ 600519.SS → 2 articles
- ✅ 000858.SZ → 2 articles
- ✅ 600519 → 2 articles
- ✅ 000858 → 2 articles
- ✅ 300750 → 2 articles

### Hong Kong Symbols
- ✅ HKEX:700 → 2 articles
- ✅ 0700.HK → 2 articles
- ✅ 700 → 2 articles
- ✅ 2318 → 2 articles
- ✅ 09988 → 2 articles

### Other Symbols
- ✅ NASDAQ:AAPL → 5 articles
- ✅ NYSE:TSLA → 5 articles
- ✅ LSE:SHEL → 5 articles
- ✅ TSE:7203 → 5 articles
- ✅ ASML → 5 articles

### Mixed Symbol Lists
- ✅ [NASDAQ:AAPL, SSE:600519] → 2 articles (China detected)
- ✅ [NYSE:TSLA, HKEX:700] → 2 articles (Hong Kong detected)
- ✅ [NASDAQ:AAPL, LSE:SHEL] → 5 articles (no China/HK)

## Benefits
1. **Optimized API Usage**: Fewer requests for China/HK symbols
2. **Adequate Coverage**: More articles for other markets
3. **Flexible Detection**: Supports multiple symbol formats
4. **Batch Processing**: Consistent limits across mixed symbol batches
5. **Logging**: Comprehensive debug logging for troubleshooting

## Deployment
The changes are ready for deployment and will take effect immediately after the next Coolify deployment. No database migrations or additional configuration required.

## Compatibility
- Works with both `NewsFetcher` and `NewsAnalyzer` classes
- Maintains backward compatibility with existing code
- Supports all existing symbol formats
- No breaking changes to existing API

## Future Enhancements
- Could be extended to support more regions with different limits
- Could implement symbol-specific limits based on market characteristics
- Could add configuration file for easy limit adjustments 