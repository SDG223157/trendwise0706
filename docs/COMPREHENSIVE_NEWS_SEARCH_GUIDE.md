# Comprehensive News Search Guide

## Overview

Your news search system now supports **three types of search** with intelligent auto-detection:

1. **Symbol Search** - Search by stock symbols (AAPL, MSFT, etc.)
2. **Keyword Search** - Search by content keywords (earnings, merger, etc.)
3. **Mixed Search** - Combine symbols and keywords in one query

## Search Methods

### 1. Web Interface Search

**URL**: `/news/search`

**Universal Search Box**:
```
Search Query Examples:
- "AAPL earnings report"      → Mixed search (symbol + keywords)
- "AAPL MSFT"                → Symbol search (multiple symbols)
- "artificial intelligence"   → Keyword search
- "CHINA AAPL"               → Symbol search with region filter
```

**Advanced Parameters**:
- `q` - Universal search query
- `symbol` - Specific symbol search
- `keywords` - Specific keyword search
- `sentiment` - Filter by sentiment (positive, negative, neutral)
- `processing` - Filter by AI processing status
- `page` - Page number for pagination

### 2. API Search Endpoint

**URL**: `/news/api/search`
**Methods**: `GET`, `POST`

#### GET Request Examples:

```bash
# Keyword search
curl "/news/api/search?q=artificial intelligence&search_type=keyword"

# Symbol search
curl "/news/api/search?symbols=AAPL&symbols=MSFT&search_type=symbol"

# Mixed search
curl "/news/api/search?q=AAPL earnings&search_type=mixed"

# Auto-detection (recommended)
curl "/news/api/search?q=AAPL merger news&search_type=auto"
```

#### POST Request Example:

```bash
curl -X POST "/news/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "AAPL artificial intelligence",
    "search_type": "auto",
    "sentiment": "positive",
    "page": 1,
    "per_page": 20
  }'
```

#### Response Format:

```json
{
  "status": "success",
  "data": {
    "articles": [
      {
        "id": 12345,
        "title": "Apple Announces AI Integration",
        "content": "First 1000 characters of content...",
        "url": "https://...",
        "published_at": "2024-01-15T10:30:00",
        "source": "TechCrunch",
        "sentiment": {
          "label": "positive",
          "score": 0.8
        },
        "summary": {
          "ai_summary": "AI-generated summary...",
          "ai_insights": "AI-generated insights...",
          "ai_sentiment_rating": 4
        },
        "symbols": [{"symbol": "AAPL"}]
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 150,
      "has_more": true,
      "pages": 8
    },
    "search_info": {
      "query": "AAPL artificial intelligence",
      "symbols": ["AAPL"],
      "keywords": ["artificial", "intelligence"],
      "type": "mixed",
      "total_results": 150
    }
  }
}
```

## Search Types

### Symbol Search
**Best for**: Company-specific news, stock analysis, financial reports

**Features**:
- Searches in `symbols_json` field for exact matches
- Supports multiple exchange formats (NASDAQ:AAPL, NYSE:MSFT)
- Includes region filtering (US, CHINA, HK)
- Returns full AI summaries and insights
- Advanced sorting (LATEST, HIGHEST sentiment, LOWEST sentiment)

**Examples**:
```
AAPL                    → Apple news
NASDAQ:AAPL NYSE:MSFT   → Apple and Microsoft news
CHINA AAPL              → Apple news from Chinese sources
0700.HK                 → Tencent (Hong Kong format)
```

### Keyword Search
**Best for**: Topic research, trend analysis, thematic searches

**Features**:
- Searches in `title` and `content_excerpt` fields
- Supports phrase matching with quotes
- Fast performance with optimized indexes
- Sentiment filtering available

**Examples**:
```
artificial intelligence        → AI-related articles
"earnings report"             → Exact phrase matching
merger acquisition            → M&A news
cybersecurity blockchain      → Multiple topics
```

### Mixed Search
**Best for**: Comprehensive research combining companies and topics

**Features**:
- Automatically detects symbols and keywords
- Combines results from both search types
- Deduplicates overlapping results
- Provides comprehensive coverage

**Examples**:
```
AAPL artificial intelligence   → Apple AI news specifically
MSFT earnings Q4              → Microsoft Q4 earnings
TSLA autonomous driving       → Tesla self-driving news
```

## Advanced Features

### Auto-Detection Logic

The system automatically determines search type based on patterns:

```python
# Symbol patterns detected:
- [A-Z]{1,5}           → AAPL, MSFT, GOOGL
- [A-Z]+:[A-Z0-9]+     → NASDAQ:AAPL, NYSE:MSFT
- \d{4,6}\.HK          → 0700.HK, 00941.HK
- \d{6}\.S[SZ]         → 000001.SS, 000001.SZ

# Everything else treated as keywords
```

### Optimization Features

1. **Storage Optimized**: Content excerpts limited to 1000 characters
2. **Performance Indexes**: Optimized database indexes for fast searching
3. **Redis Caching**: Search results cached for 5 minutes
4. **Smart Pagination**: Efficient pagination with has_more flags

### Search Filters

- **Sentiment**: `positive`, `negative`, `neutral`, `highest`, `lowest`
- **Date**: Specific date filtering (YYYY-MM-DD format)
- **Region**: `US`, `CHINA`, `HK` (for symbol search)
- **Processing**: `all`, `processed`, `unprocessed` (AI processing status)
- **Source**: Filter by news source

## Usage Examples

### Research Use Cases

```bash
# 1. Company earnings analysis
curl "/news/api/search?q=AAPL earnings Q1&sentiment=positive"

# 2. Industry trend research
curl "/news/api/search?q=electric vehicle autonomous&search_type=keyword"

# 3. Multi-company comparison
curl "/news/api/search?symbols=AAPL&symbols=MSFT&symbols=GOOGL"

# 4. Regional market analysis
curl "/news/api/search?q=CHINA semiconductor supply chain"

# 5. Sentiment-specific research
curl "/news/api/search?q=cryptocurrency&sentiment=negative"
```

### Integration Examples

```javascript
// Frontend integration
async function searchNews(query, options = {}) {
  const params = new URLSearchParams({
    q: query,
    search_type: options.type || 'auto',
    sentiment: options.sentiment || '',
    page: options.page || 1,
    per_page: options.perPage || 20
  });
  
  const response = await fetch(`/news/api/search?${params}`);
  return await response.json();
}

// Usage
const results = await searchNews("AAPL AI innovation", {
  type: 'mixed',
  sentiment: 'positive'
});
```

## Performance Considerations

### Optimization Tips

1. **Use symbol search** for company-specific queries (faster)
2. **Limit keyword searches** to relevant terms (better performance)
3. **Use pagination** for large result sets
4. **Cache results** on client side when appropriate
5. **Combine filters** to narrow down results efficiently

### Storage Optimization

Run the optimization tool to reduce storage usage:

```bash
# Optimize content excerpt sizes
python optimize_content_excerpt.py
```

This will:
- ✅ Reduce storage by ~25-50%
- ✅ Maintain full keyword search functionality
- ✅ Improve query performance
- ✅ Reduce memory usage

## Monitoring and Maintenance

### Search Index Health

Check search index synchronization:
```bash
python scripts/setup_search_optimization.py --status
```

### Performance Monitoring

Monitor search performance through logs:
```bash
# Search query logs
grep "Search completed" /var/log/app.log

# Performance timing
grep "Cache hit\|Cache miss" /var/log/app.log
```

## Future Enhancements

Planned improvements:
- **Full-text search**: PostgreSQL FTS integration
- **Search suggestions**: Auto-complete functionality  
- **Advanced analytics**: Search trend analysis
- **Machine learning**: Personalized search results
- **Real-time updates**: WebSocket-based live search

---

## Quick Reference

| Search Type | Best For | Performance | Features |
|-------------|----------|-------------|----------|
| **Symbol** | Company news | ⚡ Fastest | Full AI data, region filters |
| **Keyword** | Topic research | 🚀 Fast | Content search, phrase matching |
| **Mixed** | Comprehensive | ⚡ Fast | Combined results, auto-detection |

**Ready to use!** Your news search system now provides comprehensive, intelligent search across both symbols and content. 🎉 