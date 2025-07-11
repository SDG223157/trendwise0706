#!/usr/bin/env python3
"""
Fix: Latest Search Content Bug

This fixes the issue where searching "latest" looks for articles containing 
the literal word "latest" instead of just applying the 3-day time filter.

The fix ensures "latest" is completely excluded from content search when
used as a time-based filter keyword.
"""

import sys
import os
sys.path.insert(0, '.')

def fix_latest_search_content_bug():
    """Fix the latest search to exclude 'latest' from content search"""
    
    file_path = 'app/utils/search/optimized_news_search.py'
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the problematic code section
        old_code = '''            for keyword in keywords:
                # Skip sentiment sorting keywords from content search
                if keyword.lower() in sentiment_sort_keywords:
                    logger.debug(f"🔄 Skipping sentiment sort keyword '{keyword}' from content search")
                    continue
                    
                if '"' in keyword:  # Exact phrase match
                    phrase = keyword.replace('"', '')
                    keyword_conditions.append(
                        or_(
                            NewsSearchIndex.title.like(f'%{phrase}%'),
                            NewsSearchIndex.ai_summary.like(f'%{phrase}%'),
                            NewsSearchIndex.ai_insights.like(f'%{phrase}%')
                        )
                    )
                else:  # Individual word match
                    # For special keywords like "latest", search mainly in title
                    if keyword.lower() in special_keywords:
                        keyword_conditions.append(
                            or_(
                                NewsSearchIndex.title.like(f'%{keyword}%'),
                                NewsSearchIndex.source.like(f'%{keyword}%')
                            )
                        )
                        logger.debug(f"🕐 Special keyword '{keyword}' - searching title/source")
                    else:
                        keyword_conditions.append(
                            or_(
                                NewsSearchIndex.title.like(f'%{keyword}%'),
                                NewsSearchIndex.ai_summary.like(f'%{keyword}%'),
                                NewsSearchIndex.ai_insights.like(f'%{keyword}%')
                            )
                        )'''
        
        new_code = '''            for keyword in keywords:
                # Skip sentiment sorting keywords from content search
                if keyword.lower() in sentiment_sort_keywords:
                    logger.debug(f"🔄 Skipping sentiment sort keyword '{keyword}' from content search")
                    continue
                
                # Skip time-based special keywords from content search (they're handled as filters)
                if keyword.lower() == 'latest':
                    logger.debug(f"🕐 Skipping time-based keyword '{keyword}' from content search - using as filter only")
                    continue
                    
                if '"' in keyword:  # Exact phrase match
                    phrase = keyword.replace('"', '')
                    keyword_conditions.append(
                        or_(
                            NewsSearchIndex.title.like(f'%{phrase}%'),
                            NewsSearchIndex.ai_summary.like(f'%{phrase}%'),
                            NewsSearchIndex.ai_insights.like(f'%{phrase}%')
                        )
                    )
                else:  # Individual word match
                    # For non-time special keywords like "news", "breaking", search mainly in title
                    if keyword.lower() in special_keywords and keyword.lower() != 'latest':
                        keyword_conditions.append(
                            or_(
                                NewsSearchIndex.title.like(f'%{keyword}%'),
                                NewsSearchIndex.source.like(f'%{keyword}%')
                            )
                        )
                        logger.debug(f"🕐 Special keyword '{keyword}' - searching title/source")
                    else:
                        keyword_conditions.append(
                            or_(
                                NewsSearchIndex.title.like(f'%{keyword}%'),
                                NewsSearchIndex.ai_summary.like(f'%{keyword}%'),
                                NewsSearchIndex.ai_insights.like(f'%{keyword}%')
                            )
                        )'''
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print("✅ FIXED: Latest search content bug resolved!")
            print("📁 Modified file:", file_path)
            print("\n🔧 Changes made:")
            print("   - 'latest' keyword now excluded from content search")
            print("   - Only applies 3-day time filter (as intended)")
            print("   - Should now show all recent articles instead of just 17")
            print("\n🔄 Restart your application for changes to take effect")
            print("\n📊 Expected results after fix:")
            print("   - 'latest' search should return ~1,809 articles (all recent)")
            print("   - Instead of just 17 articles containing 'latest' word")
            
        else:
            print("❌ Could not find the target code section to replace")
            print("The file might have been already modified or have a different structure")
            print("\n🔍 Looking for alternative patterns...")
            
            # Try to find a simpler pattern to fix
            simple_pattern = "if keyword.lower() in special_keywords:"
            if simple_pattern in content:
                print("✅ Found alternative pattern - manual fix needed")
                print(f"Look for: {simple_pattern}")
                print("Add this check before it:")
                print("    if keyword.lower() == 'latest':")
                print("        logger.debug(f\"🕐 Skipping time-based keyword '{keyword}' from content search\")")
                print("        continue")
            
    except Exception as e:
        print(f"❌ Error applying fix: {str(e)}")

if __name__ == "__main__":
    fix_latest_search_content_bug() 