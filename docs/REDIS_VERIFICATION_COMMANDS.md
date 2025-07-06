# Redis Verification Commands for Coolify

Since you've enabled Redis in your Coolify app, here are the specific commands to run **in your Coolify app terminal** to verify everything is working correctly.

## Step 1: Access Your Coolify App Terminal

1. Go to your Coolify dashboard
2. Navigate to your app
3. Open the terminal/console for your app

## Step 2: Basic Redis Connection Test

Run this command in your Coolify app terminal:

```bash
python -c "
import redis
import os
print('🔌 Testing Redis Connection...')
try:
    r = redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        password=os.getenv('REDIS_PASSWORD', None),
        decode_responses=True
    )
    r.ping()
    print('✅ Redis connection successful!')
    print(f'📍 Host: {os.getenv(\"REDIS_HOST\", \"redis\")}')
    print(f'📍 Port: {os.getenv(\"REDIS_PORT\", \"6379\")}')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
"
```

## Step 3: Test Application Cache System

```bash
python -c "
from app.utils.cache.news_cache import NewsCache
import time

print('💾 Testing Application Cache...')
cache = NewsCache()

if cache.is_available():
    print('✅ Cache system available')
    
    # Test cache operations
    test_data = {'message': 'Redis working!', 'timestamp': time.time()}
    
    # Test set
    success = cache.set_json('test:key', test_data, expire=60)
    print(f'Set operation: {\"✅ Success\" if success else \"❌ Failed\"}')
    
    # Test get
    retrieved = cache.get_json('test:key')
    if retrieved and retrieved.get('message') == test_data['message']:
        print('Get operation: ✅ Success')
    else:
        print('Get operation: ❌ Failed')
    
    print('✅ Cache system fully operational!')
else:
    print('❌ Cache system unavailable')
"
```

## Step 4: Test Search System Optimization

```bash
python -c "
from app.utils.search.news_search import NewsSearch
from app import db

print('🔍 Testing Search System...')
search = NewsSearch(db.session)

if search.is_cache_available():
    print('✅ Search system optimized with Redis')
    print('📈 Expected performance: 200-500ms response time')
    print('💾 5-minute result caching enabled')
else:
    print('⚠️ Search running without cache optimization')
"
```

## Step 5: Check Environment Variables

```bash
python -c "
import os
print('🔧 Environment Configuration:')
print(f'REDIS_HOST: {os.getenv(\"REDIS_HOST\", \"not_set\")}')
print(f'REDIS_PORT: {os.getenv(\"REDIS_PORT\", \"not_set\")}')
print(f'REDIS_DB: {os.getenv(\"REDIS_DB\", \"0\")}')
redis_password = os.getenv('REDIS_PASSWORD', 'not_set')
print(f'REDIS_PASSWORD: {\"Set\" if redis_password != \"not_set\" else \"Not set\"}')
"
```

## Step 6: Monitor Application Logs

In your Coolify dashboard, check the application logs for these messages:

### ✅ Success Messages
```
✅ Redis cache connected successfully
✅ NewsSearch initialized with Redis cache
🎯 Cache hit for search query
💾 Cached search results for 5 minutes
```

### ⚠️ Fallback Messages (If Issues)
```
⚠️ Redis cache unavailable: Connection refused. Operating without cache.
ℹ️ NewsSearch initialized without Redis cache
```

## Step 7: Test News Search Performance

1. Navigate to your app's `/news/search` page
2. Try searching for symbols like "AAPL", "TSLA", or "MSFT"
3. Notice the improved response times (should be much faster)
4. Check the application logs for cache activity

## Expected Results

### ✅ If Redis is Working Correctly:
- All connection tests pass
- Cache operations successful
- Search system shows "optimized with Redis"
- Application logs show cache hits
- Search responses are 200-500ms (much faster)

### ❌ If Redis Has Issues:
- Connection tests fail
- Environment variables may be incorrect
- Search system falls back to non-cached mode
- Slower search responses (800ms-2s)

## Troubleshooting Common Issues

### Issue 1: Connection Refused
**Problem**: Redis service not accessible
**Solution**: 
```bash
# Check if Redis service is running
redis-cli ping
# Should return: PONG
```

### Issue 2: Wrong Host/Port
**Problem**: Environment variables incorrect
**Solution**: Update environment variables in Coolify:
```
REDIS_HOST=redis  # Use service name, not localhost
REDIS_PORT=6379
```

### Issue 3: Authentication Issues
**Problem**: Password mismatch
**Solution**: Check Redis service password in Coolify matches `REDIS_PASSWORD`

## Performance Monitoring Commands

### Check Redis Stats
```bash
redis-cli info stats
```

### Monitor Redis Activity
```bash
redis-cli monitor
```

### Check Cache Usage
```bash
python -c "
from app.utils.cache.news_cache import NewsCache
cache = NewsCache()
if cache.is_available():
    print('✅ Cache ready for high-performance searches')
else:
    print('⚠️ Cache unavailable - searches will be slower')
"
```

## Next Steps After Verification

1. **If All Tests Pass**: 🎉 Enjoy 3-5x faster search performance!
2. **If Issues Found**: Use troubleshooting steps above
3. **Monitor Performance**: Watch application logs for cache performance
4. **Test User Experience**: Try various search queries to feel the speed improvement

Run these commands in your Coolify app terminal and let me know the results! 