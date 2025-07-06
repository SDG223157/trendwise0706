#!/usr/bin/env python3
"""
Check Data Status After Recovery

This script checks the current state of both news_articles and news_search_index
to understand what data exists and what needs to be synced.
"""

import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol, ArticleMetric
from sqlalchemy import text, func
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_data_status():
    """Check current data status in all tables"""
    
    print("📊 CURRENT DATA STATUS CHECK")
    print("=" * 50)
    
    # Check news_articles
    articles_total = db.session.query(NewsArticle).count()
    articles_with_ai = db.session.query(NewsArticle).filter(
        NewsArticle.ai_summary.isnot(None),
        NewsArticle.ai_insights.isnot(None),
        NewsArticle.ai_summary != '',
        NewsArticle.ai_insights != ''
    ).count()
    
    # Check recent articles
    recent_articles = db.session.query(NewsArticle).order_by(
        NewsArticle.created_at.desc()
    ).limit(5).all()
    
    print(f"📰 NEWS_ARTICLES TABLE:")
    print(f"   • Total articles: {articles_total:,}")
    print(f"   • With AI processing: {articles_with_ai:,}")
    print(f"   • AI coverage: {(articles_with_ai/articles_total*100):.1f}%" if articles_total > 0 else "   • AI coverage: 0%")
    
    if recent_articles:
        print(f"   • Most recent article: {recent_articles[0].created_at}")
        print(f"   • Recent article titles:")
        for i, article in enumerate(recent_articles[:3], 1):
            print(f"     {i}. {article.title[:60]}...")
    
    # Check search index
    search_total = db.session.query(NewsSearchIndex).count()
    search_with_ai = db.session.query(NewsSearchIndex).filter(
        NewsSearchIndex.ai_summary.isnot(None),
        NewsSearchIndex.ai_insights.isnot(None),
        NewsSearchIndex.ai_summary != '',
        NewsSearchIndex.ai_insights != ''
    ).count()
    
    print(f"\n🔍 NEWS_SEARCH_INDEX TABLE:")
    print(f"   • Total entries: {search_total:,}")
    print(f"   • With AI content: {search_with_ai:,}")
    print(f"   • AI coverage: {(search_with_ai/search_total*100):.1f}%" if search_total > 0 else "   • AI coverage: 0%")
    
    # Check related tables
    symbols_count = db.session.query(ArticleSymbol).count()
    metrics_count = db.session.query(ArticleMetric).count()
    
    print(f"\n🔗 RELATED TABLES:")
    print(f"   • Article symbols: {symbols_count:,}")
    print(f"   • Article metrics: {metrics_count:,}")
    
    # Check sync status
    print(f"\n🔄 SYNC STATUS:")
    sync_gap = articles_with_ai - search_with_ai
    if sync_gap > 0:
        print(f"   • ⚠️  {sync_gap:,} AI-processed articles need syncing to search index")
        print(f"   • 🔄 Run sync process to populate search index")
    elif sync_gap == 0 and articles_with_ai > 0:
        print(f"   • ✅ All AI-processed articles are synced to search index")
    else:
        print(f"   • 📝 Need to process articles with AI and sync to search index")
    
    # Source analysis
    if articles_total > 0:
        sources = db.session.query(
            NewsArticle.source,
            func.count(NewsArticle.id).label('count')
        ).group_by(NewsArticle.source).order_by(func.count(NewsArticle.id).desc()).all()
        
        print(f"\n📡 SOURCES BREAKDOWN:")
        for source, count in sources[:5]:
            print(f"   • {source}: {count:,} articles")
    
    # Date range analysis
    if articles_total > 0:
        date_range = db.session.query(
            func.min(NewsArticle.published_at),
            func.max(NewsArticle.published_at)
        ).first()
        
        print(f"\n📅 DATE RANGE:")
        print(f"   • Oldest article: {date_range[0] if date_range[0] else 'Unknown'}")
        print(f"   • Newest article: {date_range[1] if date_range[1] else 'Unknown'}")
    
    return {
        'articles_total': articles_total,
        'articles_with_ai': articles_with_ai,
        'search_total': search_total,
        'search_with_ai': search_with_ai,
        'sync_needed': sync_gap > 0,
        'sync_gap': max(0, sync_gap)
    }

def recommend_actions(status):
    """Recommend next actions based on data status"""
    
    print(f"\n🎯 RECOMMENDED ACTIONS:")
    
    if status['articles_total'] == 0:
        print("   1. 🌐 Start fetching news articles from sources")
        print("   2. 🤖 Enable AI processing for new articles")
        print("   3. 🔍 Monitor search index population")
    
    elif status['articles_with_ai'] == 0:
        print("   1. 🤖 Run AI processing on existing articles")
        print("   2. ⏰ Enable AI processing scheduler")
        print("   3. 🔄 Sync processed articles to search index")
    
    elif status['sync_gap'] > 0:
        print(f"   1. 🔄 Run sync process for {status['sync_gap']:,} articles")
        print("   2. ✅ Test search functionality after sync")
        print("   3. 📊 Monitor search performance")
    
    else:
        print("   1. ✅ Data is synced - test search functionality")
        print("   2. 🚀 Enable buffer architecture transformation")
        print("   3. 📊 Monitor system performance")

def main():
    """Main status check"""
    
    app = create_app()
    
    with app.app_context():
        print("📊 TrendWise Data Status Check")
        print("=" * 40)
        print()
        
        try:
            status = check_data_status()
            recommend_actions(status)
            
            print(f"\n" + "=" * 50)
            print("✅ Data status check completed")
            
            if status['sync_needed']:
                print("🔄 Next step: Run data sync process")
                print("   Command: python populate_search_index_ai_data.py")
            else:
                print("🎯 Next step: Test search functionality")
                print("   Check: /news/search on your application")
            
        except Exception as e:
            print(f"❌ Error checking data status: {str(e)}")
            print("🔍 Check database connection and table structure")

if __name__ == '__main__':
    main() 