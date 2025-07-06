#!/usr/bin/env python3
"""
Quick AI Status Check
Simple script to check if articles have AI processing completed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from datetime import datetime, timedelta

def check_ai_status():
    """Check current AI processing status"""
    app = create_app()
    
    with app.app_context():
        # Get counts
        total_articles = NewsArticle.query.count()
        
        # Articles with AI content
        with_summary = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_summary != ''
        ).count()
        
        with_insights = NewsArticle.query.filter(
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_insights != ''
        ).count()
        
        with_sentiment = NewsArticle.query.filter(
            NewsArticle.ai_sentiment_rating.isnot(None)
        ).count()
        
        # Articles without AI content
        without_ai = NewsArticle.query.filter(
            NewsArticle.ai_summary.is_(None)
        ).count()
        
        # Search index count
        search_index_count = NewsSearchIndex.query.count()
        
        print(f"📊 AI Processing Status:")
        print(f"   Total articles: {total_articles}")
        print(f"   With AI summaries: {with_summary}")
        print(f"   With AI insights: {with_insights}")
        print(f"   With AI sentiment: {with_sentiment}")
        print(f"   Without AI: {without_ai}")
        print(f"   Search index entries: {search_index_count}")
        
        # Show sample articles
        print(f"\n📄 Sample Articles:")
        
        # Get 5 most recent articles
        recent_articles = NewsArticle.query.order_by(NewsArticle.id.desc()).limit(5).all()
        
        for article in recent_articles:
            print(f"   • Article {article.id}: {article.title[:80]}...")
            print(f"     Created: {article.created_at}")
            print(f"     AI Summary: {'✅' if article.ai_summary else '❌'}")
            print(f"     AI Insights: {'✅' if article.ai_insights else '❌'}")
            print(f"     AI Sentiment: {'✅' if article.ai_sentiment_rating is not None else '❌'} ({article.ai_sentiment_rating})")
            print(f"     Content length: {len(article.content) if article.content else 0} chars")
            print()
            
        # Check recent activity - use created_at since updated_at doesn't exist
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_articles = NewsArticle.query.filter(
            NewsArticle.created_at >= recent_cutoff
        ).count()
        
        print(f"⏰ Recent Activity (last 1 hour): {recent_articles} articles created")
        
        # Check environment variables
        api_key = os.getenv("OPENROUTER_API_KEY")
        print(f"🔑 OpenRouter API Key: {'✅ Set' if api_key else '❌ Missing'}")
        
        # Analysis
        print(f"\n🔍 Analysis:")
        if total_articles == 0:
            print("   ❌ No articles found - need to fetch news first")
        elif without_ai == 0:
            print("   ✅ All articles have AI processing completed!")
        elif not api_key:
            print("   ❌ OpenRouter API key is missing - AI processing cannot work")
        else:
            print(f"   ⚠️ {without_ai} articles still need AI processing")
            print("   💡 Check AI scheduler status or run manual processing")

if __name__ == "__main__":
    check_ai_status() 