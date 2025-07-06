# Automated News AI Scheduler

## Overview

The TrendWise application now includes an **automated background scheduler** that processes news articles with AI summaries and insights every 10 minutes, eliminating the need for manual intervention.

## 🎯 Key Features

### Automated Processing
- **Runs every 3 minutes** automatically in the background
- **No manual clicks** required - replaces the "Update AI Summaries" button
- **Processes up to 10 articles per run** to manage API quotas
- **Smart filtering** - only processes articles that need AI analysis

### AI-Generated Content
For each unprocessed article, the system automatically generates:
- **AI Summary** with key concepts, points, and context
- **AI Insights** with market implications and conclusions  
- **AI Sentiment Rating** from -100 (extremely bearish) to +100 (extremely bullish)

### Built-in Safeguards
- **Rate limiting** to respect API quotas
- **Content validation** to ensure quality output
- **Error handling** with automatic retry logic
- **Database transaction safety** with rollback on failures

## 📁 Files Added/Modified

### New Files
- `app/utils/scheduler/news_scheduler.py` - Main scheduler implementation
- `app/templates/news/scheduler_status.html` - Management interface
- `AUTOMATED_NEWS_AI_SCHEDULER.md` - This documentation

### Modified Files
- `app/__init__.py` - Scheduler initialization on app startup
- `app/news/routes.py` - Added scheduler management API routes
- `app/templates/news/fetch.html` - Added scheduler link
- `requirements.txt` - Added `schedule>=1.2.0` dependency

## 🚀 Installation & Setup

### 1. Install Dependencies
```bash
pip install "schedule>=1.2.0"
```

### 2. Environment Variables
Ensure the following environment variable is set:
```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 3. Automatic Startup
The scheduler starts automatically when the Flask application launches:
```
🤖 Automated news AI processing scheduler started successfully!
⏰ Will process articles every 3 minutes automatically
🔄 Running initial processing job...
```

## 🎛️ Management Interface

Access the scheduler management page at:
**`/news/scheduler`** (Admin access required)

### Status Dashboard
- **Current Status**: Running/Stopped with visual indicators
- **Next Scheduled Run**: When the next processing will occur
- **Unprocessed Articles**: Count of articles awaiting AI processing
- **API Configuration**: Verification of OpenRouter API key

### Control Panel
- **Start Scheduler**: Begin automated processing
- **Stop Scheduler**: Halt automated processing  
- **Process Articles Now**: Trigger immediate processing run

## 🔧 API Endpoints

### Status & Management
- `GET /news/api/scheduler/status` - Get scheduler status
- `POST /news/api/scheduler/start` - Start the scheduler
- `POST /news/api/scheduler/stop` - Stop the scheduler
- `POST /news/api/scheduler/run-now` - Trigger immediate processing

### Example Status Response
```json
{
  "success": true,
  "status": {
    "running": true,
    "next_run": "2024-12-15T16:00:00",
    "jobs_count": 2,
    "api_key_configured": true,
    "max_articles_per_run": 10,
    "unprocessed_articles_count": 5
  }
}
```

## ⚙️ Configuration Options

### Processing Limits
```python
MAX_ARTICLES_PER_RUN = 10  # Articles processed per run
CONTENT_TRUNCATE_LIMIT = 4000  # Max content length for API
```

### Scheduling
```python
# Schedule the processing job
schedule.every(3).minutes.do(run_processing_job)  # Every 3 minutes
```

## 📊 Processing Logic

### Article Selection
The scheduler processes articles that meet these criteria:
- Have content (not null/empty)
- Missing at least one of: AI summary, AI insights, or sentiment rating
- Ordered by ID (newest first)
- Limited to 10 per run

### Processing Steps
1. **Validate Content**: Ensure article has sufficient content (>10 characters)
2. **Generate AI Summary**: Create structured summary with key points
3. **Generate AI Insights**: Analyze market implications
4. **Calculate Sentiment**: Rate from -100 to +100
5. **Validate Output**: Ensure generated content meets quality thresholds
6. **Save to Database**: Commit successful results

### Error Handling
- Individual article failures don't stop the batch
- Database rollback on processing errors
- Comprehensive logging for debugging
- Continuation on API rate limit errors

## 🔍 Monitoring & Logs

### Log Messages
The scheduler provides detailed logging:
```
🤖 Starting automated AI processing job...
📄 Found 12 articles to process
✓ Generated AI summary for article 1234
✓ Generated AI insights for article 1234  
✓ Generated AI sentiment for article 1234: 45
✓ Successfully processed article 1234
🎯 Processing job completed:
   ✅ Successfully processed: 11 articles
   ❌ Failed: 1 articles
   📊 Total: 12 articles
```

### Status Monitoring
- Real-time status updates every 30 seconds in the web interface
- API endpoints for programmatic status checking
- Database query counts for unprocessed articles

## 🛠️ Troubleshooting

### Common Issues

#### Scheduler Not Starting
```
Error: OPENROUTER_API_KEY is required for AI processing
```
**Solution**: Set the `OPENROUTER_API_KEY` environment variable

#### No Articles Being Processed
**Check**: 
1. Articles have content: `SELECT COUNT(*) FROM news_articles WHERE content IS NOT NULL`
2. Articles need processing: `WHERE ai_summary IS NULL OR ai_insights IS NULL`
3. API key is valid and has credits

#### Processing Failures
**Check logs for**:
- API rate limiting (429 errors)
- Content too long (truncation warnings)
- Database connection issues
- Insufficient API credits

### Manual Recovery
If the scheduler stops working:
1. Visit `/news/scheduler` (admin access required)
2. Click "Stop Scheduler" then "Start Scheduler"  
3. Use "Process Articles Now" for immediate processing
4. Check logs for error details

## 🔐 Security & Access

### Admin-Only Access
All scheduler management requires admin privileges:
```python
@login_required
@admin_required
def scheduler_status():
```

### API Rate Limiting
- 2-second delays between article processing
- Respects OpenRouter API limits
- Graceful handling of rate limit responses

## 💡 Benefits

### For Users
- **No manual intervention** required
- **Always up-to-date** AI analysis
- **Consistent processing** every 4 hours
- **Improved user experience** with automated content

### For Administrators  
- **Reduced maintenance** overhead
- **Transparent monitoring** via web interface
- **Flexible control** with start/stop/run-now options
- **Comprehensive logging** for troubleshooting

## 🔄 Future Enhancements

### Potential Improvements
1. **Custom Scheduling**: Allow different intervals per user/admin settings
2. **Processing Priorities**: Priority queues for urgent articles
3. **Batch Size Configuration**: Dynamic article limits based on API quotas
4. **Email Notifications**: Alerts for processing failures or quota limits
5. **Analytics Dashboard**: Historical processing statistics and trends

### Advanced Features
- **Multi-tenant Support**: Different schedules for different organizations
- **API Integration**: Webhook notifications for processing completion
- **Content Filtering**: Smart filtering by article quality/relevance
- **Performance Metrics**: Processing time and success rate tracking

---

## Summary

The automated news AI scheduler transforms TrendWise from a manual processing system to a fully automated AI-powered news analysis platform. Users no longer need to manually trigger AI processing - the system works continuously in the background, ensuring fresh AI insights are always available.

**Key Benefits:**
- 🤖 **Fully Automated**: No manual intervention required
- ⏰ **Regular Processing**: Every 4 hours automatically  
- 🎯 **Smart & Efficient**: Only processes articles that need AI analysis
- 🛡️ **Safe & Reliable**: Built-in error handling and rate limiting
- 📊 **Transparent**: Real-time monitoring and control interface

The system is production-ready and can handle the automated processing of news articles at scale while maintaining API efficiency and data integrity.

## 📈 **Updated Processing Schedule (Latest)**

**Current Configuration:**
- **Frequency**: Every 3 minutes
- **Batch Size**: 10 articles per run
- **Daily Runs**: 480 runs per day (24 hours × 20 runs per hour)
- **Daily Capacity**: Up to 4,800 articles per day (10 × 480 runs)

**Benefits of 3-Minute Schedule:**
- **Ultra-Fast Processing**: Articles get AI analysis within 3 minutes
- **Real-Time Responsiveness**: Users see processed content almost immediately
- **Efficient Batching**: Smaller batches reduce API load per run
- **Massive Throughput**: Significantly higher daily processing capacity 