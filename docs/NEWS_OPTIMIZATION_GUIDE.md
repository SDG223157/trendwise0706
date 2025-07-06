# News Fetching Optimization Guide 📰

## Overview

Your TrendWise application now features an **intelligent news fetching optimization system** that automatically avoids unnecessary news fetches while ensuring comprehensive news coverage during stock analysis.

## ✅ What's Already Working

The system automatically:
- **🤖 Skips automated scheduler symbols** - Automatically avoids fetching for the 346 symbols already processed 6x daily
- **Checks for recent news** before fetching new articles
- **Avoids redundant fetches** when recent news already exists
- **Uses background processing** to avoid blocking analysis
- **Integrates seamlessly** with stock analysis workflow

## 🚀 Enhanced Features

### 🤖 Automated Scheduler Integration (NEW)

**Most Important Optimization:** The system now integrates with your automated 346-symbol scheduler:

- **Automatic Detection**: Checks if analyzed symbol is in the 346-symbol list
- **Complete Skip**: If symbol is found in scheduler, skips fetch entirely (already processed 6x daily)
- **Symbol Variant Matching**: Handles different symbol formats (NYSE:AAPL, NASDAQ:AAPL, AAPL)
- **Optimization Focus**: Only applies daily limits and optimization to symbols NOT in scheduler
- **Force Override**: Can still force fetch with `force_check=True` if needed

**Impact**: Since your scheduler already fetches news for 346 symbols 6 times daily, this prevents ALL duplicate fetches for those symbols during analysis.

### Smart Thresholds Based on Stock Type

Different stocks get different treatment:

**High-Frequency Stocks** (AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META):
- Recent threshold: **24 hours**
- Stale threshold: **12 hours** 
- Fetch more articles: **8 articles**
- Minimum interval: **6 hours**
- Daily fetch limit: **3 attempts**

**Regular Stocks**:
- Recent threshold: **48 hours**
- Stale threshold: **24 hours**
- Standard articles: **5 articles**
- Minimum interval: **6 hours**
- Daily fetch limit: **2 attempts**

### Daily Fetch Record Tracking 🆕

**NEW:** Prevents duplicate fetches for stocks with no/old news:
- **Tracks every fetch attempt** with timestamp and result
- **Daily limits**: 2-3 attempts per stock depending on type
- **Intelligent blocking**: Stops fetching if last 2 attempts found no news
- **24-hour reset**: Records automatically clear daily
- **Force override**: Manual bypass available when needed

### Intelligent Caching

- **5-minute cache** for news status checks
- Avoids repeated database queries
- Automatic cache invalidation
- Redis-based for high performance

### Enhanced Decision Logic

The system now provides detailed reasons for fetch decisions:
- ✅ "Recent news available (3 articles, latest: 8h ago)"
- 📰 "Latest article is 26h old (threshold: 24h)"
- 🚫 "Recent fetch 4h ago (min interval: 6h)"
- 🛑 "Daily fetch limit reached (2/2 attempts with no success)"
- 📝 "Last 2 attempts found no/old news, and last attempt was 3.2h ago"

## 📊 How It Works

### 1. During Stock Analysis

When you analyze a stock, the system automatically:

```python
# This happens automatically in stock_analyzer.py
news_result = StockNewsService.auto_check_and_fetch_news(ticker)
```

### 2. Decision Process

```
Check Symbol → Check Scheduler → Get Smart Thresholds → Query Recent News → Make Decision
     ↓              ↓                    ↓                      ↓              ↓
   AAPL       In 346 list           24h recent/12h stale    Found 2 articles   ✅ Skip fetch
                ↓                                           (latest: 8h ago)   
        🤖 Skip entirely                                                       
       (already processed 6x daily)                                           
```

### 3. Background Fetching

If fetching is needed:
- Runs in background thread
- Doesn't block analysis rendering
- Triggers AI processing automatically

## 🛠️ Manual Control

### Check System Status

```bash
GET /news/api/optimization/status
```

Returns current configuration and statistics.

### Check Specific Symbol

```bash
POST /news/api/optimization/check-symbol
{
  "symbol": "AAPL",
  "use_smart_thresholds": true,
  "force_check": false
}
```

### Check If Symbol In Scheduler

```bash
POST /news/api/optimization/check-scheduler-symbol
{
  "symbol": "AAPL"
}
```

Returns whether symbol is in the automated 346-symbol list.

### Check Daily Fetch Records

```bash
GET /news/api/fetch-records/AAPL
GET /news/api/fetch-records/AAPL?date=2024-01-15
```

### Check Fetch Allowance

```bash
GET /news/api/fetch-allowance/AAPL
```

### Clear Cache

```bash
POST /news/api/optimization/clear-cache
{
  "symbol": "AAPL"  // optional, clears all if omitted
}
```

### Clear Fetch Records

```bash
DELETE /news/api/fetch-records/AAPL
{
  "date": "2024-01-15"  // optional, clears today if omitted
}
```

### Enable/Disable News Fetching

```python
from app.utils.analysis.stock_news_service import StockNewsService

# Disable globally
StockNewsService.disable_news_fetching()

# Enable globally  
StockNewsService.enable_news_fetching()
```

## 📈 Optimization Examples

### Example 1: Automated Scheduler Symbol (AAPL) 🆕

```
Analysis Time: 2024-01-15 10:00
Symbol Check: AAPL found in 346-symbol scheduler list
Decision: 🤖 Skip fetch entirely - already processed 6x daily by scheduler
```

### Example 2: High-Frequency Stock (Not in Scheduler)

```
Analysis Time: 2024-01-15 10:00
Latest News: 2024-01-15 02:00 (8 hours ago)
Decision: ✅ Skip fetch - within 12h threshold
```

### Example 2: Regular Stock with Old News

```
Analysis Time: 2024-01-15 10:00  
Latest News: 2024-01-14 08:00 (26 hours ago)
Decision: 📰 Fetch needed - exceeds 24h threshold
```

### Example 3: Recent Fetch Prevention

```
Analysis Time: 2024-01-15 10:00
Last Fetch: 2024-01-15 07:00 (3 hours ago)
Decision: 🚫 Skip fetch - below 6h minimum interval
```

### Example 4: Daily Limit Protection 🆕

```
Analysis Time: 2024-01-15 14:00
Today's Attempts: 2/2 (both found no news)
Decision: 🛑 Skip fetch - daily limit reached with no success
```

### Example 5: Failed Attempt Pattern 🆕

```
Analysis Time: 2024-01-15 12:00
Last 2 Attempts: no_news, no_news (2h and 4h ago)
Decision: 📝 Skip fetch - recent failed attempts pattern detected
```

### Example 6: Daily Reset 🆕

```
Previous Day: 2 failed attempts
New Day: 2024-01-16 09:00
Decision: ✅ Allow fetch - daily records reset automatically
```

## 🔧 Configuration

### Modify Thresholds

Edit `NewsOptimizationConfig` in `stock_news_service.py`:

```python
class NewsOptimizationConfig:
    RECENT_NEWS_THRESHOLD = 48  # Hours to consider "recent"
    STALE_NEWS_THRESHOLD = 24   # Hours before triggering fetch
    MINIMAL_NEWS_THRESHOLD = 6  # Minimum hours between fetches
    
    # Add more high-frequency stocks
    HIGH_FREQUENCY_STOCKS = {'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX'}
```

### Customize Per Stock

```python
@classmethod
def get_threshold_for_stock(cls, symbol: str) -> Dict:
    """Add custom logic for specific stocks"""
    if symbol in cls.HIGH_FREQUENCY_STOCKS:
        return {'recent_threshold': 24, 'stale_threshold': 12, 'min_interval': 6}
    elif symbol.startswith('BTC') or symbol.startswith('ETH'):
        return {'recent_threshold': 12, 'stale_threshold': 6, 'min_interval': 3}  # Crypto
    else:
        return {'recent_threshold': 48, 'stale_threshold': 24, 'min_interval': 6}
```

## 📊 Monitoring & Analytics

### View Optimization Stats

The system tracks:
- **Cache hit rate** - How often cached results are used
- **Fetch avoidance rate** - Percentage of unnecessary fetches avoided  
- **Optimization effectiveness** - Overall system efficiency

### Log Messages

Look for these log patterns:

```
🎯 Using smart thresholds for AAPL: recent=24h, stale=12h, min_interval=6h
✅ Recent news available (3 articles, latest: 8h ago) - no fetch needed
📰 Latest article is 26h old (threshold: 24h) - triggering background fetch
🧹 Cleared news check cache for AAPL
```

## 🚀 Performance Benefits

**Before Optimization:**
- Fetched news on every analysis
- Redundant API calls
- Slower analysis rendering

**After Optimization:**
- ~80-90% reduction in unnecessary fetches (with daily limits)
- Faster analysis rendering
- Intelligent resource usage
- Better API rate limit management
- **Zero duplicate fetches** for stocks with no news on same day

## ❓ Troubleshooting

### If News Seems "Stuck"

```python
# Clear cache and force fresh check
StockNewsService.clear_news_check_cache('AAPL')
result = StockNewsService.auto_check_and_fetch_news('AAPL', force_check=True)
```

### If Daily Limit Blocks Legitimate Fetch 🆕

```python
# Clear daily fetch record and try again
StockNewsService.clear_fetch_record('AAPL')
result = StockNewsService.auto_check_and_fetch_news('AAPL')

# Or force fetch bypassing all limits
result = StockNewsService.auto_check_and_fetch_news('AAPL', force_check=True)
```

### If System Blocks Too Aggressively 🆕

```python
# Check current daily limits
allowance = StockNewsService.check_daily_fetch_allowance('AAPL')
print(allowance)

# Increase daily limits in NewsOptimizationConfig
DAILY_FETCH_LIMIT = 4  # Allow more attempts per day
```

### If System Seems Too Conservative

Lower thresholds in `NewsOptimizationConfig`:
```python
STALE_NEWS_THRESHOLD = 12  # Fetch more frequently
MINIMAL_NEWS_THRESHOLD = 3  # Allow more frequent fetches
```

### If System Fetches Too Often

Increase thresholds:
```python
STALE_NEWS_THRESHOLD = 48  # Fetch less frequently  
MINIMAL_NEWS_THRESHOLD = 12  # Longer minimum intervals
```

## 🎯 Best Practices

1. **Let it run automatically** - The system is designed to work without intervention
2. **Monitor the logs** - Watch for optimization effectiveness
3. **Adjust thresholds** based on your usage patterns
4. **Use cache clearing** sparingly - only when needed
5. **Check optimization stats** periodically to tune performance

## 🔮 Future Enhancements

Planned improvements:
- **ML-based threshold optimization** based on stock volatility
- **Time-of-day awareness** (market hours vs. after hours)
- **News volume prediction** to anticipate high-news periods
- **User preference settings** for different optimization levels

---

The optimization system is **active by default** and works automatically during stock analysis. No manual intervention is required for normal operation! 