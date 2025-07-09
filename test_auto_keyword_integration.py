#!/usr/bin/env python3
"""
Test script to verify automatic keyword extraction integration
"""

import os
import sys
import logging

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.models import db
from app.utils.keywords.auto_keyword_extraction import AutoKeywordExtractor
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_auto_keyword_extraction():
    """Test the automatic keyword extraction service"""
    
    logger.info("🧪 Testing automatic keyword extraction integration...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Find an article from the buffer table (news_articles) with AI content
            article_query = text("""
                SELECT id, title, ai_summary, ai_insights 
                FROM news_articles 
                WHERE ai_summary IS NOT NULL 
                AND ai_insights IS NOT NULL 
                AND ai_summary != '' 
                AND ai_insights != ''
                LIMIT 1
            """)
            
            result = db.session.execute(article_query)
            article = result.fetchone()
            
            if not article:
                logger.info("❌ No articles with AI content found in buffer table")
                logger.info("💡 Run news fetching and AI processing first")
                return
                
            article_id = article[0]
            logger.info(f"📰 Testing with article ID: {article_id}")
            logger.info(f"📝 Title: {article[1][:80]}...")
            
            # Test the auto keyword extraction
            extractor = AutoKeywordExtractor()
            result = extractor.extract_keywords_for_article(article_id)
            
            # Display results
            if result['success']:
                logger.info(f"✅ Extraction successful: {result['message']}")
                logger.info(f"🔑 Keywords extracted: {result['keywords_extracted']}")
                
                # Check what keywords were extracted
                keywords_query = text("""
                    SELECT nk.keyword, nk.category, ak.relevance_score
                    FROM article_keywords ak
                    JOIN news_keywords nk ON ak.keyword_id = nk.id
                    WHERE ak.article_id = :article_id
                    ORDER BY ak.relevance_score DESC
                    LIMIT 10
                """)
                
                keywords_result = db.session.execute(keywords_query, {'article_id': article_id})
                keywords = keywords_result.fetchall()
                
                if keywords:
                    logger.info("🔍 Top keywords extracted:")
                    for keyword in keywords:
                        logger.info(f"   • {keyword[0]} ({keyword[1]}) - Score: {keyword[2]:.2f}")
                else:
                    logger.info("❌ No keywords found in database")
                    
            else:
                logger.error(f"❌ Extraction failed: {result['message']}")
                
        except Exception as e:
            logger.error(f"❌ Error in test: {str(e)}")
            
def check_integration_status():
    """Check if the integration is working correctly"""
    
    logger.info("🔍 Checking automatic keyword extraction integration status...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if keyword tables exist
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name IN ('news_keywords', 'article_keywords', 'keyword_similarities', 'search_analytics')
            """)
            
            tables_result = db.session.execute(tables_query)
            tables = [row[0] for row in tables_result.fetchall()]
            
            logger.info(f"✅ Found {len(tables)} keyword tables: {', '.join(tables)}")
            
            # Check total keywords in system
            total_keywords_query = text("SELECT COUNT(*) FROM news_keywords")
            total_keywords = db.session.execute(total_keywords_query).scalar()
            
            # Check total article-keyword relationships
            total_relationships_query = text("SELECT COUNT(*) FROM article_keywords")
            total_relationships = db.session.execute(total_relationships_query).scalar()
            
            # Check articles with AI content in buffer
            ai_articles_query = text("""
                SELECT COUNT(*) 
                FROM news_articles 
                WHERE ai_summary IS NOT NULL 
                AND ai_insights IS NOT NULL
            """)
            ai_articles = db.session.execute(ai_articles_query).scalar()
            
            logger.info(f"📊 System status:")
            logger.info(f"   🔑 Total keywords: {total_keywords}")
            logger.info(f"   🔗 Total relationships: {total_relationships}")
            logger.info(f"   🤖 Articles with AI content: {ai_articles}")
            
            # Check if any articles have keywords
            articles_with_keywords_query = text("""
                SELECT COUNT(DISTINCT article_id) 
                FROM article_keywords
            """)
            articles_with_keywords = db.session.execute(articles_with_keywords_query).scalar()
            
            logger.info(f"   📰 Articles with keywords: {articles_with_keywords}")
            
            if total_keywords > 0 and total_relationships > 0:
                logger.info("✅ Integration appears to be working correctly!")
            else:
                logger.info("⚠️ Integration needs testing - no keywords found yet")
                
        except Exception as e:
            logger.error(f"❌ Error checking integration status: {str(e)}")

if __name__ == "__main__":
    logger.info("🚀 Starting automatic keyword extraction integration test")
    
    # Check current status
    check_integration_status()
    
    # Test the extraction
    test_auto_keyword_extraction()
    
    logger.info("✅ Integration test completed") 