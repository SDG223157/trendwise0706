#!/usr/bin/env python3
"""
Quick Fix: Change "Latest" Search Period from 3 to 7 days

This fix changes the "latest" keyword filter from 3 days to 7 days
to accommodate databases where articles are older.
"""

import sys
import os
sys.path.insert(0, '.')

def fix_latest_search_period():
    """Change the latest search filter from 3 days to 7 days"""
    
    file_path = 'app/utils/search/optimized_news_search.py'
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace 3 days with 7 days in the latest filter
        old_code = 'three_days_ago = datetime.now() - timedelta(days=3)'
        new_code = 'seven_days_ago = datetime.now() - timedelta(days=7)'
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            content = content.replace('three_days_ago', 'seven_days_ago')
            content = content.replace('filtering to last 3 days', 'filtering to last 7 days')
            content = content.replace('last 3 days', 'last 7 days')
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print("✅ Fixed: Changed 'latest' filter from 3 days to 7 days")
            print("📁 Modified file:", file_path)
            print("\n🔄 You need to restart your application for changes to take effect")
            
        else:
            print("❌ Could not find the target code to replace")
            print("The file might have been already modified or have a different structure")
    
    except Exception as e:
        print(f"❌ Error applying fix: {str(e)}")

if __name__ == "__main__":
    fix_latest_search_period() 