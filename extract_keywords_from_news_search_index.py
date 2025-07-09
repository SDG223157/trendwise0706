#!/usr/bin/env python3
"""
Extract Keywords from NEWS_SEARCH_INDEX - CORRECTED VERSION

This script extracts keywords from the PERMANENT news_search_index table
(not the buffer news_articles table) for AI-powered search suggestions.
"""

import os
import sys
import logging
from datetime import datetime
import argparse

# Add the project root to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import NewsSearchIndex, NewsKeyword, ArticleKeyword
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
    parser = argparse.ArgumentParser(description='Extract keywords from news_search_index (permanent table)')
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
        logger.info("🚀 Starting keyword extraction from news_search_index (permanent table)...")
        
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
            batch_stats = process_articles_batch(
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

def process_articles_batch(limit: int = 100, skip_processed: bool = True) -> dict:
    """Process a batch of articles from news_search_index for keyword extraction"""
    stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'keywords_extracted': 0
    }
    
    try:
        # Get articles that need processing from NEWS_SEARCH_INDEX (permanent table)
        query = db.session.query(NewsSearchIndex).filter(
            NewsSearchIndex.ai_summary.isnot(None),
            NewsSearchIndex.ai_insights.isnot(None),
            NewsSearchIndex.ai_summary != '',
            NewsSearchIndex.ai_insights != ''
        )
        
        if skip_processed:
            # Skip articles that already have keywords
            processed_article_ids = db.session.query(ArticleKeyword.article_id).distinct()
            query = query.filter(~NewsSearchIndex.id.in_(processed_article_ids))
        
        articles = query.limit(limit).all()
        
        logger.info(f"Processing {len(articles)} articles from news_search_index for keyword extraction")
        
        for article in articles:
            try:
                # Create a temporary article object for the extraction service
                # Convert NewsSearchIndex to a compatible format
                temp_article = type('ArticleObj', (), {
                    'id': article.id,
                    'title': article.title,
                    'ai_summary': article.ai_summary,
                    'ai_insights': article.ai_insights
                })()
                
                # Extract keywords
                keywords = keyword_extraction_service.extract_keywords_from_article(temp_article)
                
                if keywords:
                    # Store keywords
                    if store_keywords(article, keywords):
                        stats['processed'] += 1
                        stats['keywords_extracted'] += len(keywords)
                    else:
                        stats['errors'] += 1
                else:
                    stats['skipped'] += 1
                    logger.debug(f"No keywords extracted for article {article.id}")
            
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {str(e)}")
                stats['errors'] += 1
        
        logger.info(f"Keyword extraction batch completed: {stats}")
        
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        stats['errors'] = limit
    
    return stats

def store_keywords(article, keywords: list) -> bool:
    """Store extracted keywords in the database"""
    try:
        from nltk.stem import PorterStemmer
        stemmer = PorterStemmer()
        
        for keyword_data in keywords:
            keyword_text = keyword_data['keyword'].strip()
            normalized_keyword = stemmer.stem(keyword_text.lower())
            category = keyword_data['category']
            relevance_score = keyword_data['relevance_score']
            
            # Get or create keyword
            keyword_obj = db.session.query(NewsKeyword).filter_by(
                normalized_keyword=normalized_keyword,
                category=category
            ).first()
            
            if keyword_obj:
                # Update existing keyword
                keyword_obj.frequency += 1
                keyword_obj.last_seen = datetime.utcnow()
                # Update relevance score (weighted average)
                old_weight = keyword_obj.frequency - 1
                keyword_obj.relevance_score = (
                    (keyword_obj.relevance_score * old_weight + relevance_score) / 
                    keyword_obj.frequency
                )
            else:
                # Create new keyword
                keyword_obj = NewsKeyword(
                    keyword=keyword_text,
                    normalized_keyword=normalized_keyword,
                    category=category,
                    relevance_score=relevance_score,
                    frequency=1,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                db.session.add(keyword_obj)
                db.session.flush()  # Get the ID
            
            # Create article-keyword relationship
            article_keyword = ArticleKeyword(
                article_id=article.id,
                keyword_id=keyword_obj.id,
                relevance_in_article=relevance_score,
                extraction_source=keyword_data.get('source', 'unknown')
            )
            db.session.add(article_keyword)
        
        db.session.commit()
        logger.debug(f"Stored {len(keywords)} keywords for article {article.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store keywords for article {article.id}: {str(e)}")
        db.session.rollback()
        return False

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
            'total_articles': db.session.query(NewsSearchIndex).count(),
            'ai_articles': db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_insights.isnot(None),
                NewsSearchIndex.ai_summary != '',
                NewsSearchIndex.ai_insights != ''
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
        
        # Get trending keywords
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

if __name__ == '__main__':
    try:
        main()
        
        # Additional verification and cleanup
        show_sample_keywords()
        
        logger.info("🎉 Keyword extraction from news_search_index completed successfully!")
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