#!/usr/bin/env python3
"""
Diagnose Verification Issue

This script will check if the 68 "waiting" articles are actually already 
in the search index but failing strict verification due to content differences.
"""

import logging
import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from Coolify environment variables"""
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')
    
    mysql_vars = {
        'host': os.getenv('MYSQL_HOST') or os.getenv('DB_HOST'),
        'port': os.getenv('MYSQL_PORT') or os.getenv('DB_PORT', '3306'),
        'database': os.getenv('MYSQL_DATABASE') or os.getenv('DB_NAME'),
        'user': os.getenv('MYSQL_USER') or os.getenv('DB_USER'),
        'password': os.getenv('MYSQL_PASSWORD') or os.getenv('DB_PASSWORD')
    }
    
    if all(mysql_vars.values()):
        return f"mysql+pymysql://{mysql_vars['user']}:{mysql_vars['password']}@{mysql_vars['host']}:{mysql_vars['port']}/{mysql_vars['database']}"
    
    raise ValueError("Could not determine database connection")

def diagnose_verification_issue():
    """Diagnose why articles appear to be waiting when they might be synced"""
    try:
        # Get database session
        database_url = get_database_url()
        engine = create_engine(database_url, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        logger.info("🔍 Diagnosing verification issue...")
        
        # 1. Count total AI-processed articles
        ai_processed_query = text("""
            SELECT COUNT(*) as total_count
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
        """)
        
        ai_processed_count = session.execute(ai_processed_query).fetchone().total_count
        logger.info(f"📊 Total AI-processed articles: {ai_processed_count}")
        
        # 2. Count how many are missing from search index (scheduler's logic)
        missing_from_index_query = text("""
            SELECT COUNT(*) as missing_count
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND na.external_id NOT IN (
                SELECT DISTINCT nsi.external_id 
                FROM news_search_index nsi 
                WHERE nsi.external_id IS NOT NULL
            )
        """)
        
        missing_count = session.execute(missing_from_index_query).fetchone().missing_count
        logger.info(f"📊 Articles missing from search index: {missing_count}")
        
        # 3. Count articles in search index  
        search_index_query = text("SELECT COUNT(*) as count FROM news_search_index")
        search_index_count = session.execute(search_index_query).fetchone().count
        logger.info(f"📊 Total articles in search index: {search_index_count}")
        
        # 4. Check how many AI articles have external_id matches in search index
        external_id_matches_query = text("""
            SELECT COUNT(DISTINCT na.external_id) as matched_count
            FROM news_articles na
            INNER JOIN news_search_index nsi ON na.external_id = nsi.external_id
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
        """)
        
        external_id_matches = session.execute(external_id_matches_query).fetchone().matched_count
        logger.info(f"📊 AI articles with external_id matches in search index: {external_id_matches}")
        
        # 5. Check strict verification count (exact AI content match)
        strict_verification_query = text("""
            SELECT COUNT(DISTINCT na.external_id) as strict_count
            FROM news_articles na
            INNER JOIN news_search_index nsi ON (
                na.external_id = nsi.external_id
                AND na.ai_summary = nsi.ai_summary
                AND na.ai_insights = nsi.ai_insights
                AND na.ai_sentiment_rating = nsi.ai_sentiment_rating
            )
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
        """)
        
        strict_count = session.execute(strict_verification_query).fetchone().strict_count
        logger.info(f"📊 Articles passing strict verification: {strict_count}")
        
        # 6. Sample some articles that have external_id match but fail strict verification
        sample_mismatch_query = text("""
            SELECT 
                na.id as na_id,
                na.external_id,
                LENGTH(na.ai_summary) as na_summary_len,
                LENGTH(nsi.ai_summary) as nsi_summary_len,
                LENGTH(na.ai_insights) as na_insights_len,
                LENGTH(nsi.ai_insights) as nsi_insights_len,
                na.ai_sentiment_rating as na_sentiment,
                nsi.ai_sentiment_rating as nsi_sentiment
            FROM news_articles na
            INNER JOIN news_search_index nsi ON na.external_id = nsi.external_id
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_summary != '' 
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND (
                na.ai_summary != nsi.ai_summary
                OR na.ai_insights != nsi.ai_insights  
                OR na.ai_sentiment_rating != nsi.ai_sentiment_rating
            )
            LIMIT 5
        """)
        
        mismatches = session.execute(sample_mismatch_query).fetchall()
        
        logger.info(f"\n🔍 ANALYSIS:")
        logger.info(f"   • Total AI-processed: {ai_processed_count}")
        logger.info(f"   • Missing from index: {missing_count}")
        logger.info(f"   • External ID matches: {external_id_matches}")
        logger.info(f"   • Strict verification: {strict_count}")
        logger.info(f"   • Search index total: {search_index_count}")
        
        # Calculate the discrepancy
        external_id_but_not_strict = external_id_matches - strict_count
        
        if external_id_but_not_strict > 0:
            logger.warning(f"\n🚨 VERIFICATION ISSUE DETECTED:")
            logger.warning(f"   • {external_id_but_not_strict} articles are in search index (by external_id)")
            logger.warning(f"   • But they FAIL strict verification (AI content mismatch)")
            logger.warning(f"   • This explains why scheduler thinks there are {ai_processed_count - strict_count} 'waiting' articles")
            
            if mismatches:
                logger.warning(f"\n📝 Sample content mismatches:")
                for mismatch in mismatches:
                    logger.warning(f"   Article {mismatch.na_id} ({mismatch.external_id}):")
                    logger.warning(f"      Summary: {mismatch.na_summary_len} vs {mismatch.nsi_summary_len} chars")
                    logger.warning(f"      Insights: {mismatch.na_insights_len} vs {mismatch.nsi_insights_len} chars") 
                    logger.warning(f"      Sentiment: {mismatch.na_sentiment} vs {mismatch.nsi_sentiment}")
            
            logger.info(f"\n💡 SOLUTION:")
            logger.info(f"   • Articles ARE synced (by external_id)")
            logger.info(f"   • Need to relax verification logic")
            logger.info(f"   • Or run one-time verification fix")
            
        else:
            logger.info(f"\n✅ VERIFICATION LOOKS GOOD:")
            logger.info(f"   • All synced articles pass strict verification")
            logger.info(f"   • The {missing_count} missing articles truly need syncing")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Error in diagnosis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("🔍 TrendWise Verification Issue Diagnosis")
    logger.info("=" * 50)
    diagnose_verification_issue() 