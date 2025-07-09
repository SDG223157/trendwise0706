# 🚀 Coolify AI Keyword Search Deployment

## ✅ Prerequisites

Your `requirements.txt` already includes the necessary modules:
- `nltk==3.8.1` - Natural language processing
- `fuzzywuzzy==0.18.0` - Fuzzy string matching
- `python-Levenshtein==0.21.1` - Fast string similarity

## 📋 Step-by-Step Deployment

### 1. Deploy to Coolify
First, deploy your app to Coolify as usual. Your existing `requirements.txt` will automatically install the AI keyword search dependencies.

### 2. SSH into your Coolify container
```bash
# Connect to your Coolify container
coolify ssh your-app-name

# Or use regular SSH if you have container access
ssh user@your-coolify-server
cd /path/to/your/app
```

### 3. Run the AI Search Setup Script
```bash
# Make the script executable
chmod +x coolify_setup_ai_search.py

# Run the setup script
python3 coolify_setup_ai_search.py
```

This will:
- ✅ Download required NLTK data
- ✅ Create keyword database tables
- ✅ Extract keywords from your existing articles
- ✅ Test all API endpoints

### 4. Verify the Installation
```bash
# Run the verification script
python3 test_ai_search_coolify.py
```

### 5. Test the API Endpoints
```bash
# Test search suggestions
curl "http://your-domain/news/api/suggestions?q=earnings"

# Test trending keywords
curl "http://your-domain/news/api/keywords/trending"

# Test analytics
curl "http://your-domain/news/api/analytics/suggestions"
```

## 🎯 Expected Results

After successful deployment, you should see:

### 1. Enhanced Search Page
- Real-time AI suggestions as you type
- Category icons (💰 financial, 🔧 technology, 🏢 company)
- Trending keywords section
- Keyboard navigation (arrow keys)

### 2. API Responses
```json
{
  "suggestions": [
    {
      "keyword": "earnings",
      "category": "financial",
      "relevance_score": 0.95,
      "frequency": 125
    }
  ],
  "query": "earnings",
  "total_results": 1,
  "cached": false
}
```

### 3. Database Tables Created
- `news_keywords` - Extracted keywords with categories
- `article_keywords` - Article-keyword relationships
- `keyword_similarities` - Semantic relationships
- `search_analytics` - User behavior tracking

## 🚨 Troubleshooting

### Issue: "Module not found" errors
```bash
# Reinstall requirements
pip install -r requirements.txt
```

### Issue: "Database tables not created"
```bash
# Run setup again
python3 coolify_setup_ai_search.py
```

### Issue: "No keywords found"
```bash
# Check if you have articles with AI summaries
python3 -c "
from app import create_app, db
from app.models import NewsArticle
app = create_app()
with app.app_context():
    count = NewsArticle.query.filter(NewsArticle.ai_summary.isnot(None)).count()
    print(f'Articles with AI summaries: {count}')
"
```

### Issue: "Slow suggestions"
```bash
# Check Redis connection
redis-cli ping
```

## 🔄 Maintenance

### Weekly: Clean old analytics
```bash
python3 -c "
from app import create_app, db
from app.models import SearchAnalytics
from datetime import datetime, timedelta
app = create_app()
with app.app_context():
    cutoff = datetime.utcnow() - timedelta(days=30)
    old_records = SearchAnalytics.query.filter(SearchAnalytics.created_at < cutoff).delete()
    db.session.commit()
    print(f'Cleaned {old_records} old analytics records')
"
```

### Monthly: Extract new keywords
```bash
python3 extract_keywords_from_articles.py --recent --days 30
```

## 🎉 Success Indicators

✅ **Your AI keyword search is working when:**
1. Search page shows suggestions as you type
2. API endpoints return keyword data
3. Database contains extracted keywords
4. Response times are <100ms for cached suggestions

## 📞 Quick Support Commands

```bash
# Check keyword count
python3 -c "from app import create_app, db; from app.models import NewsKeyword; app = create_app(); app.app_context().push(); print(f'Keywords: {NewsKeyword.query.count()}')"

# Test suggestions manually
python3 -c "from app.utils.search.intelligent_suggestions import intelligent_suggestion_service; print(intelligent_suggestion_service.get_suggestions('earnings', limit=3))"

# Check API endpoint
curl "http://localhost/news/api/suggestions?q=test"
```

---

**Ready to deploy?** Follow these steps and your AI keyword search system will be live on Coolify! 🚀 