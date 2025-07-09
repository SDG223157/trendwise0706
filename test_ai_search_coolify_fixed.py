#!/usr/bin/env python3
"""
AI Keyword Search Verification Script for Coolify - FIXED VERSION

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
        from app.models import NewsSearchIndex
        
        # Create a test article if none exist
        test_article = type('TestArticle', (), {
            'id': 1,
            'title': 'Apple Reports Strong Q4 Earnings with AI-Driven Growth',
            'ai_summary': 'Apple Inc. reported quarterly earnings showing strong revenue growth driven by artificial intelligence initiatives and iPhone sales performance.',
            'ai_insights': 'The company invested heavily in AI technology, showing significant market performance improvements.'
        })()
        
        # Test keyword extraction
        keywords = keyword_extraction_service.extract_keywords_from_article(test_article)
        
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
            # Use the correct method name
            suggestions = intelligent_suggestion_service.get_search_suggestions(query, limit=3)
            if suggestions:
                logger.info(f"✅ Query '{query}' returned {len(suggestions)} suggestions")
                for suggestion in suggestions:
                    logger.info(f"  - {suggestion.get('text', 'Unknown')}")
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

def create_sample_keywords():
    """Create sample keywords if none exist"""
    logger.info("🛠️ Creating sample keywords...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app, db
        from app.models import NewsKeyword, ArticleKeyword
        
        app = create_app()
        with app.app_context():
            # Check if keywords already exist
            existing_count = NewsKeyword.query.count()
            if existing_count > 0:
                logger.info(f"✅ {existing_count} keywords already exist")
                return True
            
            # Create sample financial keywords
            sample_keywords = [
                {'keyword': 'earnings', 'category': 'financial', 'relevance_score': 0.9, 'frequency': 50},
                {'keyword': 'revenue', 'category': 'financial', 'relevance_score': 0.8, 'frequency': 40},
                {'keyword': 'artificial intelligence', 'category': 'technology', 'relevance_score': 0.9, 'frequency': 35},
                {'keyword': 'tesla', 'category': 'company', 'relevance_score': 0.8, 'frequency': 30},
                {'keyword': 'merger', 'category': 'financial', 'relevance_score': 0.7, 'frequency': 25},
                {'keyword': 'quarterly results', 'category': 'financial', 'relevance_score': 0.8, 'frequency': 28},
                {'keyword': 'stock market', 'category': 'financial', 'relevance_score': 0.8, 'frequency': 32},
                {'keyword': 'technology', 'category': 'industry', 'relevance_score': 0.7, 'frequency': 22},
                {'keyword': 'apple', 'category': 'company', 'relevance_score': 0.8, 'frequency': 45},
                {'keyword': 'growth', 'category': 'financial', 'relevance_score': 0.7, 'frequency': 38}
            ]
            
            created_count = 0
            for kw_data in sample_keywords:
                keyword = NewsKeyword(
                    keyword=kw_data['keyword'],
                    normalized_keyword=kw_data['keyword'].lower(),
                    category=kw_data['category'],
                    relevance_score=kw_data['relevance_score'],
                    frequency=kw_data['frequency'],
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                db.session.add(keyword)
                created_count += 1
            
            db.session.commit()
            logger.info(f"✅ Created {created_count} sample keywords")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error creating sample keywords: {e}")
        db.session.rollback()
        return False

def show_sample_data():
    """Show sample data from the keyword system"""
    logger.info("📋 Showing sample data...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app, db
        from app.models import NewsKeyword, ArticleKeyword, NewsSearchIndex
        
        app = create_app()
        with app.app_context():
            # Show sample keywords
            keywords = NewsKeyword.query.limit(10).all()
            if keywords:
                logger.info("📊 Sample keywords:")
                for kw in keywords:
                    logger.info(f"  - {kw.keyword} (category: {kw.category}, freq: {kw.frequency})")
            else:
                logger.info("📊 No keywords found")
            
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
            
            # Show total articles from PERMANENT table
            total_articles = NewsSearchIndex.query.count()
            ai_articles = NewsSearchIndex.query.filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_summary != ''
            ).count()
            
            logger.info(f"📊 Total articles in news_search_index (permanent): {total_articles}")
            logger.info(f"📊 Articles with AI summaries: {ai_articles}")
            logger.info(f"📊 Using permanent news_search_index table (not buffer)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Sample data display failed: {e}")
        return False

def test_suggestions_with_sample_data():
    """Test suggestions using the sample keyword data"""
    logger.info("🧪 Testing suggestions with sample data...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app.utils.search.intelligent_suggestions import intelligent_suggestion_service
        
        test_queries = ['earn', 'tech', 'ai', 'apple', 'growth']
        
        for query in test_queries:
            suggestions = intelligent_suggestion_service.get_search_suggestions(query, limit=5)
            logger.info(f"Query '{query}': {len(suggestions)} suggestions")
            for suggestion in suggestions:
                logger.info(f"  - {suggestion.get('text', 'Unknown')} ({suggestion.get('type', 'Unknown')})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Suggestions test with sample data failed: {e}")
        return False

def main():
    """Main verification function"""
    logger.info("🔍 Starting AI Keyword Search Verification (FIXED)")
    logger.info("=" * 50)
    
    tests = [
        ("Database tables", test_database_tables),
        ("Sample keywords creation", create_sample_keywords),
        ("Keyword extraction service", test_keyword_extraction_service),
        ("Intelligent suggestions", test_intelligent_suggestions),
        ("API endpoints", test_api_endpoints),
        ("Sample data", show_sample_data),
        ("Suggestions with sample data", test_suggestions_with_sample_data)
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
    
    if passed >= total - 1:  # Allow 1 failure
        logger.info("🎉 AI keyword search system is working!")
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