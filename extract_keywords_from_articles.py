#!/usr/bin/env python3
"""
Extract Keywords from Articles Script

This script extracts keywords from existing articles and populates the keyword tables
for AI-powered search suggestions. It processes articles in batches to avoid memory issues.
"""

import os
import sys
import logging
from datetime import datetime
import argparse

# Add the project root to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import NewsArticle, NewsKeyword, ArticleKeyword
from app.utils.ai.keyword_extraction_service import keyword_extraction_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('keyword_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to run keyword extraction"""
    parser = argparse.ArgumentParser(description='Extract keywords from articles')
    parser.add_argument('--batch-size', type=int, default=100, 
                       help='Number of articles to process in each batch (default: 100)')
    parser.add_argument('--max-articles', type=int, default=None,
                       help='Maximum number of articles to process (default: all)')
    parser.add_argument('--skip-processed', action='store_true',
                       help='Skip articles that already have keywords extracted')
    parser.add_argument('--reset', action='store_true',
                       help='Reset all keyword data before processing')
    parser.add_argument('--test', action='store_true',
                       help='Test mode - process only 10 articles')
    
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        logger.info("🚀 Starting keyword extraction process...")
        
        # Test mode
        if args.test:
            args.batch_size = 10
            args.max_articles = 10
            logger.info("🧪 Running in test mode")
        
        # Reset option
        if args.reset:
            reset_keyword_data()
        
        # Get statistics before processing
        stats_before = get_stats()
        logger.info(f"📊 Before processing: {stats_before}")
        
        # Process articles in batches
        total_processed = 0
        total_keywords = 0
        batch_num = 1
        
        while True:
            logger.info(f"🔄 Processing batch {batch_num} (batch size: {args.batch_size})")
            
            # Process batch
            batch_stats = keyword_extraction_service.process_articles_batch(
                limit=args.batch_size,
                skip_processed=args.skip_processed
            )
            
            # Update totals
            total_processed += batch_stats['processed']
            total_keywords += batch_stats['keywords_extracted']
            
            logger.info(f"📊 Batch {batch_num} results: {batch_stats}")
            
            # Check if we should continue
            if (batch_stats['processed'] == 0 or 
                (args.max_articles and total_processed >= args.max_articles)):
                break
            
            batch_num += 1
        
        # Get statistics after processing
        stats_after = get_stats()
        logger.info(f"📊 After processing: {stats_after}")
        
        # Summary
        logger.info("✅ Keyword extraction completed!")
        logger.info(f"📈 Summary:")
        logger.info(f"   - Articles processed: {total_processed}")
        logger.info(f"   - Keywords extracted: {total_keywords}")
        logger.info(f"   - Unique keywords: {stats_after['unique_keywords']}")
        logger.info(f"   - Article-keyword relationships: {stats_after['article_keywords']}")
        
        # Test the results
        if total_processed > 0:
            test_suggestions()

def reset_keyword_data():
    """Reset all keyword data"""
    logger.info("🗑️ Resetting keyword data...")
    
    try:
        # Delete all data (cascade will handle relationships)
        db.session.execute("DELETE FROM article_keywords")
        db.session.execute("DELETE FROM keyword_similarities")
        db.session.execute("DELETE FROM news_keywords")
        db.session.execute("DELETE FROM search_analytics")
        db.session.commit()
        
        logger.info("✅ Keyword data reset successfully")
        
    except Exception as e:
        logger.error(f"❌ Error resetting keyword data: {str(e)}")
        db.session.rollback()
        raise

def get_stats():
    """Get current statistics"""
    try:
        stats = {
            'total_articles': db.session.query(NewsArticle).count(),
            'ai_articles': db.session.query(NewsArticle).filter(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_summary != '',
                NewsArticle.ai_insights != ''
            ).count(),
            'unique_keywords': db.session.query(NewsKeyword).count(),
            'article_keywords': db.session.query(ArticleKeyword).count(),
            'processed_articles': db.session.query(ArticleKeyword.article_id).distinct().count()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting statistics: {str(e)}")
        return {}

def test_suggestions():
    """Test the keyword suggestions"""
    logger.info("🧪 Testing keyword suggestions...")
    
    try:
        # Test queries
        test_queries = [
            'artificial intelligence',
            'earnings',
            'ai',
            'tesla',
            'technology',
            'bitcoin',
            'merger'
        ]
        
        for query in test_queries:
            suggestions = keyword_extraction_service.get_keyword_suggestions(query, limit=5)
            logger.info(f"   Query '{query}': {len(suggestions)} suggestions")
            
            for suggestion in suggestions[:3]:  # Show top 3
                logger.info(f"     - {suggestion['keyword']} ({suggestion['category']}) - {suggestion['relevance_score']:.2f}")
        
        # Test trending keywords
        trending = keyword_extraction_service.get_trending_keywords(days=30, limit=10)
        logger.info(f"📈 Trending keywords: {len(trending)} found")
        
        for keyword in trending[:5]:  # Show top 5
            logger.info(f"     - {keyword['keyword']} ({keyword['frequency']} times)")
            
    except Exception as e:
        logger.error(f"❌ Error testing suggestions: {str(e)}")

def show_sample_keywords():
    """Show sample keywords for verification"""
    logger.info("🔍 Sample keywords by category:")
    
    try:
        categories = ['company', 'technology', 'financial', 'industry', 'concept']
        
        for category in categories:
            keywords = db.session.query(NewsKeyword).filter(
                NewsKeyword.category == category
            ).order_by(NewsKeyword.frequency.desc()).limit(10).all()
            
            logger.info(f"   {category.capitalize()}: {len(keywords)} keywords")
            for keyword in keywords[:5]:  # Show top 5
                logger.info(f"     - {keyword.keyword} (freq: {keyword.frequency}, rel: {keyword.relevance_score:.2f})")
                
    except Exception as e:
        logger.error(f"❌ Error showing sample keywords: {str(e)}")

def verify_extraction():
    """Verify the extraction results"""
    logger.info("🔍 Verifying extraction results...")
    
    try:
        # Check for any issues
        issues = []
        
        # Check for keywords without articles
        orphaned_keywords = db.session.query(NewsKeyword).filter(
            ~NewsKeyword.id.in_(
                db.session.query(ArticleKeyword.keyword_id).distinct()
            )
        ).count()
        
        if orphaned_keywords > 0:
            issues.append(f"Found {orphaned_keywords} keywords without articles")
        
        # Check for articles without keywords
        articles_without_keywords = db.session.query(NewsArticle).filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            ~NewsArticle.id.in_(
                db.session.query(ArticleKeyword.article_id).distinct()
            )
        ).count()
        
        if articles_without_keywords > 0:
            issues.append(f"Found {articles_without_keywords} AI articles without keywords")
        
        # Check for duplicate keywords
        duplicate_keywords = db.session.execute("""
            SELECT normalized_keyword, category, COUNT(*) as count
            FROM news_keywords
            GROUP BY normalized_keyword, category
            HAVING COUNT(*) > 1
        """).fetchall()
        
        if duplicate_keywords:
            issues.append(f"Found {len(duplicate_keywords)} duplicate keyword-category pairs")
        
        if issues:
            logger.warning("⚠️ Issues found:")
            for issue in issues:
                logger.warning(f"   - {issue}")
        else:
            logger.info("✅ No issues found - extraction looks good!")
            
    except Exception as e:
        logger.error(f"❌ Error verifying extraction: {str(e)}")

def cleanup_keywords():
    """Clean up low-quality keywords"""
    logger.info("🧹 Cleaning up low-quality keywords...")
    
    try:
        # Remove keywords with very low relevance
        low_relevance = db.session.query(NewsKeyword).filter(
            NewsKeyword.relevance_score < 0.1
        ).count()
        
        if low_relevance > 0:
            db.session.query(NewsKeyword).filter(
                NewsKeyword.relevance_score < 0.1
            ).delete()
            logger.info(f"   Removed {low_relevance} keywords with low relevance")
        
        # Remove keywords that appear only once and have low relevance
        single_occurrence = db.session.query(NewsKeyword).filter(
            NewsKeyword.frequency == 1,
            NewsKeyword.relevance_score < 0.3
        ).count()
        
        if single_occurrence > 0:
            db.session.query(NewsKeyword).filter(
                NewsKeyword.frequency == 1,
                NewsKeyword.relevance_score < 0.3
            ).delete()
            logger.info(f"   Removed {single_occurrence} single-occurrence low-relevance keywords")
        
        # Remove very short keywords (likely fragments)
        short_keywords = db.session.query(NewsKeyword).filter(
            db.func.length(NewsKeyword.keyword) < 3
        ).count()
        
        if short_keywords > 0:
            db.session.query(NewsKeyword).filter(
                db.func.length(NewsKeyword.keyword) < 3
            ).delete()
            logger.info(f"   Removed {short_keywords} very short keywords")
        
        db.session.commit()
        logger.info("✅ Cleanup completed")
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up keywords: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    try:
        main()
        
        # Additional verification and cleanup
        verify_extraction()
        cleanup_keywords()
        show_sample_keywords()
        
        logger.info("🎉 Keyword extraction process completed successfully!")
        logger.info("💡 Next steps:")
        logger.info("   1. Test suggestions: curl 'http://localhost:5000/news/api/suggestions?q=artificial'")
        logger.info("   2. Check trending: curl 'http://localhost:5000/news/api/keywords/trending'")
        logger.info("   3. Monitor analytics: curl 'http://localhost:5000/news/api/analytics/suggestions'")
        
    except KeyboardInterrupt:
        logger.info("⏸️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        sys.exit(1) 