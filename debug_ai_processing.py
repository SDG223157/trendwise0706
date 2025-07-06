#!/usr/bin/env python3
"""
Debug AI Processing Issues
Comprehensive diagnostics for AI processing workflow problems
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol
from app.utils.scheduler.news_scheduler import NewsAIScheduler
import logging
from datetime import datetime, timedelta
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def check_ai_processing_status():
    """Check current AI processing status and identify issues"""
    try:
        # Get article counts
        total_articles = NewsArticle.query.count()
        
        # Check AI field status
        articles_with_ai_summary = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_summary != ''
        ).count()
        
        articles_with_ai_insights = NewsArticle.query.filter(
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_insights != ''
        ).count()
        
        articles_with_ai_sentiment = NewsArticle.query.filter(
            NewsArticle.ai_sentiment_rating.isnot(None)
        ).count()
        
        # Check for articles that should be processed
        articles_without_ai = NewsArticle.query.filter(
            NewsArticle.ai_summary.is_(None)
        ).count()
        
        # Get sample articles for detailed inspection
        sample_articles = NewsArticle.query.limit(5).all()
        
        # Check recent activity
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_articles = NewsArticle.query.filter(
            NewsArticle.created_at >= recent_cutoff
        ).count()
        
        recent_articles = NewsArticle.query.filter(
            NewsArticle.created_at >= recent_cutoff
        ).count()
        
        return {
            'total_articles': total_articles,
            'articles_with_ai_summary': articles_with_ai_summary,
            'articles_with_ai_insights': articles_with_ai_insights,
            'articles_with_ai_sentiment': articles_with_ai_sentiment,
            'articles_without_ai': articles_without_ai,
            'recent_articles': recent_articles,
            'sample_articles': [
                {
                    'id': article.id,
                    'title': article.title[:100] + "..." if len(article.title) > 100 else article.title,
                    'created_at': article.created_at.isoformat(),
                    'updated_at': None,  # NewsArticle doesn't have updated_at field
                    'has_ai_summary': bool(article.ai_summary and article.ai_summary.strip()),
                    'has_ai_insights': bool(article.ai_insights and article.ai_insights.strip()),
                    'ai_sentiment_rating': article.ai_sentiment_rating,
                    'content_length': len(article.content) if article.content else 0
                }
                for article in sample_articles
            ]
        }
        
    except Exception as e:
        logger.error(f"Error checking AI processing status: {str(e)}")
        return {'error': str(e)}

def test_ai_scheduler_functionality():
    """Test if the AI scheduler can process a single article"""
    try:
        # Get an article without AI processing
        test_article = NewsArticle.query.filter(
            NewsArticle.ai_summary.is_(None)
        ).first()
        
        if not test_article:
            return {'error': 'No articles found that need AI processing'}
        
        print(f"🧪 Testing AI processing on article ID {test_article.id}")
        print(f"   Title: {test_article.title[:100]}...")
        print(f"   Content length: {len(test_article.content) if test_article.content else 0}")
        
        # Initialize AI scheduler
        try:
            scheduler = NewsAIScheduler()
            
            # Initialize with Flask app to set up database session
            from flask import current_app
            scheduler.init_app(current_app)
            print("✅ AI Scheduler initialized successfully")
        except Exception as e:
            return {'error': f'Failed to initialize AI scheduler: {str(e)}'}
        
        # Test AI processing on this article
        try:
            print("🤖 Attempting to process article with AI...")
            
            # Use the scheduler's database session
            with scheduler.get_db_session() as session:
                success = scheduler.process_single_article(session, test_article)
                
                if success:
                    # Reload article to check if changes were saved
                    db.session.refresh(test_article)
                    
                    result = {
                        'success': True,
                        'article_id': test_article.id,
                        'ai_summary_generated': bool(test_article.ai_summary and test_article.ai_summary.strip()),
                        'ai_insights_generated': bool(test_article.ai_insights and test_article.ai_insights.strip()),
                        'ai_sentiment_generated': test_article.ai_sentiment_rating is not None,
                        'ai_summary_length': len(test_article.ai_summary) if test_article.ai_summary else 0,
                        'ai_insights_length': len(test_article.ai_insights) if test_article.ai_insights else 0,
                        'ai_sentiment_rating': test_article.ai_sentiment_rating
                    }
                    
                    print(f"✅ AI processing completed!")
                    print(f"   AI Summary: {'✅' if result['ai_summary_generated'] else '❌'} ({result['ai_summary_length']} chars)")
                    print(f"   AI Insights: {'✅' if result['ai_insights_generated'] else '❌'} ({result['ai_insights_length']} chars)")
                    print(f"   AI Sentiment: {'✅' if result['ai_sentiment_generated'] else '❌'} (rating: {result['ai_sentiment_rating']})")
                    
                    return result
                else:
                    return {'error': 'AI processing returned False - check logs for details'}
                    
        except Exception as e:
            logger.error(f"AI processing test failed: {str(e)}")
            logger.error(traceback.format_exc())
            return {'error': f'AI processing failed: {str(e)}'}
        
    except Exception as e:
        logger.error(f"Error in AI scheduler test: {str(e)}")
        return {'error': str(e)}

def check_ai_api_configuration():
    """Check if AI API is properly configured"""
    try:
        # Check environment variables
        import os
        
        api_token = os.getenv("APIFY_API_TOKEN")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        config_status = {
            'apify_token_set': bool(api_token and api_token.strip() and api_token != "MISSING_API_TOKEN"),
            'openrouter_key_set': bool(openrouter_key and openrouter_key.strip()),
            'apify_token_length': len(api_token) if api_token else 0,
            'openrouter_key_length': len(openrouter_key) if openrouter_key else 0
        }
        
        print("🔑 API Configuration Check:")
        print(f"   APIFY_API_TOKEN: {'✅ Set' if config_status['apify_token_set'] else '❌ Missing/Invalid'} ({config_status['apify_token_length']} chars)")
        print(f"   OPENROUTER_API_KEY: {'✅ Set' if config_status['openrouter_key_set'] else '❌ Missing/Invalid'} ({config_status['openrouter_key_length']} chars)")
        
        return config_status
        
    except Exception as e:
        logger.error(f"Error checking API configuration: {str(e)}")
        return {'error': str(e)}

    def check_database_permissions():
        """Check if we can update articles in the database"""
        try:
            # Try to update a test article
            test_article = NewsArticle.query.first()
            
            if not test_article:
                return {'error': 'No articles found to test database updates'}
            
            original_title = test_article.title
            
            # Try to update the article (add a temporary marker)
            test_article.title = test_article.title + " [TEST]"
            db.session.commit()
            
            # Verify the update worked
            db.session.refresh(test_article)
            
            if test_article.title != original_title:
                # Revert the change
                test_article.title = original_title
                db.session.commit()
                print("✅ Database update permissions: OK")
                return {'database_writable': True}
            else:
                print("❌ Database update failed")
                return {'database_writable': False, 'error': 'Update did not persist'}
                
        except Exception as e:
            logger.error(f"Database permission test failed: {str(e)}")
            db.session.rollback()
            return {'database_writable': False, 'error': str(e)}

def main():
    """Main diagnostic function"""
    print("🔍 AI Processing Diagnostics")
    print("=" * 60)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Step 1: Check overall AI processing status
        print("\n📊 Current AI Processing Status:")
        status = check_ai_processing_status()
        
        if 'error' in status:
            print(f"❌ Error: {status['error']}")
            return
        
        print(f"   Total articles: {status['total_articles']}")
        print(f"   Articles with AI summaries: {status['articles_with_ai_summary']}")
        print(f"   Articles with AI insights: {status['articles_with_ai_insights']}")
        print(f"   Articles with AI sentiment: {status['articles_with_ai_sentiment']}")
        print(f"   Articles without AI: {status['articles_without_ai']}")
        print(f"   Recent articles (1h): {status['recent_articles']}")
        
        if status['sample_articles']:
            print(f"\n📄 Sample Articles:")
            for article in status['sample_articles']:
                print(f"   • ID {article['id']}: {article['title']}")
                print(f"     Created: {article['created_at'][:19]}")
                print(f"     Updated: {article['updated_at'][:19] if article['updated_at'] else 'Never'}")
                print(f"     AI Content: Summary={'✅' if article['has_ai_summary'] else '❌'}, Insights={'✅' if article['has_ai_insights'] else '❌'}, Sentiment={article['ai_sentiment_rating'] or '❌'}")
                print(f"     Content: {article['content_length']} chars")
                print()
        
        # Step 2: Check API configuration
        print("\n🔑 API Configuration:")
        api_config = check_ai_api_configuration()
        
        # Step 3: Check database permissions
        print("\n💾 Database Permissions:")
        db_perms = check_database_permissions()
        
        # Step 4: Test AI scheduler if articles need processing
        if status['articles_without_ai'] > 0:
            print(f"\n🧪 Testing AI Processing (found {status['articles_without_ai']} articles needing AI):")
            test_result = test_ai_scheduler_functionality()
            
            if 'error' in test_result:
                print(f"❌ AI Processing Test Failed: {test_result['error']}")
            else:
                print(f"✅ AI Processing Test Completed!")
                if test_result.get('success'):
                    print("🎉 AI processing is working! Results saved to database.")
                    
                    # Verify auto-sync triggered
                    print("\n🔄 Checking if auto-sync triggered...")
                    search_entries = NewsSearchIndex.query.count()
                    print(f"   Search index entries: {search_entries}")
                    
                    if search_entries > 0:
                        print("✅ Auto-sync appears to be working!")
                    else:
                        print("⚠️ Auto-sync may not have triggered yet")
        else:
            print(f"\n✅ All articles already have AI processing!")
        
        # Step 5: Provide recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if status['articles_without_ai'] == 0:
            print("   ✅ AI processing appears to be working - all articles processed")
        elif not api_config.get('openrouter_key_set'):
            print("   ❌ OPENROUTER_API_KEY is missing - AI processing cannot work")
        elif not db_perms.get('database_writable'):
            print("   ❌ Database permission issue - cannot save AI results")
        elif 'test_result' in locals() and test_result.get('success'):
            print("   ✅ AI processing is working! Monitor for auto-completion")
        else:
            print("   ⚠️ Check AI scheduler logs for detailed error messages")
            print("   💡 Consider manually triggering AI processing via /news/ai-status")

if __name__ == "__main__":
    main() 