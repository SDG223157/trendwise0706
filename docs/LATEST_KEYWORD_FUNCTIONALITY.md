# Latest Keyword Functionality

## Overview

The "latest" keyword in TrendWise search has been enhanced to provide a time-filtered view of articles from the last 3 days, sorted from newest to oldest. This feature helps users quickly find the most recent and relevant news articles.

## Features

### 1. Time-Based Filtering
- **Filter Range**: Articles published within the last 3 days
- **Automatic Detection**: The system automatically detects the "latest" keyword in search queries
- **Sort Order**: Articles are sorted from newest to oldest (latest first)

### 2. Search Integration
- **Keyword Search**: Works with `search_by_keywords()` method
- **Symbol Search**: Works with `search_by_symbols()` method when no specific symbols are provided
- **Mixed Search**: Supported in hybrid search scenarios

### 3. Visual Indicators
- **UI Badge**: Shows "🕐 Last 3 Days" indicator when "latest" filter is active
- **Color Coding**: Purple badge (`text-purple-600`) to distinguish from other filters

## Usage Examples

### Basic Latest Search
```
Search query: "latest"
Result: Shows all articles from the last 3 days, sorted newest first
```

### Latest with Keywords
```
Search query: "latest tech"
Result: Shows tech-related articles from the last 3 days
```

### Latest with Region
```
Search query: "latest china"
Result: Shows Chinese news articles from the last 3 days
```

### Combined Filters
```
Search query: "latest highest"
Result: Shows articles from last 3 days with highest sentiment ratings
```

## Technical Implementation

### Backend Processing

#### 1. Query Detection
- The `_parse_unified_search_params()` function detects "latest" in the search query
- Sets `search_params['has_latest'] = True` flag
- Removes "latest" from the keywords list for content matching

#### 2. Search Enhancement
- `OptimizedNewsSearch` class enhanced with `_has_latest_keyword` flag
- Date filtering applied using `published_at >= three_days_ago`
- Overrides sort order to 'LATEST' to ensure newest first

#### 3. Database Query
```python
# Date filter for last 3 days
three_days_ago = datetime.now() - timedelta(days=3)
query = query.filter(NewsSearchIndex.published_at >= three_days_ago)
```

### Frontend Display

#### 1. Search Results
- Articles are displayed with standard AI-enhanced formatting
- Time filter is clearly indicated with purple "🕐 Last 3 Days" badge
- Combines with other filters (region, sentiment) seamlessly

#### 2. Visual Indicators
```html
{% if search_params.get('has_latest') %}
    <span class="text-purple-600 font-medium">🕐 Last 3 Days</span>
{% endif %}
```

## File Changes

### Modified Files
1. **app/utils/search/optimized_news_search.py**
   - Enhanced `search_by_keywords()` with latest detection
   - Enhanced `search_by_symbols()` with latest detection
   - Added 3-day date filtering logic

2. **app/news/routes.py**
   - Added `has_latest` flag detection in `_parse_unified_search_params()`
   - Set `_has_latest_keyword` flag on OptimizedNewsSearch instances

3. **app/templates/news/search.html**
   - Added "🕐 Last 3 Days" visual indicator
   - Consistent display across all search result states

### Test Files
- **test_latest_functionality.py**: Comprehensive test script to verify functionality

## Search Flow

1. **User Input**: User types "latest" in search query
2. **Query Parsing**: System detects "latest" keyword and sets flag
3. **Date Filtering**: Query is filtered to last 3 days
4. **Sort Override**: Sort order is set to 'LATEST' (newest first)
5. **Results Display**: Articles shown with "🕐 Last 3 Days" indicator

## Benefits

### For Users
- **Quick Access**: Fast way to find recent news
- **Relevance**: Focus on timely, current events
- **Clarity**: Clear visual indication of time filtering

### For System
- **Performance**: Smaller result set improves query speed
- **Efficiency**: Reduces data processing for time-sensitive searches
- **Flexibility**: Works with all existing search features

## Testing

### Manual Testing
1. Search for "latest" - should show recent articles only
2. Search for "latest tech" - should show recent tech articles
3. Search for "latest china" - should show recent Chinese articles
4. Verify "🕐 Last 3 Days" badge appears

### Automated Testing
Run the test script:
```bash
python test_latest_functionality.py
```

The script verifies:
- Articles returned are all from last 3 days
- Total count is accurate
- Both keyword and symbol searches work
- Visual indicators function correctly

## Deployment

### Requirements
- Database contains articles with `published_at` timestamps
- Search index (`NewsSearchIndex`) is populated and current
- No additional dependencies required

### Deployment Steps
1. Deploy code changes to Coolify
2. Verify search index is populated
3. Test "latest" functionality
4. Monitor performance and user feedback

## Future Enhancements

### Potential Improvements
1. **Configurable Time Range**: Allow users to specify days (e.g., "latest 7 days")
2. **Time Range Presets**: Quick buttons for 1 day, 3 days, 1 week
3. **Timezone Support**: Account for user timezone preferences
4. **Real-time Updates**: Auto-refresh latest articles periodically

### Advanced Features
1. **Breaking News**: Special handling for urgent/breaking news
2. **Trending Topics**: Show most discussed topics in last 3 days
3. **Comparative Analysis**: Compare latest vs. historical sentiment
4. **Smart Notifications**: Alert users to important latest news

## Conclusion

The "latest" keyword functionality provides users with a powerful tool to quickly access the most recent and relevant news articles. The implementation is seamless, efficient, and integrates well with existing search features while maintaining system performance.

This feature significantly enhances the user experience by providing immediate access to timely information, which is crucial for financial news and market analysis applications. 