#!/usr/bin/env python3
"""
Scheduler Status Checker and Emergency Force Kill

This script checks the status of both schedulers and provides an emergency
force kill option if they appear to be stuck or need immediate termination.
"""

import sys
import os
sys.path.insert(0, '.')

def check_scheduler_status():
    """Check the current status of both schedulers"""
    print("🔍 Checking TrendWise Scheduler Status...")
    print()
    
    try:
        # Import the schedulers
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        
        # Check AI Processing Scheduler
        print("📅 AI Processing Scheduler:")
        try:
            ai_status = news_scheduler.get_status()
            print(f"   Running: {'✅ YES' if ai_status.get('running', False) else '❌ NO'}")
            print(f"   Status: {ai_status.get('status', 'unknown')}")
            
            # Check threads
            if hasattr(news_scheduler, 'scheduler_thread'):
                thread_alive = news_scheduler.scheduler_thread and news_scheduler.scheduler_thread.is_alive()
                print(f"   Main Thread: {'🟢 ALIVE' if thread_alive else '🔴 DEAD'}")
            
            if hasattr(news_scheduler, 'initial_thread'):
                initial_alive = news_scheduler.initial_thread and news_scheduler.initial_thread.is_alive()
                print(f"   Initial Thread: {'🟢 ALIVE' if initial_alive else '🔴 DEAD'}")
                
        except Exception as e:
            print(f"   ❌ Error checking AI scheduler: {e}")
        
        print()
        
        # Check News Fetch Scheduler
        print("📡 News Fetch Scheduler:")
        try:
            fetch_status = news_fetch_scheduler.get_status()
            print(f"   Running: {'✅ YES' if fetch_status.get('running', False) else '❌ NO'}")
            print(f"   Status: {fetch_status.get('status', 'unknown')}")
            
            # Check threads
            if hasattr(news_fetch_scheduler, 'thread'):
                thread_alive = news_fetch_scheduler.thread and news_fetch_scheduler.thread.is_alive()
                print(f"   Main Thread: {'🟢 ALIVE' if thread_alive else '🔴 DEAD'}")
            
            if hasattr(news_fetch_scheduler, 'initial_thread'):
                initial_alive = news_fetch_scheduler.initial_thread and news_fetch_scheduler.initial_thread.is_alive()
                print(f"   Initial Thread: {'🟢 ALIVE' if initial_alive else '🔴 DEAD'}")
                
            if hasattr(news_fetch_scheduler, 'manual_threads'):
                manual_count = len([t for t in news_fetch_scheduler.manual_threads if t.is_alive()]) if news_fetch_scheduler.manual_threads else 0
                print(f"   Manual Threads: {'🟢' if manual_count == 0 else '🟡'} {manual_count} active")
                
        except Exception as e:
            print(f"   ❌ Error checking fetch scheduler: {e}")
        
        print()
        
        # Determine overall status
        ai_running = ai_status.get('running', False) if 'ai_status' in locals() else False
        fetch_running = fetch_status.get('running', False) if 'fetch_status' in locals() else False
        
        print("📊 Overall Status:")
        if ai_running and fetch_running:
            print("   ✅ Both schedulers are running normally")
        elif ai_running or fetch_running:
            print("   ⚠️ One scheduler is running, one is stopped")
        else:
            print("   🔴 Both schedulers are stopped")
        
        return ai_running, fetch_running
        
    except Exception as e:
        print(f"❌ Critical error checking scheduler status: {e}")
        return False, False

def emergency_force_kill():
    """Emergency force kill both schedulers"""
    print()
    print("🚨" + "="*50)
    print("🚨 EMERGENCY FORCE KILL OPERATION")
    print("🚨" + "="*50)
    print()
    
    print("⚠️ WARNING: This will forcibly terminate both scheduler threads")
    print("⚠️ Use only if schedulers are stuck or need immediate shutdown")
    print("⚠️ Current processing will be abandoned")
    print()
    
    confirmation = input("Type 'FORCE KILL' to proceed or anything else to cancel: ")
    
    if confirmation != "FORCE KILL":
        print("❌ Force kill cancelled.")
        return False
    
    print()
    print("💀 Initiating emergency force kill...")
    
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        import schedule
        
        results = {'ai': False, 'fetch': False}
        
        # Force kill AI scheduler
        print("🔫 Force killing AI Processing Scheduler...")
        try:
            # Try graceful stop first
            if hasattr(news_scheduler, 'running') and news_scheduler.running:
                success = news_scheduler.stop()
                if success:
                    results['ai'] = True
                    print("   ✅ AI scheduler stopped gracefully")
                else:
                    print("   ⚠️ Graceful stop failed, forcing...")
            
            # Force kill if needed
            if not results['ai']:
                news_scheduler.running = False
                if hasattr(news_scheduler, 'scheduler_thread'):
                    news_scheduler.scheduler_thread = None
                schedule.clear()
                results['ai'] = True
                print("   💀 AI scheduler force killed")
                
        except Exception as e:
            print(f"   ❌ Failed to force kill AI scheduler: {e}")
        
        # Force kill fetch scheduler
        print("🔫 Force killing News Fetch Scheduler...")
        try:
            # Try graceful stop first
            if hasattr(news_fetch_scheduler, 'running') and news_fetch_scheduler.running:
                success = news_fetch_scheduler.stop()
                if success:
                    results['fetch'] = True
                    print("   ✅ Fetch scheduler stopped gracefully")
                else:
                    print("   ⚠️ Graceful stop failed, forcing...")
            
            # Force kill if needed
            if not results['fetch']:
                news_fetch_scheduler.running = False
                if hasattr(news_fetch_scheduler, 'thread'):
                    news_fetch_scheduler.thread = None
                if hasattr(news_fetch_scheduler, 'manual_threads'):
                    news_fetch_scheduler.manual_threads = []
                results['fetch'] = True
                print("   💀 Fetch scheduler force killed")
                
        except Exception as e:
            print(f"   ❌ Failed to force kill fetch scheduler: {e}")
        
        print()
        print("📊 Force Kill Results:")
        print(f"   AI Scheduler: {'✅ KILLED' if results['ai'] else '❌ FAILED'}")
        print(f"   Fetch Scheduler: {'✅ KILLED' if results['fetch'] else '❌ FAILED'}")
        
        if results['ai'] and results['fetch']:
            print("✅ Emergency force kill completed successfully")
            return True
        else:
            print("⚠️ Partial force kill - some schedulers may still be running")
            return False
            
    except Exception as e:
        print(f"❌ Critical error during force kill: {e}")
        return False

def main():
    """Main function"""
    print("🤖 TrendWise Scheduler Status Checker")
    print("="*40)
    
    # Check current status
    ai_running, fetch_running = check_scheduler_status()
    
    # Offer force kill if any scheduler is running
    if ai_running or fetch_running:
        print()
        print("💡 Options:")
        print("   1. Continue monitoring (Ctrl+C to exit)")
        print("   2. Emergency force kill all schedulers")
        print()
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "2":
            success = emergency_force_kill()
            if success:
                print("\n✅ All schedulers have been terminated")
            else:
                print("\n⚠️ Some schedulers may still be running")
        else:
            print("\n📊 Status monitoring (Ctrl+C to exit)")
            try:
                while True:
                    import time
                    time.sleep(30)
                    print("\n" + "="*40)
                    check_scheduler_status()
            except KeyboardInterrupt:
                print("\n\n👋 Monitoring stopped by user")
    else:
        print("\n✅ No schedulers are currently running")

if __name__ == "__main__":
    main() 