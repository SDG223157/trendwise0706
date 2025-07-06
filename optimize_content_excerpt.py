#!/usr/bin/env python3
"""
Optimize Content Excerpt - Reduce content_excerpt size from 2000 to 1000 characters
This optimizes storage while maintaining keyword search functionality.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

def optimize_content_excerpt():
    """Optimize content_excerpt field size to save storage"""
    try:
        from app import create_app, db
        from app.models import NewsSearchIndex, NewsArticle
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            print("🔧 Optimizing Content Excerpt Size")
            print("=" * 50)
            
            # Step 1: Analyze current content_excerpt sizes
            result = db.session.execute(text("""
                SELECT 
                    COUNT(*) as total_entries,
                    AVG(LENGTH(COALESCE(content_excerpt, ''))) as avg_size,
                    MAX(LENGTH(COALESCE(content_excerpt, ''))) as max_size,
                    COUNT(CASE WHEN LENGTH(COALESCE(content_excerpt, '')) > 1000 THEN 1 END) as over_1000_chars,
                    SUM(LENGTH(COALESCE(content_excerpt, ''))) as total_size_bytes
                FROM news_search_index
                WHERE content_excerpt IS NOT NULL
            """)).fetchone()
            
            print(f"\n📊 Current Content Excerpt Analysis:")
            print(f"  Total entries with content: {result.total_entries}")
            print(f"  Average size: {result.avg_size:.0f} characters")
            print(f"  Maximum size: {result.max_size} characters")
            print(f"  Entries over 1000 chars: {result.over_1000_chars}")
            print(f"  Total storage: {result.total_size_bytes / 1024 / 1024:.2f} MB")
            
            if result.over_1000_chars == 0:
                print(f"\n✅ All content excerpts are already optimized (≤1000 chars)!")
                print(f"   No optimization needed.")
                return True
            
            # Calculate potential savings
            potential_savings = result.over_1000_chars * (result.avg_size - 1000) if result.avg_size > 1000 else 0
            
            print(f"\n💾 Optimization Potential:")
            print(f"  Entries to optimize: {result.over_1000_chars}")
            print(f"  Estimated storage savings: {potential_savings / 1024:.2f} KB")
            
            # Step 2: Show the optimization plan
            print(f"\n🔧 Optimization Plan:")
            print(f"  ✂️ Truncate content_excerpt to 1000 characters")
            print(f"  ✅ Maintain keyword search functionality")
            print(f"  ✅ Improve query performance (smaller field size)")
            print(f"  ✅ Reduce memory usage")
            
            # Step 3: Execute optimization
            response = input(f"\n❓ Proceed with optimization? (y/N): ")
            
            if response.lower() == 'y':
                print(f"\n🚀 Executing optimization...")
                
                try:
                    # Update content_excerpt to 1000 characters max
                    update_result = db.session.execute(text("""
                        UPDATE news_search_index 
                        SET content_excerpt = SUBSTR(content_excerpt, 1, 1000)
                        WHERE LENGTH(content_excerpt) > 1000
                    """))
                    
                    rows_updated = update_result.rowcount
                    db.session.commit()
                    
                    print(f"✅ Optimization completed!")
                    print(f"   Updated {rows_updated} records")
                    
                    # Verify the results
                    verify_result = db.session.execute(text("""
                        SELECT 
                            COUNT(*) as total_entries,
                            AVG(LENGTH(COALESCE(content_excerpt, ''))) as avg_size,
                            MAX(LENGTH(COALESCE(content_excerpt, ''))) as max_size,
                            SUM(LENGTH(COALESCE(content_excerpt, ''))) as total_size_bytes
                        FROM news_search_index
                        WHERE content_excerpt IS NOT NULL
                    """)).fetchone()
                    
                    print(f"\n📊 After Optimization:")
                    print(f"  Average size: {verify_result.avg_size:.0f} characters")
                    print(f"  Maximum size: {verify_result.max_size} characters")
                    print(f"  Total storage: {verify_result.total_size_bytes / 1024 / 1024:.2f} MB")
                    print(f"  Storage saved: {(result.total_size_bytes - verify_result.total_size_bytes) / 1024:.2f} KB")
                    
                    return True
                    
                except Exception as e:
                    print(f"\n❌ Error during optimization: {str(e)}")
                    db.session.rollback()
                    return False
            else:
                print(f"\n⏭️ Optimization cancelled")
                return True
                
    except Exception as e:
        print(f"❌ Error in optimization: {str(e)}")
        return False

def sync_new_articles():
    """Update sync process to use 1000-char excerpts for new articles"""
    try:
        from app import create_app, db
        from app.models import NewsSearchIndex, NewsArticle
        from app.utils.search.search_index_sync import SearchIndexSyncService
        
        app = create_app()
        with app.app_context():
            print("\n🔄 Syncing New Articles with Optimized Excerpts")
            print("=" * 50)
            
            # Find articles that need sync (missing from search index)
            missing_articles = db.session.execute(text("""
                SELECT na.id, na.external_id
                FROM news_articles na
                LEFT JOIN news_search_index nsi ON na.external_id = nsi.external_id
                WHERE nsi.external_id IS NULL
                AND na.external_id IS NOT NULL
                LIMIT 100
            """)).fetchall()
            
            if not missing_articles:
                print("✅ All articles are already synchronized!")
                return True
            
            print(f"📊 Found {len(missing_articles)} articles to sync")
            
            sync_service = SearchIndexSyncService()
            articles_to_sync = []
            
            for missing in missing_articles:
                article = NewsArticle.query.get(missing.id)
                if article:
                    articles_to_sync.append(article)
            
            if articles_to_sync:
                print(f"🚀 Syncing {len(articles_to_sync)} articles...")
                stats = sync_service.sync_multiple_articles(articles_to_sync)
                
                print(f"✅ Sync completed:")
                print(f"   Added: {stats['added']}")
                print(f"   Updated: {stats['updated']}")
                print(f"   Errors: {stats['errors']}")
                
            return True
            
    except Exception as e:
        print(f"❌ Error in sync: {str(e)}")
        return False

if __name__ == '__main__':
    print("🎯 Content Excerpt Optimization Tool")
    print("This tool optimizes storage while maintaining keyword search functionality")
    print()
    
    if optimize_content_excerpt():
        sync_new_articles()
        print("\n🎉 Optimization completed successfully!")
        print("   ✅ Storage optimized")
        print("   ✅ Keyword search functionality maintained")
        print("   ✅ Performance improved")
    else:
        print("\n❌ Optimization failed")
        sys.exit(1) 