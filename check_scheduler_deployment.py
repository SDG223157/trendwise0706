#!/usr/bin/env python3
"""
TrendWise Scheduler Deployment Check

This script checks the current deployment status of both schedulers
and verifies their auto-start configuration.
"""

import sys
import os
sys.path.insert(0, '.')

def check_scheduler_deployment():
    """Check scheduler deployment status"""
    print("🚀 TrendWise Scheduler Deployment Check")
    print("="*45)
    print()
    
    try:
        # Import Flask app and schedulers
        from app import create_app
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        
        # Create app context
        app = create_app()
        
        with app.app_context():
            print("📋 SCHEDULER CONFIGURATION:")
            print("-" * 25)
            
            # Check AI Processing Scheduler
            print("🤖 AI Processing Scheduler:")
            print(f"   • Status: {'⚠️ MANUAL START REQUIRED' if hasattr(news_scheduler, 'running') else '❌ Not initialized'}")
            print(f"   • Configuration: Only initializes, requires manual start (App1099_db_v11 style)")
            print(f"   • Schedule: Every 3 minutes")
            print(f"   • Purpose: Process articles with AI summaries")
            print()
            
            # Check News Fetch Scheduler  
            print("📡 News Fetch Scheduler:")
            print(f"   • Status: {'⚠️ MANUAL START REQUIRED' if hasattr(news_fetch_scheduler, 'running') else '❌ Not initialized'}")
            print(f"   • Configuration: Only initializes, requires manual start (App1099_db_v11 style)")
            print(f"   • Schedule: 6 times daily (market-based)")
            print(f"   • Purpose: Fetch news for 346 symbols")
            print()
            
            # Check actual running status
            print("📊 CURRENT RUNNING STATUS:")
            print("-" * 25)
            
            try:
                ai_status = news_scheduler.get_status()
                print(f"🤖 AI Processing Scheduler:")
                print(f"   • Running: {'✅ Yes' if ai_status.get('running', False) else '❌ No'}")
                print(f"   • Jobs Scheduled: {ai_status.get('jobs_count', 0)}")
                if ai_status.get('next_run'):
                    print(f"   • Next Run: {ai_status['next_run']}")
                print()
            except Exception as e:
                print(f"🤖 AI Processing Scheduler: ❌ Error checking status - {e}")
                print()
            
            try:
                fetch_status = news_fetch_scheduler.get_status()
                print(f"📡 News Fetch Scheduler:")
                print(f"   • Running: {'✅ Yes' if fetch_status.get('running', False) else '❌ No'}")
                print(f"   • Jobs Scheduled: {fetch_status.get('jobs_count', 0)}")
                if fetch_status.get('next_run'):
                    print(f"   • Next Run: {fetch_status['next_run']}")
                    print(f"   • Next Market: {fetch_status.get('next_run_details', 'Unknown')}")
                print(f"   • Total Symbols: {fetch_status.get('symbols_count', 0)}")
                print()
            except Exception as e:
                print(f"📡 News Fetch Scheduler: ❌ Error checking status - {e}")
                print()
            
            # Check news fetching global status
            print("🌐 GLOBAL NEWS FETCHING STATUS:")
            print("-" * 30)
            try:
                from app.utils.analysis.stock_news_service import StockNewsService
                is_enabled = StockNewsService.is_news_fetching_enabled()
                print(f"   • Global News Fetching: {'✅ Enabled' if is_enabled else '❌ Disabled'}")
                print()
            except Exception as e:
                print(f"   • Global News Fetching: ❌ Error checking - {e}")
                print()
            
            # Show manual start instructions
            print("🔧 HOW TO START SCHEDULERS (App1099_db_v11 Style):")
            print("-" * 48)
            print("1. Via Manual Script (RECOMMENDED):")
            print("   • Run: python3 start_schedulers.py")
            print("   • This starts both schedulers AND enables global news fetching")
            print("   • Provides detailed status feedback")
            print()
            print("2. Via Web Interface (Admin Panel):")
            print("   • Go to /news/scheduler")
            print("   • Click 'Start All Schedulers'")
            print()
            print("3. Via API (requires admin login):")
            print("   • POST to /news/api/scheduler/start")
            print("   • This starts both schedulers AND enables global news fetching")
            print()
            print("4. Stop Both Schedulers:")
            print("   • Run: python3 start_schedulers.py stop")
            print()
            
            # Show status check URLs
            print("📊 STATUS CHECK ENDPOINTS:")
            print("-" * 25)
            print("• AI Scheduler Status: /news/api/scheduler/status")
            print("• Fetch Scheduler Status: /news/api/fetch-scheduler/status")
            print("• Full Scheduler Management: /news/scheduler")
            print("• Fetch Scheduler Management: /news/fetch-scheduler")
            print()
            
            print("✅ Scheduler deployment check completed!")
            
    except Exception as e:
        print(f"❌ Error checking scheduler deployment: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_scheduler_deployment() 