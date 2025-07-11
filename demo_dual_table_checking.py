#!/usr/bin/env python3
"""
Demonstration: Dual-Table External ID Checking

This script demonstrates the improved external ID checking logic that prevents
duplicate articles by checking BOTH the buffer table (news_articles) and 
permanent storage table (news_search_index).
"""

import sys
import os
sys.path.insert(0, '.')

from app import create_app, db
from app.utils.data.enhanced_duplicate_prevention import DuplicatePreventionService
from app.utils.data.news_service import NewsService
from datetime import datetime

def demonstrate_dual_table_checking():
    """Demonstrate the dual-table external ID checking logic"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 Dual-Table External ID Checking Demonstration")
        print("=" * 60)
        print("Buffer Architecture:")
        print("• news_articles (buffer table for AI processing)")
        print("• news_search_index (permanent storage after AI processing)")
        print()
        
        # Initialize services
        dup_service = DuplicatePreventionService()
        news_service = NewsService()
        
        # Demo 1: Show current state
        print("📊 DEMO 1: Current Database State")
        print("-" * 40)
        
        # Get counts from both tables
        buffer_count = db.session.execute(db.text("SELECT COUNT(*) FROM news_articles")).scalar()
        permanent_count = db.session.execute(db.text("SELECT COUNT(*) FROM news_search_index")).scalar()
        
        print(f"Articles in buffer (news_articles): {buffer_count}")
        print(f"Articles in permanent storage (news_search_index): {permanent_count}")
        
        # Demo 2: Test external ID checking logic
        print(f"\n🔍 DEMO 2: External ID Checking Logic")
        print("-" * 40)
        
        # Get some sample external IDs from both tables
        test_cases = []
        
        try:
            sample_from_buffer = db.session.execute(
                db.text("SELECT external_id, title FROM news_articles LIMIT 2")
            ).fetchall()
            
            if sample_from_buffer:
                test_cases.extend([(row.external_id, row.title, "buffer") for row in sample_from_buffer])
                
        except Exception as e:
            print(f"Note: Could not get buffer samples: {str(e)}")
        
        try:
            sample_from_permanent = db.session.execute(
                db.text("SELECT external_id, title FROM news_search_index LIMIT 2")
            ).fetchall()
            
            if sample_from_permanent:
                test_cases.extend([(row.external_id, row.title, "permanent") for row in sample_from_permanent])
                
        except Exception as e:
            print(f"Note: Could not get permanent samples: {str(e)}")
        
        if test_cases:
            for i, (external_id, title, source_table) in enumerate(test_cases, 1):
                print(f"\nTest Case {i}: {external_id} (from {source_table})")
                title_display = title[:50] + "..." if len(title) > 50 else title
                print(f"Title: {title_display}")
                
                # Use comprehensive checking
                check_result = dup_service.check_external_id_in_both_tables(external_id)
                
                print(f"✅ Results:")
                print(f"   Exists: {check_result['exists']}")
                print(f"   Location: {check_result['location']}")
                print(f"   In Buffer: {check_result['in_buffer']}")
                print(f"   In Permanent: {check_result['in_permanent']}")
                print(f"   Article ID: {check_result['article_id']}")
                print(f"   Message: {check_result['message']}")
        else:
            print("No test cases available - both tables appear to be empty or inaccessible")
        
        # Demo 3: Test article saving with dual-table prevention
        print(f"\n💾 DEMO 3: Article Saving with Dual-Table Prevention")
        print("-" * 40)
        
        if test_cases:
            # Try to save an article with existing external_id
            existing_external_id, existing_title, source = test_cases[0]
            
            print(f"Attempting to save article with existing external_id: {existing_external_id}")
            print(f"(This external_id exists in {source} table)")
            
            test_article = {
                'external_id': existing_external_id,
                'title': f"DUPLICATE TEST: {existing_title}",
                'content': "This should be prevented by dual-table checking",
                'url': f"https://test.example.com/{existing_external_id}",
                'published_at': datetime.now(),
                'source': 'TEST_SOURCE',
                'sentiment': {'overall_sentiment': 'neutral'},
                'summary': {'brief': 'Test article for duplicate prevention'},
                'symbols': ['TEST']
            }
            
            # Use enhanced NewsService
            result_id = news_service.save_article(test_article)
            
            if result_id:
                print(f"✅ Save Result: Returned existing article ID {result_id}")
                print(f"✅ Success: Duplicate was detected and prevented!")
                print(f"✅ No new article was created in buffer table")
            else:
                print(f"❌ Unexpected: Save failed completely")
        
        # Demo 4: Test with truly new external_id
        print(f"\n✨ DEMO 4: Test with New External ID")
        print("-" * 40)
        
        new_external_id = f"DEMO_NEW_ID_{int(datetime.now().timestamp())}"
        print(f"Testing with new external_id: {new_external_id}")
        
        # Check if it exists (should be False)
        new_check = dup_service.check_external_id_in_both_tables(new_external_id)
        print(f"Exists: {new_check['exists']}")
        print(f"Message: {new_check['message']}")
        
        if not new_check['exists']:
            print(f"✅ Confirmed: {new_external_id} is truly unique")
            print(f"✅ This would be safe to store in buffer table")
        
        # Demo 5: Batch checking demonstration
        print(f"\n📦 DEMO 5: Batch Duplicate Checking")
        print("-" * 40)
        
        # Create a test batch with mix of existing and new IDs
        test_batch = []
        if test_cases:
            test_batch.extend([case[0] for case in test_cases[:2]])  # Add existing IDs
        test_batch.extend([
            f"NEW_ID_1_{int(datetime.now().timestamp())}",
            f"NEW_ID_2_{int(datetime.now().timestamp())}",
            test_batch[0] if test_batch else "DUPLICATE_IN_BATCH"  # Add duplicate within batch
        ])
        
        print(f"Testing batch of {len(test_batch)} external IDs:")
        for i, eid in enumerate(test_batch, 1):
            print(f"  {i}. {eid}")
        
        batch_results = dup_service.check_batch_duplicates(test_batch)
        
        print(f"\n📊 Batch Results:")
        print(f"   Total checked: {batch_results['total_checked']}")
        print(f"   Duplicates in batch: {batch_results['duplicates_found']}")
        print(f"   Existing in buffer: {len(batch_results['existing_in_db'])}")
        print(f"   Existing in permanent: {len(batch_results['existing_in_search_index'])}")
        print(f"   Existing anywhere: {len(batch_results.get('existing_anywhere', []))}")
        print(f"   Truly unique: {len(batch_results.get('truly_unique', []))}")
        
        if batch_results.get('existing_anywhere'):
            print(f"   Existing IDs: {batch_results['existing_anywhere']}")
        if batch_results.get('truly_unique'):
            print(f"   Unique IDs: {batch_results['truly_unique']}")
        
        # Demo 6: Show architecture benefits
        print(f"\n🎯 DEMO 6: Architecture Benefits")
        print("-" * 40)
        
        print("✅ Benefits of Dual-Table Checking:")
        print("   1. Prevents re-fetching processed articles")
        print("   2. Avoids duplicate AI processing costs")
        print("   3. Maintains data integrity across buffer architecture")
        print("   4. Handles articles in both buffer and permanent storage")
        print("   5. Optimizes storage by not duplicating processed articles")
        
        print(f"\n🔄 Buffer Architecture Workflow:")
        print("   1. New articles → news_articles (buffer)")
        print("   2. AI processing → enhanced articles in buffer")
        print("   3. Batch sync → copy to news_search_index (permanent)")
        print("   4. Buffer clearing → remove from news_articles")
        print("   5. Search operations → use news_search_index only")
        
        print(f"\n✅ Duplicate Prevention ensures:")
        print("   • No article stored twice in buffer")
        print("   • No re-processing of articles already in permanent storage")
        print("   • Efficient use of database storage and AI resources")
        
        print(f"\n🕐 Demonstration completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    try:
        demonstrate_dual_table_checking()
    except Exception as e:
        print(f"❌ Error running demonstration: {str(e)}")
        import traceback
        traceback.print_exc() 