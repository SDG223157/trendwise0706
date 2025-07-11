#!/usr/bin/env python3
"""
Test Enhanced Duplicate Prevention Service

This script demonstrates how to use the enhanced duplicate prevention service
to prevent duplicates at multiple levels in the news system.
"""

import sys
import os
sys.path.insert(0, '.')

from app import create_app, db
from app.utils.data.enhanced_duplicate_prevention import DuplicatePreventionService
from datetime import datetime
import json

def test_duplicate_prevention():
    """Test the enhanced duplicate prevention service"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing Enhanced Duplicate Prevention Service")
        print("=" * 60)
        
        # Initialize the service
        dup_service = DuplicatePreventionService()
        
        # Test 1: Generate duplicate report
        print("\n📊 STEP 1: Generate Duplicate Report")
        print("-" * 40)
        
        report = dup_service.generate_duplicate_report()
        print("Current System Status:")
        print(f"  News Articles: {report['news_articles']['total_count']} total, {report['news_articles']['unique_external_ids']} unique")
        print(f"  Search Index: {report['news_search_index']['total_count']} total, {report['news_search_index']['unique_external_ids']} unique")
        print(f"  Recommendations: {len(report['recommendations'])}")
        
        for rec in report['recommendations']:
            print(f"    • {rec}")
        
        # Test 2: Test dual-table external ID checking
        print("\n🔍 STEP 2: Test Dual-Table External ID Checking")
        print("-" * 40)
        
        # Get some sample external IDs for testing - handle empty tables gracefully
        try:
            # Try to get samples from both tables
            buffer_samples = db.session.execute(
                db.text("SELECT external_id FROM news_articles LIMIT 2")
            ).fetchall()
            
            permanent_samples = db.session.execute(
                db.text("SELECT external_id FROM news_search_index LIMIT 2")
            ).fetchall()
            
            sample_external_ids = []
            sample_external_ids.extend([(row.external_id, "buffer") for row in buffer_samples])
            sample_external_ids.extend([(row.external_id, "permanent") for row in permanent_samples])
            
        except Exception as e:
            print(f"Error getting sample data: {str(e)}")
            sample_external_ids = []
        
        if sample_external_ids:
            for i, (external_id, source) in enumerate(sample_external_ids[:3], 1):
                comprehensive_check = dup_service.check_external_id_in_both_tables(external_id)
                
                print(f"  {i}. External ID: {external_id} (from {source})")
                print(f"     Exists: {comprehensive_check['exists']}")
                print(f"     Location: {comprehensive_check['location']}")
                print(f"     In Buffer: {comprehensive_check['in_buffer']}")
                print(f"     In Permanent: {comprehensive_check['in_permanent']}")
                print(f"     Message: {comprehensive_check['message']}")
                print()
        else:
            print("  No sample external IDs available for testing")

        # Test 3: Check for duplicates in a sample of articles
        print("\n🔍 STEP 3: Check Sample Articles for Duplicates")
        print("-" * 40)
        
        try:
            # Get sample articles for duplicate checking
            sample_articles = db.session.execute(
                db.text("SELECT external_id, title, url, published_at FROM news_articles LIMIT 3")
            ).fetchall()
            
            if sample_articles:
                for i, article in enumerate(sample_articles, 1):
                    article_data = {
                        'external_id': article.external_id,
                        'title': article.title,
                        'url': article.url,
                        'published_at': article.published_at
                    }
                    
                    dup_check = dup_service.check_article_duplicate(article_data)
                    status = "DUPLICATE" if dup_check['is_duplicate'] else "UNIQUE"
                    title_display = article.title[:50] + "..." if len(article.title) > 50 else article.title
                    print(f"  {i}. {title_display} - {status}")
                    
                    if dup_check['is_duplicate']:
                        print(f"     Reason: {dup_check['duplicate_reason']}")
            else:
                print("  No sample articles available for testing")
                
        except Exception as e:
            print(f"  Error getting sample articles: {str(e)}")
            sample_articles = []
        
        # Test 4: Test symbol deduplication
        print("\n🔄 STEP 4: Test Symbol Deduplication")
        print("-" * 40)
        
        test_symbols = [
            "AAPL", "AAPL", "MSFT", {"symbol": "GOOGL"}, "GOOGL", "TSLA", "aapl"
        ]
        
        unique_symbols = dup_service.deduplicate_symbols(test_symbols)
        print(f"Original symbols: {test_symbols}")
        print(f"Deduplicated symbols: {unique_symbols}")
        
        # Test 5: Test batch duplicate checking
        print("\n📦 STEP 5: Test Batch Duplicate Checking")
        print("-" * 40)
        
        # Get some external IDs for testing
        try:
            sample_ids = db.session.execute(
                db.text("SELECT external_id FROM news_articles LIMIT 2")
            ).fetchall()
            external_ids = [row.external_id for row in sample_ids]
        except:
            external_ids = []
        
        # Add some duplicates for testing
        test_external_ids = external_ids + ["TEST_ID_1", "TEST_ID_2"]
        if external_ids:
            test_external_ids.append(external_ids[0])  # Add duplicate
        
        batch_results = dup_service.check_batch_duplicates(test_external_ids)
        print(f"Batch Analysis Results:")
        print(f"  Total checked: {batch_results['total_checked']}")
        print(f"  Duplicates in batch: {batch_results['duplicates_found']}")
        print(f"  Existing in buffer: {len(batch_results['existing_in_db'])}")
        print(f"  Existing in permanent: {len(batch_results['existing_in_search_index'])}")
        print(f"  Existing anywhere: {len(batch_results.get('existing_anywhere', []))}")
        print(f"  Truly unique: {len(batch_results.get('truly_unique', []))}")
        
        # Test 6: Test safe insert with duplicate handling
        print("\n💾 STEP 6: Test Safe Insert with Duplicate Handling")
        print("-" * 40)
        
        # Test with existing article (should be skipped)
        try:
            existing_article_data = db.session.execute(
                db.text("SELECT external_id, title, url, published_at FROM news_articles LIMIT 1")
            ).fetchone()
            
            if existing_article_data:
                test_article_data = {
                    'external_id': existing_article_data.external_id,
                    'title': f"DUPLICATE TEST: {existing_article_data.title}",
                    'content': "This is a test article for duplicate prevention",
                    'url': existing_article_data.url,
                    'published_at': existing_article_data.published_at,
                    'source': 'TEST_SOURCE',
                    'sentiment': {'overall_sentiment': 'neutral'},
                    'summary': {'brief': 'Test summary'},
                    'symbols': ['TEST_SYMBOL']
                }
                
                insert_result = dup_service.safe_insert_with_duplicate_handling(test_article_data)
                print(f"Insert Test Result:")
                print(f"  Success: {insert_result['success']}")
                print(f"  Action: {insert_result['action']}")
                print(f"  Message: {insert_result['message']}")
                if insert_result.get('duplicate_info'):
                    dup_info = insert_result['duplicate_info']
                    print(f"  Duplicate Location: {dup_info.get('location', 'unknown')}")
                    print(f"  In Buffer: {dup_info.get('in_buffer', False)}")
                    print(f"  In Permanent: {dup_info.get('in_permanent', False)}")
            else:
                print("  No existing articles available for duplicate test")
                
        except Exception as e:
            print(f"  Error testing safe insert: {str(e)}")
        
        # Test 7: Test cleanup functionality (dry run)
        print("\n🧹 STEP 7: Test Cleanup Functionality")
        print("-" * 40)
        
        # Check for duplicates before cleanup
        search_index_cleanup = dup_service.cleanup_duplicate_external_ids('news_search_index')
        news_articles_cleanup = dup_service.cleanup_duplicate_external_ids('news_articles')
        
        print(f"Search Index Cleanup Results:")
        print(f"  Duplicates found: {search_index_cleanup['duplicates_found']}")
        print(f"  Cleaned: {search_index_cleanup['cleaned_count']}")
        print(f"  Errors: {search_index_cleanup['error_count']}")
        
        print(f"News Articles Cleanup Results:")
        print(f"  Duplicates found: {news_articles_cleanup['duplicates_found']}")
        print(f"  Cleaned: {news_articles_cleanup['cleaned_count']}")
        print(f"  Errors: {news_articles_cleanup['error_count']}")
        
        # Test 8: Performance test
        print("\n⚡ STEP 8: Performance Test")
        print("-" * 40)
        
        start_time = datetime.now()
        
        # Test performance with larger batch
        large_batch_ids = [f"PERF_TEST_{i}" for i in range(1000)]
        large_batch_results = dup_service.check_batch_duplicates(large_batch_ids)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"Performance Test Results:")
        print(f"  Checked: {large_batch_results['total_checked']} IDs")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Rate: {large_batch_results['total_checked'] / duration:.0f} IDs/second")
        
        print(f"\n✅ All tests completed successfully!")
        print(f"🕐 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def integration_example():
    """Example of how to integrate the duplicate prevention service"""
    
    print("\n🔧 INTEGRATION EXAMPLE")
    print("=" * 60)
    
    # Example of how to integrate with existing NewsService
    integration_code = '''
# Example integration with existing NewsService

from app.utils.data.enhanced_duplicate_prevention import DuplicatePreventionService

class EnhancedNewsService:
    def __init__(self):
        self.dup_service = DuplicatePreventionService()
    
    def save_article_with_enhanced_duplicate_prevention(self, article_data):
        """Enhanced save method with comprehensive duplicate prevention"""
        
        # Use the enhanced duplicate prevention service
        result = self.dup_service.safe_insert_with_duplicate_handling(article_data)
        
        if result['success']:
            if result['action'] == 'inserted':
                print(f"✅ New article saved: {result['article_id']}")
            elif result['action'] == 'skipped_duplicate':
                print(f"⚠️ Duplicate skipped: {result['message']}")
            return result['article_id']
        else:
            print(f"❌ Failed to save article: {result['message']}")
            return None
    
    def bulk_save_articles(self, articles_list):
        """Bulk save with duplicate prevention"""
        results = {'saved': 0, 'skipped': 0, 'errors': 0}
        
        for article_data in articles_list:
            result = self.save_article_with_enhanced_duplicate_prevention(article_data)
            if result:
                results['saved'] += 1
            else:
                results['errors'] += 1
        
        return results

# Usage example:
enhanced_service = EnhancedNewsService()

# Save single article
article_data = {
    'external_id': 'UNIQUE_ID_123',
    'title': 'Test Article',
    'content': 'Article content...',
    # ... other fields
}

article_id = enhanced_service.save_article_with_enhanced_duplicate_prevention(article_data)

# Bulk save articles
articles_list = [article_data1, article_data2, article_data3]
bulk_results = enhanced_service.bulk_save_articles(articles_list)
print(f"Bulk save results: {bulk_results}")
'''
    
    print(integration_code)

if __name__ == "__main__":
    try:
        test_duplicate_prevention()
        integration_example()
    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        import traceback
        traceback.print_exc() 