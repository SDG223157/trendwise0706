#!/usr/bin/env python3
"""
Populate Search Index from Existing Articles
Specifically designed for situations where news_articles has data but news_search_index is empty
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol
from app.utils.search.search_index_sync import SearchIndexSyncService
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_existing_articles():
    """Analyze existing articles to understand the population task"""
    try:
        # Get article counts
        total_articles = NewsArticle.query.count()
        ai_processed = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_summary != '',
            NewsArticle.ai_insights != ''
        ).count()
        
        # Get search index count
        search_index_count = NewsSearchIndex.query.count()
        
        # Get articles with symbols
        articles_with_symbols = db.session.query(NewsArticle.id).join(
            ArticleSymbol, NewsArticle.id == ArticleSymbol.article_id
        ).distinct().count()
        
        # Get date ranges
        oldest_article = NewsArticle.query.order_by(NewsArticle.published_at.asc()).first()
        newest_article = NewsArticle.query.order_by(NewsArticle.published_at.desc()).first()
        
        # Sample AI-processed articles
        sample_ai_articles = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None)
        ).limit(3).all()
        
        return {
            'total_articles': total_articles,
            'ai_processed': ai_processed,
            'search_index_count': search_index_count,
            'articles_with_symbols': articles_with_symbols,
            'date_range': {
                'oldest': oldest_article.published_at.isoformat() if oldest_article else None,
                'newest': newest_article.published_at.isoformat() if newest_article else None
            },
            'sample_ai_articles': [
                {
                    'id': article.id,
                    'title': article.title[:100] + "..." if len(article.title) > 100 else article.title,
                    'published_at': article.published_at.isoformat(),
                    'has_ai_summary': bool(article.ai_summary and article.ai_summary.strip()),
                    'has_ai_insights': bool(article.ai_insights and article.ai_insights.strip()),
                    'ai_sentiment_rating': article.ai_sentiment_rating
                }
                for article in sample_ai_articles
            ]
        }
        
    except Exception as e:
        logger.error(f"Error analyzing existing articles: {str(e)}")
        return {'error': str(e)}

def populate_search_index_priority_ai(dry_run: bool = False):
    """
    Populate search index with priority on AI-processed articles
    
    Args:
        dry_run: If True, show what would be done without making changes
    """
    try:
        sync_service = SearchIndexSyncService()
        
        # Step 1: Get AI-processed articles first (highest priority)
        ai_articles = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_summary != '',
            NewsArticle.ai_insights != ''
        ).order_by(NewsArticle.published_at.desc()).all()
        
        # Step 2: Get remaining articles (lower priority)
        remaining_articles = NewsArticle.query.filter(
            ~NewsArticle.id.in_([a.id for a in ai_articles])
        ).order_by(NewsArticle.published_at.desc()).all()
        
        results = {
            'ai_articles_processed': 0,
            'remaining_articles_processed': 0,
            'total_added': 0,
            'total_updated': 0,
            'total_skipped': 0,
            'total_errors': 0,
            'priority_samples': []
        }
        
        logger.info(f"Found {len(ai_articles)} AI-processed articles and {len(remaining_articles)} remaining articles")
        
        # Step 3: Process AI articles first (priority)
        if ai_articles:
            logger.info(f"🎯 Processing {len(ai_articles)} AI-enhanced articles (PRIORITY)")
            
            if not dry_run:
                ai_stats = sync_service.sync_multiple_articles(ai_articles)
                results['ai_articles_processed'] = len(ai_articles)
                results['total_added'] += ai_stats['added']
                results['total_updated'] += ai_stats['updated']
                results['total_skipped'] += ai_stats['skipped']
                results['total_errors'] += ai_stats['errors']
                
                logger.info(f"✅ AI articles: {ai_stats['added']} added, {ai_stats['updated']} updated, {ai_stats['errors']} errors")
            else:
                results['ai_articles_processed'] = len(ai_articles)
                logger.info(f"🔍 DRY RUN: Would process {len(ai_articles)} AI articles")
        
        # Step 4: Process remaining articles
        if remaining_articles:
            logger.info(f"📰 Processing {len(remaining_articles)} remaining articles")
            
            if not dry_run:
                remaining_stats = sync_service.sync_multiple_articles(remaining_articles)
                results['remaining_articles_processed'] = len(remaining_articles)
                results['total_added'] += remaining_stats['added']
                results['total_updated'] += remaining_stats['updated']
                results['total_skipped'] += remaining_stats['skipped']
                results['total_errors'] += remaining_stats['errors']
                
                logger.info(f"✅ Remaining articles: {remaining_stats['added']} added, {remaining_stats['updated']} updated, {remaining_stats['errors']} errors")
            else:
                results['remaining_articles_processed'] = len(remaining_articles)
                logger.info(f"🔍 DRY RUN: Would process {len(remaining_articles)} remaining articles")
        
        # Store priority samples
        results['priority_samples'] = [
            {
                'id': article.id,
                'title': article.title[:80] + "..." if len(article.title) > 80 else article.title,
                'published_at': article.published_at.isoformat(),
                'ai_sentiment_rating': article.ai_sentiment_rating,
                'has_full_ai': bool(article.ai_summary and article.ai_insights)
            }
            for article in ai_articles[:5]  # Top 5 AI articles
        ]
        
        return results
        
    except Exception as e:
        logger.error(f"Error populating search index: {str(e)}")
        return {'error': str(e)}

def verify_search_index_population():
    """Verify that search index was populated correctly"""
    try:
        # Check search index count
        search_count = NewsSearchIndex.query.count()
        
        # Check AI-enhanced entries
        ai_search_count = NewsSearchIndex.query.filter(
            NewsSearchIndex.ai_summary.isnot(None),
            NewsSearchIndex.ai_insights.isnot(None),
            NewsSearchIndex.ai_summary != '',
            NewsSearchIndex.ai_insights != ''
        ).count()
        
        # Sample search index entries
        sample_entries = NewsSearchIndex.query.limit(3).all()
        
        return {
            'total_search_entries': search_count,
            'ai_enhanced_entries': ai_search_count,
            'sample_entries': [
                {
                    'id': entry.id,
                    'external_id': entry.external_id,
                    'title': entry.title[:80] + "..." if len(entry.title) > 80 else entry.title,
                    'has_ai_summary': bool(entry.ai_summary and entry.ai_summary.strip()),
                    'has_ai_insights': bool(entry.ai_insights and entry.ai_insights.strip()),
                    'ai_sentiment_rating': entry.ai_sentiment_rating
                }
                for entry in sample_entries
            ]
        }
        
    except Exception as e:
        logger.error(f"Error verifying search index: {str(e)}")
        return {'error': str(e)}

def main():
    """Main execution function"""
    print("🔄 Populate Search Index from Existing Articles")
    print("=" * 60)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Step 1: Analyze existing articles
        print("\n📊 Analyzing Existing Articles...")
        analysis = analyze_existing_articles()
        
        if 'error' in analysis:
            print(f"❌ Error: {analysis['error']}")
            return
        
        print(f"   Total articles: {analysis['total_articles']}")
        print(f"   AI-processed articles: {analysis['ai_processed']}")
        print(f"   Search index entries: {analysis['search_index_count']}")
        print(f"   Articles with symbols: {analysis['articles_with_symbols']}")
        print(f"   Date range: {analysis['date_range']['oldest'][:10] if analysis['date_range']['oldest'] else 'N/A'} to {analysis['date_range']['newest'][:10] if analysis['date_range']['newest'] else 'N/A'}")
        
        if analysis['sample_ai_articles']:
            print(f"\n🎯 Sample AI-Processed Articles:")
            for sample in analysis['sample_ai_articles']:
                print(f"   • ID {sample['id']}: {sample['title']}")
                print(f"     Published: {sample['published_at'][:10]}")
                print(f"     AI Rating: {sample['ai_sentiment_rating']}")
                print()
        
        # Step 2: Run dry run
        print("\n🔍 Running DRY RUN...")
        dry_results = populate_search_index_priority_ai(dry_run=True)
        
        if 'error' in dry_results:
            print(f"❌ Error: {dry_results['error']}")
            return
        
        print(f"   AI articles to process: {dry_results['ai_articles_processed']}")
        print(f"   Remaining articles to process: {dry_results['remaining_articles_processed']}")
        print(f"   Total articles: {dry_results['ai_articles_processed'] + dry_results['remaining_articles_processed']}")
        
        if dry_results['priority_samples']:
            print(f"\n🎯 Priority AI Articles (Top 5):")
            for sample in dry_results['priority_samples']:
                print(f"   • ID {sample['id']}: {sample['title']}")
                print(f"     Published: {sample['published_at'][:10]}, AI Rating: {sample['ai_sentiment_rating']}")
        
        # Step 3: Ask for confirmation
        if dry_results['ai_articles_processed'] + dry_results['remaining_articles_processed'] > 0:
            total_to_process = dry_results['ai_articles_processed'] + dry_results['remaining_articles_processed']
            response = input(f"\n✅ Populate search index with {total_to_process} articles? (y/N): ")
            
            if response.lower() == 'y':
                print("\n🚀 Populating search index...")
                final_results = populate_search_index_priority_ai(dry_run=False)
                
                if 'error' in final_results:
                    print(f"❌ Error: {final_results['error']}")
                else:
                    print(f"\n✅ SUCCESS!")
                    print(f"   AI articles processed: {final_results['ai_articles_processed']}")
                    print(f"   Remaining articles processed: {final_results['remaining_articles_processed']}")
                    print(f"   Total added to search index: {final_results['total_added']}")
                    print(f"   Total updated: {final_results['total_updated']}")
                    print(f"   Total skipped: {final_results['total_skipped']}")
                    print(f"   Total errors: {final_results['total_errors']}")
                    
                    # Step 4: Verify results
                    print("\n🔍 Verifying Search Index Population...")
                    verification = verify_search_index_population()
                    
                    if 'error' not in verification:
                        print(f"   Search index entries: {verification['total_search_entries']}")
                        print(f"   AI-enhanced entries: {verification['ai_enhanced_entries']}")
                        print(f"   Population success rate: {(verification['total_search_entries'] / (final_results['ai_articles_processed'] + final_results['remaining_articles_processed']) * 100):.1f}%")
                        
                        if verification['sample_entries']:
                            print(f"\n📄 Sample Search Index Entries:")
                            for entry in verification['sample_entries']:
                                print(f"   • ID {entry['id']}: {entry['title']}")
                                print(f"     External ID: {entry['external_id']}")
                                print(f"     AI Content: {'✅' if entry['has_ai_summary'] and entry['has_ai_insights'] else '❌'}")
            else:
                print("\n❌ Operation cancelled")
        else:
            print("\n⚠️  No articles found to process")

if __name__ == "__main__":
    main() 