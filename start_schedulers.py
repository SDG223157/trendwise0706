#!/usr/bin/env python3
"""
Manual Start Both Schedulers Script - App1099_db_v11 Style

This script starts both the AI Processing Scheduler and News Fetch Scheduler
manually, matching the approach used in App1099_db_v11 where both schedulers
require manual activation.
"""

import sys
import os
sys.path.insert(0, '.')

def start_schedulers():
    """Start both schedulers manually with full control"""
    print("🚀 TrendWise Manual Scheduler Startup")
    print("=" * 40)
    print("📋 Following App1099_db_v11 approach: Both schedulers require manual start")
    print()
    
    try:
        # Import the schedulers and Flask app
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        from app.utils.analysis.stock_news_service import StockNewsService
        from app import create_app
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Both schedulers should already be initialized via app startup
            # Now we manually start them
            
            # CRITICAL: Enable global news fetching first
            print("🌐 Enabling global news fetching...")
            try:
                StockNewsService.enable_news_fetching()
                print("✅ Global news fetching enabled successfully!")
                print()
            except Exception as e:
                print(f"❌ Failed to enable global news fetching: {e}")
                print()
            
            # Start AI Processing Scheduler
            print("🤖 Starting AI Processing Scheduler...")
            try:
                news_scheduler.start()
                print("✅ AI Processing Scheduler started successfully!")
                print("   • Processes articles with AI summaries and insights")
                print("   • Runs every 3 minutes automatically")
                print("   • Syncs processed articles to search index")
                print("   • Clears buffer after successful processing")
                print()
            except Exception as e:
                print(f"❌ Failed to start AI Processing Scheduler: {e}")
                print()
            
            # Start News Fetch Scheduler
            print("📡 Starting News Fetch Scheduler...")
            try:
                success = news_fetch_scheduler.start()
                if success:
                    print("✅ News Fetch Scheduler started successfully!")
                    print("   • Fetches news for 346 symbols automatically")
                    print("   • Runs 6 times daily at market-based times")
                    print("   • Processes symbols in chunks of 5")
                    print("   • Includes retry logic for failed symbols")
                    print("   • Runs initial fetch job immediately")
                else:
                    print("❌ Failed to start News Fetch Scheduler")
                print()
            except Exception as e:
                print(f"❌ Failed to start News Fetch Scheduler: {e}")
                print()
            
            # Check final status
            print("🔍 Final Status Verification:")
            print("-" * 30)
            
            try:
                ai_status = news_scheduler.get_status()
                print(f"🤖 AI Processing Scheduler: {'✅ RUNNING' if ai_status.get('running', False) else '❌ STOPPED'}")
                if ai_status.get('running', False):
                    print(f"   • Jobs Scheduled: {ai_status.get('jobs_count', 0)}")
                    if ai_status.get('next_run'):
                        print(f"   • Next Run: {ai_status['next_run']}")
                print()
            except Exception as e:
                print(f"🤖 AI Processing Scheduler: ❌ Error checking status - {e}")
                print()
            
            try:
                fetch_status = news_fetch_scheduler.get_status()
                print(f"📡 News Fetch Scheduler: {'✅ RUNNING' if fetch_status.get('running', False) else '❌ STOPPED'}")
                if fetch_status.get('running', False):
                    print(f"   • Jobs Scheduled: {fetch_status.get('jobs_count', 0)}")
                    if fetch_status.get('next_run'):
                        print(f"   • Next Run: {fetch_status['next_run']}")
                        print(f"   • Next Market: {fetch_status.get('next_run_details', 'Unknown')}")
                    print(f"   • Total Symbols: {fetch_status.get('symbols_count', 0)}")
                print()
            except Exception as e:
                print(f"📡 News Fetch Scheduler: ❌ Error checking status - {e}")
                print()
            
            # Final success check
            try:
                ai_running = news_scheduler.get_status().get('running', False)
                fetch_running = news_fetch_scheduler.get_status().get('running', False)
                global_enabled = StockNewsService.is_news_fetching_enabled()
                
                if ai_running and fetch_running and global_enabled:
                    print("🎉 SUCCESS: Both schedulers are now running!")
                    print("🌐 Global news fetching is enabled")
                    print()
                    print("📊 Monitor your schedulers at:")
                    print("   • AI Scheduler Management: /news/scheduler")
                    print("   • Fetch Scheduler Management: /news/fetch-scheduler")
                    print("   • Admin Panel: /admin")
                    print()
                    print("🔄 Scheduler Schedule Summary:")
                    print("   • AI Processing: Every 3 minutes")
                    print("   • News Fetch: 6 times daily (market-based)")
                    print("     - 🌏 23:30 UTC - Asian Pre-Market")
                    print("     - 🌏 08:30 UTC - Asian Close")
                    print("     - 🌍 07:30 UTC - European Pre-Market")
                    print("     - 🌍 17:00 UTC - European Close")
                    print("     - 🌎 14:00 UTC - US Pre-Market")
                    print("     - 🌎 21:30 UTC - US After-Hours")
                else:
                    print("⚠️ WARNING: Not all components started successfully")
                    print(f"   • AI Processing: {'✅' if ai_running else '❌'}")
                    print(f"   • News Fetch: {'✅' if fetch_running else '❌'}")
                    print(f"   • Global News Fetching: {'✅' if global_enabled else '❌'}")
                    print()
                    print("💡 Check the deployment logs for details")
                    print("🔧 Try running the individual start commands via admin panel")
                    
            except Exception as e:
                print(f"❌ Error during final status check: {e}")
                
    except Exception as e:
        print(f"❌ Critical error starting schedulers: {e}")
        print("💡 Make sure you're running this from the project root directory")
        print("🔧 Ensure all dependencies are installed and database is accessible")

def stop_schedulers():
    """Stop both schedulers manually"""
    print("🛑 TrendWise Manual Scheduler Shutdown")
    print("=" * 40)
    print()
    
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        from app.utils.analysis.stock_news_service import StockNewsService
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            # Stop AI Processing Scheduler
            print("🤖 Stopping AI Processing Scheduler...")
            try:
                news_scheduler.stop()
                print("✅ AI Processing Scheduler stopped successfully!")
            except Exception as e:
                print(f"❌ Failed to stop AI Processing Scheduler: {e}")
            
            # Stop News Fetch Scheduler
            print("📡 Stopping News Fetch Scheduler...")
            try:
                success = news_fetch_scheduler.stop()
                if success:
                    print("✅ News Fetch Scheduler stopped successfully!")
                else:
                    print("❌ Failed to stop News Fetch Scheduler")
            except Exception as e:
                print(f"❌ Failed to stop News Fetch Scheduler: {e}")
            
            # Disable global news fetching
            print("🌐 Disabling global news fetching...")
            try:
                StockNewsService.disable_news_fetching()
                print("✅ Global news fetching disabled successfully!")
            except Exception as e:
                print(f"❌ Failed to disable global news fetching: {e}")
            
            print()
            print("🏁 Scheduler shutdown completed!")
            
    except Exception as e:
        print(f"❌ Error stopping schedulers: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop_schedulers()
    else:
        start_schedulers() 