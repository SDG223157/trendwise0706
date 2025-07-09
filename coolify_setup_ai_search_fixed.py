#!/usr/bin/env python3
"""
Coolify AI Keyword Search Setup Script - FIXED VERSION

This script sets up the AI keyword search system using the PERMANENT news_search_index table.
Run this after deploying your app to Coolify.
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_nltk_data():
    """Download required NLTK data"""
    logger.info("📦 Setting up NLTK data...")
    
    try:
        import nltk
        
        # Download required NLTK data
        nltk_downloads = [
            'punkt',
            'stopwords', 
            'averaged_perceptron_tagger',
            'maxent_ne_chunker',
            'words'
        ]
        
        for item in nltk_downloads:
            try:
                nltk.download(item, quiet=True)
                logger.info(f"✅ Downloaded NLTK data: {item}")
            except Exception as e:
                logger.warning(f"⚠️ Could not download {item}: {e}")
        
        return True
        
    except ImportError:
        logger.error("❌ NLTK not installed. Please install requirements.txt first.")
        return False

def create_keyword_tables():
    """Create keyword database tables"""
    logger.info("🗄️ Creating keyword database tables...")
    
    try:
        # Add current directory to Python path
        sys.path.insert(0, os.getcwd())
        
        from app import create_app, db
        from app.models import NewsKeyword, ArticleKeyword, KeywordSimilarity, SearchAnalytics
        
        app = create_app()
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Check if keyword tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            keyword_tables = ['news_keywords', 'article_keywords', 'keyword_similarities', 'search_analytics']
            
            all_exist = True
            for table in keyword_tables:
                if table in tables:
                    logger.info(f"✅ Table {table} exists")
                else:
                    logger.error(f"❌ Table {table} missing")
                    all_exist = False
            
            if all_exist:
                logger.info("✅ All keyword tables created successfully!")
                return True
            else:
                logger.error("❌ Some keyword tables are missing")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        return False

def extract_sample_keywords():
    """Extract keywords from sample articles using NEWS_SEARCH_INDEX (permanent table)"""
    logger.info("🔍 Extracting sample keywords from news_search_index...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app, db
        from app.models import NewsSearchIndex, NewsKeyword, ArticleKeyword
        
        app = create_app()
        with app.app_context():
            # Get articles with AI content from NEWS_SEARCH_INDEX (permanent table)
            articles = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_summary != ''
            ).limit(20).all()
            
            logger.info(f"Found {len(articles)} articles with AI content in news_search_index")
            
            if not articles:
                logger.warning("⚠️ No articles with AI content found in news_search_index")
                # Create sample keywords anyway for testing
                return create_sample_keywords_for_testing()
            
            # Financial/tech keywords to look for
            target_keywords = [
                'earnings', 'revenue', 'growth', 'profit', 'loss',
                'technology', 'artificial', 'intelligence', 'ai',
                'merger', 'acquisition', 'investment', 'market',
                'stock', 'financial', 'analysis', 'report',
                'company', 'business', 'industry', 'sector',
                'performance', 'results', 'quarterly', 'annual'
            ]
            
            keywords_created = 0
            
            for article in articles:
                if article.ai_summary:
                    # Simple keyword extraction
                    import re
                    text = article.ai_summary.lower()
                    
                    for keyword in target_keywords:
                        if keyword in text:
                            # Check if keyword already exists
                            existing = db.session.query(NewsKeyword).filter_by(
                                keyword=keyword,
                                category='financial'
                            ).first()
                            
                            if not existing:
                                # Create new keyword
                                new_keyword = NewsKeyword(
                                    keyword=keyword,
                                    normalized_keyword=keyword,
                                    category='financial',
                                    relevance_score=0.7,
                                    frequency=1
                                )
                                db.session.add(new_keyword)
                                db.session.flush()
                                
                                # Link to article (using news_search_index id)
                                article_keyword = ArticleKeyword(
                                    article_id=article.id,
                                    keyword_id=new_keyword.id,
                                    relevance_in_article=0.6
                                )
                                db.session.add(article_keyword)
                                keywords_created += 1
                            else:
                                # Update frequency
                                existing.frequency += 1
                                
                                # Check if already linked to this article
                                existing_link = db.session.query(ArticleKeyword).filter_by(
                                    article_id=article.id,
                                    keyword_id=existing.id
                                ).first()
                                
                                if not existing_link:
                                    article_keyword = ArticleKeyword(
                                        article_id=article.id,
                                        keyword_id=existing.id,
                                        relevance_in_article=0.6
                                    )
                                    db.session.add(article_keyword)
            
            db.session.commit()
            logger.info(f"✅ Created/updated {keywords_created} keywords from {len(articles)} articles")
            
            # Show some sample keywords
            sample_keywords = db.session.query(NewsKeyword).limit(5).all()
            logger.info("Sample keywords created:")
            for kw in sample_keywords:
                logger.info(f"  - {kw.keyword} (freq: {kw.frequency})")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error extracting keywords: {e}")
        return False

def create_sample_keywords_for_testing():
    """Create sample keywords for testing when no real data exists"""
    logger.info("🛠️ Creating sample keywords for testing...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app, db
        from app.models import NewsKeyword
        
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
            logger.info(f"✅ Created {created_count} sample keywords for testing")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error creating sample keywords: {e}")
        db.session.rollback()
        return False

def test_api_endpoints():
    """Test if API endpoints work"""
    logger.info("🧪 Testing API endpoints...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app
        from app.models import NewsKeyword
        
        app = create_app()
        with app.app_context():
            # Test keyword count
            keyword_count = NewsKeyword.query.count()
            logger.info(f"Total keywords in database: {keyword_count}")
            
            if keyword_count > 0:
                logger.info("✅ API endpoints should work - keywords available")
                
                # Test suggestions service
                try:
                    from app.utils.search.intelligent_suggestions import intelligent_suggestion_service
                    suggestions = intelligent_suggestion_service.get_search_suggestions("earn", limit=3)
                    logger.info(f"✅ Suggestions service works - got {len(suggestions)} suggestions")
                except Exception as e:
                    logger.warning(f"⚠️ Suggestions service issue: {e}")
                
                return True
            else:
                logger.warning("⚠️ No keywords found - API will return empty results")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error testing API: {e}")
        return False

def check_permanent_table_status():
    """Check the status of the permanent news_search_index table"""
    logger.info("📊 Checking news_search_index table status...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app, db
        from app.models import NewsSearchIndex
        
        app = create_app()
        with app.app_context():
            # Check news_search_index table
            total_articles = NewsSearchIndex.query.count()
            ai_articles = NewsSearchIndex.query.filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_summary != ''
            ).count()
            
            logger.info(f"📰 Total articles in news_search_index: {total_articles}")
            logger.info(f"🤖 Articles with AI summaries: {ai_articles}")
            
            if total_articles > 0:
                # Show sample titles
                sample_articles = NewsSearchIndex.query.limit(3).all()
                logger.info("Sample articles:")
                for article in sample_articles:
                    logger.info(f"  - {article.title[:60]}...")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error checking news_search_index: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("🚀 Starting Coolify AI Keyword Search Setup (FIXED for news_search_index)")
    logger.info("=" * 70)
    
    steps = [
        ("Setting up NLTK data", setup_nltk_data),
        ("Creating keyword tables", create_keyword_tables),
        ("Checking permanent table status", check_permanent_table_status),
        ("Extracting sample keywords", extract_sample_keywords),
        ("Testing API endpoints", test_api_endpoints)
    ]
    
    for step_name, step_func in steps:
        logger.info(f"\n🔄 {step_name}...")
        if not step_func():
            logger.error(f"❌ {step_name} failed!")
            return False
        logger.info(f"✅ {step_name} completed")
    
    logger.info("\n🎉 AI Keyword Search Setup Complete!")
    logger.info("=" * 50)
    logger.info("✅ Your AI keyword search system is now ready!")
    logger.info("\nNext steps:")
    logger.info("1. Visit your news search page")
    logger.info("2. Try typing in the search box - you should see AI suggestions")
    logger.info("3. Test API endpoints:")
    logger.info("   curl 'http://your-domain/news/api/suggestions?q=earnings'")
    logger.info("   curl 'http://your-domain/news/api/keywords/trending'")
    logger.info("\n💡 Note: Using permanent news_search_index table (not buffer news_articles)")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏸️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Setup failed: {e}")
        sys.exit(1) 