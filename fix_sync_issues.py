#!/usr/bin/env python3
"""
Fix Sync Issues Script

This script fixes common sync issues identified by investigate_sync_issue.py:
- Removes orphaned search index entries
- Cleans up duplicate entries
- Forces sync of AI-processed articles
- Validates data consistency
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path
sys.path.append(os.getcwd())

def fix_sync_issues(confirm=True):
    """Fix sync issues with confirmation prompts"""
    
    # Database connection
    db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        print("🔧 SYNC ISSUES FIX SCRIPT")
        print("=" * 50)
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. CHECK FOR ORPHANED SEARCH INDEX ENTRIES
        print("🔍 STEP 1: Checking for orphaned search index entries")
        print("-" * 50)
        
        orphaned_count = session.execute(text('''
            SELECT COUNT(*) FROM news_search_index nsi
            LEFT JOIN news_articles na ON nsi.external_id = na.external_id
            WHERE na.external_id IS NULL
        ''')).scalar()
        
        print(f"Found {orphaned_count:,} orphaned search index entries")
        
        if orphaned_count > 0:
            if confirm:
                response = input(f"Delete {orphaned_count:,} orphaned entries? (y/N): ")
                if response.lower() != 'y':
                    print("Skipped orphaned entry cleanup")
                    orphaned_count = 0
            
            if orphaned_count > 0:
                print(f"🗑️ Deleting {orphaned_count:,} orphaned search index entries...")
                
                delete_result = session.execute(text('''
                    DELETE nsi FROM news_search_index nsi
                    LEFT JOIN news_articles na ON nsi.external_id = na.external_id
                    WHERE na.external_id IS NULL
                '''))
                
                session.commit()
                print(f"✅ Deleted {delete_result.rowcount:,} orphaned entries")
        
        # 2. CHECK FOR DUPLICATE SEARCH INDEX ENTRIES
        print(f"\n🔄 STEP 2: Checking for duplicate search index entries")
        print("-" * 50)
        
        duplicates = session.execute(text('''
            SELECT external_id, COUNT(*) as count, MIN(id) as keep_id
            FROM news_search_index 
            WHERE external_id IS NOT NULL
            GROUP BY external_id 
            HAVING COUNT(*) > 1
        ''')).fetchall()
        
        duplicate_count = len(duplicates)
        total_duplicates = sum(dup.count - 1 for dup in duplicates)  # -1 because we keep one
        
        print(f"Found {duplicate_count:,} external_ids with duplicates ({total_duplicates:,} entries to remove)")
        
        if duplicate_count > 0:
            if confirm:
                response = input(f"Remove {total_duplicates:,} duplicate entries? (y/N): ")
                if response.lower() != 'y':
                    print("Skipped duplicate cleanup")
                    duplicate_count = 0
            
            if duplicate_count > 0:
                print(f"🗑️ Removing {total_duplicates:,} duplicate search index entries...")
                
                removed_count = 0
                for dup in duplicates:
                    # Keep the entry with the lowest ID (oldest), delete the rest
                    delete_result = session.execute(text('''
                        DELETE FROM news_search_index 
                        WHERE external_id = :external_id 
                        AND id != :keep_id
                    '''), {
                        'external_id': dup.external_id,
                        'keep_id': dup.keep_id
                    })
                    removed_count += delete_result.rowcount
                
                session.commit()
                print(f"✅ Removed {removed_count:,} duplicate entries")
        
        # 3. FORCE SYNC AI-PROCESSED ARTICLES
        print(f"\n🔄 STEP 3: Force sync AI-processed articles")
        print("-" * 50)
        
        unsynced_articles = session.execute(text('''
            SELECT na.id, na.external_id, na.title, na.published_at,
                   na.ai_summary, na.ai_insights, na.ai_sentiment_rating
            FROM news_articles na
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_sentiment_rating IS NOT NULL
            AND na.ai_summary != ''
            AND na.ai_insights != ''
            AND na.external_id IS NOT NULL
            AND na.published_at IS NOT NULL
            AND na.external_id NOT IN (
                SELECT DISTINCT external_id FROM news_search_index 
                WHERE external_id IS NOT NULL
            )
            ORDER BY na.id DESC
        ''')).fetchall()
        
        unsynced_count = len(unsynced_articles)
        print(f"Found {unsynced_count:,} AI-processed articles that need syncing")
        
        if unsynced_count > 0:
            if confirm:
                response = input(f"Force sync {unsynced_count:,} articles? (y/N): ")
                if response.lower() != 'y':
                    print("Skipped force sync")
                    unsynced_count = 0
            
            if unsynced_count > 0:
                print(f"🚀 Force syncing {unsynced_count:,} AI-processed articles...")
                
                synced_count = 0
                failed_count = 0
                
                for article in unsynced_articles:
                    try:
                        # Get symbols for this article
                        symbols = session.execute(text('''
                            SELECT symbol FROM article_symbols 
                            WHERE article_id = :article_id
                        '''), {'article_id': article.id}).fetchall()
                        
                        symbols_json = str([s.symbol for s in symbols])
                        
                        # Create content excerpt
                        content_excerpt = ""
                        if hasattr(article, 'content') and article.content:
                            content_excerpt = article.content[:500] + "..." if len(article.content) > 500 else article.content
                        
                        # Insert into search index using ON DUPLICATE KEY UPDATE
                        insert_result = session.execute(text('''
                            INSERT INTO news_search_index (
                                external_id, article_id, title, content_excerpt, 
                                published_at, source, ai_summary, ai_insights, 
                                ai_sentiment_rating, symbols_json, created_at, updated_at
                            ) VALUES (
                                :external_id, :article_id, :title, :content_excerpt,
                                :published_at, 'Unknown', :ai_summary, :ai_insights,
                                :ai_sentiment_rating, :symbols_json, NOW(), NOW()
                            )
                            ON DUPLICATE KEY UPDATE
                                article_id = VALUES(article_id),
                                title = VALUES(title),
                                ai_summary = VALUES(ai_summary),
                                ai_insights = VALUES(ai_insights),
                                ai_sentiment_rating = VALUES(ai_sentiment_rating),
                                updated_at = NOW()
                        '''), {
                            'external_id': article.external_id,
                            'article_id': article.id,
                            'title': article.title or '',
                            'content_excerpt': content_excerpt,
                            'published_at': article.published_at,
                            'ai_summary': article.ai_summary or '',
                            'ai_insights': article.ai_insights or '',
                            'ai_sentiment_rating': article.ai_sentiment_rating or 3,
                            'symbols_json': symbols_json
                        })
                        
                        synced_count += 1
                        
                        if synced_count % 100 == 0:
                            print(f"   Synced {synced_count:,}/{unsynced_count:,} articles...")
                            
                    except Exception as e:
                        failed_count += 1
                        print(f"   ❌ Failed to sync article {article.id}: {str(e)}")
                        continue
                
                session.commit()
                print(f"✅ Force sync completed: {synced_count:,} synced, {failed_count:,} failed")
        
        # 4. FINAL VALIDATION
        print(f"\n✅ STEP 4: Final validation")
        print("-" * 50)
        
        # Recheck counts
        final_articles = session.execute(text('SELECT COUNT(*) FROM news_articles')).scalar()
        final_search_index = session.execute(text('SELECT COUNT(*) FROM news_search_index')).scalar()
        final_ai_processed = session.execute(text('''
            SELECT COUNT(*) FROM news_articles 
            WHERE ai_summary IS NOT NULL 
            AND ai_insights IS NOT NULL 
            AND ai_sentiment_rating IS NOT NULL
        ''')).scalar()
        final_synced = session.execute(text('''
            SELECT COUNT(DISTINCT na.external_id) FROM news_articles na
            INNER JOIN news_search_index nsi ON na.external_id = nsi.external_id
            WHERE na.ai_summary IS NOT NULL 
            AND na.ai_insights IS NOT NULL 
            AND na.ai_sentiment_rating IS NOT NULL
        ''')).scalar()
        
        print(f"Final counts:")
        print(f"  Articles: {final_articles:,}")
        print(f"  Search index entries: {final_search_index:,}")
        print(f"  AI-processed articles: {final_ai_processed:,}")
        print(f"  Successfully synced: {final_synced:,}")
        
        if final_ai_processed > 0:
            sync_rate = (final_synced / final_ai_processed) * 100
            print(f"  Sync success rate: {sync_rate:.1f}%")
            
            if sync_rate >= 95:
                print("✅ Sync performance is now healthy!")
            else:
                remaining_unsynced = final_ai_processed - final_synced
                print(f"⚠️ Still {remaining_unsynced:,} articles not synced")
        
        # Check for remaining duplicates
        remaining_duplicates = session.execute(text('''
            SELECT COUNT(*) - COUNT(DISTINCT external_id) FROM news_search_index
            WHERE external_id IS NOT NULL
        ''')).scalar()
        
        if remaining_duplicates == 0:
            print("✅ No duplicate external_ids detected")
        else:
            print(f"⚠️ Still {remaining_duplicates:,} duplicate entries remain")
        
        print(f"\n🎯 SUMMARY:")
        print(f"  • Orphaned entries cleaned: {orphaned_count > 0}")
        print(f"  • Duplicates cleaned: {duplicate_count > 0}")
        print(f"  • Articles force synced: {unsynced_count > 0}")
        print(f"  • Final sync rate: {sync_rate:.1f}% " if final_ai_processed > 0 else "  • No AI-processed articles found")
        
    except Exception as e:
        print(f"❌ Error during sync fix: {str(e)}")
        session.rollback()
    finally:
        session.close()

def main():
    """Main execution with safety prompt"""
    print("🔧 SYNC ISSUES FIX SCRIPT")
    print("=" * 50)
    print("This script will:")
    print("  1. Remove orphaned search index entries")
    print("  2. Clean up duplicate entries") 
    print("  3. Force sync AI-processed articles")
    print("  4. Validate final state")
    print()
    
    response = input("Continue with fixes? (y/N): ")
    if response.lower() == 'y':
        fix_sync_issues(confirm=True)
    else:
        print("Operation cancelled")

if __name__ == "__main__":
    main() 