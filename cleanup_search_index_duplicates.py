#!/usr/bin/env python3
"""
Cleanup Search Index Duplicates

This script removes duplicate entries from the news_search_index table
that were created before the duplicate prevention was implemented.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, NewsSearchIndex, NewsArticle
from sqlalchemy import text, func
from datetime import datetime

def cleanup_search_index_duplicates():
    """Remove duplicate entries from news_search_index table"""
    app = create_app()
    
    with app.app_context():
        print("🧹 Cleaning up Search Index Duplicates")
        print("=" * 50)
        
        # Check current state
        total_search_entries = NewsSearchIndex.query.count()
        total_ai_articles = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_summary != '',
            NewsArticle.ai_insights != ''
        ).count()
        
        print(f"📊 Current State:")
        print(f"   • Search index entries: {total_search_entries}")
        print(f"   • AI-processed articles: {total_ai_articles}")
        print(f"   • Potential duplicates: {total_search_entries - total_ai_articles}")
        
        # Find duplicates by external_id
        duplicate_query = text("""
            SELECT external_id, COUNT(*) as count
            FROM news_search_index 
            WHERE external_id IS NOT NULL
            GROUP BY external_id 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """)
        
        duplicates = db.session.execute(duplicate_query).fetchall()
        
        if not duplicates:
            print("✅ No duplicates found in search index!")
            return
        
        print(f"\n🔍 Found {len(duplicates)} external_ids with duplicates:")
        total_duplicate_entries = 0
        for dup in duplicates[:10]:  # Show first 10
            print(f"   • external_id '{dup.external_id}': {dup.count} entries")
            total_duplicate_entries += dup.count - 1  # -1 because we keep one
        
        if len(duplicates) > 10:
            print(f"   • ... and {len(duplicates) - 10} more")
        
        print(f"\n📊 Total duplicate entries to remove: {total_duplicate_entries}")
        
        # Ask for confirmation
        response = input("\n❓ Do you want to proceed with cleanup? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Cleanup cancelled")
            return
        
        # Remove duplicates - keep the most recent entry for each external_id
        print("\n🧹 Removing duplicates...")
        
        removed_count = 0
        
        for dup in duplicates:
            try:
                # Get all entries for this external_id, ordered by created_at DESC
                entries = NewsSearchIndex.query.filter_by(
                    external_id=dup.external_id
                ).order_by(NewsSearchIndex.created_at.desc()).all()
                
                # Keep the first (most recent) entry, remove the rest
                entries_to_remove = entries[1:]  # Skip the first one
                
                for entry in entries_to_remove:
                    db.session.delete(entry)
                    removed_count += 1
                
                if len(entries_to_remove) > 0:
                    print(f"   ✅ Removed {len(entries_to_remove)} duplicates for external_id: {dup.external_id}")
                
            except Exception as e:
                print(f"   ❌ Error processing external_id {dup.external_id}: {str(e)}")
                continue
        
        # Commit all changes
        print(f"\n💾 Committing changes...")
        db.session.commit()
        
        # Verify results
        new_total_entries = NewsSearchIndex.query.count()
        remaining_duplicates = db.session.execute(duplicate_query).fetchall()
        
        print(f"\n✅ Cleanup completed!")
        print(f"   • Entries removed: {removed_count}")
        print(f"   • Entries before: {total_search_entries}")
        print(f"   • Entries after: {new_total_entries}")
        print(f"   • Remaining duplicates: {len(remaining_duplicates)}")
        
        # Show final state
        final_ai_articles = NewsArticle.query.filter(
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_summary != '',
            NewsArticle.ai_insights != ''
        ).count()
        
        print(f"\n📊 Final State:")
        print(f"   • Search index entries: {new_total_entries}")
        print(f"   • AI-processed articles: {final_ai_articles}")
        print(f"   • Difference: {new_total_entries - final_ai_articles}")
        
        if new_total_entries <= final_ai_articles:
            print("✅ Search index is now clean - no more duplicates!")
        else:
            print("⚠️ Some entries may still need attention")

def analyze_search_index_integrity():
    """Analyze search index integrity without making changes"""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 Search Index Integrity Analysis")
        print("=" * 40)
        
        # Check for articles with multiple search index entries
        multi_entries_query = text("""
            SELECT a.external_id, a.title, COUNT(si.id) as search_entries
            FROM news_articles a
            LEFT JOIN news_search_index si ON a.external_id = si.external_id
            WHERE a.ai_summary IS NOT NULL 
            AND a.ai_insights IS NOT NULL
            GROUP BY a.external_id, a.title
            HAVING COUNT(si.id) > 1
            ORDER BY COUNT(si.id) DESC
            LIMIT 10
        """)
        
        multi_entries = db.session.execute(multi_entries_query).fetchall()
        
        if multi_entries:
            print(f"⚠️ Articles with multiple search index entries:")
            for entry in multi_entries:
                print(f"   • {entry.title[:60]}... ({entry.search_entries} entries)")
        else:
            print("✅ No articles with multiple search index entries found")
        
        # Check for orphaned search index entries
        orphaned_query = text("""
            SELECT si.external_id, si.title
            FROM news_search_index si
            LEFT JOIN news_articles a ON si.external_id = a.external_id
            WHERE a.external_id IS NULL
            LIMIT 10
        """)
        
        orphaned = db.session.execute(orphaned_query).fetchall()
        
        if orphaned:
            print(f"\n⚠️ Orphaned search index entries (no corresponding article):")
            for entry in orphaned:
                print(f"   • {entry.title[:60]}...")
        else:
            print("\n✅ No orphaned search index entries found")

if __name__ == "__main__":
    print("🧹 Search Index Cleanup Tool")
    print("=" * 50)
    
    # First analyze
    analyze_search_index_integrity()
    
    # Then cleanup
    cleanup_search_index_duplicates() 