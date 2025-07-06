# Database Migration Guide for Coolify Deployment

## 🚀 Complete Guide for News Search Performance Optimization on Coolify

This guide will help you implement the database migration for your news search optimizations on your Coolify deployment.

## 📋 Prerequisites

1. **Coolify Setup**: Your app is deployed on Coolify
2. **Database**: MySQL/PostgreSQL database connected to your Coolify app
3. **Flask-Migrate**: Already configured in your app (`app/__init__.py`)

## 🔧 Migration Setup for Coolify

### Step 1: Update Environment Variables

In your Coolify dashboard, ensure these environment variables are set:

```env
# Production Database (MySQL/PostgreSQL)
DATABASE_URL=mysql://username:password@hostname:port/database
# OR for PostgreSQL:
# DATABASE_URL=postgresql://username:password@hostname:port/database

# Flask Configuration
FLASK_APP=wsgi.py
FLASK_ENV=production

# Optional: Redis for caching (recommended for performance)
REDIS_URL=redis://your-redis-host:6379/0
```

### Step 2: Create Migration Files

Create these migration files in your local environment, then deploy:

#### A. Initial Migration (if needed)
```bash
# Run locally with production database settings
export DATABASE_URL="your_production_database_url"
flask db migrate -m "Initial migration"
```

#### B. News Search Optimization Migration

Create this custom migration file:

```python
# migrations/versions/add_news_search_indexes.py
"""Add indexes for news search optimization

Revision ID: news_search_optimization
Revises: [previous_revision_id]
Create Date: 2025-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'news_search_optimization'
down_revision = '[previous_revision_id]'  # Replace with your last migration ID
branch_labels = None
depends_on = None

def upgrade():
    # Create indexes for news_articles table
    op.create_index('idx_news_published_at', 'news_articles', ['published_at'])
    op.create_index('idx_news_source', 'news_articles', ['source'])
    op.create_index('idx_news_sentiment_label', 'news_articles', ['sentiment_label'])
    op.create_index('idx_news_sentiment_score', 'news_articles', ['sentiment_score'])
    op.create_index('idx_news_ai_sentiment_rating', 'news_articles', ['ai_sentiment_rating'])
    op.create_index('idx_news_created_at', 'news_articles', ['created_at'])
    
    # Create composite indexes for common query patterns
    op.create_index('idx_published_sentiment', 'news_articles', ['published_at', 'ai_sentiment_rating'])
    op.create_index('idx_published_created', 'news_articles', ['published_at', 'created_at'])
    op.create_index('idx_sentiment_published', 'news_articles', ['sentiment_score', 'published_at'])
    op.create_index('idx_ai_sentiment_published', 'news_articles', ['ai_sentiment_rating', 'published_at'])
    op.create_index('idx_source_published', 'news_articles', ['source', 'published_at'])
    op.create_index('idx_sentiment_label_published', 'news_articles', ['sentiment_label', 'published_at'])
    
    # Create indexes for article_symbols table
    op.create_index('idx_symbol', 'article_symbols', ['symbol'])
    op.create_index('idx_symbol_article', 'article_symbols', ['symbol', 'article_id'])

def downgrade():
    # Drop indexes in reverse order
    op.drop_index('idx_symbol_article', 'article_symbols')
    op.drop_index('idx_symbol', 'article_symbols')
    op.drop_index('idx_sentiment_label_published', 'news_articles')
    op.drop_index('idx_source_published', 'news_articles')
    op.drop_index('idx_ai_sentiment_published', 'news_articles')
    op.drop_index('idx_sentiment_published', 'news_articles')
    op.drop_index('idx_published_created', 'news_articles')
    op.drop_index('idx_published_sentiment', 'news_articles')
    op.drop_index('idx_news_created_at', 'news_articles')
    op.drop_index('idx_news_ai_sentiment_rating', 'news_articles')
    op.drop_index('idx_news_sentiment_score', 'news_articles')
    op.drop_index('idx_news_sentiment_label', 'news_articles')
    op.drop_index('idx_news_source', 'news_articles')
    op.drop_index('idx_news_published_at', 'news_articles')
```

### Step 3: Create Deployment Script

Create a deployment script that runs migrations:

```bash
# deploy-migration.sh
#!/bin/bash

echo "🚀 Starting deployment with database migration..."

# Set database connection for production
export DATABASE_URL=$DATABASE_URL

# Run database migrations
echo "📊 Running database migrations..."
flask db upgrade

# Check if migration was successful
if [ $? -eq 0 ]; then
    echo "✅ Database migration completed successfully!"
else
    echo "❌ Database migration failed!"
    exit 1
fi

echo "🎉 Deployment completed!"
```

## 🏗 Coolify Implementation Methods

### Method 1: Using Coolify Build Commands

In your Coolify application settings:

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
flask db upgrade && python wsgi.py
```

### Method 2: Using Docker with Migration

Update your `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create entrypoint script
RUN echo '#!/bin/bash\nflask db upgrade\nexec python wsgi.py' > /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 5000

CMD ["/app/entrypoint.sh"]
```

### Method 3: Using Coolify Pre-deployment Hook

In Coolify dashboard, set up a pre-deployment script:

```bash
# Pre-deployment Hook
#!/bin/bash
cd /app
flask db upgrade
```

## 📊 Manual Migration on Coolify

If you need to run migrations manually:

### Step 1: Access Coolify Container

```bash
# SSH into your Coolify container
docker exec -it your-app-container bash

# Or use Coolify's terminal feature in the dashboard
```

### Step 2: Run Migrations

```bash
# Inside the container
cd /app
flask db upgrade

# Check migration status
flask db current

# View migration history
flask db history
```

## 🔄 Safe Migration Practices

### 1. **Backup Before Migration**

```bash
# Create database backup before migration
mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. **Test Migration Locally**

```bash
# Test with production data structure
export DATABASE_URL="your_test_database_url"
flask db upgrade
```

### 3. **Zero-Downtime Migration Strategy**

For production systems with no downtime tolerance:

```python
# Create backward-compatible migrations
def upgrade():
    # 1. Add new indexes (safe operation)
    op.create_index('idx_news_published_at', 'news_articles', ['published_at'])
    
    # 2. For column changes, use these steps:
    # Step 1: Add new column (if needed)
    # Step 2: Populate new column 
    # Step 3: Update application to use new column
    # Step 4: Remove old column in next migration
```

## 🚨 Troubleshooting

### Common Issues and Solutions

**1. "Table doesn't exist" Error**
```bash
# Check if tables exist
flask db current
flask db show

# If no tables, run initial migration
flask db upgrade
```

**2. "Index already exists" Error**
```bash
# Check existing indexes
SHOW INDEX FROM news_articles;

# Skip if indexes already exist (modify migration)
```

**3. "Connection timeout" Error**
```bash
# Increase connection timeout in migration
op.execute("SET innodb_lock_wait_timeout = 300")
```

**4. "Migration file not found"**
```bash
# Regenerate migration files
flask db migrate -m "Regenerate migration"
```

## 📈 Performance Verification

After migration, verify the performance improvements:

### 1. **Check Index Usage**

```sql
-- MySQL
EXPLAIN SELECT * FROM news_articles WHERE published_at > '2025-01-01' ORDER BY ai_sentiment_rating DESC;

-- Should show "Using index" in Extra column
```

### 2. **Monitor Query Performance**

```python
# Add to your Flask app for monitoring
import time
from flask import g

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        app.logger.info(f"Request took {duration:.3f}s")
    return response
```

### 3. **Test Search Performance**

```bash
# Use curl to test search endpoints
curl -w "@curl-format.txt" "https://your-app.com/news/search?symbol=AAPL"

# Create curl-format.txt:
echo '     time_namelookup:  %{time_namelookup}\n      time_connect:  %{time_connect}\n   time_appconnect:  %{time_appconnect}\n  time_pretransfer:  %{time_pretransfer}\n     time_redirect:  %{time_redirect}\n    time_starttransfer:  %{time_starttransfer}\n                     ----------\n        time_total:  %{time_total}\n' > curl-format.txt
```

## 🎯 Expected Results

After successful migration:

- **Search response time**: 2-10 seconds → 200-500ms (5-20x improvement)
- **Database query time**: Reduced by 60-80%
- **Pagination speed**: 1-3 seconds → 100-200ms (5-15x improvement)
- **Concurrent user support**: Significantly increased

## 📝 Post-Migration Checklist

- [ ] Database indexes created successfully
- [ ] Application starts without errors
- [ ] Search functionality works correctly
- [ ] Performance improvements verified
- [ ] Error monitoring configured
- [ ] Database backup schedule updated
- [ ] Team notified of changes

## 🔗 Additional Resources

### Coolify Documentation
- [Coolify Database Management](https://coolify.io/docs/databases)
- [Environment Variables](https://coolify.io/docs/applications/environment-variables)

### Flask-Migrate Resources
- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [Alembic Migration Guide](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

---

## 🆘 Need Help?

If you encounter issues:

1. **Check Coolify logs** in the dashboard
2. **Verify database connectivity** from the application
3. **Test migrations locally** before deploying
4. **Use database backup** if migration fails

Remember: Always backup your database before running migrations in production! 🛡️ 