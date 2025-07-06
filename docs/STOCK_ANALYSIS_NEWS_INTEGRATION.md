# Stock Analysis News Integration

## Overview

This feature automatically integrates news fetching and AI processing into the stock analysis workflow. When users perform stock analysis, they can now easily access news information for the analyzed stock and trigger automatic news processing.

## Features Implemented

### 1. Automatic News Processing Service (`app/utils/analysis/stock_news_service.py`)

**Core Functionality:**
- Fetches latest 10 news articles for any stock symbol
- Processes articles with AI summaries and insights using OpenRouter API
- Runs asynchronously to avoid blocking analysis page rendering
- Integrates with existing news scheduler infrastructure
- **FIXED**: Proper Flask application context management for background threads

**Key Methods:**
- `fetch_and_process_stock_news()` - Main function to fetch and process news
- `get_processing_status()` - Returns news processing status for a symbol
- `get_recent_news()` - Gets recent news articles for a symbol
- `_fetch_and_process_background()` - **FIXED**: Background processing with proper app context

**Critical Fix Applied:**
The background news processing was failing with "Working outside of application context" errors. This has been fixed by:

```python
def _fetch_and_process_background(self, symbol: str):
    """Background processing method with proper Flask app context"""
    try:
        # CRITICAL FIX: Import Flask app and create application context for background thread
        from flask import current_app
        from app import create_app
        
        # Get the current app or create one if needed
        try:
            app = current_app._get_current_object()
        except RuntimeError:
            # No app context available, create one
            app = create_app()
        
        # Run with proper application context
        with app.app_context():
            logger.info(f"🔄 Background news processing started for {symbol} (with app context)")
            result = self._fetch_and_process_sync(symbol)
            logger.info(f"✅ Background news processing completed for {symbol}: {result}")
            
    except Exception as e:
        logger.error(f"❌ Background news processing failed for {symbol}: {str(e)}")
```

### 2. Stock Analysis Integration (`app/utils/analyzer/stock_analyzer.py`)

**Integration Points:**
- `create_stock_visualization()` - Triggers news processing after analysis
- `create_stock_visualization_old()` - Legacy function also triggers news processing

**Implementation:**
```python
# Trigger background news processing after analysis
try:
    logger.info(f"🔄 Triggering background news processing for {ticker}")
    stock_news_service.fetch_and_process_stock_news(ticker, background=True)
except Exception as news_error:
    logger.warning(f"⚠️ News processing failed for {ticker}: {str(news_error)}")
```

### 3. API Routes (`app/routes.py`)

**New API Endpoints:**
- `/api/stock/<symbol>/news-status` - Get news processing status
- `/api/stock/<symbol>/recent-news` - Get recent news articles

**Frontend Integration:**
- News status button added to analysis page navigation
- Real-time status checking with JavaScript
- Direct links to view news articles

### 4. User Interface Integration

**Analysis Page Enhancements:**
- **News Status Button**: Check processing status and article count
- **View News Link**: Direct access to news articles for the analyzed stock
- **Real-time Updates**: JavaScript polling for status updates

**JavaScript Functions:**
```javascript
// Check news processing status
async function checkNewsStatus(symbol) {
    const response = await fetch(`/api/stock/${symbol}/news-status`);
    const data = await response.json();
    // Display status and provide news link
}

// View recent news articles
function viewRecentNews(symbol) {
    window.open(`/news?symbol=${symbol}`, '_blank');
}
```

## How It Works

### Workflow Integration

1. **User performs stock analysis** (via `/quick_analyze` or `/analyze`)
2. **Analysis completes** and visualization is generated
3. **Background news processing triggers automatically**:
   - Fetches latest 10 news articles for the stock symbol
   - Processes articles with AI summaries and insights
   - Saves to database with proper Flask app context
4. **User can check status** via the news status button
5. **User can view articles** via the "View News" link

### Background Processing

The system uses background threads to avoid blocking the analysis page:

```python
# Non-blocking background processing
thread = threading.Thread(
    target=self._fetch_and_process_background,
    args=(symbol,),
    daemon=True
)
thread.start()
```

**Key Features:**
- **Non-blocking**: Analysis page renders immediately
- **Proper context**: Flask app context maintained in background threads
- **Error handling**: Graceful failure without affecting analysis
- **Status tracking**: Real-time status updates available

### Symbol Normalization

The system handles different stock symbol formats:

```python
def _normalize_symbol_for_news(self, symbol: str) -> str:
    """Normalize stock symbol for news API compatibility"""
    # Handle Chinese stocks: 600519.SS -> SSE:600519
    if symbol.endswith('.SS'):
        return f"SSE:{symbol[:-3]}"
    # Handle Hong Kong stocks: 1211.HK -> HKG:1211  
    elif symbol.endswith('.HK'):
        return f"HKG:{symbol[:-3]}"
    # Handle other exchanges...
    return symbol
```

## Error Handling

### Application Context Issues (FIXED)

**Problem**: Background threads were failing with "Working outside of application context"

**Solution**: Proper Flask app context management in background threads

**Before (Broken)**:
```python
def _fetch_and_process_background(self, symbol: str):
    # This would fail - no app context
    result = self._fetch_and_process_sync(symbol)
```

**After (Fixed)**:
```python
def _fetch_and_process_background(self, symbol: str):
    # Proper app context management
    with app.app_context():
        result = self._fetch_and_process_sync(symbol)
```

### Graceful Degradation

- If news processing fails, stock analysis still completes
- Error messages logged but don't affect user experience
- Status API returns error information for debugging

## Testing

A test script is provided to verify the integration:

```bash
python test_news_integration.py
```

This tests both synchronous and background processing modes.

## Configuration

### Environment Variables Required

```bash
# For AI processing (inherited from existing scheduler)
OPENROUTER_API_KEY=your_api_key_here

# Database connection (inherited from main app)
MYSQL_HOST=localhost
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
```

### Customization Options

```python
# In StockNewsService.__init__()
self.max_articles = 10  # Maximum articles to fetch per stock
```

## Benefits

### For Users
1. **Seamless Integration**: News automatically available after analysis
2. **No Manual Steps**: No need to separately search for news
3. **Real-time Status**: Know when news processing is complete
4. **Direct Access**: One-click access to relevant news articles

### For System
1. **Non-blocking**: Analysis performance unaffected
2. **Scalable**: Background processing handles multiple requests
3. **Robust**: Proper error handling and context management
4. **Integrated**: Uses existing news infrastructure

## Future Enhancements

### Potential Improvements
1. **Caching**: Cache recent news to avoid duplicate fetching
2. **Prioritization**: Process news for popular stocks first
3. **Notifications**: Real-time notifications when processing completes
4. **Filtering**: Allow users to filter news by sentiment or relevance

### Technical Improvements
1. **Queue System**: Use Redis/Celery for more robust background processing
2. **Batch Processing**: Process multiple stocks simultaneously
3. **Rate Limiting**: More sophisticated rate limiting for news APIs
4. **Monitoring**: Enhanced logging and monitoring for background processes

## Troubleshooting

### Common Issues

1. **"Working outside of application context"**
   - **Status**: FIXED in current version
   - **Cause**: Background threads without Flask app context
   - **Solution**: Proper app context management implemented

2. **No news articles found**
   - **Cause**: Symbol normalization or API issues
   - **Check**: Logs for symbol normalization and API responses

3. **AI processing fails**
   - **Cause**: Missing OPENROUTER_API_KEY or API quota exceeded
   - **Check**: Environment variables and API quota

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('app.utils.analysis.stock_news_service').setLevel(logging.DEBUG)
```

---

*Last Updated: December 2024*
*Status: Production Ready with App Context Fix* 