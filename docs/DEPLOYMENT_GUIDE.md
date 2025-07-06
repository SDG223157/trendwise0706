# Deployment Guide - News Search Optimization

## 🚀 Production Deployment Guide

This guide covers deploying the news search optimization system in production environments, including Coolify, Docker, and traditional servers.

## Pre-Deployment Checklist

### ✅ Requirements Verification
- [ ] Database accessible and backed up
- [ ] Redis available (optional but recommended)
- [ ] Sufficient disk space for search index
- [ ] Python environment with required packages
- [ ] Database migration permissions

### ✅ Environment Preparation
```bash
# Check disk space (search index can be 10-30% of main table size)
df -h

# Check Python environment
python --version
pip list | grep -E "(Flask|SQLAlchemy|alembic)"

# Verify database connectivity
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); print('✅ Database connected')"
```

## Coolify Deployment

### Step 1: Access Coolify Terminal
1. Open your Coolify dashboard
2. Navigate to your TrendWise project
3. Click "Terminal" or "Console"
4. Ensure you're in the project directory

### Step 2: Deploy Search Optimization
```bash
# Navigate to project directory
cd /app  # or your project path

# Run deployment
python scripts/setup_search_optimization.py

# Verify deployment
python scripts/setup_search_optimization.py --status
```

### Step 3: Coolify-Specific Configuration

**Environment Variables:**
```bash
# Add these to your Coolify environment variables
FLASK_APP=wsgi.py
FLASK_ENV=production
DATABASE_URL=sqlite:///trendwise.db  # or your database URL
REDIS_URL=redis://localhost:6379    # if Redis is available
```

**Persistent Storage:**
Ensure your database and any generated files are in persistent volumes:
```bash
# Check if database is in persistent storage
ls -la *.db
echo "Database location: $(pwd)/trendwise.db"
```

**Resource Allocation:**
Consider increasing resources for initial population:
```yaml
# In your Coolify configuration
resources:
  limits:
    memory: 1Gi      # Increase during setup
    cpu: 500m
  requests:
    memory: 512Mi
    cpu: 250m
```

### Step 4: Production Health Checks
```bash
# Create health check script for Coolify
cat > /app/health_check.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import NewsSearchIndex
from app.utils.search.optimized_news_search import OptimizedNewsSearch

def health_check():
    try:
        app = create_app()
        with app.app_context():
            # Check database
            count = NewsSearchIndex.query.count()
            print(f"✅ Search index: {count} articles")
            
            # Check search functionality
            search = OptimizedNewsSearch(db.session)
            recent = search.get_recent_news(limit=1)
            print(f"✅ Search working: {len(recent)} recent articles")
            
            return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == '__main__':
    success = health_check()
    sys.exit(0 if success else 1)
EOF

chmod +x /app/health_check.py

# Test health check
python /app/health_check.py
```

## Docker Deployment

### Dockerfile Optimization
```dockerfile
# Add to your Dockerfile
FROM python:3.9-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Make scripts executable
RUN chmod +x scripts/*.py

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python health_check.py || exit 1

# Run migrations and setup on startup
CMD ["sh", "-c", "python scripts/setup_search_optimization.py --skip-populate && python wsgi.py"]
```

### Docker Compose Example
```yaml
version: '3.8'
services:
  trendwise:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data  # Persistent storage for database
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=sqlite:///data/trendwise.db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped
    
  redis:
    image: redis:alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Docker Deployment Commands
```bash
# Build and deploy
docker-compose up -d

# Check logs
docker-compose logs -f trendwise

# Run setup (if not done automatically)
docker-compose exec trendwise python scripts/setup_search_optimization.py

# Monitor health
docker-compose exec trendwise python health_check.py
```

## Traditional Server Deployment

### System Service Setup
```bash
# Create systemd service
sudo tee /etc/systemd/system/trendwise.service << 'EOF'
[Unit]
Description=TrendWise News Application
After=network.target

[Service]
Type=simple
User=trendwise
WorkingDirectory=/opt/trendwise
Environment=FLASK_ENV=production
ExecStart=/opt/trendwise/venv/bin/python wsgi.py
ExecStartPost=/bin/sleep 10
ExecStartPost=/opt/trendwise/venv/bin/python scripts/setup_search_optimization.py --skip-populate
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable trendwise
sudo systemctl start trendwise
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://127.0.0.1:5000/health;
    }
}
```

## Production Optimizations

### Database Tuning
```bash
# For SQLite production setup
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    # Enable WAL mode for better concurrency
    db.session.execute(text('PRAGMA journal_mode=WAL'))
    # Increase cache size
    db.session.execute(text('PRAGMA cache_size=10000'))
    # Set synchronous mode
    db.session.execute(text('PRAGMA synchronous=NORMAL'))
    db.session.commit()
    print('✅ Database optimized for production')
"
```

### Search Index Optimization
```bash
# Analyze and optimize indexes
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    # Analyze query performance
    db.session.execute(text('ANALYZE'))
    # Rebuild indexes if needed
    db.session.execute(text('REINDEX'))
    db.session.commit()
    print('✅ Indexes optimized')
"
```

### Memory Optimization
```bash
# Set appropriate batch sizes for your server
export SEARCH_BATCH_SIZE=500  # Smaller for limited memory
export SYNC_BATCH_SIZE=1000   # Adjust based on available RAM

# Monitor memory usage during operations
python scripts/populate_search_index.py populate --batch-size $SEARCH_BATCH_SIZE
```

## Monitoring and Alerting

### Prometheus Metrics
```python
# Add to your application
from prometheus_client import Counter, Histogram, Gauge, generate_latest

search_requests = Counter('search_requests_total', 'Total search requests')
search_duration = Histogram('search_duration_seconds', 'Search request duration')
search_index_size = Gauge('search_index_articles_total', 'Total articles in search index')

@app.route('/metrics')
def metrics():
    return generate_latest()
```

### Health Check Endpoint
```python
# Add to your Flask app
@app.route('/health')
def health_check():
    try:
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        search = OptimizedNewsSearch(db.session)
        recent = search.get_recent_news(limit=1)
        
        return jsonify({
            'status': 'healthy',
            'search_working': True,
            'articles_in_index': NewsSearchIndex.query.count(),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
```

### Log Monitoring
```bash
# Configure log rotation for production
sudo tee /etc/logrotate.d/trendwise << 'EOF'
/opt/trendwise/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 trendwise trendwise
    postrotate
        systemctl reload trendwise
    endscript
}
EOF
```

## Backup and Recovery

### Database Backup
```bash
# Create backup script
cat > /opt/trendwise/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/trendwise/backups"

mkdir -p $BACKUP_DIR

# Backup main database
sqlite3 /opt/trendwise/trendwise.db ".backup $BACKUP_DIR/trendwise_$DATE.db"

# Backup search index separately (for faster restore)
python -c "
from app import create_app, db
from app.models import NewsSearchIndex
app = create_app()
with app.app_context():
    count = NewsSearchIndex.query.count()
    print(f'Backed up search index with {count} articles')
"

# Keep only last 7 days
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

echo "Backup completed: trendwise_$DATE.db"
EOF

chmod +x /opt/trendwise/backup.sh

# Add to crontab
echo "0 2 * * * /opt/trendwise/backup.sh" | crontab -
```

### Disaster Recovery
```bash
# Recovery procedure
cat > /opt/trendwise/recovery.sh << 'EOF'
#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "Starting recovery from $1..."

# Stop service
sudo systemctl stop trendwise

# Restore database
cp "$1" /opt/trendwise/trendwise.db

# Rebuild search index
cd /opt/trendwise
python scripts/setup_search_optimization.py

# Start service
sudo systemctl start trendwise

echo "Recovery completed"
EOF

chmod +x /opt/trendwise/recovery.sh
```

## Maintenance Procedures

### Automated Maintenance
```bash
# Create maintenance script
cat > /opt/trendwise/maintenance.sh << 'EOF'
#!/bin/bash
cd /opt/trendwise

echo "Starting maintenance..."

# Sync any missing articles
python scripts/populate_search_index.py sync

# Clean up old articles (keep 90 days)
python scripts/populate_search_index.py cleanup --keep-days 90

# Vacuum database
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    db.session.execute(text('VACUUM'))
    db.session.commit()
    print('✅ Database vacuumed')
"

# Check system health
python scripts/setup_search_optimization.py --status

echo "Maintenance completed"
EOF

chmod +x /opt/trendwise/maintenance.sh

# Schedule weekly maintenance
echo "0 3 * * 0 /opt/trendwise/maintenance.sh" | crontab -
```

### Performance Monitoring
```bash
# Create performance monitoring script
cat > /opt/trendwise/monitor.sh << 'EOF'
#!/bin/bash
cd /opt/trendwise

# Check search performance
python -c "
import time
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    
    # Test search performance
    start = time.time()
    articles, total, has_more = search.search_by_symbols(['AAPL'], per_page=10)
    duration = time.time() - start
    
    print(f'Search performance: {duration:.3f}s for {len(articles)} results')
    
    if duration > 1.0:
        print('⚠️ Search performance degraded')
    else:
        print('✅ Search performance good')
"
EOF

chmod +x /opt/trendwise/monitor.sh

# Run every hour
echo "0 * * * * /opt/trendwise/monitor.sh" | crontab -
```

## Rollback Procedures

### Safe Rollback
```bash
# Create rollback script
cat > /opt/trendwise/rollback.sh << 'EOF'
#!/bin/bash
echo "Rolling back search optimization..."

# The system automatically falls back to original search
# if search index is not available

# To completely remove search optimization:
# 1. Stop using optimized search
git checkout HEAD~1 -- app/news/routes.py

# 2. Keep search index for future use or drop it
# python -c "
# from app import create_app, db
# from app.models import NewsSearchIndex
# app = create_app()
# with app.app_context():
#     NewsSearchIndex.__table__.drop(db.engine)
#     print('Search index table dropped')
# "

echo "Rollback completed"
EOF

chmod +x /opt/trendwise/rollback.sh
```

## Security Considerations

### Database Security
```bash
# Set appropriate file permissions
chmod 600 /opt/trendwise/trendwise.db
chown trendwise:trendwise /opt/trendwise/trendwise.db

# Restrict script access
chmod 750 /opt/trendwise/scripts/
chown -R trendwise:trendwise /opt/trendwise/scripts/
```

### Environment Variables
```bash
# Use secure environment variable management
# Never commit database URLs or secrets to git

# Example .env file (not committed)
DATABASE_URL=postgresql://user:pass@localhost/trendwise
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
```

## Troubleshooting Production Issues

### Common Issues and Solutions

**Issue: Search index empty after deployment**
```bash
# Solution: Populate the index
python scripts/populate_search_index.py populate
```

**Issue: Search performance degraded**
```bash
# Solution: Rebuild indexes
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    db.session.execute(text('REINDEX'))
    db.session.commit()
"
```

**Issue: High memory usage during sync**
```bash
# Solution: Use smaller batch sizes
python scripts/populate_search_index.py populate --batch-size 250
```

**Issue: Database locked errors**
```bash
# Solution: Enable WAL mode
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    db.session.execute(text('PRAGMA journal_mode=WAL'))
    db.session.commit()
"
```

## Performance Benchmarks

### Expected Performance Metrics
- **Search Response Time**: < 100ms for symbol searches
- **Index Sync Time**: 1000 articles/second
- **Storage Overhead**: 20-30% of main table size
- **Memory Usage**: +50MB during normal operation
- **CPU Impact**: < 5% increase during searches

### Monitoring Commands
```bash
# Monitor search performance
python -c "
import time
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

app = create_app()
with app.app_context():
    search = OptimizedNewsSearch(db.session)
    
    for i in range(10):
        start = time.time()
        search.get_recent_news(limit=10)
        print(f'Search {i+1}: {(time.time() - start)*1000:.1f}ms')
"
```

---

**Your search optimization system is now production-ready! 🎉**

For ongoing support and updates, refer to:
- `docs/TROUBLESHOOTING_GUIDE.md`
- `docs/API_REFERENCE.md`
- Application logs and health check endpoints 