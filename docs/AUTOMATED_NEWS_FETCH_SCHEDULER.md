# Automated News Fetch Scheduler

## Overview

The Automated News Fetch Scheduler automatically runs the "Fetch Top 100" news functionality at strategic market opening and closing times. It runs 6 times daily, synchronized with Asian, European, and US market sessions to capture news when markets are most active.

## Features

- **Market-Based Scheduling**: Runs 6 times daily at optimal market timing
- **Global Market Coverage**: Synchronized with Asian, European, and US market sessions
- **Complete Symbol Coverage**: Processes all 346 symbols from the default list
- **Intelligent Processing**: Handles symbols in chunks with delays to avoid API rate limits
- **Retry Logic**: Automatically retries failed symbols up to 2 times
- **Error Handling**: Comprehensive error logging and graceful failure handling
- **Web Interface**: Easy-to-use control panel for management
- **Real-Time Progress**: Live progress tracking with detailed statistics
- **Background Processing**: Runs in background threads without blocking the application

## How It Works

### 1. Market-Based Scheduling
- Uses Python's `schedule` library with specific UTC times
- Runs 6 times daily at market opening/closing times:
  - 🌏 **23:30 UTC** - Asian Pre-Market (30 min before Tokyo/HK open)
  - 🌏 **08:30 UTC** - Asian Close (30 min after Asian markets close)
  - 🌍 **07:30 UTC** - European Pre-Market (30 min before London/Frankfurt open)
  - 🌍 **17:00 UTC** - European Close (30 min after European markets close)
  - 🌎 **14:00 UTC** - US Pre-Market (30 min before NYSE/NASDAQ open)
  - 🌎 **21:30 UTC** - US After-Hours (30 min after US markets close)
- Starts automatically when the scheduler is enabled
- Runs in a separate background thread

### 2. Symbol Processing
- Processes all symbols from the DEFAULT_SYMBOLS list (same as "Fetch Top 100")
- Shuffles symbols for variety in processing order
- Processes in chunks of 5 symbols at a time
- Includes 3-second delays between chunks to avoid overwhelming APIs
- Fetches 2 articles per symbol by default

### 3. Error Handling
- Retries failed symbols up to 2 times with delays
- Logs all successes and failures
- Continues processing even if some symbols fail
- Provides detailed completion statistics

### 4. Integration
- Works seamlessly with existing news infrastructure
- Integrates with the AI processing scheduler for complete automation
- Uses the same NewsAnalysisService as manual fetching

## Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Fetch Schedule** | Market-based (6 times daily) | Runs at market opening/closing times |
| **Total Symbols** | 346 | Number of symbols processed |
| **Articles per Symbol** | 2 | Maximum articles fetched per symbol |
| **Chunk Size** | 5 | Symbols processed simultaneously |
| **Retry Attempts** | 2 | Number of retries for failed symbols |

## Web Interface

### Accessing the Scheduler
1. Go to the News Fetch page (`/news/fetch`)
2. Click the "🤖 Auto Fetch Scheduler" button
3. Or navigate directly to `/news/fetch-scheduler`

### Controls Available
- **▶️ Start Scheduler**: Begin automated fetching every 6 hours
- **⏹️ Stop Scheduler**: Stop automated fetching
- **🚀 Run Now**: Manually trigger a fetch job immediately

### Status Information
- **Current Status**: Running/Stopped with visual indicator
- **Jobs Scheduled**: Number of scheduled jobs
- **Next Run**: When the next automatic run will occur
- **Configuration**: Current settings and parameters

## Usage Instructions

### Starting the Scheduler
1. Navigate to the News Fetch Scheduler page
2. Click "▶️ Start Scheduler"
3. Confirm the scheduler is running (green indicator)
4. The next market session and run time will be displayed
5. View the complete daily schedule showing all 6 market times

### Stopping the Scheduler
1. Click "⏹️ Stop Scheduler"
2. Confirm the scheduler has stopped (red indicator)
3. No more automatic runs will occur

### Manual Execution
1. Click "🚀 Run Now" to trigger an immediate fetch
2. The job runs in the background
3. Check application logs for progress and results

## Monitoring and Logs

### Log Messages
The scheduler provides detailed logging with emojis for easy identification:

```
🚀 News fetch scheduler started - will run at market opening/closing times
📅 Scheduled 6 daily runs:
  🌏 23:30 UTC - Asian Pre-Market
  🌏 08:30 UTC - Asian Close
  🌍 07:30 UTC - European Pre-Market
  🌍 17:00 UTC - European Close
  🌎 14:00 UTC - US Pre-Market
  🌎 21:30 UTC - US After-Hours
⏰ Scheduled news fetch job triggered - US Pre-Market
🤖 Starting automated news fetch job...
📊 Processing 346 symbols in 70 chunks
🔄 Processing chunk 1/70: ['NASDAQ:AAPL', 'NYSE:MSFT', ...]
✅ Fetched 2 articles for NASDAQ:AAPL
⚠️ No articles found for NYSE:XYZ
❌ Error processing HKEX:123: Connection timeout
🎯 US Pre-Market job completed:
   ✅ Successfully processed: 330 symbols
   ❌ Failed: 16 symbols
   📄 Total articles fetched: 660
   ⏱️ Duration: 520.7 seconds
```

### Performance Metrics
Each run provides comprehensive statistics:
- **Processed Symbols**: Number of symbols successfully processed
- **Failed Symbols**: Number of symbols that failed after retries
- **Total Articles**: Total number of articles fetched
- **Duration**: Time taken to complete the job

## Integration with AI Processing

The News Fetch Scheduler works perfectly with the existing AI Processing Scheduler:

1. **News Fetch Scheduler** (6 times daily at market times): Fetches fresh news articles when markets are most active
2. **AI Processing Scheduler** (every 5 minutes): Processes articles with AI summaries and insights

This creates a complete automation pipeline:
- Fresh news is fetched 6 times daily at optimal market timing
- AI processing happens every 5 minutes for rapid turnaround
- Your database stays current with market-synchronized content and minimal manual intervention
- News is captured at the most relevant times for each global market session

## Troubleshooting

### Common Issues

**Scheduler Won't Start**
- Check application logs for error messages
- Ensure no other scheduler instances are running
- Verify database connectivity

**No Articles Being Fetched**
- Check if the scheduler is actually running
- Verify API keys and external service connectivity
- Review failed symbol logs for patterns

**High Failure Rate**
- Some exchanges may have temporary issues
- API rate limits may be exceeded
- Network connectivity problems

### Best Practices

1. **Monitor Regularly**: Check the scheduler status page periodically
2. **Review Logs**: Look for patterns in failed symbols
3. **Coordinate with AI Processing**: Ensure both schedulers are running for full automation
4. **Test Manually**: Use "Run Now" to test functionality

## Technical Details

### File Structure
```
app/utils/scheduler/news_fetch_scheduler.py  # Main scheduler service
app/news/routes.py                          # API routes (lines 1757+)
app/templates/news/fetch_scheduler_status.html  # Web interface
```

### Dependencies
- `schedule`: Python job scheduling library
- `threading`: Background thread execution
- `requests`: HTTP requests for news fetching
- `random`: Symbol shuffling for variety

### Database Integration
- Uses existing NewsArticle model
- Integrates with ArticleSymbol relationships
- Maintains data consistency with manual fetching

## Future Enhancements

Potential improvements for future versions:
- **Configurable Intervals**: Allow custom fetch intervals
- **Symbol Filtering**: Choose specific symbols to process
- **Performance Optimization**: Parallel processing for faster execution
- **Advanced Retry Logic**: Exponential backoff for failed requests
- **Email Notifications**: Alerts for significant failures

---

## Quick Start

1. **Install**: The scheduler is ready to use (no additional setup required)
2. **Access**: Go to `/news/fetch-scheduler` in your application
3. **Start**: Click "▶️ Start Scheduler"
4. **Monitor**: Check status and logs regularly
5. **Enjoy**: Automated news fetching every 6 hours!

The scheduler provides a "set it and forget it" solution for keeping your news database current with minimal manual intervention. 