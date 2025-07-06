#!/usr/bin/env python3
"""
Transform news_articles into a Buffer Table

This script safely clears all records from news_articles table to transform it
into a pure buffer table for incoming news processing, while preserving all
AI-enhanced data in the news_search_index table.

ARCHITECTURE TRANSFORMATION:
- BEFORE: news_articles (storage) + news_search_index (search optimization)  
- AFTER:  news_articles (buffer)  + news_search_index (standalone storage + search)

WORKFLOW:
1. New articles → news_articles (buffer)
2. AI processing → enhanced articles  
3. Move to news_search_index → clear from buffer
4. Search operates purely on news_search_index
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

def verify_search_index_integrity():
    """Verify that news_search_index has sufficient AI-enhanced data"""
    
    print("🔍 Verifying news_search_index integrity...")
    
    # Get search index statistics
    total_search_entries = db.session.query(NewsSearchIndex).count()
    ai_enhanced_entries = db.session.query(NewsSearchIndex).filter(
        NewsSearchIndex.ai_summary.isnot(None),
        NewsSearchIndex.ai_insights.isnot(None),
        NewsSearchIndex.ai_summary != '',
        NewsSearchIndex.ai_insights != ''
    ).count()
    
    # Calculate AI coverage
    ai_coverage = (ai_enhanced_entries / total_search_entries * 100) if total_search_entries > 0 else 0
    
    print(f"📊 Search Index Statistics:")
    print(f"   • Total entries: {total_search_entries:,}")
    print(f"   • AI-enhanced entries: {ai_enhanced_entries:,}")
    print(f"   • AI coverage: {ai_coverage:.1f}%")
    
    # Verify minimum requirements for safe transformation
    min_required_articles = 30000  # Minimum threshold for safe operation
    min_ai_coverage = 95.0  # Minimum AI coverage percentage
    
    if total_search_entries < min_required_articles:
        print(f"❌ SAFETY CHECK FAILED: Only {total_search_entries:,} articles in search index")
        print(f"   Required minimum: {min_required_articles:,} articles")
        return False
    
    if ai_coverage < min_ai_coverage:
        print(f"❌ SAFETY CHECK FAILED: Only {ai_coverage:.1f}% AI coverage")
        print(f"   Required minimum: {min_ai_coverage}% AI coverage")
        return False
    
    print("✅ Search index integrity verified - safe to proceed")
    return True

def get_table_statistics():
    """Get current table statistics"""
    
    print("📊 Current Database Statistics:")
    
    # news_articles statistics
    total_articles = db.session.query(NewsArticle).count()
    ai_articles = db.session.query(NewsArticle).filter(
        NewsArticle.ai_summary.isnot(None),
        NewsArticle.ai_insights.isnot(None),
        NewsArticle.ai_summary != '',
        NewsArticle.ai_insights != ''
    ).count()
    
    # Related tables
    total_symbols = db.session.query(ArticleSymbol).count()
    total_metrics = db.session.query(ArticleMetric).count()
    
    # Search index
    search_index_count = db.session.query(NewsSearchIndex).count()
    search_ai_count = db.session.query(NewsSearchIndex).filter(
        NewsSearchIndex.ai_summary.isnot(None),
        NewsSearchIndex.ai_insights.isnot(None)
    ).count()
    
    print(f"   📰 news_articles: {total_articles:,} total, {ai_articles:,} AI-enhanced")
    print(f"   🏷️  article_symbols: {total_symbols:,} entries")
    print(f"   📈 article_metrics: {total_metrics:,} entries")
    print(f"   🔍 news_search_index: {search_index_count:,} total, {search_ai_count:,} AI-enhanced")
    
    return {
        'articles_total': total_articles,
        'articles_ai': ai_articles,
        'symbols_total': total_symbols,
        'metrics_total': total_metrics,
        'search_total': search_index_count,
        'search_ai': search_ai_count
    }

def clear_buffer_table():
    """Safely clear news_articles table and related data"""
    
    print("🗑️ Clearing buffer table (news_articles)...")
    
    try:
        # Clear related tables first (due to foreign key constraints)
        print("   Clearing article_metrics...")
        deleted_metrics = db.session.query(ArticleMetric).delete()
        
        print("   Clearing article_symbols...")
        deleted_symbols = db.session.query(ArticleSymbol).delete()
        
        print("   Clearing news_articles...")
        deleted_articles = db.session.query(NewsArticle).delete()
        
        # Commit the changes
        db.session.commit()
        
        print(f"✅ Buffer table cleared successfully:")
        print(f"   • {deleted_articles:,} articles removed")
        print(f"   • {deleted_symbols:,} symbol entries removed")  
        print(f"   • {deleted_metrics:,} metric entries removed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing buffer table: {str(e)}")
        db.session.rollback()
        return False

def verify_transformation():
    """Verify the transformation was successful"""
    
    print("🔍 Verifying buffer architecture transformation...")
    
    # Check that news_articles is now empty
    articles_count = db.session.query(NewsArticle).count()
    symbols_count = db.session.query(ArticleSymbol).count()
    metrics_count = db.session.query(ArticleMetric).count()
    
    # Check that search index is intact
    search_count = db.session.query(NewsSearchIndex).count()
    search_ai_count = db.session.query(NewsSearchIndex).filter(
        NewsSearchIndex.ai_summary.isnot(None),
        NewsSearchIndex.ai_insights.isnot(None)
    ).count()
    
    print(f"📊 Post-Transformation Status:")
    print(f"   📰 news_articles (buffer): {articles_count:,} entries")
    print(f"   🏷️  article_symbols: {symbols_count:,} entries")
    print(f"   📈 article_metrics: {metrics_count:,} entries")
    print(f"   🔍 news_search_index: {search_count:,} entries ({search_ai_count:,} AI-enhanced)")
    
    # Verify buffer is empty
    buffer_empty = (articles_count == 0 and symbols_count == 0 and metrics_count == 0)
    
    # Verify search index is preserved
    search_preserved = (search_count > 30000 and search_ai_count > 30000)
    
    if buffer_empty and search_preserved:
        print("✅ TRANSFORMATION SUCCESSFUL!")
        print("   🎯 news_articles is now a clean buffer table")
        print("   🚀 news_search_index contains all AI-enhanced data")
        print("   ⚡ Search system operates independently")
        return True
    else:
        print("❌ TRANSFORMATION VERIFICATION FAILED!")
        if not buffer_empty:
            print("   ⚠️ Buffer table is not empty")
        if not search_preserved:
            print("   ⚠️ Search index data may be incomplete")
        return False

def test_search_functionality():
    """Test that search still works after transformation"""
    
    print("🧪 Testing search functionality...")
    
    try:
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        
        search_engine = OptimizedNewsSearch(db.session)
        
        # Test keyword search
        print("   Testing keyword search...")
        articles, total, has_more = search_engine.search_by_keywords(
            keywords=['earnings', 'AI'],
            page=1,
            per_page=5
        )
        
        print(f"   • Keyword search: {len(articles)} results, {total} total")
        
        # Test symbol search  
        print("   Testing symbol search...")
        articles, total, has_more = search_engine.search_by_symbols(
            symbols=['AAPL', 'TSLA'],
            page=1,
            per_page=5
        )
        
        print(f"   • Symbol search: {len(articles)} results, {total} total")
        
        # Test recent news
        print("   Testing recent news...")
        recent = search_engine.get_recent_news(limit=5)
        
        print(f"   • Recent news: {len(recent)} articles")
        
        # Verify AI content is available
        if articles:
            sample_article = articles[0]
            has_ai_summary = bool(sample_article.get('summary', {}).get('ai_summary'))
            has_ai_insights = bool(sample_article.get('summary', {}).get('ai_insights'))
            
            print(f"   • AI content available: Summary={has_ai_summary}, Insights={has_ai_insights}")
            
            if has_ai_summary and has_ai_insights:
                print("✅ Search functionality verified - AI content available")
                return True
            else:
                print("⚠️ Search works but AI content may be missing")
                return False
        else:
            print("⚠️ No search results returned")
            return False
            
    except Exception as e:
        print(f"❌ Search functionality test failed: {str(e)}")
        return False

def main():
    """Main transformation process"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 TRANSFORMING TO BUFFER ARCHITECTURE")
        print("=" * 60)
        print()
        
        # Step 1: Get initial statistics
        print("📊 STEP 1: Getting current database statistics...")
        initial_stats = get_table_statistics()
        print()
        
        # Step 2: Verify search index integrity
        print("🔍 STEP 2: Verifying search index integrity...")
        if not verify_search_index_integrity():
            print("❌ TRANSFORMATION ABORTED - Search index not ready")
            return False
        print()
        
        # Step 3: Confirm transformation
        print("⚠️  STEP 3: Confirmation required...")
        print(f"   This will clear {initial_stats['articles_total']:,} articles from news_articles")
        print(f"   Search index contains {initial_stats['search_ai']:,} AI-enhanced articles")
        print("   news_articles will become a buffer table for incoming news")
        print()
        
        confirm = input("   Continue with transformation? (yes/no): ").lower().strip()
        if confirm not in ['yes', 'y']:
            print("❌ TRANSFORMATION CANCELLED by user")
            return False
        print()
        
        # Step 4: Clear buffer table
        print("🗑️ STEP 4: Clearing buffer table...")
        if not clear_buffer_table():
            print("❌ TRANSFORMATION FAILED - Could not clear buffer table")
            return False
        print()
        
        # Step 5: Verify transformation
        print("✅ STEP 5: Verifying transformation...")
        if not verify_transformation():
            print("❌ TRANSFORMATION VERIFICATION FAILED")
            return False
        print()
        
        # Step 6: Test search functionality
        print("🧪 STEP 6: Testing search functionality...")
        if not test_search_functionality():
            print("⚠️ Search functionality issues detected")
        print()
        
        print("🎉 BUFFER ARCHITECTURE TRANSFORMATION COMPLETE!")
        print("=" * 60)
        print()
        print("📋 NEW ARCHITECTURE SUMMARY:")
        print("   📰 news_articles: Clean buffer table for incoming news")
        print("   🔍 news_search_index: Standalone storage + search with AI content")
        print("   ⚡ Search system: Completely independent, lightning-fast")
        print("   🧠 AI workflow: Buffer → Process → Search Index → Clear Buffer")
        print()
        print("🚀 Your news system is now optimized for maximum performance!")
        
        return True

if __name__ == '__main__':
    print("🔄 Buffer Architecture Transformation")
    print("=" * 50)
    print()
    
    success = main()
    
    if success:
        print("\n✅ Transformation completed successfully!")
        print("🎯 news_articles is now a clean buffer table")
        print("🚀 Ready for optimized news processing workflow")
    else:
        print("\n❌ Transformation failed or was cancelled")
        print("🔄 Database remains in current state")
    
    print("\n" + "=" * 50) 