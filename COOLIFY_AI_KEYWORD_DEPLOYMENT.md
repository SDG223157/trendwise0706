# AI Keyword Search - Coolify Deployment Guide

## 🚀 Quick Setup on Coolify

### 1. Upload the Deployment Script
First, upload the deployment script to your Coolify environment:

```bash
# Copy the deployment script to your Coolify container
scp deploy_ai_keyword_search.py your-coolify-server:/path/to/trendwise0706/
```

### 2. Run the Deployment Script
SSH into your Coolify container and run:

```bash
cd /path/to/trendwise0706
python3 deploy_ai_keyword_search.py
```

This will:
- ✅ Install all required dependencies
- ✅ Create keyword database tables
- ✅ Extract sample keywords from existing articles
- ✅ Test API endpoints
- ✅ Set up the AI-powered search system

### 3. Verify the Installation

After deployment, test the new features:

```bash
# Test search suggestions
curl 'http://your-coolify-url/news/api/suggestions?q=earnings'

# Test trending keywords
curl 'http://your-coolify-url/news/api/keywords/trending'

# Test analytics
curl 'http://your-coolify-url/news/api/analytics/suggestions'
```

### 4. Expected API Responses

**Search Suggestions:**
```json
{
  "suggestions": [
    {
      "keyword": "earnings",
      "category": "financial",
      "relevance_score": 0.95,
      "frequency": 125
    },
    {
      "keyword": "earnings report",
      "category": "financial", 
      "relevance_score": 0.88,
      "frequency": 89
    }
  ],
  "query": "earnings",
  "total_results": 2,
  "cached": false
}
```

**Trending Keywords:**
```json
{
  "trending_keywords": [
    {
      "keyword": "artificial intelligence",
      "category": "technology",
      "frequency": 234,
      "growth_rate": 15.2
    },
    {
      "keyword": "merger",
      "category": "financial",
      "frequency": 156,
      "growth_rate": 12.8
    }
  ],
  "time_period": "24h",
  "total_trending": 2
}
```

## 🎯 Testing the Enhanced Search UI

After deployment, visit your news search page and you should see:

1. **Real-time Suggestions**: As you type, AI-powered suggestions appear
2. **Category Icons**: Different icons for financial, technology, company keywords
3. **Trending Topics**: Popular searches displayed prominently
4. **Smart Autocomplete**: Suggestions based on your database content

## 📊 Features Activated

### AI-Powered Search Suggestions
- **Semantic matching**: Finds related concepts, not just exact matches
- **Context-aware**: Understands financial and market terminology
- **Real-time**: <100ms response time for cached suggestions
- **Self-improving**: Learns from user interactions

### Enhanced Search Experience
- **Keyboard navigation**: Arrow keys to navigate suggestions
- **Visual categories**: Icons distinguish between company, financial, tech keywords
- **Search history**: Remembers recent searches
- **Trending topics**: Shows what's popular in your database

### Analytics & Monitoring
- **Click tracking**: Monitors which suggestions users select
- **Performance metrics**: Response times and cache hit rates
- **User behavior**: Search patterns and preferences

## 🔧 Configuration Options

### Environment Variables
Add these to your Coolify environment:

```bash
# AI Keyword Extraction
OPENROUTER_API_KEY=your_openrouter_key  # Optional: for advanced AI extraction
KEYWORD_EXTRACTION_ENABLED=true
SUGGESTIONS_CACHE_TIME=300  # 5 minutes

# Search Performance
MAX_SUGGESTIONS=10
SIMILARITY_THRESHOLD=0.6
ENABLE_SEARCH_ANALYTICS=true
```

### Database Configuration
The system creates these new tables:
- `news_keywords`: Extracted keywords with relevance scores
- `article_keywords`: Article-keyword relationships
- `keyword_similarities`: Semantic relationships
- `search_analytics`: User behavior tracking

## 🚨 Troubleshooting

### Common Issues

**1. "No keywords found" Error**
```bash
# Re-run keyword extraction
python3 extract_keywords_from_articles.py --batch-size 50
```

**2. Slow Suggestions**
```bash
# Check Redis connection
redis-cli ping

# Warm the cache
curl 'http://your-url/news/api/suggestions?q=earnings'
```

**3. API Endpoints Not Working**
```bash
# Check if tables exist
python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print('Tables:', [t for t in tables if 'keyword' in t])
"
```

## 📈 Performance Optimization

### Cache Warming
Run this after deployment to pre-populate the cache:

```bash
# Common search terms
curl 'http://your-url/news/api/suggestions?q=earnings'
curl 'http://your-url/news/api/suggestions?q=revenue'
curl 'http://your-url/news/api/suggestions?q=merger'
curl 'http://your-url/news/api/suggestions?q=technology'
```

### Keyword Extraction
For better keyword quality, run the full extraction:

```bash
# Extract keywords from all articles (may take time)
python3 extract_keywords_from_articles.py --all
```

## 🎉 Success Indicators

You'll know the system is working when:

1. **Search page loads with suggestions** as you type
2. **API endpoints respond** with keyword data
3. **Trending keywords** appear on the search page
4. **Response times** are <100ms for cached suggestions
5. **Analytics data** is being collected

## 📱 Mobile Optimization

The enhanced search UI is mobile-responsive with:
- Touch-friendly suggestion selection
- Responsive layout for different screen sizes
- Optimized performance for mobile connections

## 🔄 Maintenance

### Weekly Tasks
```bash
# Clean up old analytics data
python3 -c "
from app import create_app, db
from app.models import SearchAnalytics
from datetime import datetime, timedelta

app = create_app()
with app.app_context():
    cutoff = datetime.utcnow() - timedelta(days=30)
    old_analytics = SearchAnalytics.query.filter(SearchAnalytics.created_at < cutoff).delete()
    db.session.commit()
    print(f'Cleaned up {old_analytics} old analytics records')
"
```

### Monthly Tasks
```bash
# Re-extract keywords from new articles
python3 extract_keywords_from_articles.py --recent --days 30
```

## 📞 Support

If you encounter issues:
1. Check the `ai_keyword_deploy.log` file for detailed logs
2. Verify database connections and table existence
3. Test API endpoints individually
4. Check Redis connectivity for caching

---

**Ready to deploy?** Run the deployment script and test the enhanced search experience! 🚀 