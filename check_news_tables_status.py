#!/usr/bin/env python3
"""
Check News Tables Status
Check current state of all news-related tables for fresh rebuild
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_table_status():
    """Check status of all news-related tables"""
    try:
        # Check news_articles table
        news_articles_count = NewsArticle.query.count()
        ai_processed_count = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None)
        ).count()
        
        # Check news_search_index table  
        search_index_count = NewsSearchIndex.query.count()
        
        # Check article_symbols table
        try:
            article_symbols_count = ArticleSymbol.query.count()
            unique_symbols_count = db.session.query(ArticleSymbol.symbol).distinct().count()
        except Exception as e:
            article_symbols_count = "Error: " + str(e)
            unique_symbols_count = "Error: " + str(e)
        
        # Check AI processing status
        ai_summaries = NewsArticle.query.filter(NewsArticle.ai_summary.isnot(None)).count()
        ai_insights = NewsArticle.query.filter(NewsArticle.ai_insights.isnot(None)).count()
        ai_sentiment = NewsArticle.query.filter(NewsArticle.ai_sentiment_rating.isnot(None)).count()
        
        # Sample articles for verification
        sample_articles = NewsArticle.query.limit(5).all()
        
        results = {
            'news_articles': {
                'total': news_articles_count,
                'ai_processed': ai_processed_count,
                'ai_summaries': ai_summaries,
                'ai_insights': ai_insights,
                'ai_sentiment': ai_sentiment,
                'sample_titles': [article.title[:100] for article in sample_articles]
            },
            'news_search_index': {
                'total': search_index_count
            },
            'article_symbols': {
                'total': article_symbols_count,
                'unique_symbols': unique_symbols_count
            }
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error checking table status: {str(e)}")
        return {'error': str(e)}

def clear_all_news_tables(confirm=False):
    """Clear all news-related tables for fresh start"""
    if not confirm:
        print("⚠️  This will DELETE ALL news data! Use confirm=True to proceed.")
        return
    
    try:
        # Clear in correct order to avoid foreign key constraints
        ArticleSymbol.query.delete()
        NewsSearchIndex.query.delete()
        NewsArticle.query.delete()
        
        db.session.commit()
        logger.info("✅ All news tables cleared successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error clearing tables: {str(e)}")
        db.session.rollback()
        return False

def main():
    """Main execution function"""
    print("📊 News Tables Status Check")
    print("=" * 50)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Check current status
        status = check_table_status()
        
        if 'error' in status:
            print(f"❌ Error: {status['error']}")
            return
        
        print(f"\n📰 News Articles Table:")
        print(f"   Total articles: {status['news_articles']['total']}")
        print(f"   AI processed: {status['news_articles']['ai_processed']}")
        print(f"   With AI summaries: {status['news_articles']['ai_summaries']}")
        print(f"   With AI insights: {status['news_articles']['ai_insights']}")
        print(f"   With AI sentiment: {status['news_articles']['ai_sentiment']}")
        
        print(f"\n🔍 News Search Index Table:")
        print(f"   Total entries: {status['news_search_index']['total']}")
        
        print(f"\n🏷️  Article Symbols Table:")
        print(f"   Total symbol entries: {status['article_symbols']['total']}")
        print(f"   Unique symbols: {status['article_symbols']['unique_symbols']}")
        
        if status['news_articles']['sample_titles']:
            print(f"\n📄 Sample Article Titles:")
            for i, title in enumerate(status['news_articles']['sample_titles'], 1):
                print(f"   {i}. {title}")
        
        # Determine recommended action
        print(f"\n🎯 Recommended Action:")
        if status['news_articles']['total'] == 0:
            print("   ✅ Tables are empty - ready for fresh data fetching")
        elif status['news_search_index']['total'] == 0:
            print("   🔧 Search index empty - need to populate from existing articles")
        else:
            print("   ⚠️  Tables have data - consider backup before clearing")
        
        # Ask if user wants to clear tables
        if status['news_articles']['total'] > 0:
            response = input(f"\n🗑️  Clear all news tables for fresh start? (y/N): ")
            if response.lower() == 'y':
                confirm_response = input(f"⚠️  Are you SURE? This will delete {status['news_articles']['total']} articles! (y/N): ")
                if confirm_response.lower() == 'y':
                    if clear_all_news_tables(confirm=True):
                        print("✅ All news tables cleared successfully!")
                        print("🚀 Ready for fresh news data fetching")
                    else:
                        print("❌ Failed to clear tables")
                else:
                    print("❌ Operation cancelled")
            else:
                print("❌ Operation cancelled")

if __name__ == "__main__":
    main() 