# Performance Optimization Guide - News Search System

## ⚡ Maximizing Search Performance

This guide provides advanced techniques to optimize the performance of your news search system.

## Performance Benchmarks

### Target Performance Metrics
| Operation | Target Time | Excellent | Good | Needs Improvement |
|-----------|-------------|-----------|------|-------------------|
| Symbol Search | < 50ms | < 30ms | < 100ms | > 200ms |
| Keyword Search | < 100ms | < 50ms | < 200ms | > 500ms |
| Recent News | < 20ms | < 10ms | < 50ms | > 100ms |
| Sync Operations | > 1000 articles/sec | > 2000/sec | > 500/sec | < 200/sec |

### Measuring Current Performance
```bash
# Run performance benchmark
python -c "
import time
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    
    # Test various operations
    operations = [
        ('Recent News (10)', lambda: search.get_recent_news(limit=10)),
        ('Symbol Search (AAPL)', lambda: search.search_by_symbols(['AAPL'], per_page=10)),
        ('Keyword Search', lambda: search.search_by_keywords(['earnings'], per_page=10)),
        ('Trending Symbols', lambda: search.get_trending_symbols(days=7)),
        ('Stats', lambda: search.get_search_stats()),
    ]
    
    for name, operation in operations:
        times = []
        for i in range(10):
            start = time.time()
            result = operation()
            duration = time.time() - start
            times.append(duration * 1000)  # Convert to milliseconds
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f'{name:20} | Avg: {avg_time:6.1f}ms | Min: {min_time:6.1f}ms | Max: {max_time:6.1f}ms')
"
```

## Database Optimization

### 1. Index Analysis and Optimization

```bash
# Analyze index usage
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    # Check index usage statistics
    result = db.session.execute(text('PRAGMA index_list(news_search_index)')).fetchall()
    print('Current indexes:')
    for row in result:
        print(f'  {row}')
    
    # Analyze query performance
    db.session.execute(text('ANALYZE news_search_index'))
    db.session.commit()
    print('✅ Index statistics updated')
"
```

### 2. Database Configuration Optimization

```bash
# Optimize SQLite settings for performance
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    # Performance optimizations
    optimizations = [
        ('PRAGMA journal_mode=WAL', 'Enable Write-Ahead Logging'),
        ('PRAGMA synchronous=NORMAL', 'Optimize sync mode'),
        ('PRAGMA cache_size=50000', 'Increase cache size'),
        ('PRAGMA temp_store=MEMORY', 'Store temp data in memory'),
        ('PRAGMA mmap_size=268435456', 'Enable memory mapping (256MB)'),
        ('PRAGMA optimize', 'Optimize database'),
    ]
    
    for pragma, description in optimizations:
        try:
            result = db.session.execute(text(pragma)).fetchone()
            print(f'✅ {description}: {result[0] if result else \"Applied\"}')
        except Exception as e:
            print(f'⚠️ {description}: {e}')
    
    db.session.commit()
"
```

## Caching Optimization

### 1. Cache Performance Testing

```bash
# Test cache performance
python -c "
import time
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    
    # Test cache miss vs hit
    print('Testing cache performance...')
    
    # First call (cache miss)
    start = time.time()
    result1 = search.get_recent_news(limit=10)
    time1 = time.time() - start
    
    # Second call (cache hit)
    start = time.time()
    result2 = search.get_recent_news(limit=10)
    time2 = time.time() - start
    
    print(f'Cache miss: {time1*1000:.1f}ms')
    print(f'Cache hit: {time2*1000:.1f}ms')
    print(f'Speedup: {time1/time2:.1f}x' if time2 > 0 else 'Infinite speedup')
"
```

### 2. Cache Warming

```bash
# Warm up cache with common queries
python -c "
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

def warm_cache():
    app = create_app()
    with app.app_context():
        search = OptimizedNewsSearch(db.session)
        
        # Common symbols to cache
        common_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA']
        
        print('Warming cache with common queries...')
        
        # Recent news
        search.get_recent_news(limit=20)
        print('✅ Recent news cached')
        
        # Common symbol searches
        for symbol in common_symbols:
            search.search_by_symbols([symbol], per_page=10)
            print(f'✅ {symbol} searches cached')
        
        # Trending symbols
        search.get_trending_symbols(days=7)
        print('✅ Trending symbols cached')
        
        print('Cache warming complete!')

warm_cache()
"
```

## Memory Optimization

### 1. Memory Usage Monitoring

```bash
# Monitor memory usage during operations
python -c "
import psutil
import gc
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

def monitor_memory():
    process = psutil.Process()
    
    app = create_app()
    with app.app_context():
        search = OptimizedNewsSearch(db.session)
        
        print('Memory usage during search operations:')
        print(f'Initial: {process.memory_info().rss / 1024 / 1024:.1f} MB')
        
        # Perform operations
        operations = [
            ('Symbol search', lambda: search.search_by_symbols(['AAPL'], per_page=50)),
            ('Recent news', lambda: search.get_recent_news(limit=100)),
            ('Trending symbols', lambda: search.get_trending_symbols(days=30)),
        ]
        
        for name, operation in operations:
            result = operation()
            mem_after = process.memory_info().rss / 1024 / 1024
            print(f'After {name}: {mem_after:.1f} MB')
            
            # Cleanup
            gc.collect()
            db.session.expunge_all()
            
            mem_cleaned = process.memory_info().rss / 1024 / 1024
            print(f'After cleanup: {mem_cleaned:.1f} MB')
            print()

monitor_memory()
"
```

## Performance Testing

### 1. Comprehensive Performance Test

```bash
# Create performance test script
cat > performance_test.py << 'EOF'
import time
import statistics
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

def run_performance_tests():
    app = create_app()
    with app.app_context():
        search = OptimizedNewsSearch(db.session)
        
        # Test scenarios
        test_scenarios = [
            ("Recent News", lambda: search.get_recent_news(limit=10)),
            ("Single Symbol", lambda: search.search_by_symbols(['AAPL'], per_page=10)),
            ("Multiple Symbols", lambda: search.search_by_symbols(['AAPL', 'MSFT', 'GOOGL'], per_page=10)),
            ("Keyword Search", lambda: search.search_by_keywords(['earnings'], per_page=10)),
            ("Trending Symbols", lambda: search.get_trending_symbols(days=7)),
            ("Search Stats", lambda: search.get_search_stats()),
        ]
        
        print("Performance Test Results:")
        print("=" * 80)
        
        for scenario_name, test_func in test_scenarios:
            times = []
            
            # Run test multiple times
            for i in range(10):
                start = time.time()
                try:
                    result = test_func()
                    duration = time.time() - start
                    times.append(duration * 1000)  # Convert to ms
                except Exception as e:
                    print(f"❌ {scenario_name}: Error - {e}")
                    break
            
            if times:
                avg_time = statistics.mean(times)
                median_time = statistics.median(times)
                min_time = min(times)
                max_time = max(times)
                std_dev = statistics.stdev(times) if len(times) > 1 else 0
                
                # Performance rating
                if avg_time < 50:
                    rating = "🟢 Excellent"
                elif avg_time < 100:
                    rating = "🟡 Good"
                elif avg_time < 200:
                    rating = "🟠 Fair"
                else:
                    rating = "🔴 Poor"
                
                print(f"{scenario_name:20} | {rating:12} | Avg: {avg_time:6.1f}ms | "
                      f"Median: {median_time:6.1f}ms | Min: {min_time:6.1f}ms | "
                      f"Max: {max_time:6.1f}ms | StdDev: {std_dev:6.1f}ms")
        
        print("=" * 80)
        print("Performance test complete!")

if __name__ == "__main__":
    run_performance_tests()
EOF

python performance_test.py
```

## System-Level Optimization

### 1. Database Optimization

```bash
# Optimize database for better performance
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    # Optimize database
    db.session.execute(text('VACUUM'))
    db.session.execute(text('ANALYZE'))
    db.session.execute(text('PRAGMA optimize'))
    db.session.commit()
    print('✅ Database optimized')
"
```

### 2. Index Optimization

```bash
# Create additional performance indexes
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    # Create covering indexes for common queries
    indexes = [
        ('CREATE INDEX IF NOT EXISTS idx_search_symbols_published ON news_search_index(symbols_json, published_at DESC)', 'Symbol+Date covering index'),
        ('CREATE INDEX IF NOT EXISTS idx_search_compound_perf ON news_search_index(sentiment_label, published_at DESC, source)', 'Compound performance index'),
    ]
    
    for sql, description in indexes:
        try:
            db.session.execute(text(sql))
            print(f'✅ {description}')
        except Exception as e:
            print(f'⚠️ {description}: {e}')
    
    db.session.commit()
"
```

## Monitoring and Profiling

### 1. Query Performance Analysis

```bash
# Enable SQL logging to analyze slow queries
python -c "
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    # This will show all SQL queries
    articles, total, has_more = search.search_by_symbols(['AAPL'], per_page=5)
    print(f'Found {len(articles)} articles')
"
```

### 2. System Resource Monitoring

```bash
# Monitor system resources during operations
python -c "
import psutil
import time
from app import create_app, db
from app.utils.search.search_index_sync import SearchIndexSyncService

def monitor_resources():
    process = psutil.Process()
    print('Resource monitoring during operations:')
    
    app = create_app()
    with app.app_context():
        sync_service = SearchIndexSyncService()
        
        for i in range(5):
            start = time.time()
            status = sync_service.full_sync_status()
            duration = time.time() - start
            
            mem_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            print(f'Check {i+1}: {duration:.3f}s, Memory: {mem_mb:.1f}MB, CPU: {cpu_percent:.1f}%')
            time.sleep(1)

monitor_resources()
"
```

## Best Practices

### 1. Query Optimization
- Use appropriate indexes for your query patterns
- Limit result sets early in queries
- Use efficient WHERE clauses
- Avoid N+1 query problems

### 2. Cache Strategy
- Implement multi-level caching
- Use appropriate TTL values
- Warm cache with common queries
- Monitor cache hit rates

### 3. Memory Management
- Use batch processing for large datasets
- Implement proper cleanup in long-running processes
- Monitor memory usage in production
- Use generators for large result sets

### 4. Database Maintenance
- Regular VACUUM and ANALYZE operations
- Monitor query performance
- Optimize database configuration
- Use appropriate storage engines

### 5. Monitoring
- Track performance metrics
- Set up alerts for performance degradation
- Regular performance testing
- Profile code for bottlenecks

## Troubleshooting Performance Issues

### Common Issues and Solutions

1. **Slow Symbol Searches**
   - Check if indexes are being used
   - Verify symbol JSON format is correct
   - Consider optimizing symbol storage

2. **Memory Leaks**
   - Monitor memory growth over time
   - Implement proper session cleanup
   - Use memory profiling tools

3. **Cache Performance**
   - Verify Redis connectivity
   - Check cache hit rates
   - Monitor cache memory usage

4. **Database Locks**
   - Enable WAL mode for SQLite
   - Reduce transaction time
   - Monitor lock contention

## Production Optimization Checklist

- [ ] Database optimizations applied (WAL, cache size, etc.)
- [ ] Appropriate indexes created and analyzed
- [ ] Cache warming implemented
- [ ] Memory usage monitored
- [ ] Performance benchmarks established
- [ ] Regular maintenance scheduled
- [ ] Monitoring and alerting configured
- [ ] Backup and recovery procedures tested

---

**With these optimizations, your search system should achieve sub-100ms response times for most queries and handle high-concurrency scenarios efficiently! 🚀** 