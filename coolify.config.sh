#!/bin/bash
# Coolify Configuration for TrendWise Search Optimization
# Optimized for Python 3.9.23 environment

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

# Database Configuration - Use Coolify database
# DATABASE_URL should be set by Coolify automatically
export FLASK_ENV="production"
export FLASK_APP="wsgi.py"

# Note: DATABASE_URL will be set by Coolify based on your database service
# Common formats:
# PostgreSQL: postgresql://user:password@host:port/database
# MySQL: mysql+pymysql://user:password@host:port/database

# Python path
export PYTHONPATH="$(pwd):$PYTHONPATH"

# =============================================================================
# COOLIFY DEPLOYMENT COMMANDS
# =============================================================================

# For Coolify Build Command (optional):
# pip install -r requirements.txt

# For Coolify Start Command (choose one):

# Option 1: Full deployment with search optimization
# bash scripts/coolify_deploy_search_optimization.sh && python wsgi.py

# Option 2: Quick setup then start
# bash scripts/coolify_quick_setup.sh && python wsgi.py

# Option 3: Simple start (if already configured)
# python wsgi.py

# =============================================================================
# COOLIFY HEALTHCHECK COMMANDS
# =============================================================================

# Health check endpoint (use in Coolify health check URL):
# GET /health

# Or use the dedicated health check script:
# python coolify_health_check.py

# =============================================================================
# MAINTENANCE COMMANDS FOR COOLIFY TERMINAL
# =============================================================================

# Quick system status:
# python scripts/setup_search_optimization.py --status

# Health check:
# python coolify_health_check.py

# Populate search index:
# python scripts/populate_search_index.py populate

# Sync search index:
# python scripts/populate_search_index.py sync

# =============================================================================
# TROUBLESHOOTING COMMANDS
# =============================================================================

# If you see MySQL errors, run:
# bash scripts/coolify_quick_setup.sh

# Check database file:
# ls -la trendwise.db

# Check Python environment:
# python -c "import sys; print(sys.version); import flask, sqlalchemy; print('Flask/SQLAlchemy OK')"

# Test database connection:
# python -c "
# import os
# os.environ['DATABASE_URL'] = 'sqlite:///$(pwd)/trendwise.db'
# from app import create_app, db
# app = create_app()
# with app.app_context():
#     from app.models import NewsArticle
#     print(f'Articles: {NewsArticle.query.count()}')
# "

# =============================================================================
# RECOMMENDED COOLIFY SETTINGS
# =============================================================================

# Build Command:
# pip install -r requirements.txt

# Start Command:
# bash scripts/coolify_deploy_search_optimization.sh && python wsgi.py

# Health Check Path:
# /health

# Port:
# 5000 (or whatever your Flask app uses)

# Environment Variables to set in Coolify:
# DATABASE_URL=(automatically set by Coolify database service)
# FLASK_ENV=production
# FLASK_APP=wsgi.py

echo "📋 Coolify Configuration Loaded"
echo "🚀 To deploy: Use the commands above in your Coolify settings"
echo "🔧 For quick setup: bash scripts/coolify_quick_setup.sh"
echo "💡 For full deployment: bash scripts/coolify_deploy_search_optimization.sh" 