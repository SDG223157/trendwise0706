"""
Examples of how to integrate Redis caching into your existing routes and services
Copy these patterns into your actual code files
"""

# ============================================================================
# 1. USER AUTHENTICATION CACHING INTEGRATION
# ============================================================================

# In app/auth/routes.py - Replace existing user queries
from app.utils.cache.user_cache import user_cache

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced login with user caching"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        # TRY CACHE FIRST
        cached_user = user_cache.get_user_by_email(email)
        if cached_user:
            logger.debug(f"🎯 User cache hit for email: {email}")
            user = User(**cached_user)  # Reconstruct user object
        else:
            # FALLBACK TO DATABASE
            user = User.query.filter_by(email=email).first()
            if user:
                user_cache.cache_user_complete(user.to_dict())
                logger.debug(f"💾 Cached user data for: {email}")
        
        # ... rest of login logic

# In app/models.py - Add cache invalidation to User model
class User(UserMixin, db.Model):
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()
        
        # INVALIDATE AND UPDATE CACHE
        user_cache.invalidate_user(self.id, self.email, self.username)
        user_cache.cache_user_complete(self.to_dict())

# ============================================================================
# 2. ADMIN ROUTES CACHING INTEGRATION  
# ============================================================================

# In app/admin/routes.py - Cache expensive admin queries
from app.utils.cache.db_cache import db_cache

@bp.route('/manage_users')
@login_required
@admin_required
def manage_users():
    """Enhanced admin users page with caching"""
    page = request.args.get('page', 1, type=int)
    
    # TRY CACHE FIRST
    cached_user_list = db_cache.get_admin_user_list(page)
    if cached_user_list:
        logger.debug(f"🎯 Admin user list cache hit for page: {page}")
        return render_template('admin/manage_users.html', **cached_user_list)
    
    # FALLBACK TO DATABASE
    query = User.query
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get statistics with caching
    cached_stats = db_cache.get_user_statistics()
    if not cached_stats:
        stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter(User.is_active == True).count(),
            'admin_users': User.query.filter(User.is_admin == True).count(),
        }
        db_cache.set_user_statistics(stats)
        logger.debug("💾 Cached user statistics")
    else:
        stats = cached_stats
        logger.debug("🎯 User statistics cache hit")
    
    template_data = {
        'users': users,
        'stats': stats
    }
    
    # CACHE THE RESULTS
    db_cache.set_admin_user_list(template_data, page)
    logger.debug(f"💾 Cached admin user list for page: {page}")
    
    return render_template('admin/manage_users.html', **template_data)

# ============================================================================
# 3. NEWS ROUTES AI PROCESSING CACHING
# ============================================================================

# In app/news/routes.py - Cache AI processing results
from app.utils.cache.api_cache import api_cache

@bp.route('/api/update-summaries', methods=['POST'])
@login_required
def update_ai_summaries():
    """Enhanced AI processing with caching"""
    try:
        articles = NewsArticle.query.filter(
            db.or_(
                NewsArticle.ai_summary.is_(None),
                NewsArticle.ai_insights.is_(None),
                NewsArticle.ai_sentiment_rating.is_(None)
            ),
            NewsArticle.content.isnot(None),
            db.func.length(db.func.trim(NewsArticle.content)) > 20
        ).limit(10).all()
        
        processed = 0
        for article in articles:
            content = article.content
            
            # CHECK CACHE FIRST
            cached_analysis = api_cache.get_ai_complete_analysis(content)
            if cached_analysis:
                logger.debug(f"🎯 AI analysis cache hit for article {article.id}")
                
                if cached_analysis['summary']:
                    article.ai_summary = cached_analysis['summary']
                if cached_analysis['insights']:
                    article.ai_insights = cached_analysis['insights']
                if cached_analysis['sentiment_rating'] is not None:
                    article.ai_sentiment_rating = cached_analysis['sentiment_rating']
                
                db.session.commit()
                processed += 1
                continue
            
            # FALLBACK TO API CALLS
            ai_summary = None
            ai_insights = None
            ai_sentiment_rating = None
            
            # Make API calls (existing code)...
            # ... your existing OpenRouter API calls here ...
            
            # CACHE THE RESULTS
            if ai_summary or ai_insights or ai_sentiment_rating is not None:
                api_cache.set_ai_complete_analysis(
                    content, ai_summary, ai_insights, ai_sentiment_rating
                )
                logger.debug(f"💾 Cached AI analysis for article {article.id}")
        
        return jsonify({'status': 'success', 'processed': processed})
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# 4. STOCK DATA SERVICE CACHING INTEGRATION
# ============================================================================

# In app/utils/data/data_service.py - Cache expensive data operations
from app.utils.cache.stock_cache import stock_cache

class DataService:
    def get_historical_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Enhanced historical data fetching with caching"""
        
        # CHECK CACHE FIRST
        cached_data = stock_cache.get_stock_data(ticker, start_date, end_date)
        if cached_data:
            logger.debug(f"🎯 Stock data cache hit for {ticker}")
            df = pd.DataFrame(cached_data['data'])
            df.set_index('Date', inplace=True)
            return df
        
        # CHECK TABLE EXISTS CACHE
        table_name = f"his_{self.clean_ticker_for_table_name(ticker)}"
        table_exists = stock_cache.get_table_exists(table_name)
        
        if table_exists is None:
            # Check database and cache result
            exists = self.table_exists(table_name)
            stock_cache.set_table_exists(table_name, exists)
            logger.debug(f"💾 Cached table existence for {table_name}")
        else:
            exists = table_exists
            logger.debug(f"🎯 Table existence cache hit for {table_name}")
        
        # ... existing data fetching logic ...
        
        # CACHE THE RESULTS
        if not df.empty:
            cache_data = {
                'data': df.reset_index().to_dict('records'),
                'ticker': ticker,
                'start_date': start_date,
                'end_date': end_date
            }
            stock_cache.set_stock_data(ticker, start_date, end_date, cache_data)
            logger.debug(f"💾 Cached stock data for {ticker}")
        
        return df
    
    def get_financial_data(self, ticker: str, metric_description: str, 
                          start_year: str, end_year: str) -> pd.Series:
        """Enhanced financial data with caching"""
        
        # CHECK CACHE FIRST
        cached_metric = stock_cache.get_financial_metric(
            ticker, metric_description, start_year, end_year
        )
        if cached_metric:
            logger.debug(f"🎯 Financial metric cache hit for {ticker}:{metric_description}")
            return pd.Series(
                cached_metric['values'],
                index=cached_metric['years'],
                name=metric_description
            )
        
        # ... existing financial data fetching logic ...
        
        # CACHE THE RESULTS
        if not result.empty:
            cache_data = {
                'values': result.values.tolist(),
                'years': result.index.tolist(),
                'metric': metric_description
            }
            stock_cache.set_financial_metric(
                ticker, metric_description, start_year, end_year, cache_data
            )
            logger.debug(f"💾 Cached financial metric for {ticker}:{metric_description}")
        
        return result

# ============================================================================
# 5. NEWS SEARCH ENHANCEMENT (ADD TO EXISTING)
# ============================================================================

# In app/utils/search/news_search.py - Enhance existing search
from app.utils.cache.db_cache import db_cache

class NewsSearch:
    def get_processing_status_cached(self, symbol: str) -> Dict:
        """Enhanced processing status with caching"""
        
        # CHECK CACHE FIRST
        cached_status = db_cache.get_symbol_processing_status(symbol)
        if cached_status:
            logger.debug(f"🎯 Processing status cache hit for {symbol}")
            return cached_status
        
        # FALLBACK TO DATABASE
        total_articles = self.session.query(NewsArticle).join(ArticleSymbol).filter(
            ArticleSymbol.symbol.like(f'%{symbol}%')
        ).count()
        
        ai_processed = self.session.query(NewsArticle).join(ArticleSymbol).filter(
            ArticleSymbol.symbol.like(f'%{symbol}%'),
            NewsArticle.ai_summary.isnot(None),
            NewsArticle.ai_insights.isnot(None),
            NewsArticle.ai_sentiment_rating.isnot(None)
        ).count()
        
        status = {
            'symbol': symbol,
            'total_articles': total_articles,
            'ai_processed': ai_processed,
            'processing_rate': round((ai_processed / total_articles * 100), 1) if total_articles > 0 else 0
        }
        
        # CACHE THE RESULTS
        db_cache.set_symbol_processing_status(symbol, status)
        logger.debug(f"💾 Cached processing status for {symbol}")
        
        return status

# ============================================================================
# 6. SYMBOL SUGGESTIONS CACHING
# ============================================================================

# In app/news/routes.py - Enhance symbol suggestions
@bp.route('/api/symbol-suggest')
@login_required
def symbol_suggest():
    """Enhanced symbol suggestions with caching"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    # CHECK CACHE FIRST
    cached_suggestions = db_cache.get_symbol_suggestions(query)
    if cached_suggestions:
        logger.debug(f"🎯 Symbol suggestions cache hit for: {query}")
        return jsonify(cached_suggestions)
    
    # ... existing symbol suggestion logic ...
    
    # CACHE THE RESULTS
    if suggestions:
        db_cache.set_symbol_suggestions(query, suggestions)
        logger.debug(f"💾 Cached symbol suggestions for: {query}")
    
    return jsonify(suggestions)

# ============================================================================
# 7. PERFORMANCE MONITORING
# ============================================================================

# Add to any route for monitoring
def log_cache_performance():
    """Log cache performance statistics"""
    from app.utils.cache.api_cache import api_cache
    from app.utils.cache.stock_cache import stock_cache
    from app.utils.cache.db_cache import db_cache
    
    stats = {
        'api_cache': api_cache.get_cache_performance_stats(),
        'stock_cache': stock_cache.get_cache_stats(),
        'db_cache': db_cache.is_available()
    }
    
    logger.info(f"📊 Cache Performance: {stats}")
    return stats

# ============================================================================
# 8. CACHE WARMING STRATEGY
# ============================================================================

def warm_cache_startup():
    """Warm up cache with commonly accessed data on app startup"""
    try:
        # Warm user statistics
        if not db_cache.get_user_statistics():
            stats = {
                'total_users': User.query.count(),
                'active_users': User.query.filter(User.is_active == True).count(),
            }
            db_cache.set_user_statistics(stats)
            logger.info("🔥 Warmed up user statistics cache")
        
        # Warm trending symbols
        if not db_cache.get_trending_symbols():
            # Get some sample trending data
            trending = []  # Your logic here
            db_cache.set_trending_symbols(trending)
            logger.info("🔥 Warmed up trending symbols cache")
            
    except Exception as e:
        logger.error(f"Error warming cache: {str(e)}")

# Call this in app/__init__.py after app creation:
# warm_cache_startup() 