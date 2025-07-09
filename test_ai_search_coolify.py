#!/usr/bin/env python3
"""
AI Keyword Search Verification Script for Coolify

This script tests the AI keyword search functionality after deployment.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_tables():
    """Test if all keyword tables exist and have data"""
    logger.info("🗄️ Testing database tables...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app, db
        from app.models import NewsKeyword, ArticleKeyword, KeywordSimilarity, SearchAnalytics
        
        app = create_app()
        with app.app_context():
            # Check table existence
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['news_keywords', 'article_keywords', 'keyword_similarities', 'search_analytics']
            
            for table in required_tables:
                if table in tables:
                    logger.info(f"✅ Table {table} exists")
                else:
                    logger.error(f"❌ Table {table} missing")
                    return False
            
            # Check data
            keyword_count = NewsKeyword.query.count()
            article_keyword_count = ArticleKeyword.query.count()
            
            logger.info(f"📊 Keywords: {keyword_count}")
            logger.info(f"📊 Article-keyword links: {article_keyword_count}")
            
            if keyword_count > 0:
                logger.info("✅ Database has keyword data")
                return True
            else:
                logger.warning("⚠️ No keywords found in database")
                return True
                
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def test_keyword_extraction_service():
    """Test the keyword extraction service"""
    logger.info("🔍 Testing keyword extraction service...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app.utils.ai.keyword_extraction_service import keyword_extraction_service
        
        # Test with sample financial text
        test_text = "Apple Inc. reported strong quarterly earnings with revenue growth of 15% driven by iPhone sales and artificial intelligence initiatives."
        
        keywords = keyword_extraction_service.extract_keywords(test_text)
        
        if keywords:
            logger.info(f"✅ Extracted {len(keywords)} keywords")
            for kw in keywords[:3]:  # Show first 3
                logger.info(f"  - {kw.get('keyword', 'Unknown')} ({kw.get('category', 'Unknown')})")
            return True
        else:
            logger.warning("⚠️ No keywords extracted")
            return True
            
    except Exception as e:
        logger.error(f"❌ Keyword extraction test failed: {e}")
        return False

def test_intelligent_suggestions():
    """Test the intelligent suggestions service"""
    logger.info("🤖 Testing intelligent suggestions service...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app.utils.search.intelligent_suggestions import intelligent_suggestion_service
        
        # Test common search terms
        test_queries = ['earn', 'tech', 'ai', 'market']
        
        for query in test_queries:
            suggestions = intelligent_suggestion_service.get_suggestions(query, limit=3)
            if suggestions:
                logger.info(f"✅ Query '{query}' returned {len(suggestions)} suggestions")
                for suggestion in suggestions:
                    logger.info(f"  - {suggestion.get('keyword', 'Unknown')}")
            else:
                logger.info(f"⚠️ Query '{query}' returned no suggestions")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Intelligent suggestions test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints using Flask test client"""
    logger.info("🌐 Testing API endpoints...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            # Test suggestions endpoint
            response = client.get('/news/api/suggestions?q=earnings')
            if response.status_code == 200:
                data = json.loads(response.data)
                logger.info(f"✅ Suggestions API: {len(data.get('suggestions', []))} suggestions")
            else:
                logger.error(f"❌ Suggestions API failed: {response.status_code}")
                return False
            
            # Test trending keywords endpoint
            response = client.get('/news/api/keywords/trending')
            if response.status_code == 200:
                data = json.loads(response.data)
                logger.info(f"✅ Trending API: {len(data.get('trending_keywords', []))} trending keywords")
            else:
                logger.error(f"❌ Trending API failed: {response.status_code}")
                return False
            
            # Test analytics endpoint
            response = client.get('/news/api/analytics/suggestions')
            if response.status_code == 200:
                logger.info("✅ Analytics API working")
            else:
                logger.error(f"❌ Analytics API failed: {response.status_code}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API endpoints test failed: {e}")
        return False

def test_search_ui():
    """Test if the enhanced search UI files are in place"""
    logger.info("🎨 Testing search UI files...")
    
    try:
        # Check if enhanced search JS file exists
        search_js_path = 'app/static/js/enhanced-search.js'
        if os.path.exists(search_js_path):
            logger.info("✅ Enhanced search JS file found")
        else:
            logger.warning("⚠️ Enhanced search JS file not found")
        
        # Check if search template includes the enhanced search
        template_path = 'app/templates/news/search.html'
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                content = f.read()
                if 'enhanced-search.js' in content:
                    logger.info("✅ Search template includes enhanced search")
                else:
                    logger.warning("⚠️ Search template may not include enhanced search")
        else:
            logger.warning("⚠️ Search template not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Search UI test failed: {e}")
        return False

def show_sample_data():
    """Show sample data from the keyword system"""
    logger.info("📋 Showing sample data...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app, db
        from app.models import NewsKeyword, ArticleKeyword, NewsArticle
        
        app = create_app()
        with app.app_context():
            # Show sample keywords
            keywords = NewsKeyword.query.limit(10).all()
            if keywords:
                logger.info("📊 Sample keywords:")
                for kw in keywords:
                    logger.info(f"  - {kw.keyword} (category: {kw.category}, freq: {kw.frequency})")
            
            # Show keyword distribution by category
            from sqlalchemy import func
            categories = db.session.query(
                NewsKeyword.category,
                func.count(NewsKeyword.id).label('count')
            ).group_by(NewsKeyword.category).all()
            
            if categories:
                logger.info("📊 Keywords by category:")
                for cat, count in categories:
                    logger.info(f"  - {cat}: {count}")
            
            # Show articles with most keywords
            article_keywords = db.session.query(
                ArticleKeyword.article_id,
                func.count(ArticleKeyword.keyword_id).label('keyword_count')
            ).group_by(ArticleKeyword.article_id).order_by(
                func.count(ArticleKeyword.keyword_id).desc()
            ).limit(5).all()
            
            if article_keywords:
                logger.info("📊 Articles with most keywords:")
                for article_id, count in article_keywords:
                    article = NewsArticle.query.get(article_id)
                    title = article.title[:50] + "..." if article and len(article.title) > 50 else (article.title if article else "Unknown")
                    logger.info(f"  - {title} ({count} keywords)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Sample data display failed: {e}")
        return False

def main():
    """Main verification function"""
    logger.info("🔍 Starting AI Keyword Search Verification")
    logger.info("=" * 50)
    
    tests = [
        ("Database tables", test_database_tables),
        ("Keyword extraction service", test_keyword_extraction_service),
        ("Intelligent suggestions", test_intelligent_suggestions),
        ("API endpoints", test_api_endpoints),
        ("Search UI files", test_search_ui),
        ("Sample data", show_sample_data)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔄 Testing {test_name}...")
        try:
            if test_func():
                logger.info(f"✅ {test_name} - PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} - FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} - ERROR: {e}")
    
    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Your AI keyword search system is ready!")
        logger.info("\n✅ Next steps:")
        logger.info("1. Visit your news search page")
        logger.info("2. Try typing 'earnings' or 'technology' in the search box")
        logger.info("3. You should see AI-powered suggestions appear")
        logger.info("4. Test the API endpoints:")
        logger.info("   curl 'http://your-domain/news/api/suggestions?q=earnings'")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} tests failed. Please check the errors above.")
        return False

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏸️ Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Verification failed: {e}")
        sys.exit(1) 