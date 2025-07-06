# Complete News Automation System

## Overview

TrendWise now features a **complete automation system** that handles news fetching, AI processing, and content management without manual intervention. This system combines two powerful schedulers to create a seamless news pipeline.

## 🤖 Two-Scheduler Architecture

### 1. News Fetch Scheduler (Every 6 Hours)
**Purpose**: Automatically fetches fresh news articles  
**Frequency**: Every 6 hours (4 times per day)  
**Function**: Replicates "Fetch Top 100" button functionality  

### 2. AI Processing Scheduler (Every 10 Minutes)
**Purpose**: Processes articles with AI summaries and insights  
**Frequency**: Every 10 minutes (144 times per day)  
**Function**: Adds structured AI content to fetched articles  

## 📊 Complete Automation Pipeline

```
🔄 Every 6 Hours: News Fetch Scheduler
    ↓
📰 Fetches 200+ fresh articles from 100+ symbols
    ↓
💾 Stores articles in database
    ↓
🧠 Every 10 Minutes: AI Processing Scheduler
    ↓
🤖 Processes up to 10 articles with AI summaries
    ↓
📝 Adds structured summaries, insights, and sentiment
    ↓
✅ Complete automated news system
```

## 🎯 Key Benefits

### **Set It and Forget It**
- Start both schedulers once
- System runs continuously without intervention
- Handles errors gracefully and continues processing

### **Fresh Content Always**
- News fetched every 6 hours ensures current content
- AI processing every 10 minutes keeps summaries up-to-date
- 24/7 operation means no missed opportunities

### **Comprehensive Coverage**
- **100+ symbols** processed automatically
- **200+ articles** fetched every 6 hours (800+ daily)
- **1440 articles** can be AI-processed daily
- **Complete market coverage** across all major exchanges

### **Professional Quality**
- **Structured AI summaries** with consistent formatting
- **Market insights** and sentiment analysis
- **Error handling** and retry logic
- **Detailed logging** for monitoring

## 🚀 Getting Started

### Quick Setup (5 Minutes)

1. **Start News Fetch Scheduler**
   - Go to `/news/fetch-scheduler`
   - Click "▶️ Start Scheduler"
   - Verify green "Running" status

2. **Start AI Processing Scheduler**
   - Go to `/news/scheduler-status`
   - Click "▶️ Start Scheduler"
   - Verify green "Running" status

3. **Verify Operation**
   - Both schedulers show "Running" status
   - Check logs for activity
   - Monitor article counts in database

### Manual Testing

**Test News Fetching**:
- Click "🚀 Run Now" on fetch scheduler
- Watch logs for progress
- Verify new articles appear

**Test AI Processing**:
- Click "🚀 Run Now" on AI scheduler
- Check articles get AI summaries
- Verify structured format

## 📈 Performance Metrics

### Daily Capacity
| Metric | Value | Description |
|--------|-------|-------------|
| **News Fetch Runs** | 4 per day | Every 6 hours |
| **Articles Fetched** | 800+ daily | 200+ per run |
| **AI Processing Runs** | 144 per day | Every 10 minutes |
| **AI Articles Processed** | 1440 daily | 10 per run |
| **Total Automation** | 24/7 | Continuous operation |

### Resource Usage
- **CPU**: Low impact, background processing
- **Memory**: Minimal footprint
- **Network**: Controlled API usage with delays
- **Database**: Efficient batch operations

## 🎛️ Management Interfaces

### News Fetch Scheduler (`/news/fetch-scheduler`)
- **Status Monitoring**: Real-time scheduler status
- **Control Panel**: Start/Stop/Run Now buttons
- **Configuration Display**: Current settings
- **Performance Metrics**: Success/failure statistics

### AI Processing Scheduler (`/news/scheduler-status`)
- **Processing Status**: Articles being processed
- **Queue Management**: Pending articles count
- **AI Performance**: Processing success rates
- **Content Quality**: Summary generation metrics

### Manual Override (`/news/fetch`)
- **Emergency Controls**: Manual fetch if needed
- **Reset Functions**: Reset AI summaries for reprocessing
- **Monitoring Tools**: View recent articles and status

## 🔧 Configuration Options

### News Fetch Scheduler Settings
```python
FETCH_INTERVAL = 6 hours          # How often to fetch
SYMBOLS_COUNT = 100+              # Number of symbols
ARTICLES_PER_SYMBOL = 2           # Articles per symbol
CHUNK_SIZE = 5                    # Parallel processing
RETRY_ATTEMPTS = 2                # Error recovery
```

### AI Processing Scheduler Settings
```python
PROCESSING_INTERVAL = 10 minutes  # How often to process
MAX_ARTICLES_PER_RUN = 10         # Articles per run
AI_MODEL = "claude-3.5-sonnet"    # AI model used
STRUCTURED_FORMAT = True          # Use structured summaries
```

## 📊 Monitoring and Alerts

### Log Messages to Watch For

**News Fetch Scheduler**:
```
🚀 News fetch scheduler started - will run every 6 hours
🤖 Starting automated news fetch job...
📊 Processing 100 symbols in 20 chunks
✅ Fetched 2 articles for NASDAQ:AAPL
🎯 News fetch job completed: 190 articles fetched
```

**AI Processing Scheduler**:
```
🧠 AI processing scheduler started - will run every 10 minutes
🤖 Starting AI processing job...
📝 Processing article: "Apple Reports Strong Q4 Earnings"
✅ Generated structured summary and insights
🎯 AI processing completed: 10 articles processed
```

### Health Checks

**Daily Monitoring**:
- [ ] Both schedulers showing "Running" status
- [ ] New articles appearing in database
- [ ] AI summaries being generated
- [ ] No excessive error messages in logs

**Weekly Review**:
- [ ] Article fetch success rate > 90%
- [ ] AI processing success rate > 95%
- [ ] Database growth consistent with expectations
- [ ] No performance degradation

## 🛠️ Troubleshooting

### Common Issues

**Scheduler Stopped Unexpectedly**
```bash
# Check logs for errors
tail -f news_fetch_scheduler.log
tail -f ai_processing_scheduler.log

# Restart via web interface
# Or use startup scripts
python start_news_fetch_scheduler.py
```

**Low Article Fetch Rate**
- Check API connectivity
- Verify symbol list is current
- Review failed symbol patterns
- Check rate limiting issues

**AI Processing Failures**
- Verify OpenRouter API key
- Check AI model availability
- Review article content quality
- Monitor API usage limits

### Performance Optimization

**For High Volume**:
- Increase chunk size for faster processing
- Reduce delays between API calls
- Use parallel processing where possible
- Optimize database queries

**For Reliability**:
- Increase retry attempts
- Add exponential backoff
- Implement health checks
- Set up monitoring alerts

## 🔮 Future Enhancements

### Planned Features
- **Smart Scheduling**: Adjust intervals based on market hours
- **Priority Processing**: Process high-impact news first
- **Quality Scoring**: Rate article relevance and importance
- **Custom Filters**: User-defined symbol and topic filters

### Advanced Automation
- **Market Event Detection**: Identify significant market events
- **Sentiment Trending**: Track sentiment changes over time
- **Automated Reporting**: Generate daily/weekly summaries
- **Integration APIs**: Connect with external trading systems

## 📋 Quick Reference

### Essential URLs
- **News Fetch Scheduler**: `/news/fetch-scheduler`
- **AI Processing Scheduler**: `/news/scheduler-status`
- **Manual News Fetch**: `/news/fetch`
- **View Articles**: `/news/`

### Key Commands
```bash
# Start schedulers manually
python start_news_fetch_scheduler.py

# Check scheduler status
curl http://localhost:5000/news/api/fetch-scheduler/status

# View recent logs
tail -f news_fetch_scheduler.log
```

### Emergency Procedures
1. **Stop All Automation**: Use web interfaces to stop both schedulers
2. **Manual Override**: Use `/news/fetch` for emergency news fetching
3. **Reset AI Content**: Use "Reset AI Summaries" for reprocessing
4. **Database Backup**: Regular backups before major changes

---

## 🎉 Success Metrics

With the complete automation system running, you should see:

- **📈 Consistent Growth**: 800+ new articles daily
- **🤖 AI Coverage**: 1440+ articles with structured summaries daily  
- **⚡ Real-time Updates**: Fresh content every 6 hours
- **🎯 Zero Manual Work**: Complete hands-off operation
- **📊 Professional Quality**: Structured, consistent content format

The system provides **enterprise-grade automation** for news analysis with minimal maintenance required. Simply start both schedulers and enjoy continuous, high-quality news processing! 