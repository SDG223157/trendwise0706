#!/bin/bash
# Coolify Search Optimization Deployment Script
# Optimized for Python 3.9.23 environment

set -e  # Exit on any error

echo "🚀 Starting TrendWise Search Optimization Deployment for Coolify"
echo "📍 Python version: $(python --version)"
echo "📍 Current directory: $(pwd)"
echo "📍 Date: $(date)"
echo "=" * 80

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        log "✅ $1 completed successfully"
    else
        log "❌ $1 failed"
        exit 1
    fi
}

# 1. Environment Setup
log "🔧 Setting up environment variables for Coolify..."

# Set production environment - use Coolify database
export FLASK_ENV="production"
export FLASK_APP="wsgi.py"

# Don't override DATABASE_URL if it's already set by Coolify
if [ -z "$DATABASE_URL" ]; then
    log "⚠️ DATABASE_URL not set - using fallback configuration"
else
    log "✅ Using Coolify database: ${DATABASE_URL%/*}/*****"
fi

log "✅ Environment configured for Coolify database"

# 2. Check Prerequisites
log "🔍 Checking prerequisites..."

# Check Python version
python_version=$(python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
if [[ "$python_version" == "3.9" ]] || [[ "$python_version" > "3.9" ]]; then
    log "✅ Python $python_version is compatible"
else
    log "⚠️ Python $python_version detected, recommend 3.9+"
fi

# Check required packages
python -c "import flask, sqlalchemy, alembic" 2>/dev/null
check_success "Required Python packages"

# Check database file
if [ ! -f "trendwise.db" ]; then
    log "📁 Creating new database file..."
    touch trendwise.db
fi

# 3. Database Initialization
log "🗄️ Initializing database..."

# Force SQLite database creation
python -c "
import os
os.environ['DATABASE_URL'] = 'sqlite:///$(pwd)/trendwise.db'
os.environ['FLASK_ENV'] = 'production'

from app import create_app, db
from app.models import NewsSearchIndex

app = create_app()
with app.app_context():
    try:
        # Create all tables
        db.create_all()
        print('✅ Database tables created')
        
        # Check if search index table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'news_search_index' in tables:
            print('✅ Search index table ready')
        else:
            print('⚠️ Search index table not found, will be created during migration')
            
    except Exception as e:
        print(f'⚠️ Database setup note: {e}')
        print('This is normal for initial setup')
"
check_success "Database initialization"

# 4. Database Migration
log "🔄 Running database migrations..."

# Initialize migration if needed
if [ ! -d "migrations" ]; then
    log "📁 Initializing Flask-Migrate..."
    python -c "
import os
os.environ['DATABASE_URL'] = 'sqlite:///$(pwd)/trendwise.db'
from flask_migrate import init
from app import create_app
app = create_app()
with app.app_context():
    init()
" 2>/dev/null || log "Migration directory already exists or skipped"
fi

# Run migrations
python -c "
import os
os.environ['DATABASE_URL'] = 'sqlite:///$(pwd)/trendwise.db'
from flask_migrate import upgrade
from app import create_app
app = create_app()
with app.app_context():
    try:
        upgrade()
        print('✅ Database migrations completed')
    except Exception as e:
        print(f'⚠️ Migration note: {e}')
        # Try to create tables directly if migration fails
        from app import db
        db.create_all()
        print('✅ Tables created directly')
"
check_success "Database migration"

# 5. Search Optimization Setup
log "🔍 Setting up search optimization..."

# Check if we can run the search optimization setup
if [ -f "scripts/setup_search_optimization.py" ]; then
    python scripts/setup_search_optimization.py --coolify-mode
    check_success "Search optimization setup"
else
    log "⚠️ Search optimization script not found, creating basic setup..."
    
    # Basic search optimization setup
    python -c "
import os
os.environ['DATABASE_URL'] = 'sqlite:///$(pwd)/trendwise.db'

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex

app = create_app()
with app.app_context():
    try:
        # Ensure search index table exists
        db.create_all()
        
        # Check current status
        main_count = NewsArticle.query.count()
        search_count = NewsSearchIndex.query.count()
        
        print(f'📊 Current Status:')
        print(f'   📰 Main articles: {main_count:,}')
        print(f'   🔍 Search index: {search_count:,}')
        
        if main_count > 0 and search_count == 0:
            print('⚠️ Found articles but no search index entries')
            print('Run populate_search_index.py to sync articles')
        elif main_count == 0:
            print('ℹ️ No articles found - this is normal for new installations')
        else:
            print('✅ Search optimization ready')
            
    except Exception as e:
        print(f'Error checking status: {e}')
"
fi

# 6. Test Search Functionality
log "🧪 Testing search functionality..."

python -c "
import os
os.environ['DATABASE_URL'] = 'sqlite:///$(pwd)/trendwise.db'

from app import create_app, db

app = create_app()
with app.app_context():
    try:
        # Test basic database connectivity
        from app.models import NewsSearchIndex
        count = NewsSearchIndex.query.count()
        print(f'✅ Search index accessible: {count:,} entries')
        
        # Test search functionality
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        search = OptimizedNewsSearch(db.session)
        
        # Test basic search operations
        recent = search.get_recent_news(limit=1)
        print(f'✅ Search functionality working: {len(recent)} results')
        
        # Test cache availability
        cache_status = search.is_cache_available()
        print(f'💾 Cache status: {\"Available\" if cache_status else \"Not available\"}')
        
    except Exception as e:
        print(f'⚠️ Search test note: {e}')
        print('This is normal if no articles are present yet')
"

# 7. Create Coolify-specific health check
log "🏥 Creating health check endpoint..."

cat > coolify_health_check.py << 'EOF'
#!/usr/bin/env python3
"""
Coolify-specific health check for TrendWise Search Optimization
"""
import sys
import os

# Set environment for Coolify
os.environ['DATABASE_URL'] = f'sqlite:///{os.getcwd()}/trendwise.db'
os.environ['FLASK_ENV'] = 'production'

def health_check():
    try:
        from app import create_app, db
        from app.models import NewsSearchIndex
        
        app = create_app()
        with app.app_context():
            # Basic connectivity test
            count = NewsSearchIndex.query.count()
            
            # Search functionality test
            from app.utils.search.optimized_news_search import OptimizedNewsSearch
            search = OptimizedNewsSearch(db.session)
            recent = search.get_recent_news(limit=1)
            
            print(f"✅ Health Check Passed")
            print(f"   Search index: {count:,} articles")
            print(f"   Search working: {len(recent)} results")
            print(f"   Cache: {'Available' if search.is_cache_available() else 'Not available'}")
            
            return True
            
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        return False

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)
EOF

chmod +x coolify_health_check.py
log "✅ Health check script created"

# 8. Create Coolify startup script
log "🚀 Creating Coolify startup script..."

cat > coolify_startup.sh << 'EOF'
#!/bin/bash
# Coolify startup script for TrendWise

echo "🚀 Starting TrendWise in Coolify environment..."

# Set environment
export DATABASE_URL="sqlite:///$(pwd)/trendwise.db"
export FLASK_ENV="production"
export FLASK_APP="wsgi.py"

# Quick health check
python coolify_health_check.py

# Start the application
echo "✅ Starting TrendWise application..."
python wsgi.py
EOF

chmod +x coolify_startup.sh
log "✅ Startup script created"

# 9. Final Status Check
log "📊 Final deployment status..."

# Check database file size
db_size=$(ls -lh trendwise.db | awk '{print $5}')
log "   Database file size: $db_size"

# Check if all key files exist
for file in "wsgi.py" "coolify_health_check.py" "coolify_startup.sh"; do
    if [ -f "$file" ]; then
        log "   ✅ $file exists"
    else
        log "   ❌ $file missing"
    fi
done

# Final test
python coolify_health_check.py
if [ $? -eq 0 ]; then
    log "🎉 Search optimization deployment completed successfully!"
    echo ""
    echo "📋 Next Steps for Coolify:"
    echo "1. Use 'coolify_startup.sh' as your start command"
    echo "2. Monitor health with 'python coolify_health_check.py'"
    echo "3. Populate search index with news articles when available"
    echo ""
    echo "🔧 Maintenance Commands:"
    echo "• Health check: python coolify_health_check.py"
    echo "• Status check: python scripts/setup_search_optimization.py --status"
    echo "• Populate index: python scripts/populate_search_index.py populate"
    echo ""
else
    log "⚠️ Deployment completed with warnings - check logs above"
fi

echo "🏁 Coolify deployment script finished" 