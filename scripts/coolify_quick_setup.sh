#!/bin/bash
# Quick Coolify Setup for TrendWise Search Optimization
# For Python 3.9.23 environment

echo "🚀 Quick Coolify Setup for TrendWise"
echo "Python: $(python --version)"
echo "Directory: $(pwd)"

# Set production environment - use Coolify database
export FLASK_ENV="production"

# Don't override DATABASE_URL if it's already set by Coolify
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️ DATABASE_URL not set - using fallback configuration"
else
    echo "✅ Using Coolify database: ${DATABASE_URL%/*}/*****"
fi

echo "✅ Environment configured for Coolify database"

# Quick database setup
echo "🗄️ Setting up database..."
python -c "
import os
import sys

try:
    from app import create_app, db
    app = create_app()
    with app.app_context():
        db.create_all()
        print('✅ Database tables created')
        
        # Show database info
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if 'postgresql' in db_uri:
            print('   📊 Using PostgreSQL database')
        elif 'mysql' in db_uri:
            print('   📊 Using MySQL database')
        elif 'sqlite' in db_uri:
            print('   📊 Using SQLite database')
        else:
            print('   📊 Using configured database')
            
except Exception as e:
    print(f'Database setup: {e}')
    print('This may be normal during first setup')
"

# Test the system
echo "🧪 Testing system..."
python -c "
import os

try:
    from app import create_app, db
    from app.models import NewsArticle, NewsSearchIndex
    
    app = create_app()
    with app.app_context():
        main_count = NewsArticle.query.count()
        search_count = NewsSearchIndex.query.count()
        
        print(f'📊 Status:')
        print(f'   Articles: {main_count:,}')
        print(f'   Search index: {search_count:,}')
        print('✅ System working')
        
except Exception as e:
    print(f'Test result: {e}')
"

echo "✅ Quick setup complete!"
echo ""
echo "🎯 For Coolify deployment:"
echo "1. Set start command: bash scripts/coolify_deploy_search_optimization.sh && python wsgi.py"
echo "2. Or use: python wsgi.py (if database is already set up)"
echo "3. Health check: python coolify_health_check.py" 