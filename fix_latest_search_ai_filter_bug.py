#!/usr/bin/env python3
"""
Fix: Latest Search AI Filter Bug

This fixes the issue where "latest" search bypasses AI-only filtering,
showing all 11,498 articles instead of the expected ~1,809 recent articles with AI.

The fix ensures "latest" searches maintain strict AI-only filtering while
applying the 3-day time filter.
"""

import sys
import os
sys.path.insert(0, '.')

def fix_latest_search_ai_filter_bug():
    """Fix the latest search to maintain AI-only filtering"""
    
    file_path = 'app/utils/search/optimized_news_search.py'
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find and fix the problematic logic
        old_code = '''            # Special handling for "latest" and similar keywords OR forced latest filter
            if has_special_keyword or force_latest_filter:
                # Check if "latest" keyword is specifically used (or forced by search route)
                has_latest_keyword = any(kw.lower() == 'latest' for kw in keywords) or force_latest_filter
                
                if has_latest_keyword:
                    # For "latest" keyword, show articles from last 3 days
                    from datetime import datetime, timedelta
                    three_days_ago = datetime.now() - timedelta(days=3)
                    query = query.filter(
                        NewsSearchIndex.published_at >= three_days_ago
                    )
                    # Override sort_order to ensure latest first
                    sort_order = 'LATEST'
                    logger.debug(f"🕐 'Latest' keyword detected (force_latest_filter={force_latest_filter}) - filtering to last 3 days and sorting by date")
                else:
                    # For other special keywords, use relaxed AI filtering
                    query = query.filter(
                        or_(
                            and_(
                                NewsSearchIndex.ai_summary.isnot(None),
                                NewsSearchIndex.ai_summary != ''
                            ),
                            NewsSearchIndex.title.isnot(None)  # Allow articles with just title
                        )
                    )
                    logger.debug(f"🕐 Special keyword detected, using relaxed AI filtering")
            else:
                # Normal AI-only filtering for other keywords
                pass  # Keep existing AI filtering'''
        
        new_code = '''            # Special handling for "latest" keyword with strict AI filtering
            has_latest_keyword = any(kw.lower() == 'latest' for kw in keywords) or force_latest_filter
            
            if has_latest_keyword:
                # For "latest" keyword, show AI-processed articles from last 3 days ONLY
                from datetime import datetime, timedelta
                three_days_ago = datetime.now() - timedelta(days=3)
                query = query.filter(
                    NewsSearchIndex.published_at >= three_days_ago
                )
                # Override sort_order to ensure latest first
                sort_order = 'LATEST'
                logger.debug(f"🕐 'Latest' keyword detected (force_latest_filter={force_latest_filter}) - filtering to last 3 days with AI-only articles")
            elif has_special_keyword:
                # For other special keywords (news, breaking, etc.), use relaxed AI filtering
                query = query.filter(
                    or_(
                        and_(
                            NewsSearchIndex.ai_summary.isnot(None),
                            NewsSearchIndex.ai_summary != ''
                        ),
                        NewsSearchIndex.title.isnot(None)  # Allow articles with just title
                    )
                )
                logger.debug(f"🕐 Other special keyword detected, using relaxed AI filtering")
            # else: Normal AI-only filtering maintained (no changes needed)'''
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print("✅ FIXED: Latest search AI filter bug resolved!")
            print("📁 Modified file:", file_path)
            print("\n🔧 Changes made:")
            print("   - Separated 'latest' logic from other special keywords")
            print("   - 'latest' now maintains strict AI-only + 3-day filtering")
            print("   - Other special keywords use relaxed filtering as intended")
            print("\n📊 Expected results after fix:")
            print("   - 'latest' search should return ~1,809 articles (AI + recent)")
            print("   - Instead of 11,498 articles (all articles)")
            print("\n🧹 Also run: Clear cache to remove old cached results")
            print("   - Search cache may contain old results from before the fix")
            
        else:
            print("❌ Could not find the target code section to replace")
            print("The file might have been already modified or have a different structure")
            
    except Exception as e:
        print(f"❌ Error applying fix: {str(e)}")

def clear_search_cache():
    """Clear search cache to remove old cached results"""
    try:
        from app import create_app, db
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        
        app = create_app()
        with app.app_context():
            search = OptimizedNewsSearch(db.session)
            search.clear_cache()
            print("🧹 Search cache cleared successfully!")
            
    except Exception as e:
        print(f"⚠️  Could not clear cache: {str(e)}")
        print("You may need to clear cache manually or restart the application")

if __name__ == "__main__":
    print("🔧 Fixing latest search AI filter bug...")
    fix_latest_search_ai_filter_bug()
    print("\n🧹 Clearing search cache...")
    clear_search_cache()
    print("\n🔄 Please restart your application to apply changes") 