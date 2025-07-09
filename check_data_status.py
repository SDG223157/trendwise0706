#!/usr/bin/env python3
"""
Quick Data Status Check for AI Keyword Search System
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.models import NewsSearchIndex, NewsKeyword, ArticleKeyword

def main():
    app = create_app()
    
    with app.app_context():
        print("📊 TrendWise AI Keyword Search Data Status Check")
        print("=" * 50)
        
        # Check PERMANENT news_search_index table (not buffer news_articles)
        total_articles = NewsSearchIndex.query.count()
        ai_articles = NewsSearchIndex.query.filter(
            NewsSearchIndex.ai_summary.isnot(None),
            NewsSearchIndex.ai_summary != ''
        ).count()
        
        print(f"📰 Total articles in news_search_index (permanent): {total_articles}")
        print(f"🤖 Articles with AI summaries: {ai_articles}")
        
        # Check keywords
        total_keywords = NewsKeyword.query.count()
        article_keyword_links = ArticleKeyword.query.count()
        
        print(f"🔍 Total keywords: {total_keywords}")
        print(f"🔗 Article-keyword links: {article_keyword_links}")
        
        print("\n🎯 Next Steps:")
        
        if total_articles == 0:
            print("⚠️  No articles found in news_search_index (permanent table).")
            print("   This means your news fetching system needs to populate the permanent table.")
            print("   Recommendation: Check your news sync process.")
        elif ai_articles == 0:
            print("⚠️  No articles with AI summaries found in news_search_index.")
            print("   Recommendation: Run the fixed setup script to create sample keywords:")
            print("   python3 coolify_setup_ai_search_fixed.py")
        elif total_keywords == 0:
            print("⚠️  Articles found but no keywords extracted yet.")
            print("   Recommendation: Extract keywords from your permanent news_search_index:")
            print("   python3 extract_keywords_from_news_search_index.py --test")
        else:
            print("✅ System has data! Test the search functionality:")
            print("   curl 'http://your-domain/news/api/suggestions?q=earnings'")
        
        # Show sample of what we have
        if ai_articles > 0:
            print(f"\n📋 Sample articles with AI content from news_search_index:")
            sample_articles = NewsSearchIndex.query.filter(
                NewsSearchIndex.ai_summary.isnot(None),
                NewsSearchIndex.ai_summary != ''
            ).limit(3).all()
            
            for article in sample_articles:
                print(f"   - {article.title[:60]}...")
        
        if total_keywords > 0:
            print(f"\n🔍 Sample keywords:")
            sample_keywords = NewsKeyword.query.limit(5).all()
            for kw in sample_keywords:
                print(f"   - {kw.keyword} ({kw.category}) - freq: {kw.frequency}")
        
        # Architecture reminder
        print(f"\n💡 Architecture Note:")
        print(f"   - news_search_index = PERMANENT table for search")
        print(f"   - news_articles = BUFFER table (clears after AI processing)")
        print(f"   - AI keyword extraction uses news_search_index (permanent)")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 