# Maintenance and Monitoring Guide - News Search Optimization

## 🔧 System Health and Ongoing Maintenance

This guide covers how to maintain and monitor your news search optimization system for optimal performance and reliability.

## Daily Monitoring Tasks

### 1. System Health Check

```bash
# Daily health check script
cat > daily_health_check.py << 'EOF'
#!/usr/bin/env python3
from datetime import datetime
from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from app.utils.search.optimized_news_search import OptimizedNewsSearch
from app.utils.search.search_index_sync import SearchIndexSyncService

def daily_health_check():
    """Comprehensive daily health check"""
    
    print(f"🔍 Daily Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # 1. Database connectivity
            main_count = NewsArticle.query.count()
            search_count = NewsSearchIndex.query.count()
            print(f"📊 Database Status:")
            print(f"   Main articles: {main_count:,}")
            print(f"   Search index: {search_count:,}")
            
            # 2. Sync status
            sync_service = SearchIndexSyncService()
            sync_status = sync_service.full_sync_status()
            print(f"🔄 Sync Status:")
            print(f"   Sync percentage: {sync_status['sync_percentage']:.1f}%")
            print(f"   Missing from index: {sync_status['missing_from_index']:,}")
            print(f"   Orphaned entries: {sync_status['orphaned_entries']:,}")
            
            # 3. Search performance
            search = OptimizedNewsSearch(db.session)
            import time
            start = time.time()
            recent = search.get_recent_news(limit=10)
            search_time = (time.time() - start) * 1000
            print(f"⚡ Search Performance:")
            print(f"   Recent news query: {search_time:.1f}ms")
            print(f"   Results returned: {len(recent)}")
            
            # 4. Cache status
            cache_status = "✅ Available" if search.is_cache_available() else "❌ Unavailable"
            print(f"💾 Cache Status: {cache_status}")
            
            # 5. Data freshness
            if search_count > 0:
                latest_article = NewsSearchIndex.query.order_by(NewsSearchIndex.published_at.desc()).first()
                hours_old = (datetime.utcnow() - latest_article.published_at).total_seconds() / 3600
                print(f"📅 Data Freshness:")
                print(f"   Latest article: {hours_old:.1f} hours old")
                
                if hours_old > 24:
                    print("   ⚠️ Warning: No new articles in 24+ hours")
            
            # 6. Performance summary
            print(f"📈 Health Summary:")
            issues = 0
            
            if sync_status['sync_percentage'] < 95:
                print("   ⚠️ Sync below 95%")
                issues += 1
            
            if search_time > 200:
                print("   ⚠️ Search performance degraded")
                issues += 1
            
            if not search.is_cache_available():
                print("   ⚠️ Cache unavailable")
                issues += 1
            
            if issues == 0:
                print("   ✅ All systems healthy")
            else:
                print(f"   🔴 {issues} issues detected")
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    daily_health_check()
EOF

chmod +x daily_health_check.py
python daily_health_check.py
```

### 2. Performance Monitoring

```bash
# Performance monitoring script
cat > performance_monitor.py << 'EOF'
#!/usr/bin/env python3
import time
import psutil
import json
from datetime import datetime
from app import create_app, db
from app.utils.search.optimized_news_search import OptimizedNewsSearch

def monitor_performance():
    """Monitor search performance metrics"""
    
    print(f"⚡ Performance Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        search = OptimizedNewsSearch(db.session)
        process = psutil.Process()
        
        # Performance tests
        tests = [
            ("Recent News", lambda: search.get_recent_news(limit=10)),
            ("Symbol Search", lambda: search.search_by_symbols(['AAPL'], per_page=10)),
            ("Keyword Search", lambda: search.search_by_keywords(['earnings'], per_page=10)),
            ("Trending Symbols", lambda: search.get_trending_symbols(days=7)),
        ]
        
        results = []
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        for test_name, test_func in tests:
            times = []
            
            # Run test 5 times
            for i in range(5):
                start = time.time()
                try:
                    result = test_func()
                    duration = time.time() - start
                    times.append(duration * 1000)  # Convert to ms
                except Exception as e:
                    print(f"❌ {test_name} failed: {e}")
                    break
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                # Performance rating
                if avg_time < 50:
                    rating = "🟢 Excellent"
                elif avg_time < 100:
                    rating = "🟡 Good"
                elif avg_time < 200:
                    rating = "🟠 Fair"
                else:
                    rating = "🔴 Poor"
                
                results.append({
                    'test': test_name,
                    'avg_time': avg_time,
                    'min_time': min_time,
                    'max_time': max_time,
                    'rating': rating
                })
                
                print(f"{test_name:15} | {rating:12} | "
                      f"Avg: {avg_time:6.1f}ms | Min: {min_time:6.1f}ms | Max: {max_time:6.1f}ms")
        
        # Memory usage
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_delta = final_memory - initial_memory
        
        print(f"\n💾 Memory Usage:")
        print(f"   Initial: {initial_memory:.1f}MB")
        print(f"   Final: {final_memory:.1f}MB")
        print(f"   Delta: {memory_delta:+.1f}MB")
        
        # Save results to file for historical tracking
        timestamp = datetime.now().isoformat()
        performance_data = {
            'timestamp': timestamp,
            'results': results,
            'memory_usage': {
                'initial': initial_memory,
                'final': final_memory,
                'delta': memory_delta
            }
        }
        
        with open('performance_history.json', 'a') as f:
            f.write(json.dumps(performance_data) + '\n')
        
        print(f"\n📊 Performance data saved to performance_history.json")

if __name__ == "__main__":
    monitor_performance()
EOF

chmod +x performance_monitor.py
python performance_monitor.py
```

## Weekly Maintenance Tasks

### 1. Database Maintenance

```bash
# Weekly database maintenance
cat > weekly_maintenance.py << 'EOF'
#!/usr/bin/env python3
from datetime import datetime
from app import create_app, db
from app.utils.search.search_index_sync import SearchIndexSyncService
from sqlalchemy import text

def weekly_maintenance():
    """Weekly database maintenance tasks"""
    
    print(f"🔧 Weekly Maintenance - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # 1. Sync any missing articles
            print("🔄 Syncing missing articles...")
            sync_service = SearchIndexSyncService()
            sync_stats = sync_service.sync_new_articles(batch_size=1000)
            print(f"   Synced {sync_stats['added']} new articles")
            
            # 2. Remove orphaned entries
            print("🧹 Cleaning up orphaned entries...")
            removed = sync_service.remove_deleted_articles()
            print(f"   Removed {removed} orphaned entries")
            
            # 3. Database optimization
            print("📊 Optimizing database...")
            db.session.execute(text('VACUUM'))
            db.session.execute(text('ANALYZE'))
            db.session.execute(text('PRAGMA optimize'))
            db.session.commit()
            print("   Database optimized")
            
            # 4. Index maintenance
            print("🔍 Rebuilding indexes...")
            db.session.execute(text('REINDEX'))
            db.session.commit()
            print("   Indexes rebuilt")
            
            # 5. Cache warming
            print("🔥 Warming cache...")
            from app.utils.search.optimized_news_search import OptimizedNewsSearch
            search = OptimizedNewsSearch(db.session)
            
            # Warm common queries
            common_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA']
            for symbol in common_symbols:
                search.search_by_symbols([symbol], per_page=10)
            
            search.get_recent_news(limit=20)
            search.get_trending_symbols(days=7)
            print(f"   Warmed cache for {len(common_symbols)} symbols")
            
            # 6. Final status check
            print("📋 Final status check...")
            sync_status = sync_service.full_sync_status()
            print(f"   Sync percentage: {sync_status['sync_percentage']:.1f}%")
            print(f"   Articles in index: {sync_status['search_index_count']:,}")
            
            print("\n✅ Weekly maintenance completed successfully!")
            
        except Exception as e:
            print(f"❌ Weekly maintenance failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    weekly_maintenance()
EOF

chmod +x weekly_maintenance.py
python weekly_maintenance.py
```

## Monthly Maintenance Tasks

### 1. Data Archival and Cleanup

```bash
# Monthly data cleanup
cat > monthly_cleanup.py << 'EOF'
#!/usr/bin/env python3
from datetime import datetime, timedelta
from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
from app.utils.search.search_index_sync import SearchIndexSyncService

def monthly_cleanup():
    """Monthly data cleanup and archival"""
    
    print(f"🗂️ Monthly Cleanup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # 1. Data inventory
            print("📊 Current data inventory:")
            total_articles = NewsArticle.query.count()
            total_search_entries = NewsSearchIndex.query.count()
            
            # Calculate date ranges
            oldest_article = NewsArticle.query.order_by(NewsArticle.published_at.asc()).first()
            newest_article = NewsArticle.query.order_by(NewsArticle.published_at.desc()).first()
            
            print(f"   Total articles: {total_articles:,}")
            print(f"   Search entries: {total_search_entries:,}")
            
            if oldest_article and newest_article:
                date_range = (newest_article.published_at - oldest_article.published_at).days
                print(f"   Date range: {date_range} days")
                print(f"   Oldest: {oldest_article.published_at}")
                print(f"   Newest: {newest_article.published_at}")
            
            # 2. Cleanup old articles (configurable retention period)
            retention_days = 180  # Keep 6 months of data
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            print(f"\n🧹 Cleaning up articles older than {retention_days} days...")
            
            # Get articles to delete
            old_articles = NewsArticle.query.filter(
                NewsArticle.published_at < cutoff_date
            ).all()
            
            if old_articles:
                print(f"   Found {len(old_articles)} old articles to archive")
                
                # Remove from search index first
                sync_service = SearchIndexSyncService()
                deleted_count = sync_service.cleanup_old_articles(days_to_keep=retention_days)
                print(f"   Removed {deleted_count} articles from main table")
                
                # Note: Search index keeps the articles for search purposes
                remaining_search = NewsSearchIndex.query.filter(
                    NewsSearchIndex.published_at < cutoff_date
                ).count()
                print(f"   Kept {remaining_search} entries in search index")
            else:
                print("   No old articles found for cleanup")
            
            # 3. Database maintenance
            print(f"\n🔧 Database maintenance...")
            from sqlalchemy import text
            
            # Vacuum and analyze
            db.session.execute(text('VACUUM'))
            db.session.execute(text('ANALYZE'))
            db.session.commit()
            print("   Database vacuumed and analyzed")
            
            # 4. Storage statistics
            print(f"\n💾 Storage statistics:")
            
            # Get database file size
            import os
            db_file = 'trendwise.db'  # Adjust path as needed
            if os.path.exists(db_file):
                db_size = os.path.getsize(db_file) / (1024 * 1024)  # MB
                print(f"   Database size: {db_size:.1f} MB")
            
            # Final counts
            final_articles = NewsArticle.query.count()
            final_search_entries = NewsSearchIndex.query.count()
            
            print(f"   Articles after cleanup: {final_articles:,}")
            print(f"   Search entries: {final_search_entries:,}")
            
            # 5. Performance check
            print(f"\n⚡ Performance check after cleanup...")
            from app.utils.search.optimized_news_search import OptimizedNewsSearch
            search = OptimizedNewsSearch(db.session)
            
            import time
            start = time.time()
            recent = search.get_recent_news(limit=10)
            search_time = (time.time() - start) * 1000
            
            print(f"   Search performance: {search_time:.1f}ms")
            print(f"   Recent articles found: {len(recent)}")
            
            print("\n✅ Monthly cleanup completed successfully!")
            
        except Exception as e:
            print(f"❌ Monthly cleanup failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    monthly_cleanup()
EOF

chmod +x monthly_cleanup.py
python monthly_cleanup.py
```

## Automated Scheduling

### 1. Cron Job Setup

```bash
# Setup automated maintenance schedules
cat > setup_cron_jobs.sh << 'EOF'
#!/bin/bash

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create cron job entries
cat > maintenance_cron.txt << 'CRON_EOF'
# News search optimization maintenance jobs

# Daily health check (every day at 9 AM)
0 9 * * * cd /path/to/trendwise && python daily_health_check.py >> logs/daily_health.log 2>&1

# Performance monitoring (every 4 hours)
0 */4 * * * cd /path/to/trendwise && python performance_monitor.py >> logs/performance.log 2>&1

# Weekly maintenance (every Sunday at 2 AM)
0 2 * * 0 cd /path/to/trendwise && python weekly_maintenance.py >> logs/weekly_maintenance.log 2>&1

# Weekly performance analysis (every Sunday at 3 AM)
0 3 * * 0 cd /path/to/trendwise && python weekly_performance_analysis.py >> logs/weekly_analysis.log 2>&1

# Monthly cleanup (first day of month at 1 AM)
0 1 1 * * cd /path/to/trendwise && python monthly_cleanup.py >> logs/monthly_cleanup.log 2>&1

# Database backup (every day at 11 PM)
0 23 * * * cd /path/to/trendwise && cp trendwise.db backups/trendwise_$(date +\%Y\%m\%d).db
CRON_EOF

echo "Cron jobs configured in maintenance_cron.txt"
echo "To install, run: crontab maintenance_cron.txt"
echo "To view current cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"

# Create log directory
mkdir -p logs
mkdir -p backups

echo "Created logs/ and backups/ directories"
EOF

chmod +x setup_cron_jobs.sh
./setup_cron_jobs.sh
```

### 2. Systemd Service (Alternative)

```bash
# Create systemd service for monitoring
cat > create_monitoring_service.sh << 'EOF'
#!/bin/bash

# Create systemd service file
sudo tee /etc/systemd/system/trendwise-monitor.service << 'SERVICE_EOF'
[Unit]
Description=TrendWise Search Monitoring Service
After=network.target

[Service]
Type=simple
User=trendwise
WorkingDirectory=/opt/trendwise
ExecStart=/opt/trendwise/venv/bin/python performance_monitor.py
Restart=always
RestartSec=14400  # 4 hours
StandardOutput=append:/var/log/trendwise-monitor.log
StandardError=append:/var/log/trendwise-monitor.log

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Create timer for weekly maintenance
sudo tee /etc/systemd/system/trendwise-weekly.service << 'WEEKLY_EOF'
[Unit]
Description=TrendWise Weekly Maintenance
After=network.target

[Service]
Type=oneshot
User=trendwise
WorkingDirectory=/opt/trendwise
ExecStart=/opt/trendwise/venv/bin/python weekly_maintenance.py
StandardOutput=append:/var/log/trendwise-weekly.log
StandardError=append:/var/log/trendwise-weekly.log
WEEKLY_EOF

sudo tee /etc/systemd/system/trendwise-weekly.timer << 'TIMER_EOF'
[Unit]
Description=Run TrendWise Weekly Maintenance
Requires=trendwise-weekly.service

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
TIMER_EOF

# Enable services
sudo systemctl daemon-reload
sudo systemctl enable trendwise-monitor.service
sudo systemctl enable trendwise-weekly.timer
sudo systemctl start trendwise-monitor.service
sudo systemctl start trendwise-weekly.timer

echo "Systemd services created and enabled"
echo "Check status with: systemctl status trendwise-monitor"
EOF

chmod +x create_monitoring_service.sh
```

## Alerting and Notifications

### 1. Email Alerts

```bash
# Setup email alerts for critical issues
cat > setup_alerts.py << 'EOF'
#!/usr/bin/env python3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import os

class AlertManager:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('ALERT_EMAIL_USER')
        self.email_password = os.getenv('ALERT_EMAIL_PASSWORD')
        self.alert_recipients = os.getenv('ALERT_RECIPIENTS', '').split(',')
        
    def send_alert(self, subject, message, severity='INFO'):
        """Send email alert"""
        if not self.email_user or not self.email_password:
            print("Email credentials not configured")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = ', '.join(self.alert_recipients)
            msg['Subject'] = f"[TrendWise Alert - {severity}] {subject}"
            
            body = f"""
TrendWise Search System Alert

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Severity: {severity}
Subject: {subject}

Details:
{message}

Please investigate and take appropriate action.
"""
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            
            print(f"Alert sent: {subject}")
            return True
            
        except Exception as e:
            print(f"Failed to send alert: {e}")
            return False

def check_system_health():
    """Check system health and send alerts if needed"""
    from app import create_app, db
    from app.utils.search.optimized_news_search import OptimizedNewsSearch
    from app.utils.search.search_index_sync import SearchIndexSyncService
    
    alert_manager = AlertManager()
    alerts = []
    
    app = create_app()
    with app.app_context():
        try:
            # Check sync status
            sync_service = SearchIndexSyncService()
            sync_status = sync_service.full_sync_status()
            
            if sync_status['sync_percentage'] < 90:
                alerts.append({
                    'severity': 'WARNING',
                    'subject': f'Search Index Sync Low ({sync_status["sync_percentage"]:.1f}%)',
                    'message': f'Search index sync is at {sync_status["sync_percentage"]:.1f}%. Missing {sync_status["missing_from_index"]} articles from index.'
                })
            
            # Check search performance
            search = OptimizedNewsSearch(db.session)
            import time
            start = time.time()
            recent = search.get_recent_news(limit=10)
            search_time = (time.time() - start) * 1000
            
            if search_time > 500:
                alerts.append({
                    'severity': 'WARNING',
                    'subject': f'Search Performance Degraded ({search_time:.1f}ms)',
                    'message': f'Search query took {search_time:.1f}ms, which is above the 500ms threshold.'
                })
            
            # Check data freshness
            if recent:
                latest_article_time = datetime.fromisoformat(recent[0]['published_at'])
                hours_old = (datetime.utcnow() - latest_article_time).total_seconds() / 3600
                
                if hours_old > 48:
                    alerts.append({
                        'severity': 'WARNING',
                        'subject': f'Stale Data Detected ({hours_old:.1f} hours old)',
                        'message': f'Latest article is {hours_old:.1f} hours old. Data may not be updating properly.'
                    })
            
            # Check cache availability
            if not search.is_cache_available():
                alerts.append({
                    'severity': 'INFO',
                    'subject': 'Cache System Unavailable',
                    'message': 'Redis cache is not available. Performance may be impacted.'
                })
            
            # Send alerts
            for alert in alerts:
                alert_manager.send_alert(
                    alert['subject'],
                    alert['message'],
                    alert['severity']
                )
            
            if not alerts:
                print("✅ System health check passed - no alerts needed")
            else:
                print(f"📧 Sent {len(alerts)} alerts")
                
        except Exception as e:
            alert_manager.send_alert(
                'System Health Check Failed',
                f'Health check script encountered an error: {str(e)}',
                'ERROR'
            )

if __name__ == "__main__":
    check_system_health()
EOF

chmod +x setup_alerts.py
```

### 2. Slack Integration

```bash
# Setup Slack webhook alerts
cat > slack_alerts.py << 'EOF'
#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
import os
from datetime import datetime

class SlackAlerts:
    def __init__(self):
        self.webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
    def send_slack_alert(self, message, color='good'):
        """Send alert to Slack"""
        if not self.webhook_url:
            print("Slack webhook URL not configured")
            return False
        
        try:
            payload = {
                'attachments': [{
                    'color': color,
                    'title': 'TrendWise Search System Alert',
                    'text': message,
                    'timestamp': datetime.utcnow().timestamp(),
                    'footer': 'TrendWise Monitoring',
                }]
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(self.webhook_url, data=data)
            req.add_header('Content-Type', 'application/json')
            
            response = urllib.request.urlopen(req)
            print(f"Slack alert sent: {response.status}")
            return True
            
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return False

def send_daily_report():
    """Send daily status report to Slack"""
    from app import create_app, db
    from app.models import NewsArticle, NewsSearchIndex
    from app.utils.search.optimized_news_search import OptimizedNewsSearch
    
    slack = SlackAlerts()
    
    app = create_app()
    with app.app_context():
        try:
            # Gather stats
            main_count = NewsArticle.query.count()
            search_count = NewsSearchIndex.query.count()
            
            # Performance test
            search = OptimizedNewsSearch(db.session)
            import time
            start = time.time()
            recent = search.get_recent_news(limit=10)
            search_time = (time.time() - start) * 1000
            
            # Create report
            report = f"""
📊 *Daily System Report*

*Database Status:*
• Main articles: {main_count:,}
• Search index: {search_count:,}
• Sync rate: {(search_count / max(main_count, 1) * 100):.1f}%

*Performance:*
• Search time: {search_time:.1f}ms
• Cache: {'✅ Available' if search.is_cache_available() else '❌ Unavailable'}

*Data Freshness:*
• Recent articles: {len(recent)} found
• Latest: {recent[0]['published_at'] if recent else 'No articles'}

System is running {'✅ normally' if search_time < 200 else '⚠️ with issues'}
"""
            
            color = 'good' if search_time < 200 else 'warning'
            slack.send_slack_alert(report, color)
            
        except Exception as e:
            slack.send_slack_alert(f"❌ Daily report failed: {str(e)}", 'danger')

if __name__ == "__main__":
    send_daily_report()
EOF

chmod +x slack_alerts.py
```

## Log Management

### 1. Log Rotation Setup

```bash
# Setup log rotation
cat > setup_log_rotation.sh << 'EOF'
#!/bin/bash

# Create log rotation configuration
sudo tee /etc/logrotate.d/trendwise << 'LOGROTATE_EOF'
/opt/trendwise/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 trendwise trendwise
    sharedscripts
    postrotate
        # Restart services if needed
        systemctl reload trendwise-monitor || true
    endscript
}

/var/log/trendwise*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 trendwise trendwise
}
LOGROTATE_EOF

echo "Log rotation configured"
echo "Test with: sudo logrotate -d /etc/logrotate.d/trendwise"
EOF

chmod +x setup_log_rotation.sh
./setup_log_rotation.sh
```

### 2. Log Analysis Tools

```bash
# Log analysis script
cat > log_analyzer.py << 'EOF'
#!/usr/bin/env python3
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter

def analyze_performance_logs():
    """Analyze performance logs for patterns"""
    
    print("📊 Performance Log Analysis")
    print("=" * 50)
    
    try:
        # Read performance history
        with open('performance_history.json', 'r') as f:
            lines = f.readlines()
        
        if not lines:
            print("No performance data found")
            return
        
        # Parse last 24 hours
        day_ago = datetime.now() - timedelta(days=1)
        recent_data = []
        
        for line in lines:
            try:
                data = json.loads(line.strip())
                timestamp = datetime.fromisoformat(data['timestamp'])
                if timestamp >= day_ago:
                    recent_data.append(data)
            except:
                continue
        
        if not recent_data:
            print("No recent performance data")
            return
        
        # Analyze patterns
        test_stats = defaultdict(list)
        memory_stats = []
        
        for data in recent_data:
            for result in data['results']:
                test_stats[result['test']].append(result['avg_time'])
            memory_stats.append(data['memory_usage']['final'])
        
        print("📈 Performance Summary (Last 24 Hours):")
        for test, times in test_stats.items():
            if times:
                avg = sum(times) / len(times)
                print(f"  {test:20} | Avg: {avg:6.1f}ms | Samples: {len(times)}")
        
        if memory_stats:
            avg_memory = sum(memory_stats) / len(memory_stats)
            print(f"\n💾 Average Memory Usage: {avg_memory:.1f}MB")
        
    except FileNotFoundError:
        print("Performance history file not found")
    except Exception as e:
        print(f"Error analyzing logs: {e}")

def analyze_error_logs():
    """Analyze error patterns in logs"""
    
    print("\n🔍 Error Log Analysis")
    print("=" * 50)
    
    error_patterns = [
        r'ERROR',
        r'CRITICAL',
        r'Exception',
        r'Traceback',
        r'failed',
        r'timeout',
    ]
    
    log_files = [
        'logs/daily_health.log',
        'logs/performance.log',
        'logs/weekly_maintenance.log',
    ]
    
    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            print(f"\n📄 {log_file}:")
            
            errors = []
            for line in lines:
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        errors.append(line.strip())
                        break
            
            if errors:
                print(f"  Found {len(errors)} error lines:")
                for error in errors[-5:]:  # Show last 5 errors
                    print(f"    {error}")
            else:
                print("  No errors found")
                
        except FileNotFoundError:
            print(f"  {log_file} not found")
        except Exception as e:
            print(f"  Error reading {log_file}: {e}")

if __name__ == "__main__":
    analyze_performance_logs()
    analyze_error_logs()
EOF

chmod +x log_analyzer.py
python log_analyzer.py
```

## Best Practices Summary

### 1. Daily Tasks
- ✅ System health check
- ✅ Performance monitoring
- ✅ Error log review
- ✅ Data freshness verification

### 2. Weekly Tasks
- ✅ Database maintenance
- ✅ Index optimization
- ✅ Cache warming
- ✅ Performance trend analysis

### 3. Monthly Tasks
- ✅ Data archival and cleanup
- ✅ Storage optimization
- ✅ Security updates
- ✅ Backup verification

### 4. Monitoring Setup
- ✅ Automated health checks
- ✅ Performance alerting
- ✅ Log rotation
- ✅ Error notification

### 5. Documentation
- ✅ Keep maintenance logs
- ✅ Document configuration changes
- ✅ Update runbooks
- ✅ Review and update procedures

---

**With this comprehensive monitoring and maintenance system, your news search optimization will remain healthy, performant, and reliable! 🎯** 