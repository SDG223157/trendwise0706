# Troubleshooting Guide - News Search Optimization

## 🔍 Common Issues and Solutions

This guide helps you diagnose and resolve issues with the news search optimization system.

## Quick Diagnostic Commands

### System Health Check
```bash
# Check overall system status
python scripts/setup_search_optimization.py --status

# Expected output:
# ✅ Search index table exists
# ✅ Search index populated: 10,000 articles
# ✅ Sync status: 100.0% (No sync needed)
# ✅ Cache system working
```

### Database Connection Test
```bash
# Test database connectivity
python -c "
from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
app = create_app()
with app.app_context():
    print(f'Main table: {NewsArticle.query.count()} articles')
    print(f'Search index: {NewsSearchIndex.query.count()} articles')
    print('✅ Database connection successful')
"
```

### Search Functionality Test
```bash
# Test search functionality
python -c "
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch
app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    recent = search.get_recent_news(limit=5)
    print(f'✅ Search working: Found {len(recent)} recent articles')
"
```

## Installation Issues

### Issue: "No module named 'app.utils.search.optimized_news_search'"

**Symptoms:**
- ImportError when trying to use optimized search
- Module not found errors

**Diagnosis:**
```bash
# Check if files exist
ls -la app/utils/search/
ls -la scripts/
```

**Solution:**
```bash
# Ensure all files are created
python scripts/setup_search_optimization.py --skip-populate

# Or manually create missing files
git status
git add .
git commit -m "Add missing search optimization files"
```

### Issue: "Table 'news_search_index' doesn't exist"

**Symptoms:**
- Database errors when accessing search index
- Table not found errors

**Diagnosis:**
```bash
# Check if table exists
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    result = db.session.execute(text(\"SELECT name FROM sqlite_master WHERE type='table' AND name='news_search_index'\")).fetchone()
    print('Table exists:' if result else 'Table missing')
"
```

**Solution:**
```bash
# Run database migration
flask db upgrade

# Or create table manually
python -c "
from app import create_app, db
from app.models import NewsSearchIndex
app = create_app()
with app.app_context():
    db.create_all()
    print('✅ Table created')
"
```

### Issue: Migration Fails with "Column already exists"

**Symptoms:**
- Error during `flask db upgrade`
- Column constraint errors

**Diagnosis:**
```bash
# Check migration history
flask db history

# Check current database schema
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    result = db.session.execute(text('PRAGMA table_info(news_search_index)')).fetchall()
    for row in result:
        print(row)
"
```

**Solution:**
```bash
# Mark migration as complete if table already exists
flask db stamp head

# Or reset and re-run migration
rm migrations/versions/add_news_search_index_*.py
flask db migrate -m "Add news search index"
flask db upgrade
```

## Performance Issues

### Issue: Slow Search Performance

**Symptoms:**
- Search takes > 1 second
- Timeouts on search requests
- High CPU usage during searches

**Diagnosis:**
```bash
# Test search performance
python -c "
import time
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    
    # Test different search types
    tests = [
        ('Recent news', lambda: search.get_recent_news(limit=10)),
        ('Symbol search', lambda: search.search_by_symbols(['AAPL'], per_page=10)),
        ('Keyword search', lambda: search.search_by_keywords(['earnings'], per_page=10)),
    ]
    
    for name, func in tests:
        start = time.time()
        result = func()
        duration = time.time() - start
        count = len(result) if isinstance(result, list) else len(result[0])
        print(f'{name}: {duration:.3f}s ({count} results)')
"
```

**Solutions:**

1. **Rebuild indexes:**
```bash
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    db.session.execute(text('REINDEX'))
    db.session.commit()
    print('✅ Indexes rebuilt')
"
```

2. **Optimize database:**
```bash
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    db.session.execute(text('VACUUM'))
    db.session.execute(text('ANALYZE'))
    db.session.commit()
    print('✅ Database optimized')
"
```

3. **Clear cache:**
```bash
python -c "
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch
app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    search.clear_cache()
    print('✅ Cache cleared')
"
```

### Issue: High Memory Usage

**Symptoms:**
- Memory usage grows during operations
- Out of memory errors
- System becomes unresponsive

**Diagnosis:**
```bash
# Check memory usage during operations
python -c "
import psutil
import gc
from app import create_app, db
from app.utils.search.search_index_sync import SearchIndexSyncService

process = psutil.Process()
print(f'Initial memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')

app = create_app()
with app.app_context():
    sync_service = SearchIndexSyncService()
    status = sync_service.full_sync_status()
    print(f'After sync check: {process.memory_info().rss / 1024 / 1024:.1f} MB')
    
    gc.collect()
    print(f'After cleanup: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

**Solutions:**

1. **Use smaller batch sizes:**
```bash
# Reduce batch size for operations
python scripts/populate_search_index.py populate --batch-size 250
```

2. **Increase swap space (Linux):**
```bash
# Create swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

3. **Optimize Python garbage collection:**
```bash
# Set environment variables
export PYTHONHASHSEED=0
export PYTHONOPTIMIZE=1
```

## Synchronization Issues

### Issue: Search Index Out of Sync

**Symptoms:**
- Search results don't include recent articles
- Inconsistent search results
- Missing articles in search

**Diagnosis:**
```bash
# Check sync status
python -c "
from app import create_app, db
from app.utils.search.search_index_sync import SearchIndexSyncService
app = create_app()
with app.app_context():
    sync_service = SearchIndexSyncService()
    status = sync_service.full_sync_status()
    print(f'Sync percentage: {status[\"sync_percentage\"]}%')
    print(f'Missing articles: {status[\"missing_from_index\"]}')
    print(f'Sync needed: {status[\"is_sync_needed\"]}')
"
```

**Solution:**
```bash
# Sync missing articles
python scripts/populate_search_index.py sync

# Or force full resync
python scripts/populate_search_index.py populate --force
```

### Issue: Orphaned Search Index Entries

**Symptoms:**
- Search index larger than main table
- References to deleted articles
- Inconsistent counts

**Diagnosis:**
```bash
# Check for orphaned entries
python -c "
from app import create_app, db
from app.utils.search.search_index_sync import SearchIndexSyncService
app = create_app()
with app.app_context():
    sync_service = SearchIndexSyncService()
    status = sync_service.full_sync_status()
    print(f'Orphaned entries: {status[\"orphaned_entries\"]}')
"
```

**Solution:**
```bash
# Remove orphaned entries
python -c "
from app import create_app, db
from app.utils.search.search_index_sync import SearchIndexSyncService
app = create_app()
with app.app_context():
    sync_service = SearchIndexSyncService()
    removed = sync_service.remove_deleted_articles()
    print(f'Removed {removed} orphaned entries')
"
```

## Data Issues

### Issue: No Search Results

**Symptoms:**
- All searches return empty results
- Search index appears empty
- No errors during search

**Diagnosis:**
```bash
# Check data availability
python -c "
from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
app = create_app()
with app.app_context():
    main_count = NewsArticle.query.count()
    search_count = NewsSearchIndex.query.count()
    print(f'Main table: {main_count} articles')
    print(f'Search index: {search_count} articles')
    
    if search_count == 0:
        print('⚠️ Search index is empty')
    elif main_count == 0:
        print('⚠️ No articles in main table')
    else:
        print('✅ Data appears normal')
"
```

**Solutions:**

1. **If search index is empty:**
```bash
python scripts/populate_search_index.py populate
```

2. **If main table is empty:**
```bash
# Check if articles exist but in different table
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    tables = db.session.execute(text(\"SELECT name FROM sqlite_master WHERE type='table'\")).fetchall()
    for table in tables:
        if 'news' in table[0] or 'article' in table[0]:
            count = db.session.execute(text(f'SELECT COUNT(*) FROM {table[0]}')).fetchone()[0]
            print(f'{table[0]}: {count} records')
"
```

3. **If data exists but not found:**
```bash
# Check data format
python -c "
from app import create_app, db
from app.models import NewsSearchIndex
app = create_app()
with app.app_context():
    sample = NewsSearchIndex.query.first()
    if sample:
        print(f'Sample data: {sample.to_dict()}')
    else:
        print('No sample data available')
"
```

### Issue: Search Returns Incorrect Results

**Symptoms:**
- Search results don't match query
- Outdated results returned
- Missing recent articles

**Diagnosis:**
```bash
# Test specific search scenarios
python -c "
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch
from app.models import NewsSearchIndex
from datetime import datetime, timedelta

app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    
    # Test recent articles
    recent = search.get_recent_news(limit=5)
    print(f'Recent articles: {len(recent)}')
    
    # Check date range
    latest = NewsSearchIndex.query.order_by(NewsSearchIndex.published_at.desc()).first()
    oldest = NewsSearchIndex.query.order_by(NewsSearchIndex.published_at.asc()).first()
    
    if latest:
        print(f'Latest article: {latest.published_at}')
    if oldest:
        print(f'Oldest article: {oldest.published_at}')
"
```

**Solution:**
```bash
# Refresh search index
python scripts/populate_search_index.py sync

# Clear cache
python -c "
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch
app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    search.clear_cache()
    print('✅ Cache cleared')
"
```

## Cache Issues

### Issue: Cache Not Working

**Symptoms:**
- Repeated slow queries
- No performance improvement
- Cache-related errors

**Diagnosis:**
```bash
# Check cache availability
python -c "
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch
app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    print(f'Cache available: {search.is_cache_available()}')
    
    # Test cache operations
    try:
        search.clear_cache()
        print('✅ Cache operations working')
    except Exception as e:
        print(f'❌ Cache error: {e}')
"
```

**Solutions:**

1. **Check Redis connection:**
```bash
# Test Redis directly
redis-cli ping
# Should return "PONG"
```

2. **Check Redis configuration:**
```bash
# Check Redis URL
python -c "
import os
print(f'Redis URL: {os.environ.get(\"REDIS_URL\", \"Not set\")}')
"
```

3. **Restart Redis:**
```bash
# Restart Redis service
sudo systemctl restart redis
# Or for Docker
docker restart redis
```

### Issue: Stale Cache Data

**Symptoms:**
- Old search results returned
- Changes not reflected in search
- Inconsistent results

**Solution:**
```bash
# Clear all cache
python -c "
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch
app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    search.clear_cache()
    print('✅ Cache cleared')
"

# Or clear Redis entirely
redis-cli FLUSHALL
```

## Environment Issues

### Issue: Environment Variables Not Set

**Symptoms:**
- Database connection errors
- Missing configuration
- Default values used

**Diagnosis:**
```bash
# Check environment variables
python -c "
import os
vars_to_check = ['FLASK_ENV', 'DATABASE_URL', 'REDIS_URL']
for var in vars_to_check:
    value = os.environ.get(var, 'Not set')
    print(f'{var}: {value}')
"
```

**Solution:**
```bash
# Set required environment variables
export FLASK_ENV=production
export DATABASE_URL=sqlite:///$(pwd)/trendwise.db
export REDIS_URL=redis://localhost:6379

# Or create .env file
cat > .env << 'EOF'
FLASK_ENV=production
DATABASE_URL=sqlite:///trendwise.db
REDIS_URL=redis://localhost:6379
EOF
```

### Issue: File Permissions

**Symptoms:**
- Permission denied errors
- Cannot write to database
- Script execution fails

**Diagnosis:**
```bash
# Check file permissions
ls -la trendwise.db
ls -la scripts/
```

**Solution:**
```bash
# Fix permissions
chmod 664 trendwise.db
chmod +x scripts/*.py
chown -R $(whoami):$(whoami) .
```

## Monitoring and Logging

### Enable Debug Logging

```bash
# Enable detailed logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    # Your search operations here
"
```

### Monitor System Resources

```bash
# Monitor during operations
python -c "
import psutil
import time
from app import create_app, db
from app.utils.search.search_index_sync import SearchIndexSyncService

process = psutil.Process()
print('Starting monitoring...')

app = create_app()
with app.app_context():
    sync_service = SearchIndexSyncService()
    
    for i in range(5):
        start = time.time()
        status = sync_service.full_sync_status()
        duration = time.time() - start
        
        mem_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        print(f'Iteration {i+1}: {duration:.3f}s, Memory: {mem_mb:.1f}MB, CPU: {cpu_percent:.1f}%')
        time.sleep(1)
"
```

## Advanced Debugging

### SQL Query Analysis

```bash
# Enable SQL logging
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

### Database Integrity Check

```bash
# Check database integrity
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    result = db.session.execute(text('PRAGMA integrity_check')).fetchone()
    print(f'Database integrity: {result[0]}')
    
    # Check foreign key constraints
    result = db.session.execute(text('PRAGMA foreign_key_check')).fetchall()
    if result:
        print('Foreign key violations:')
        for row in result:
            print(f'  {row}')
    else:
        print('✅ No foreign key violations')
"
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Create profile script
cat > profile_search.py << 'EOF'
from memory_profiler import profile
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

@profile
def test_search():
    app = create_app()
    with app.app_context():
        search = OptimizedNewsSearch(db.session)
        for i in range(10):
            articles, total, has_more = search.search_by_symbols(['AAPL'], per_page=10)
            print(f'Iteration {i+1}: {len(articles)} articles')

if __name__ == '__main__':
    test_search()
EOF

# Run profiler
python profile_search.py
```

## Emergency Procedures

### Complete System Reset

```bash
# CAUTION: This will reset the search optimization system
echo "This will reset the search optimization system. Continue? (y/N)"
read confirm
if [ "$confirm" = "y" ]; then
    # Drop search index table
    python -c "
    from app import create_app, db
    from app.models import NewsSearchIndex
    app = create_app()
    with app.app_context():
        NewsSearchIndex.__table__.drop(db.engine)
        print('✅ Search index table dropped')
    "
    
    # Clear cache
    redis-cli FLUSHALL
    
    # Recreate everything
    python scripts/setup_search_optimization.py
    
    echo "✅ System reset complete"
fi
```

### Backup Before Changes

```bash
# Always backup before making changes
cp trendwise.db trendwise.db.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Database backed up"
```

## Getting Help

### Collect System Information

```bash
# Collect diagnostic information
cat > diagnostic_info.txt << 'EOF'
=== System Information ===
EOF

echo "Date: $(date)" >> diagnostic_info.txt
echo "Python version: $(python --version)" >> diagnostic_info.txt
echo "Operating system: $(uname -a)" >> diagnostic_info.txt

echo "" >> diagnostic_info.txt
echo "=== Environment Variables ===" >> diagnostic_info.txt
env | grep -E "(FLASK|DATABASE|REDIS)" >> diagnostic_info.txt

echo "" >> diagnostic_info.txt
echo "=== Database Status ===" >> diagnostic_info.txt
python -c "
from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
app = create_app()
with app.app_context():
    print(f'Main table: {NewsArticle.query.count()} articles')
    print(f'Search index: {NewsSearchIndex.query.count()} articles')
" >> diagnostic_info.txt

echo "" >> diagnostic_info.txt
echo "=== File Permissions ===" >> diagnostic_info.txt
ls -la trendwise.db >> diagnostic_info.txt
ls -la scripts/ >> diagnostic_info.txt

echo "Diagnostic information saved to diagnostic_info.txt"
```

### Contact Information

When seeking help, please provide:
1. The diagnostic information from above
2. Error messages or logs
3. Steps to reproduce the issue
4. What you were trying to achieve

---

**Remember: The system is designed to gracefully degrade. If the search optimization fails, it will automatically fall back to the original search system.** 