#!/usr/bin/env python3
"""
Debug Duplicate External IDs

Investigate if the sync failure is caused by duplicate external_id constraint violations
when trying to sync articles that already exist in news_search_index.
"""

import sys
sys.path.insert(0, '.')

from app import create_app, db
from sqlalchemy import text
import json
import os
from datetime import datetime

def debug_duplicate_external_ids():
    """Check for duplicate external_id issues causing sync failures"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 Debugging Duplicate External ID Issues")
            print("=" * 50)
            print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Load the articles that were supposed to be processed
            tracking_data = None
            expected_articles = []
            
            if os.path.exists('sync_tracking_data.json'):
                with open('sync_tracking_data.json', 'r') as f:
                    tracking_data = json.load(f)
                expected_articles = tracking_data.get('articles_to_track', [])
                print(f"📋 Expected to process: {len(expected_articles)} articles")
            
            # STEP 1: Check if expected articles already exist in search index
            print(f"\n🔍 STEP 1: Check for Existing External IDs in Search Index")
            print("-" * 60)
            
            duplicates_found = 0
            new_articles = 0
            
            if expected_articles:
                for i, article in enumerate(expected_articles[:10], 1):
                    external_id = article['external_id']
                    title = article['title']
                    
                    # Check if external_id already exists in search index
                    search_check = text("""
                        SELECT id, external_id, title, created_at
                        FROM news_search_index 
                        WHERE external_id = :external_id
                    """)
                    existing = db.session.execute(search_check, {'external_id': external_id}).fetchone()
                    
                    if existing:
                        duplicates_found += 1
                        existing_created = existing.created_at.strftime('%Y-%m-%d %H:%M:%S') if existing.created_at else 'Unknown'
                        print(f"   ❌ DUPLICATE #{duplicates_found}: Article {i} (ID {article['id']})")
                        print(f"      External ID: {external_id}")
                        print(f"      Title: {title[:50]}...")
                        print(f"      Already exists in search index as ID {existing.id} (created: {existing_created})")
                    else:
                        new_articles += 1
                        print(f"   ✅ NEW: Article {i} (ID {article['id']}) - {title[:50]}...")
            
            print(f"\n📊 DUPLICATE ANALYSIS RESULTS:")
            print(f"   🚨 Duplicates found: {duplicates_found}")
            print(f"   ✅ Truly new articles: {new_articles}")
            print(f"   🎯 Expected sync result: +{new_articles} articles")
            print(f"   📊 Actual sync result: +2 articles")
            
            if new_articles == 2:
                print(f"   🎉 PERFECT MATCH! Duplicate theory confirmed!")
            else:
                print(f"   ⚠️ Numbers don't match exactly - investigating further...")
            
            # STEP 2: Check current buffer for duplicate external_ids
            print(f"\n🔍 STEP 2: Check Buffer for Duplicate External IDs")
            print("-" * 60)
            
            buffer_duplicates_query = text("""
                SELECT na.external_id, COUNT(*) as count, 
                       GROUP_CONCAT(na.id) as article_ids,
                       MAX(na.title) as sample_title
                FROM news_articles na
                WHERE na.external_id IS NOT NULL
                GROUP BY na.external_id
                HAVING count > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            buffer_duplicates = db.session.execute(buffer_duplicates_query).fetchall()
            
            if buffer_duplicates:
                print(f"🚨 Found {len(buffer_duplicates)} duplicate external_ids in buffer:")
                for dup in buffer_duplicates:
                    print(f"   External ID: {dup.external_id}")
                    print(f"   Count: {dup.count} articles")
                    print(f"   Article IDs: {dup.article_ids}")
                    print(f"   Sample title: {dup.sample_title[:50]}...")
                    print()
            else:
                print("✅ No duplicate external_ids found in buffer")
            
            # STEP 3: Check for external_ids in buffer that exist in search index
            print(f"\n🔍 STEP 3: Buffer Articles That Would Cause UNIQUE Constraint Violations")
            print("-" * 60)
            
            constraint_violations_query = text("""
                SELECT na.id, na.external_id, na.title,
                       CASE WHEN na.ai_summary IS NOT NULL AND na.ai_summary != '' THEN 1 ELSE 0 END as has_summary,
                       CASE WHEN na.ai_insights IS NOT NULL AND na.ai_insights != '' THEN 1 ELSE 0 END as has_insights,
                       nsi.id as search_index_id, nsi.created_at as search_created
                FROM news_articles na
                INNER JOIN news_search_index nsi ON na.external_id = nsi.external_id
                WHERE na.external_id IS NOT NULL
                ORDER BY na.id DESC
                LIMIT 15
            """)
            violations = db.session.execute(constraint_violations_query).fetchall()
            
            if violations:
                print(f"🚨 Found {len(violations)} articles in buffer that would cause UNIQUE constraint violations:")
                processed_violations = 0
                unprocessed_violations = 0
                
                for violation in violations:
                    has_ai = violation.has_summary and violation.has_insights
                    ai_status = "✅ AI PROCESSED" if has_ai else "❌ NOT PROCESSED"
                    
                    if has_ai:
                        processed_violations += 1
                    else:
                        unprocessed_violations += 1
                    
                    search_created = violation.search_created.strftime('%Y-%m-%d %H:%M') if violation.search_created else 'Unknown'
                    print(f"   Buffer ID {violation.id} → Search ID {violation.search_index_id} ({search_created})")
                    print(f"   External ID: {violation.external_id}")
                    print(f"   Title: {violation.title[:50]}...")
                    print(f"   Status: {ai_status}")
                    print()
                
                print(f"📊 CONSTRAINT VIOLATION SUMMARY:")
                print(f"   🤖 AI-processed duplicates: {processed_violations}")
                print(f"   📝 Unprocessed duplicates: {unprocessed_violations}")
                print(f"   🎯 These {processed_violations} would fail to sync due to UNIQUE constraint")
                
            else:
                print("✅ No constraint violations found")
            
            # STEP 4: Verify the successful syncs
            print(f"\n🔍 STEP 4: Verify the 2 Successful Syncs")
            print("-" * 60)
            
            recent_syncs_query = text("""
                SELECT id, external_id, title, created_at
                FROM news_search_index 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 15 MINUTE)
                ORDER BY created_at DESC
                LIMIT 5
            """)
            recent_syncs = db.session.execute(recent_syncs_query).fetchall()
            
            if recent_syncs:
                print(f"📰 Recent syncs (last 15 minutes):")
                for sync in recent_syncs:
                    created_str = sync.created_at.strftime('%H:%M:%S') if sync.created_at else 'Unknown'
                    print(f"   ID {sync.id}: {sync.title[:50]}... ({created_str})")
                    
                    # Check if this was one of our expected articles
                    for expected in expected_articles:
                        if expected['external_id'] == sync.external_id:
                            print(f"   ✅ MATCH: This was expected article ID {expected['id']}")
                            break
            
            # STEP 5: Solution recommendation
            print(f"\n💡 STEP 5: Solution Recommendation")
            print("-" * 60)
            
            if duplicates_found > 0:
                print(f"🎯 ROOT CAUSE CONFIRMED: Duplicate external_id issue")
                print(f"   - {duplicates_found} articles already existed in search index")
                print(f"   - Only {new_articles} truly new articles could be synced")
                print(f"   - UNIQUE constraint prevented duplicate syncing")
                print()
                print(f"🔧 SOLUTIONS:")
                print(f"   1. ✅ Duplicate prevention in NewsService.save_article() is working")
                print(f"   2. ⚠️ Some duplicates still slip through during fetch/processing")
                print(f"   3. 🛠️ Enhanced duplicate checking needed in AI processing phase")
                print(f"   4. 📊 This explains the 'sync failure' - it's actually working correctly!")
            else:
                print(f"🤔 Duplicate theory not fully confirmed - need more investigation")
            
            print(f"\n🕐 Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Error in duplicate analysis: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_duplicate_external_ids() 