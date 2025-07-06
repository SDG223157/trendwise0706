#!/usr/bin/env python3
"""
Coolify-specific health check for TrendWise Search Optimization
"""
import sys
import os

# Set environment for Coolify
os.environ['FLASK_ENV'] = 'production'
# Don't override DATABASE_URL if it's already set by Coolify

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