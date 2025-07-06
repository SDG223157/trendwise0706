# Investing News Scraper Integration

## Overview

The TrendWise application now features dual news source integration, fetching news simultaneously from both **TradingView** and **Investing.com** via Apify scrapers. This enhancement provides broader news coverage and more comprehensive market insights.

## Features

### Dual Source Fetching
- **TradingView News Scraper**: Existing scraper for TradingView news
- **Investing News Scraper**: New scraper for Investing.com news
- **Parallel Processing**: Both scrapers run simultaneously for faster news gathering

### Ticker Format Conversion (Yahoo Finance Compatible)
The system automatically converts ticker symbols to Yahoo Finance format without exchange suffixes:

| TradingView Format | Investing.com Format | Yahoo Finance Equivalent |
|-------------------|---------------------|-------------------------|
| `HKEX:700` | `700` | `700.HK` |
| `HKEX:0700` | `0700` | `0700.HK` |
| `NYSE:AAPL` | `AAPL` | `AAPL` |
| `SSE:600519` | `600519` | `600519.SS` |
| `SZSE:000001` | `000001` | `000001.SZ` |
| `NASDAQ:GOOGL` | `GOOGL` | `GOOGL` |

### Source Attribution
Each news article is tagged with its source:
- `news_source`: The website (tradingview.com or investing.com)
- `scraper_type`: The scraper type (tradingview or investing)

## Implementation Details

### Core Components

1. **InvestingNewsScraper** (`app/utils/analysis/investing_news_scraper.py`)
   - Handles Investing.com news fetching
   - Converts TradingView ticker format to Investing.com format
   - Manages API calls to Apify Investing News Scraper

2. **Enhanced NewsAnalyzer** (`app/utils/analysis/news_analyzer.py`)
   - Integrated both scrapers
   - Parallel fetching using ThreadPoolExecutor
   - Handles articles from both sources

3. **Test Script** (`scripts/test_dual_news_scraper.py`)
   - Tests ticker conversion functionality
   - Validates integration between both scrapers
   - Verifies news fetching from both sources

### API Configuration

- **API Token**: Set via `APIFY_API_TOKEN` environment variable
- **TradingView Actor**: `mscraper/tradingview-news-scraper`
- **Investing Actor**: `mscraper/investing-news-scraper`

### Parallel Processing Flow

```
User requests news for symbols
         ↓
Convert symbols to appropriate formats
         ↓
Launch parallel threads:
  ├── TradingView Scraper (TradingView format)
  └── Investing Scraper (Investing format)
         ↓
Combine results from both sources
         ↓
Return unified article list with source attribution
```

## Usage

### Automatic Integration
The integration is automatically enabled in all existing news fetching operations:

1. **Manual News Fetch** (`/news/fetch`)
2. **API Endpoints** (`/news/api/fetch`)
3. **Automated Schedulers**
4. **Stock Analysis Integration**

### User Interface Updates
- Loading messages now show "Fetching news from TradingView & Investing.com..."
- Results display both sources transparently

## Testing

Run the integration test:

```bash
cd /path/to/trendwise
python scripts/test_dual_news_scraper.py
```

The test will:
1. Verify ticker format conversion
2. Test individual scrapers
3. Test integrated news fetching
4. Display source attribution

## Configuration

### Timeout Settings
- Individual scraper timeout: 60 seconds
- Retry attempts: 3 per scraper
- Parallel execution with graceful fallback

### Error Handling
- If Investing scraper fails, system continues with TradingView only
- If TradingView scraper fails, system continues with Investing only
- If both fail, appropriate error messages are logged

## Benefits

### Enhanced Coverage
- **Broader News Sources**: Coverage from both TradingView and Investing.com
- **Redundancy**: If one source is unavailable, the other continues working
- **Speed**: Parallel fetching reduces total time

### Market Insights
- **Cross-Platform Validation**: Same news from multiple sources provides validation
- **Diverse Perspectives**: Different editorial approaches from each platform
- **Comprehensive Analysis**: More data points for sentiment analysis

## Ticker Symbol Handling

### Supported Exchanges
- **HKEX**: Hong Kong Stock Exchange
- **NYSE**: New York Stock Exchange
- **NASDAQ**: NASDAQ
- **SSE**: Shanghai Stock Exchange
- **SZSE**: Shenzhen Stock Exchange
- **TSE**: Tokyo Stock Exchange
- **LSE**: London Stock Exchange

### Special Handling (Yahoo Finance Compatible)
- **Hong Kong Stocks**: Preserves leading zeros to match Yahoo Finance symbol part (HKEX:0700 → 0700, same as 0700.HK)
- **Chinese Stocks**: Maintains numeric format matching Yahoo Finance symbol part (SSE:600519 → 600519, same as 600519.SS)  
- **US Stocks**: Direct symbol mapping matches Yahoo Finance format (NYSE:AAPL → AAPL)

## Future Enhancements

### Planned Features
1. **Source Priority Configuration**: Allow users to prefer certain sources
2. **Advanced Deduplication**: Identify and merge duplicate articles from both sources
3. **Source-Specific Analysis**: Tailor sentiment analysis based on source characteristics
4. **Performance Metrics**: Track success rates and response times per source

### Potential Integrations
- Additional news sources via Apify
- Real-time news streaming
- Source reliability scoring

## Troubleshooting

### Common Issues

1. **API Rate Limits**: If hitting rate limits, the system will retry with exponential backoff
2. **Network Timeouts**: 60-second timeout per source with fallback to single source
3. **Data Format Changes**: Article parsing handles multiple field name variations

### Monitoring

Check logs for:
- `TradingView: fetched X articles`
- `Investing.com: fetched X articles`
- `Total articles fetched: X (TradingView: Y, Investing: Z)`

### Debug Mode

Enable debug logging to see detailed ticker conversion and API call information:

```python
import logging
logging.getLogger('app.utils.analysis').setLevel(logging.DEBUG)
```

## Conclusion

The dual news source integration significantly enhances TrendWise's news gathering capabilities, providing users with more comprehensive and reliable market news coverage. The system maintains backward compatibility while adding robust new functionality for better investment decision-making. 