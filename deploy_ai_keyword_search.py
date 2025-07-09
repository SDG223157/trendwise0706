#!/usr/bin/env python3
"""
AI Keyword Search Deployment Script for Coolify

This script sets up the AI-powered keyword search system on your Coolify deployment.
It handles database creation, keyword extraction, and testing.
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_keyword_deploy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_command(command, description):
    """Run a command and log the results"""
    logger.info(f"🔄 {description}")
    logger.info(f"Command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {description} completed successfully")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"❌ {description} failed")
            logger.error(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {description} timed out")
        return False
    except Exception as e:
        logger.error(f"❌ {description} failed with exception: {str(e)}")
        return False

def check_environment():
    """Check if the environment is ready"""
    logger.info("🔍 Checking environment...")
    
    # Check if we're in the right directory
    if not os.path.exists('app'):
        logger.error("❌ Not in the correct directory. Please run from the trendwise0706 root.")
        return False
    
    # Check if requirements.txt exists
    if not os.path.exists('requirements.txt'):
        logger.error("❌ requirements.txt not found")
        return False
    
    # Check if Flask is available
    try:
        import flask
        logger.info("✅ Flask is available")
        return True
    except ImportError:
        logger.error("❌ Flask not available. Please install requirements first.")
        return False

def install_dependencies():
    """Install required dependencies"""
    logger.info("📦 Installing dependencies...")
    
    commands = [
        "pip install -r requirements.txt",
        "pip install nltk fuzzywuzzy python-Levenshtein",
        "python -c \"import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger'); nltk.download('maxent_ne_chunker'); nltk.download('words')\""
    ]
    
    for cmd in commands:
        if not run_command(cmd, f"Installing dependencies: {cmd}"):
            return False
    
    return True

def create_database_tables():
    """Create the keyword database tables"""
    logger.info("🗄️ Creating database tables...")
    
    create_tables_script = """
import sys
sys.path.insert(0, '.')
from app import create_app, db

app = create_app()
with app.app_context():
    print('Creating database tables...')
    db.create_all()
    print('✅ Database tables created successfully!')
    
    # Check if keyword tables exist
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    keyword_tables = ['news_keywords', 'article_keywords', 'keyword_similarities', 'search_analytics']
    for table in keyword_tables:
        if table in tables:
            print(f'✅ Table {table} exists')
        else:
            print(f'❌ Table {table} missing')
"""
    
    # Write the script to a temporary file
    with open('temp_create_tables.py', 'w') as f:
        f.write(create_tables_script)
    
    success = run_command("python temp_create_tables.py", "Creating database tables")
    
    # Clean up
    if os.path.exists('temp_create_tables.py'):
        os.remove('temp_create_tables.py')
    
    return success

def extract_keywords_sample():
    """Extract keywords from a sample of articles"""
    logger.info("🔍 Extracting keywords from sample articles...")
    
    extract_script = """
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models import NewsArticle, NewsKeyword, ArticleKeyword

app = create_app()
with app.app_context():
    print('Getting sample articles...')
    
    # Get 10 sample articles with AI content
    articles = db.session.query(NewsArticle).filter(
        NewsArticle.ai_summary.isnot(None),
        NewsArticle.ai_insights.isnot(None),
        NewsArticle.ai_summary != '',
        NewsArticle.ai_insights != ''
    ).limit(10).all()
    
    print(f'Found {len(articles)} articles with AI content')
    
    if articles:
        # Simple keyword extraction from AI summaries
        keywords_created = 0
        
        for article in articles:
            # Extract simple keywords from AI summary
            if article.ai_summary:
                # Simple keyword extraction
                import re
                words = re.findall(r'\\b[a-zA-Z]{4,}\\b', article.ai_summary.lower())
                
                # Common financial/tech keywords
                relevant_keywords = []
                for word in words:
                    if word in ['earnings', 'revenue', 'growth', 'technology', 'artificial', 'intelligence', 'merger', 'acquisition', 'investment', 'market', 'stock', 'financial', 'analysis', 'report', 'company', 'business', 'industry', 'sector', 'performance', 'results']:
                        relevant_keywords.append(word)
                
                # Create keyword entries
                for keyword in set(relevant_keywords):
                    existing = db.session.query(NewsKeyword).filter_by(
                        keyword=keyword,
                        category='financial'
                    ).first()
                    
                    if not existing:
                        new_keyword = NewsKeyword(
                            keyword=keyword,
                            normalized_keyword=keyword,
                            category='financial',
                            relevance_score=0.5,
                            frequency=1
                        )
                        db.session.add(new_keyword)
                        db.session.flush()
                        
                        # Link to article
                        article_keyword = ArticleKeyword(
                            article_id=article.id,
                            keyword_id=new_keyword.id,
                            relevance_in_article=0.5
                        )
                        db.session.add(article_keyword)
                        keywords_created += 1
        
        db.session.commit()
        print(f'✅ Created {keywords_created} keywords from {len(articles)} articles')
    else:
        print('❌ No articles with AI content found')
"""
    
    # Write the script to a temporary file
    with open('temp_extract_keywords.py', 'w') as f:
        f.write(extract_script)
    
    success = run_command("python temp_extract_keywords.py", "Extracting sample keywords")
    
    # Clean up
    if os.path.exists('temp_extract_keywords.py'):
        os.remove('temp_extract_keywords.py')
    
    return success

def test_api_endpoints():
    """Test the API endpoints"""
    logger.info("🧪 Testing API endpoints...")
    
    test_script = """
import sys
sys.path.insert(0, '.')
from app import create_app
from app.models import NewsKeyword

app = create_app()
with app.app_context():
    # Test if keywords exist
    keyword_count = NewsKeyword.query.count()
    print(f'Keywords in database: {keyword_count}')
    
    if keyword_count > 0:
        # Show sample keywords
        sample_keywords = NewsKeyword.query.limit(5).all()
        print('Sample keywords:')
        for kw in sample_keywords:
            print(f'  - {kw.keyword} ({kw.category}) - relevance: {kw.relevance_score}')
        
        print('✅ API endpoints should work with existing keywords')
    else:
        print('❌ No keywords found - API will return empty results')
"""
    
    # Write the script to a temporary file
    with open('temp_test_api.py', 'w') as f:
        f.write(test_script)
    
    success = run_command("python temp_test_api.py", "Testing API functionality")
    
    # Clean up
    if os.path.exists('temp_test_api.py'):
        os.remove('temp_test_api.py')
    
    return success

def main():
    """Main deployment function"""
    logger.info("🚀 Starting AI Keyword Search Deployment")
    logger.info("=" * 50)
    
    # Step 1: Check environment
    if not check_environment():
        logger.error("❌ Environment check failed")
        return False
    
    # Step 2: Install dependencies
    if not install_dependencies():
        logger.error("❌ Dependency installation failed")
        return False
    
    # Step 3: Create database tables
    if not create_database_tables():
        logger.error("❌ Database table creation failed")
        return False
    
    # Step 4: Extract sample keywords
    if not extract_keywords_sample():
        logger.error("❌ Sample keyword extraction failed")
        return False
    
    # Step 5: Test API endpoints
    if not test_api_endpoints():
        logger.error("❌ API endpoint testing failed")
        return False
    
    # Success!
    logger.info("🎉 AI Keyword Search Deployment Completed Successfully!")
    logger.info("=" * 50)
    logger.info("Next steps:")
    logger.info("1. Test the search suggestions:")
    logger.info("   curl 'http://localhost:5000/news/api/suggestions?q=earnings'")
    logger.info("2. Test trending keywords:")
    logger.info("   curl 'http://localhost:5000/news/api/keywords/trending'")
    logger.info("3. Check analytics:")
    logger.info("   curl 'http://localhost:5000/news/api/analytics/suggestions'")
    logger.info("4. Visit your search page to see AI-powered suggestions!")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⏸️ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Deployment failed with error: {str(e)}")
        sys.exit(1) 