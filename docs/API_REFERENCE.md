# API Reference - News Search Optimization

## 🔧 Developer Reference Guide

This document provides detailed API reference for the news search optimization system.

## Core Classes

### OptimizedNewsSearch

The main search service using the optimized search index.

```python
from app.utils.search.optimized_news_search import OptimizedNewsSearch
from app import db

search = OptimizedNewsSearch(db.session)
```

#### search_by_symbols()

Search for articles by stock symbols with advanced filtering.

```python
articles, total_count, has_more = search.search_by_symbols(
    symbols=['AAPL', 'MSFT'],
    sentiment_filter='POSITIVE',  # POSITIVE, NEGATIVE, NEUTRAL, HIGHEST, LOWEST
    sort_order='LATEST',          # LATEST, HIGHEST, LOWEST
    date_filter='2024-01-15',     # YYYY-MM-DD format
    region_filter='US',           # US, CHINA, HK
    processing_filter='all',      # all, processed, unprocessed
    page=1,
    per_page=20,
    include_content=False         # Set True to include full article content
)
```

**Parameters:**
- `symbols` (List[str]): List of symbols to search for
- `sentiment_filter` (str): Filter by sentiment rating
- `sort_order` (str): Sort order for results
- `date_filter` (str): Filter by specific date
- `region_filter` (str): Filter by market region
- `processing_filter` (str): Filter by AI processing status
- `page` (int): Page number for pagination
- `per_page` (int): Results per page
- `include_content` (bool): Include full article content (slower)

**Returns:**
- `articles` (List[Dict]): List of article dictionaries
- `total_count` (int): Total number of matching articles
- `has_more` (bool): Whether more pages are available

#### search_by_keywords()

Search for articles by keywords in title and content.

```python
articles, total_count, has_more = search.search_by_keywords(
    keywords=['earnings', 'revenue'],
    sentiment_filter='HIGHEST',
    sort_order='LATEST',
    date_filter='2024-01-15',
    page=1,
    per_page=20
)
```

#### get_recent_news()

Get recent news articles efficiently.

```python
recent_articles = search.get_recent_news(
    limit=10,
    hours=24,
    sentiment_filter='POSITIVE'
)
```

#### get_trending_symbols()

Analyze trending symbols based on article frequency.

```python
trending = search.get_trending_symbols(
    days=7,
    min_articles=5
)
# Returns: [{'symbol': 'AAPL', 'article_count': 25}, ...]
```

#### get_search_stats()

Get search index statistics.

```python
stats = search.get_search_stats()
```

**Returns:**
```python
{
    'total_articles': 50000,
    'recent_articles': 1200,
    'sources': 15,
    'oldest_article': '2024-01-01T00:00:00',
    'newest_article': '2024-12-31T23:59:59',
    'cache_enabled': True,
    'last_updated': '2024-12-31T12:00:00'
}
```

### SearchIndexSyncService

Service for managing search index synchronization.

```python
from app.utils.search.search_index_sync import SearchIndexSyncService

sync_service = SearchIndexSyncService()
```

#### sync_article()

Sync a single article to the search index.

```python
from app.models import NewsArticle

article = NewsArticle.query.get(123)
success = sync_service.sync_article(article)
```

#### sync_multiple_articles()

Efficiently sync multiple articles.

```python
articles = NewsArticle.query.limit(100).all()
stats = sync_service.sync_multiple_articles(articles)
```

**Returns:**
```python
{
    'added': 85,
    'updated': 10,
    'skipped': 3,
    'errors': 2
}
```

#### sync_new_articles()

Sync any articles missing from the search index.

```python
stats = sync_service.sync_new_articles(batch_size=1000)
```

#### remove_deleted_articles()

Remove orphaned entries from search index.

```python
removed_count = sync_service.remove_deleted_articles()
```

#### cleanup_old_articles()

Remove old articles from main table while keeping search index.

```python
deleted_count = sync_service.cleanup_old_articles(days_to_keep=90)
```

#### full_sync_status()

Get comprehensive synchronization status.

```python
status = sync_service.full_sync_status()
```

**Returns:**
```python
{
    'main_table_count': 50000,
    'search_index_count': 49500,
    'missing_from_index': 500,
    'orphaned_entries': 0,
    'sync_percentage': 99.0,
    'main_table_date_range': {
        'oldest': '2024-01-01T00:00:00',
        'newest': '2024-12-31T23:59:59'
    },
    'search_index_date_range': {
        'oldest': '2024-01-01T00:00:00',
        'newest': '2024-12-31T23:59:59'
    },
    'is_sync_needed': True,
    'last_checked': '2024-12-31T12:00:00'
}
```

## Models

### NewsSearchIndex

The optimized search index model.

```python
from app.models import NewsSearchIndex

# Create from existing article
article = NewsArticle.query.get(123)
search_entry = NewsSearchIndex.create_from_article(article)

# Update existing entry
search_entry.update_from_article(article)

# Convert to dict (compatible with existing search results)
article_dict = search_entry.to_dict()
```

**Model Fields:**
- `id`: Primary key
- `article_id`: Reference to original article
- `external_id`: Unique identifier
- `title`: Article title (indexed)
- `content_excerpt`: First 2000 chars of content
- `url`: Article URL
- `published_at`: Publication date (indexed)
- `source`: News source (indexed)
- `sentiment_label`: Sentiment classification (indexed)
- `sentiment_score`: Numeric sentiment score (indexed)
- `ai_sentiment_rating`: AI sentiment rating 1-5 (indexed)
- `symbols_json`: JSON array of related symbols
- `created_at`: Index creation time
- `updated_at`: Last update time

## Convenience Functions

### Quick Sync Functions

```python
from app.utils.search.search_index_sync import (
    sync_article_to_search_index,
    sync_articles_to_search_index
)

# Sync single article
article = NewsArticle.query.get(123)
success = sync_article_to_search_index(article)

# Sync multiple articles
articles = NewsArticle.query.limit(100).all()
stats = sync_articles_to_search_index(articles)
```

## Integration Examples

### Adding Search to Your Route

```python
from flask import request, jsonify
from app.utils.search.optimized_news_search import OptimizedNewsSearch

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    search = OptimizedNewsSearch(db.session)
    
    if query:
        # Keyword search
        articles, total, has_more = search.search_by_keywords(
            keywords=[query],
            page=page,
            per_page=20
        )
    else:
        # Recent articles
        articles = search.get_recent_news(limit=20)
        total = len(articles)
        has_more = False
    
    return jsonify({
        'articles': articles,
        'total': total,
        'has_more': has_more,
        'page': page
    })
```

### Auto-Sync on Article Creation

```python
from app.utils.search.search_index_sync import sync_article_to_search_index

# In your article creation route
@app.route('/api/articles', methods=['POST'])
def create_article():
    # ... create article ...
    
    # Auto-sync to search index
    sync_article_to_search_index(new_article)
    
    return jsonify(new_article.to_dict())
```

### Batch Processing

```python
def process_news_batch():
    """Process a batch of new articles"""
    
    # Get unprocessed articles
    articles = NewsArticle.query.filter_by(processed=False).limit(100).all()
    
    # Process articles (AI analysis, sentiment, etc.)
    for article in articles:
        # ... your processing logic ...
        article.processed = True
    
    db.session.commit()
    
    # Sync to search index
    stats = sync_articles_to_search_index(articles)
    print(f"Synced {stats['added']} articles to search index")
```

## Performance Tips

### Optimizing Search Queries

```python
# Use specific filters to reduce result set
articles, total, has_more = search.search_by_symbols(
    symbols=['AAPL'],
    sentiment_filter='POSITIVE',  # Reduces results
    date_filter='2024-01-15',     # Specific date
    per_page=10                   # Smaller page size
)

# For dashboard widgets, use recent news
recent = search.get_recent_news(limit=5)  # Very fast
```

### Batch Operations

```python
# Sync articles in batches for better performance
def sync_all_articles():
    batch_size = 1000
    offset = 0
    
    while True:
        articles = NewsArticle.query.offset(offset).limit(batch_size).all()
        if not articles:
            break
            
        stats = sync_articles_to_search_index(articles)
        print(f"Processed batch: {stats}")
        
        offset += batch_size
```

## Error Handling

### Graceful Degradation

```python
def safe_search(symbols):
    """Search with automatic fallback"""
    try:
        # Try optimized search first
        search = OptimizedNewsSearch(db.session)
        return search.search_by_symbols(symbols=symbols)
    except Exception as e:
        logger.warning(f"Optimized search failed: {e}")
        
        # Fallback to original search
        from app.utils.search.news_search import NewsSearch
        fallback_search = NewsSearch(db.session)
        return fallback_search.optimized_symbol_search(symbols=symbols)
```

### Monitoring Integration

```python
def check_search_health():
    """Health check for monitoring systems"""
    try:
        search = OptimizedNewsSearch(db.session)
        recent = search.get_recent_news(limit=1)
        
        sync_service = SearchIndexSyncService()
        status = sync_service.full_sync_status()
        
        return {
            'status': 'healthy',
            'search_working': len(recent) >= 0,
            'sync_percentage': status.get('sync_percentage', 0)
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
```

## Cache Integration

The system automatically integrates with Redis when available:

```python
# Cache is automatic, but you can control it
search = OptimizedNewsSearch(db.session)

# Clear cache if needed
search.clear_cache()

# Check cache status
if search.is_cache_available():
    print("✅ Redis cache enabled")
else:
    print("ℹ️ No cache available")
```

---

**For more examples and advanced usage, see the full documentation in `docs/NEWS_SEARCH_INDEX_OPTIMIZATION.md`** 