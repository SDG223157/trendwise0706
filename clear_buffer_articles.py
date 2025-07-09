#!/usr/bin/env python3
"""
Buffer Articles Clearing Utility

This script safely clears the news_articles buffer table while preserving
the permanent articles in the news_search_index table.
"""

import sys
import os
sys.path.insert(0, '.')

def clear_buffer_articles():
    """Clear all articles from the news_articles buffer table"""
    print("🗑️ TrendWise Buffer Articles Clearing Utility")
    print("="*50)
    print()
    
    try:
        from app import create_app, db
        from app.models import NewsArticle, NewsSearchIndex
        
        app = create_app()
        
        with app.app_context():
            # Get counts before clearing
            buffer_count = NewsArticle.query.count()
            search_index_count = NewsSearchIndex.query.count()
            
            print(f"📊 Current Status:")
            print(f"   Buffer Table (news_articles): {buffer_count:,} articles")
            print(f"   Search Index (news_search_index): {search_index_count:,} articles")
            print()
            
            if buffer_count == 0:
                print("✅ Buffer table is already empty - nothing to clear")
                return
                
            print("⚠️ This will clear ALL articles from the buffer table")
            print("💡 Permanent articles in the search index will remain safe")
            print()
            
            confirmation = input("Type 'CLEAR BUFFER' to proceed or anything else to cancel: ")
            
            if confirmation != "CLEAR BUFFER":
                print("❌ Buffer clearing cancelled.")
                return
            
            print()
            print("🗑️ Clearing buffer articles...")
            
            # Clear all articles from buffer
            cleared_count = NewsArticle.query.delete()
            db.session.commit()
            
            print(f"✅ Successfully cleared {cleared_count:,} articles from buffer table")
            print(f"💾 {search_index_count:,} permanent articles remain in search index")
            print()
            print("🎯 Buffer clearing completed successfully!")
            
    except Exception as e:
        print(f"❌ Error clearing buffer articles: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    clear_buffer_articles()

if __name__ == "__main__":
    main() 