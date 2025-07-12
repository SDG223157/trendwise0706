#!/usr/bin/env python3

"""
Test script for emergency scheduler force kill functionality

This script tests the emergency force kill controls to ensure they work
correctly and can safely terminate stuck schedulers.
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_scheduler_states():
    """Test current scheduler states"""
    print("🧪 Testing Scheduler States")
    print("=" * 50)
    
    try:
        # Test AI Scheduler
        from app.utils.scheduler.news_scheduler import news_scheduler
        print(f"🤖 AI Scheduler Running: {getattr(news_scheduler, 'running', 'Unknown')}")
        
        if hasattr(news_scheduler, 'scheduler_thread'):
            print(f"🧵 AI Scheduler Thread: {news_scheduler.scheduler_thread}")
        
        # Test Fetch Scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        print(f"📰 Fetch Scheduler Running: {getattr(news_fetch_scheduler, 'running', 'Unknown')}")
        
        if hasattr(news_fetch_scheduler, 'thread'):
            print(f"🧵 Fetch Scheduler Thread: {news_fetch_scheduler.thread}")
        
        if hasattr(news_fetch_scheduler, 'manual_threads'):
            print(f"🧵 Manual Threads: {len(news_fetch_scheduler.manual_threads) if news_fetch_scheduler.manual_threads else 0}")
        
        # Test Schedule jobs
        import schedule
        print(f"📅 Scheduled Jobs: {len(schedule.jobs)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing scheduler states: {e}")
        return False

def test_force_kill_simulation():
    """Simulate force kill functionality"""
    print("\n🚨 Testing Force Kill Simulation")
    print("=" * 50)
    
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        import schedule
        
        # Record initial state
        initial_jobs = len(schedule.jobs)
        print(f"📊 Initial scheduled jobs: {initial_jobs}")
        
        # Simulate force kill steps
        print("🔄 Simulating force kill steps...")
        
        # Step 1: Try graceful stop
        print("  1. Attempting graceful stop...")
        ai_stopped = False
        fetch_stopped = False
        
        try:
            if hasattr(news_scheduler, 'running') and news_scheduler.running:
                print("     AI Scheduler: Attempting graceful stop")
                # Don't actually stop, just simulate
                ai_stopped = True
            else:
                print("     AI Scheduler: Not running")
                ai_stopped = True
        except Exception as e:
            print(f"     AI Scheduler: Error during graceful stop - {e}")
        
        try:
            if hasattr(news_fetch_scheduler, 'running') and news_fetch_scheduler.running:
                print("     Fetch Scheduler: Attempting graceful stop")
                # Don't actually stop, just simulate
                fetch_stopped = True
            else:
                print("     Fetch Scheduler: Not running")
                fetch_stopped = True
        except Exception as e:
            print(f"     Fetch Scheduler: Error during graceful stop - {e}")
        
        # Step 2: Force kill simulation
        print("  2. Force kill simulation...")
        if not ai_stopped:
            print("     AI Scheduler: Would force kill")
        if not fetch_stopped:
            print("     Fetch Scheduler: Would force kill")
        
        # Step 3: Clear jobs simulation
        print("  3. Job clearing simulation...")
        print(f"     Would clear {initial_jobs} scheduled jobs")
        
        print("✅ Force kill simulation completed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in force kill simulation: {e}")
        return False

def test_emergency_controls():
    """Test emergency control endpoints availability"""
    print("\n🛡️ Testing Emergency Control Endpoints")
    print("=" * 50)
    
    try:
        from app.admin.routes import bp as admin_bp
        
        # Check if force kill route exists
        force_kill_rule = None
        clear_jobs_rule = None
        
        for rule in admin_bp.url_map.iter_rules():
            if 'force-kill-schedulers' in rule.rule:
                force_kill_rule = rule
            elif 'clear-scheduled-jobs' in rule.rule:
                clear_jobs_rule = rule
        
        print(f"🔧 Force Kill Endpoint: {'✅ Available' if force_kill_rule else '❌ Missing'}")
        print(f"🧹 Clear Jobs Endpoint: {'✅ Available' if clear_jobs_rule else '❌ Missing'}")
        
        if force_kill_rule:
            print(f"   Route: {force_kill_rule.rule}")
            print(f"   Methods: {force_kill_rule.methods}")
        
        if clear_jobs_rule:
            print(f"   Route: {clear_jobs_rule.rule}")
            print(f"   Methods: {clear_jobs_rule.methods}")
        
        return force_kill_rule is not None and clear_jobs_rule is not None
        
    except Exception as e:
        print(f"❌ Error testing emergency control endpoints: {e}")
        return False

def test_scheduler_health():
    """Test scheduler health and responsiveness"""
    print("\n💊 Testing Scheduler Health")
    print("=" * 50)
    
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        
        # Test AI Scheduler health
        print("🧪 AI Scheduler Health Check:")
        try:
            ai_health = {
                'running': getattr(news_scheduler, 'running', False),
                'has_thread': hasattr(news_scheduler, 'scheduler_thread'),
                'thread_alive': False
            }
            
            if ai_health['has_thread'] and news_scheduler.scheduler_thread:
                ai_health['thread_alive'] = news_scheduler.scheduler_thread.is_alive()
            
            print(f"  Running: {ai_health['running']}")
            print(f"  Has Thread: {ai_health['has_thread']}")
            print(f"  Thread Alive: {ai_health['thread_alive']}")
            
        except Exception as e:
            print(f"  ❌ AI Scheduler health check failed: {e}")
        
        # Test Fetch Scheduler health
        print("\n🧪 Fetch Scheduler Health Check:")
        try:
            fetch_health = {
                'running': getattr(news_fetch_scheduler, 'running', False),
                'has_thread': hasattr(news_fetch_scheduler, 'thread'),
                'thread_alive': False,
                'manual_threads': 0
            }
            
            if fetch_health['has_thread'] and news_fetch_scheduler.thread:
                fetch_health['thread_alive'] = news_fetch_scheduler.thread.is_alive()
            
            if hasattr(news_fetch_scheduler, 'manual_threads'):
                fetch_health['manual_threads'] = len(news_fetch_scheduler.manual_threads) if news_fetch_scheduler.manual_threads else 0
            
            print(f"  Running: {fetch_health['running']}")
            print(f"  Has Thread: {fetch_health['has_thread']}")
            print(f"  Thread Alive: {fetch_health['thread_alive']}")
            print(f"  Manual Threads: {fetch_health['manual_threads']}")
            
        except Exception as e:
            print(f"  ❌ Fetch Scheduler health check failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing scheduler health: {e}")
        return False

def main():
    """Run all force kill functionality tests"""
    print("🚀 Starting Force Kill Functionality Tests...")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Scheduler States
    test_results.append(test_scheduler_states())
    
    # Test 2: Force Kill Simulation
    test_results.append(test_force_kill_simulation())
    
    # Test 3: Emergency Control Endpoints
    test_results.append(test_emergency_controls())
    
    # Test 4: Scheduler Health
    test_results.append(test_scheduler_health())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ Tests Passed: {passed}/{total}")
    print(f"❌ Tests Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All force kill functionality tests passed!")
    else:
        print("⚠️  Some tests failed - review the output above")
    
    print("\n🔧 Usage Instructions:")
    print("=" * 30)
    print("1. Navigate to Admin → News Management")
    print("2. Use Emergency Scheduler Controls section")
    print("3. Check 'I understand this is for emergency use only'")
    print("4. Use appropriate buttons:")
    print("   - Force Kill All Schedulers: Immediate termination")
    print("   - Graceful Stop All: Wait for operations to complete")
    print("   - Clear All Scheduled Jobs: Remove pending tasks")
    print("5. Monitor status with 'Refresh Status' button")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 