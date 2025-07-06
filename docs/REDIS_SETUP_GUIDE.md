# Redis Setup Guide for Coolify Deployment

## Current Issue
The news search system is experiencing Redis connection failures with the error:
```
Error 111 connecting to localhost:6379. Connection refused.
```

## Solution Options

### Option 1: Enable Redis Service in Coolify (Recommended)

#### Step 1: Add Redis Service
1. **Access Coolify Dashboard**
   - Go to your project dashboard
   - Navigate to "Resources" or "Services"

2. **Add Redis Service**
   - Click "Add Resource" → "Database" → "Redis"
   - Set service name: `redis`
   - Use default port: `6379`
   - Set password (optional but recommended)

3. **Configure Environment Variables**
   ```bash
   REDIS_HOST=redis  # Service name in Coolify
   REDIS_PORT=6379
   REDIS_DB=0
   REDIS_PASSWORD=your_password_here  # if set
   ```

#### Step 2: Update Docker Network
- Ensure both your app and Redis are on the same Docker network
- Coolify handles this automatically when services are in the same project

#### Step 3: Test Connection
Access your app terminal and run:
```bash
python -c "
import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
r.ping()
print('Redis connection successful!')
"
```

### Option 2: Disable Redis Caching (Quick Fix)

If you don't want to set up Redis immediately, the system now gracefully falls back to operating without cache.

#### Environment Variables to Disable Redis
```bash
REDIS_HOST=disabled
REDIS_PORT=0
```

This will cause the cache to initialize in "unavailable" mode and search will work without caching.

### Option 3: External Redis Service

#### Using Redis Cloud or External Provider
```bash
REDIS_HOST=your-redis-cloud-endpoint.com
REDIS_PORT=12345
REDIS_PASSWORD=your-secure-password
REDIS_DB=0
```

## Performance Impact

| Configuration | Search Speed | Cache Benefits | Setup Complexity |
|---------------|--------------|----------------|------------------|
| With Redis    | 200-500ms    | ✅ Full caching | Medium |
| Without Redis | 800ms-2s     | ❌ No caching  | None |

## Verification Steps

### 1. Check Redis Service Status
```bash
# In Coolify terminal
redis-cli ping
# Should return: PONG
```

### 2. Test Application Cache
```bash
# In app terminal
python -c "
from app.utils.cache.news_cache import NewsCache
cache = NewsCache()
print(f'Cache available: {cache.is_available()}')
"
```

### 3. Monitor Application Logs
Look for these log messages:
- ✅ `Redis cache connected successfully` (Good)
- ⚠️ `Redis cache unavailable: ...` (Fallback mode)
- 🔄 `Redis connection lost, disabling cache` (Connection lost)

## Troubleshooting

### Common Issues and Solutions

#### 1. Connection Refused (Port 6379)
**Problem**: Redis service not running or not accessible
**Solution**: 
- Check if Redis service is running in Coolify
- Verify REDIS_HOST points to correct service name
- Ensure services are on same network

#### 2. Host Not Found
**Problem**: DNS resolution failure
**Solution**:
- Use service name instead of localhost
- In Coolify, use the Redis service name as hostname

#### 3. Authentication Failed
**Problem**: Password mismatch
**Solution**:
- Check REDIS_PASSWORD environment variable
- Verify Redis service password setting

#### 4. Timeout Issues
**Problem**: Connection timeouts
**Solution**:
- Check network connectivity between services
- Increase timeout values in cache configuration

### Performance Monitoring

#### Check Cache Hit Rate
The system logs cache performance:
- 🎯 `Cache hit for search query` (Cache working)
- 💾 `Cached search results for 5 minutes` (Cache storing)

#### Monitor Search Response Times
Without Redis: 800ms - 2s per search
With Redis: 200ms - 500ms per search

## Coolify-Specific Setup

### Method 1: UI Setup
1. Project Dashboard → Resources
2. Add Resource → Database → Redis
3. Configure:
   - **Name**: `redis`
   - **Version**: Latest stable
   - **Memory**: 256MB (minimum)
   - **Password**: Generate secure password

### Method 2: Docker Compose Integration

Add to your `docker-compose.yml`:
```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - app-network

  app:
    # ... your app configuration
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    depends_on:
      - redis
    networks:
      - app-network

volumes:
  redis_data:

networks:
  app-network:
```

## Current System Status

✅ **Fixed**: System now gracefully handles Redis unavailability
✅ **Fixed**: Improved error messages for users
✅ **Fixed**: No more crashes when Redis is down
⚠️ **Pending**: Redis service setup for optimal performance

## Next Steps

1. **Immediate**: System will work without Redis (slower but functional)
2. **Recommended**: Set up Redis service in Coolify for optimal performance
3. **Optional**: Consider Redis Cloud for managed solution

## Impact on Search Features

| Feature | Without Redis | With Redis |
|---------|---------------|------------|
| Basic Search | ✅ Works | ✅ Fast |
| Symbol Search | ✅ Works | ✅ Cached |
| Pagination | ✅ Works | ✅ Optimized |
| Filtering | ✅ Works | ✅ Cached |
| Trending | ✅ Works | ✅ Fast |

The application will function normally without Redis, but with improved performance when Redis is available. 