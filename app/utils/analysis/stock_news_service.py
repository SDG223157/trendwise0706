#!/usr/bin/env python3
"""
Stock News Integration Service

This service automatically fetches and processes news articles for a specific stock
symbol after stock analysis is completed. It integrates with the existing news
fetching and AI processing infrastructure (which runs every 30 minutes automatically).

Features:
- Fetches latest 10 news articles for analyzed stock
- Processes articles with AI summaries and insights
- Runs asynchronously to avoid blocking analysis page rendering
- Integrates with existing news scheduler infrastructure (30-minute intervals)
- Automatically checks for recent news during analysis snapshot rendering
- Triggers background fetching if no recent news exists
- Intelligent caching and threshold management to avoid unnecessary fetches
- Daily fetch record tracking to prevent duplicate attempts for stocks with no/old news
"""

import os
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from app.utils.analysis.news_service import NewsAnalysisService
from app.utils.scheduler.news_scheduler import NewsAIScheduler
from app.models import NewsArticle, ArticleSymbol
from app import db
from sqlalchemy import text, desc, and_, or_
import requests

# Set up logging
logger = logging.getLogger(__name__)

class NewsOptimizationConfig:
    """Configuration for intelligent news fetching optimization"""
    
    # Time thresholds for different scenarios (in hours)
    RECENT_NEWS_THRESHOLD = 48  # Consider news "recent" if within 48 hours
    STALE_NEWS_THRESHOLD = 24   # Fetch if latest news is older than 24 hours
    MINIMAL_NEWS_THRESHOLD = 6  # For high-frequency stocks, minimum 6 hours between fetches
    
    # Cache control
    NEWS_CHECK_CACHE_DURATION = 300  # Cache news check results for 5 minutes
    FETCH_RECORD_CACHE_DURATION = 86400  # Cache fetch records for 24 hours (1 day)
    
    # Stock-specific thresholds (can be expanded based on volatility, trading volume, etc.)
    HIGH_FREQUENCY_STOCKS = {'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META'}
    
    # Fetch record tracking
    DAILY_FETCH_LIMIT = 2  # Maximum fetch attempts per stock per day for no-news scenarios
    
    @classmethod
    def get_threshold_for_stock(cls, symbol: str) -> Dict:
        """Get optimized thresholds based on stock characteristics"""
        symbol_upper = symbol.upper()
        
        if symbol_upper in cls.HIGH_FREQUENCY_STOCKS:
            return {
                'recent_threshold': 24,    # Check last 24 hours for high-frequency stocks
                'stale_threshold': 12,     # Fetch if older than 12 hours
                'min_interval': 6,         # Minimum 6 hours between fetches
                'daily_fetch_limit': 3     # Allow more attempts for high-frequency stocks
            }
        else:
            return {
                'recent_threshold': cls.RECENT_NEWS_THRESHOLD,
                'stale_threshold': cls.STALE_NEWS_THRESHOLD,
                'min_interval': cls.MINIMAL_NEWS_THRESHOLD,
                'daily_fetch_limit': cls.DAILY_FETCH_LIMIT
            }

class FetchRecordTracker:
    """Tracks daily fetch attempts and results to prevent redundant fetches"""
    
    def __init__(self):
        from app.utils.cache.news_cache import NewsCache
        self.cache = NewsCache()
    
    def get_daily_fetch_key(self, symbol: str, date: str = None) -> str:
        """Generate cache key for daily fetch record"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        return f"fetch_record:{symbol.upper()}:{date}"
    
    def get_fetch_record(self, symbol: str, date: str = None) -> Dict:
        """Get fetch record for a symbol on a specific date"""
        if not self.cache.is_available():
            return {'attempts': 0, 'results': []}
        
        cache_key = self.get_daily_fetch_key(symbol, date)
        record = self.cache.get_json(cache_key)
        
        if not record:
            record = {
                'symbol': symbol.upper(),
                'date': date or datetime.now().strftime('%Y-%m-%d'),
                'attempts': 0,
                'results': [],
                'first_attempt': None,
                'last_attempt': None
            }
        
        return record
    
    def record_fetch_attempt(self, symbol: str, result_type: str, articles_found: int = 0, details: str = "") -> Dict:
        """
        Record a fetch attempt and its result
        
        Args:
            symbol: Stock symbol
            result_type: 'success', 'no_news', 'old_news', 'error'
            articles_found: Number of articles found
            details: Additional details about the fetch
            
        Returns:
            Updated fetch record
        """
        if not self.cache.is_available():
            return {}
        
        record = self.get_fetch_record(symbol)
        current_time = datetime.now().isoformat()
        
        # Update attempt count
        record['attempts'] += 1
        
        # Record this attempt
        attempt_record = {
            'timestamp': current_time,
            'result_type': result_type,
            'articles_found': articles_found,
            'details': details
        }
        record['results'].append(attempt_record)
        
        # Update first/last attempt times
        if not record['first_attempt']:
            record['first_attempt'] = current_time
        record['last_attempt'] = current_time
        
        # Save to cache
        cache_key = self.get_daily_fetch_key(symbol)
        self.cache.set_json(cache_key, record, expire=NewsOptimizationConfig.FETCH_RECORD_CACHE_DURATION)
        
        logger.info(f"📝 Recorded fetch attempt for {symbol}: {result_type} ({articles_found} articles)")
        return record
    
    def should_allow_fetch(self, symbol: str, force: bool = False) -> Dict:
        """
        Check if a fetch should be allowed based on daily record
        
        Args:
            symbol: Stock symbol
            force: Force fetch regardless of daily limits
            
        Returns:
            Dict with decision and reasoning
        """
        if force:
            return {
                'allow_fetch': True,
                'reason': 'forced_fetch',
                'details': 'Fetch forced by user override'
            }
        
        if not self.cache.is_available():
            return {
                'allow_fetch': True,
                'reason': 'cache_unavailable',
                'details': 'Cache not available, allowing fetch'
            }
        
        record = self.get_fetch_record(symbol)
        thresholds = NewsOptimizationConfig.get_threshold_for_stock(symbol)
        daily_limit = thresholds['daily_fetch_limit']
        
        # Check if we've exceeded daily limit
        if record['attempts'] >= daily_limit:
            # Check if any recent attempts were successful
            recent_success = any(
                r['result_type'] == 'success' and r['articles_found'] > 0 
                for r in record['results']
            )
            
            if not recent_success:
                return {
                    'allow_fetch': False,
                    'reason': 'daily_limit_exceeded',
                    'details': f"Exceeded daily limit ({daily_limit}) with no successful fetches today",
                    'attempts_today': record['attempts'],
                    'daily_limit': daily_limit,
                    'last_results': [r['result_type'] for r in record['results'][-3:]]
                }
        
        # Check recent failed attempts
        if record['results']:
            recent_results = record['results'][-2:]  # Last 2 attempts
            if len(recent_results) >= 2:
                all_failed = all(
                    r['result_type'] in ['no_news', 'old_news'] and r['articles_found'] == 0
                    for r in recent_results
                )
                
                if all_failed:
                    # Check if last attempt was recent (within 6 hours)
                    last_attempt = datetime.fromisoformat(record['last_attempt'])
                    hours_since = (datetime.now() - last_attempt).total_seconds() / 3600
                    
                    if hours_since < 6:
                        return {
                            'allow_fetch': False,
                            'reason': 'recent_failed_attempts',
                            'details': f"Last 2 attempts found no/old news, and last attempt was {hours_since:.1f}h ago",
                            'hours_since_last': hours_since,
                            'last_results': [r['result_type'] for r in recent_results]
                        }
        
        return {
            'allow_fetch': True,
            'reason': 'within_limits',
            'details': f"Within daily limit ({record['attempts']}/{daily_limit})",
            'attempts_today': record['attempts'],
            'daily_limit': daily_limit
        }
    
    def get_daily_stats(self, symbol: str = None, date: str = None) -> Dict:
        """Get daily fetch statistics"""
        if not self.cache.is_available():
            return {'error': 'Cache not available'}
        
        if symbol:
            # Stats for specific symbol
            record = self.get_fetch_record(symbol, date)
            return {
                'symbol': symbol,
                'date': record['date'],
                'total_attempts': record['attempts'],
                'results_summary': {
                    'success': len([r for r in record['results'] if r['result_type'] == 'success']),
                    'no_news': len([r for r in record['results'] if r['result_type'] == 'no_news']),
                    'old_news': len([r for r in record['results'] if r['result_type'] == 'old_news']),
                    'error': len([r for r in record['results'] if r['result_type'] == 'error'])
                },
                'first_attempt': record['first_attempt'],
                'last_attempt': record['last_attempt']
            }
        else:
            # Overall stats would require scanning cache keys
            # Simplified implementation for now
            return {
                'date': date or datetime.now().strftime('%Y-%m-%d'),
                'note': 'Use symbol parameter for detailed stats'
            }
    
    def clear_daily_record(self, symbol: str, date: str = None):
        """Clear fetch record for a symbol on a specific date"""
        if not self.cache.is_available():
            return False
        
        cache_key = self.get_daily_fetch_key(symbol, date)
        try:
            self.cache.redis.delete(cache_key) if self.cache.redis else None
            logger.info(f"🧹 Cleared daily fetch record for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error clearing fetch record: {str(e)}")
            return False

class StockNewsService:
    """Service for integrating stock analysis with news fetching and AI processing"""
    
    # Global control variable for news fetching
    _news_fetching_enabled = True
    
    # Cache for recent news checks to avoid repeated database queries
    _news_check_cache = {}
    
    # Fetch record tracker for daily limits
    _fetch_tracker = None
    
    @classmethod
    def get_fetch_tracker(cls):
        """Get or create fetch record tracker instance"""
        if cls._fetch_tracker is None:
            cls._fetch_tracker = FetchRecordTracker()
        return cls._fetch_tracker
    
    @classmethod
    def is_news_fetching_enabled(cls) -> bool:
        """Check if news fetching is globally enabled"""
        return cls._news_fetching_enabled
    
    @classmethod 
    def enable_news_fetching(cls):
        """Enable news fetching globally"""
        cls._news_fetching_enabled = True
        logger.info("📰 News fetching globally enabled")
        
    @classmethod
    def disable_news_fetching(cls):
        """Disable news fetching globally"""
        cls._news_fetching_enabled = False
        logger.info("🚫 News fetching globally disabled")

    @staticmethod
    def check_recent_news_status(symbol: str, hours_threshold: int = None, use_smart_thresholds: bool = True) -> Dict:
        """
        Enhanced news status checking with intelligent thresholds and caching
        
        Args:
            symbol: Stock symbol to check (will be normalized to TradingView format)
            hours_threshold: Override default threshold (optional)
            use_smart_thresholds: Use stock-specific intelligent thresholds
            
        Returns:
            Dict with comprehensive status information
        """
        try:
            from app.utils.symbol_utils import normalize_ticker
            from app.utils.search.news_search import NewsSearch
            from app.utils.cache.news_cache import NewsCache
            
            # Check cache first to avoid repeated database queries
            cache_key = f"news_check:{symbol}:{hours_threshold}:{use_smart_thresholds}"
            cache = NewsCache()
            
            if cache.is_available():
                cached_result = cache.get_json(cache_key)
                if cached_result:
                    logger.debug(f"📋 Using cached news status for {symbol}")
                    return cached_result
            
            # Get intelligent thresholds for this stock
            if use_smart_thresholds:
                thresholds = NewsOptimizationConfig.get_threshold_for_stock(symbol)
                recent_threshold = hours_threshold or thresholds['recent_threshold']
                stale_threshold = thresholds['stale_threshold']
                min_interval = thresholds['min_interval']
                
                logger.info(f"🎯 Using smart thresholds for {symbol}: recent={recent_threshold}h, stale={stale_threshold}h, min_interval={min_interval}h")
            else:
                recent_threshold = hours_threshold or NewsOptimizationConfig.RECENT_NEWS_THRESHOLD
                stale_threshold = NewsOptimizationConfig.STALE_NEWS_THRESHOLD
                min_interval = NewsOptimizationConfig.MINIMAL_NEWS_THRESHOLD
            
            # Get symbol variants for comprehensive search
            news_search = NewsSearch(db.session)
            symbol_variants = news_search.get_symbol_variants(symbol)
            
            # Also add TradingView format conversion
            tv_symbol = normalize_ticker(symbol, purpose='search')
            if tv_symbol not in symbol_variants:
                symbol_variants.append(tv_symbol)
            
            logger.debug(f"🔍 Checking recent news for {symbol}, variants: {symbol_variants}")
            
            # Calculate cutoff time for "recent" news
            recent_cutoff = datetime.now() - timedelta(hours=recent_threshold)
            
            # Query for recent articles with any of the symbol variants
            recent_articles = db.session.query(NewsArticle).join(ArticleSymbol).filter(
                and_(
                    ArticleSymbol.symbol.in_(symbol_variants),
                    NewsArticle.published_at >= recent_cutoff
                )
            ).order_by(desc(NewsArticle.published_at)).all()
            
            # Get latest article for any variant
            latest_article = db.session.query(NewsArticle).join(ArticleSymbol).filter(
                ArticleSymbol.symbol.in_(symbol_variants)
            ).order_by(desc(NewsArticle.published_at)).first()
            
            # Calculate age of latest article
            latest_age_hours = None
            if latest_article:
                age_delta = datetime.now() - latest_article.published_at
                latest_age_hours = int(age_delta.total_seconds() / 3600)
            
            has_recent_news = len(recent_articles) > 0
            
            # Enhanced logic for determining if we should fetch
            should_fetch = False
            fetch_reason = ""
            
            if not has_recent_news:
                should_fetch = True
                fetch_reason = f"No articles found within {recent_threshold} hours"
            elif latest_age_hours and latest_age_hours > stale_threshold:
                should_fetch = True
                fetch_reason = f"Latest article is {latest_age_hours}h old (threshold: {stale_threshold}h)"
            elif latest_age_hours and latest_age_hours < min_interval:
                should_fetch = False
                fetch_reason = f"Recent fetch {latest_age_hours}h ago (min interval: {min_interval}h)"
            else:
                should_fetch = False
                fetch_reason = f"Recent news available ({len(recent_articles)} articles, latest: {latest_age_hours}h ago)"
            
            result = {
                'has_recent_news': has_recent_news,
                'latest_article_age_hours': latest_age_hours,
                'total_recent_articles': len(recent_articles),
                'should_fetch': should_fetch,
                'fetch_reason': fetch_reason,
                'symbol_variants': symbol_variants,
                'thresholds_used': {
                    'recent_threshold': recent_threshold,
                    'stale_threshold': stale_threshold,
                    'min_interval': min_interval
                },
                'optimization_applied': use_smart_thresholds,
                'cutoff_time': recent_cutoff.isoformat(),
                'check_time': datetime.now().isoformat()
            }
            
            # Cache the result for a few minutes to avoid repeated checks
            if cache.is_available():
                cache.set_json(cache_key, result, expire=NewsOptimizationConfig.NEWS_CHECK_CACHE_DURATION)
            
            logger.info(f"📊 News status for {symbol}: {fetch_reason}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error checking recent news status for {symbol}: {str(e)}")
            return {
                'has_recent_news': False,
                'latest_article_age_hours': None,
                'total_recent_articles': 0,
                'should_fetch': True,
                'fetch_reason': f"Error during check: {str(e)}",
                'symbol_variants': [symbol],
                'error': str(e),
                'optimization_applied': use_smart_thresholds
            }

    @staticmethod
    def trigger_background_news_fetch(symbol: str, limit: int = 5) -> Dict:
        """
        Trigger background news fetching and AI processing for a symbol with fetch recording
        
        Args:
            symbol: Stock symbol to fetch news for
            limit: Number of articles to fetch (default 5)
            
        Returns:
            Dict with operation status
        """
        try:
            from app.utils.symbol_utils import normalize_ticker
            
            # Convert to TradingView format for fetching
            tv_symbol = normalize_ticker(symbol, purpose='search')
            fetch_tracker = StockNewsService.get_fetch_tracker()
            
            logger.info(f"Triggering background news fetch for {symbol} (as {tv_symbol})")
            
            def fetch_and_process():
                """Background task to fetch and process news with result recording"""
                result_type = 'error'
                articles_found = 0
                details = ''
                
                try:
                    # Initialize services
                    news_service = NewsAnalysisService()
                    
                    # Fetch news articles
                    logger.info(f"Fetching {limit} articles for {tv_symbol}")
                    articles = news_service.fetch_and_analyze_news(
                        symbols=[tv_symbol],
                        limit=limit,
                        timeout=30
                    )
                    
                    if articles and len(articles) > 0:
                        articles_found = len(articles)
                        result_type = 'success'
                        details = f'Successfully fetched {articles_found} articles'
                        logger.info(f"Successfully fetched {articles_found} articles for {tv_symbol}")
                        
                        # Trigger AI processing for the fetched articles
                        article_ids = [article.get('id') for article in articles if article.get('id')]
                        if article_ids:
                            StockNewsService._trigger_ai_processing(article_ids)
                    else:
                        result_type = 'no_news'
                        details = f'No articles found for {tv_symbol}'
                        logger.warning(f"No articles fetched for {tv_symbol}")
                        
                except Exception as e:
                    result_type = 'error'
                    details = f'Fetch error: {str(e)}'
                    logger.error(f"Error in background news fetch for {tv_symbol}: {str(e)}")
                finally:
                    # Record the fetch attempt and result
                    fetch_tracker.record_fetch_attempt(
                        symbol=symbol,
                        result_type=result_type,
                        articles_found=articles_found,
                        details=details
                    )
                    
            # Start background thread
            thread = threading.Thread(target=fetch_and_process, daemon=True)
            thread.start()
            
            return {
                'status': 'started',
                'symbol': symbol,
                'tv_symbol': tv_symbol,
                'limit': limit,
                'message': f'Background news fetch started for {symbol}',
                'will_record_result': True
            }
            
        except Exception as e:
            # Record the error immediately
            fetch_tracker = StockNewsService.get_fetch_tracker()
            fetch_tracker.record_fetch_attempt(
                symbol=symbol,
                result_type='error',
                articles_found=0,
                details=f'Failed to start fetch: {str(e)}'
            )
            
            logger.error(f"Error triggering background news fetch for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'symbol': symbol,
                'error': str(e),
                'recorded_attempt': True
            }

    @staticmethod 
    def _trigger_ai_processing(article_ids: List[int]):
        """
        Trigger AI processing for specific articles
        
        Args:
            article_ids: List of article IDs to process
        """
        try:
            # Check if OpenRouter API key is available
            openrouter_key = os.getenv('OPENROUTER_API_KEY')
            if not openrouter_key:
                logger.warning("OpenRouter API key not available, skipping AI processing")
                return
                
            logger.info(f"Triggering AI processing for {len(article_ids)} articles")
            
            # Make request to update AI summaries endpoint
            try:
                import requests
                response = requests.post(
                    'http://localhost:5000/news/api/update-summaries',
                    json={'article_ids': article_ids},
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"AI processing triggered successfully for {len(article_ids)} articles")
                else:
                    logger.warning(f"AI processing request failed with status {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error making AI processing request: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error triggering AI processing: {str(e)}")

    @staticmethod
    def auto_check_and_fetch_news(symbol: str, force_check: bool = False, use_smart_thresholds: bool = True) -> Dict:
        """
        Enhanced automatic news checking and fetching with intelligent optimization and daily limits
        
        This is the main function to call during analysis snapshot rendering
        
        Args:
            symbol: Stock symbol being analyzed
            force_check: Bypass cache and force fresh check
            use_smart_thresholds: Use stock-specific intelligent thresholds
            
        Returns:
            Dict with comprehensive operation results
        """
        try:
            logger.info(f"🔄 Auto-checking news status for {symbol} (smart_thresholds={use_smart_thresholds})")
            
            # Check if news fetching is globally enabled
            if not StockNewsService.is_news_fetching_enabled():
                logger.info("🚫 News fetching is globally disabled")
                return {
                    'status': 'disabled',
                    'message': 'News fetching is globally disabled',
                    'reason': 'global_disabled'
                }
            
            # NEW: Check if symbol is in the automated 346 symbols list (fetched 6 times daily)
            if not force_check:
                is_in_scheduler = StockNewsService._check_if_symbol_in_scheduler(symbol)
                if is_in_scheduler['in_scheduler']:
                    logger.info(f"🤖 Symbol {symbol} is in automated scheduler ({is_in_scheduler['matching_variant']}) - skipping fetch (already processed 6x daily)")
                    return {
                        'status': 'in_automated_scheduler',
                        'message': f'Symbol {symbol} is automatically fetched 6 times daily by scheduler',
                        'reason': 'automated_scheduler_coverage',
                        'scheduler_details': is_in_scheduler,
                        'optimization_details': {
                            'automated_scheduler_protection': True,
                            'scheduler_symbol_match': is_in_scheduler['matching_variant'],
                            'total_scheduler_symbols': is_in_scheduler['total_scheduler_symbols']
                        }
                    }
            
            # Check daily fetch limits (only for symbols NOT in automated scheduler)
            fetch_tracker = StockNewsService.get_fetch_tracker()
            fetch_allowance = fetch_tracker.should_allow_fetch(symbol, force=force_check)
            
            if not fetch_allowance['allow_fetch']:
                logger.info(f"🛑 Daily fetch limit reached for {symbol}: {fetch_allowance['details']}")
                return {
                    'status': 'daily_limit_reached',
                    'message': f'Daily fetch limit reached for {symbol}',
                    'reason': fetch_allowance['reason'],
                    'fetch_allowance': fetch_allowance,
                    'optimization_details': {
                        'daily_fetch_protection': True,
                        'attempts_today': fetch_allowance.get('attempts_today', 0),
                        'daily_limit': fetch_allowance.get('daily_limit', 2)
                    }
                }
            
            # Check recent news status with enhanced logic
            news_status = StockNewsService.check_recent_news_status(
                symbol, 
                use_smart_thresholds=use_smart_thresholds
            )
            
            # If we should fetch news, trigger background fetch
            if news_status['should_fetch']:
                logger.info(f"📰 {news_status['fetch_reason']} - triggering background fetch")
                
                # Determine fetch limit based on stock characteristics
                if use_smart_thresholds and symbol.upper() in NewsOptimizationConfig.HIGH_FREQUENCY_STOCKS:
                    fetch_limit = 8  # More articles for high-frequency stocks
                else:
                    fetch_limit = 5  # Standard limit
                
                fetch_result = StockNewsService.trigger_background_news_fetch(symbol, limit=fetch_limit)
                
                return {
                    'status': 'fetch_triggered',
                    'news_status': news_status,
                    'fetch_result': fetch_result,
                    'fetch_allowance': fetch_allowance,
                    'message': f'Background news fetch triggered for {symbol}',
                    'reason': news_status['fetch_reason'],
                    'optimization_details': {
                        'smart_thresholds': use_smart_thresholds,
                        'fetch_limit': fetch_limit,
                        'thresholds_used': news_status.get('thresholds_used', {}),
                        'daily_fetch_protection': True,
                        'attempts_today': fetch_allowance.get('attempts_today', 0)
                    }
                }
            else:
                logger.info(f"✅ {news_status['fetch_reason']} - no fetch needed")
                return {
                    'status': 'no_fetch_needed', 
                    'news_status': news_status,
                    'fetch_allowance': fetch_allowance,
                    'message': f'Recent news exists for {symbol}',
                    'reason': news_status['fetch_reason'],
                    'optimization_details': {
                        'smart_thresholds': use_smart_thresholds,
                        'thresholds_used': news_status.get('thresholds_used', {}),
                        'daily_fetch_protection': True,
                        'attempts_today': fetch_allowance.get('attempts_today', 0)
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Error in auto_check_and_fetch_news for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Error checking news for {symbol}',
                'reason': 'exception_occurred'
            }

    @staticmethod
    def _check_if_symbol_in_scheduler(symbol: str) -> Dict:
        """
        Check if a symbol is in the automated 346 symbols list by converting to TradingView format
        
        Args:
            symbol: Stock symbol to check
            
        Returns:
            Dict with scheduler check results
        """
        try:
            # Get the 346 symbols list from the scheduler
            try:
                from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
                scheduler_symbols = news_fetch_scheduler.get_symbols()
            except Exception as e:
                logger.warning(f"Could not get scheduler symbols: {str(e)}")
                return {
                    'in_scheduler': False,
                    'error': f'Could not access scheduler: {str(e)}',
                    'total_scheduler_symbols': 0
                }
            
            # PRIORITY 1: Convert input symbol to TradingView format (most important)
            from app.utils.symbol_utils import normalize_ticker
            tv_symbol = None
            try:
                tv_symbol = normalize_ticker(symbol, purpose='search')
                logger.debug(f"Converted {symbol} to TradingView format: {tv_symbol}")
                
                # Check direct TradingView format match first
                if tv_symbol in scheduler_symbols:
                    logger.debug(f"Direct TradingView match found: {tv_symbol}")
                    return {
                        'in_scheduler': True,
                        'matching_variant': tv_symbol,
                        'conversion_used': 'direct_tradingview',
                        'symbol_variants': [tv_symbol],
                        'total_scheduler_symbols': len(scheduler_symbols),
                        'checked_against': len(scheduler_symbols)
                    }
            except Exception as e:
                logger.debug(f"Could not normalize symbol {symbol}: {str(e)}")
            
            # PRIORITY 2: If TradingView conversion didn't work or match, try exact symbol
            if symbol.upper() in scheduler_symbols:
                logger.debug(f"Direct symbol match found: {symbol.upper()}")
                return {
                    'in_scheduler': True,
                    'matching_variant': symbol.upper(),
                    'conversion_used': 'direct_symbol',
                    'symbol_variants': [symbol.upper()],
                    'total_scheduler_symbols': len(scheduler_symbols),
                    'checked_against': len(scheduler_symbols)
                }
            
            # PRIORITY 3: Generate additional variants as fallback (existing logic)
            symbol_variants = []
            
            # Add the original and TradingView conversion
            if tv_symbol:
                symbol_variants.append(tv_symbol)
            symbol_variants.append(symbol.upper())
            
            # Generate common exchange variants for plain symbols
            clean_symbol = symbol.upper().strip()
            if '.' not in clean_symbol and ':' not in clean_symbol:
                # Plain symbol like AAPL - add common exchange prefixes
                symbol_variants.extend([
                    f"NASDAQ:{clean_symbol}",
                    f"NYSE:{clean_symbol}",
                    f"HKEX:{clean_symbol}",
                    f"LSE:{clean_symbol}",
                    f"TSE:{clean_symbol}",
                    f"SSE:{clean_symbol}",
                    f"SZSE:{clean_symbol}"
                ])
            
            # Handle Yahoo Finance format conversions
            if clean_symbol.endswith('.SS'):
                base = clean_symbol[:-3]
                symbol_variants.append(f"SSE:{base}")
            elif clean_symbol.endswith('.SZ'):
                base = clean_symbol[:-3]
                symbol_variants.append(f"SZSE:{base}")
            elif clean_symbol.endswith('.HK'):
                base = clean_symbol[:-3]
                symbol_variants.append(f"HKEX:{base}")
            elif clean_symbol.endswith('.T'):
                base = clean_symbol[:-2]
                symbol_variants.append(f"TSE:{base}")
            elif clean_symbol.endswith('.L'):
                base = clean_symbol[:-2]
                symbol_variants.append(f"LSE:{base}")
            
            # Remove duplicates while preserving order
            seen = set()
            unique_variants = []
            for variant in symbol_variants:
                if variant not in seen:
                    seen.add(variant)
                    unique_variants.append(variant)
            
            # Check all variants against scheduler symbols
            matching_variant = None
            for variant in unique_variants:
                if variant in scheduler_symbols:
                    matching_variant = variant
                    break
            
            is_in_scheduler = matching_variant is not None
            
            logger.debug(f"Scheduler check for {symbol}: variants={unique_variants[:5]}{'...' if len(unique_variants) > 5 else ''}, in_scheduler={is_in_scheduler}, match={matching_variant}")
            
            return {
                'in_scheduler': is_in_scheduler,
                'matching_variant': matching_variant,
                'conversion_used': 'variant_matching' if matching_variant else 'no_match',
                'symbol_variants': unique_variants,
                'total_scheduler_symbols': len(scheduler_symbols),
                'checked_against': len(scheduler_symbols)
            }
            
        except Exception as e:
            logger.error(f"Error checking if {symbol} is in scheduler: {str(e)}")
            return {
                'in_scheduler': False,
                'error': str(e),
                'total_scheduler_symbols': 0
            }

    @staticmethod
    def clear_news_check_cache(symbol: str = None):
        """
        Clear cached news check results
        
        Args:
            symbol: Clear cache for specific symbol, or all if None
        """
        from app.utils.cache.news_cache import NewsCache
        cache = NewsCache()
        
        if not cache.is_available():
            return
            
        if symbol:
            # Clear cache for specific symbol
            pattern = f"news_check:{symbol}:*"
            cache.delete_pattern(pattern)
            logger.info(f"🧹 Cleared news check cache for {symbol}")
        else:
            # Clear all news check cache
            pattern = "news_check:*"
            cache.delete_pattern(pattern)
            logger.info("🧹 Cleared all news check cache")

    @staticmethod
    def get_fetch_record_stats(symbol: str, date: str = None) -> Dict:
        """
        Get daily fetch record statistics for a symbol
        
        Args:
            symbol: Stock symbol to check
            date: Date to check (YYYY-MM-DD format), defaults to today
            
        Returns:
            Dict with fetch record statistics
        """
        try:
            fetch_tracker = StockNewsService.get_fetch_tracker()
            return fetch_tracker.get_daily_stats(symbol, date)
        except Exception as e:
            logger.error(f"Error getting fetch record stats: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    def clear_fetch_record(symbol: str, date: str = None) -> bool:
        """
        Clear fetch record for a symbol
        
        Args:
            symbol: Stock symbol
            date: Date to clear (defaults to today)
            
        Returns:
            Success status
        """
        try:
            fetch_tracker = StockNewsService.get_fetch_tracker()
            return fetch_tracker.clear_daily_record(symbol, date)
        except Exception as e:
            logger.error(f"Error clearing fetch record: {str(e)}")
            return False
    
    @staticmethod
    def check_daily_fetch_allowance(symbol: str) -> Dict:
        """
        Check if a symbol is allowed to be fetched based on daily limits
        
        Args:
            symbol: Stock symbol to check
            
        Returns:
            Dict with allowance information
        """
        try:
            fetch_tracker = StockNewsService.get_fetch_tracker()
            return fetch_tracker.should_allow_fetch(symbol)
        except Exception as e:
            logger.error(f"Error checking fetch allowance: {str(e)}")
            return {
                'allow_fetch': True,
                'reason': 'error_checking',
                'details': f'Error occurred: {str(e)}'
            }

    @staticmethod
    def get_news_optimization_stats(symbols: List[str] = None) -> Dict:
        """
        Get optimization statistics for monitoring efficiency
        
        Args:
            symbols: List of symbols to analyze, or analyze all recent if None
            
        Returns:
            Dict with optimization statistics
        """
        try:
            from app.utils.cache.news_cache import NewsCache
            
            if not symbols:
                # Get recently analyzed symbols from cache/database
                symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']  # Example fallback
            
            stats = {
                'total_symbols_checked': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'fetch_avoided': 0,
                'fetch_triggered': 0,
                'high_frequency_stocks': 0,
                'optimization_effectiveness': 0.0
            }
            
            cache = NewsCache()
            
            for symbol in symbols:
                stats['total_symbols_checked'] += 1
                
                # Check if we have cached data
                cache_key = f"news_check:{symbol}:*"
                if cache.is_available():
                    # Simplified check - in reality you'd scan for matching keys
                    cached_result = cache.get_json(f"news_check:{symbol}:None:True")
                    if cached_result:
                        stats['cache_hits'] += 1
                        if not cached_result.get('should_fetch', True):
                            stats['fetch_avoided'] += 1
                        else:
                            stats['fetch_triggered'] += 1
                    else:
                        stats['cache_misses'] += 1
                
                # Check if it's a high-frequency stock
                if symbol.upper() in NewsOptimizationConfig.HIGH_FREQUENCY_STOCKS:
                    stats['high_frequency_stocks'] += 1
            
            # Calculate effectiveness
            if stats['total_symbols_checked'] > 0:
                stats['optimization_effectiveness'] = (stats['fetch_avoided'] / stats['total_symbols_checked']) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting optimization stats: {str(e)}")
            return {'error': str(e)}

# Legacy function for backward compatibility
def trigger_stock_news_analysis(symbol: str, max_articles: int = 10):
    """Legacy function - use StockNewsService.auto_check_and_fetch_news instead"""
    logger.warning("Using deprecated trigger_stock_news_analysis, use StockNewsService.auto_check_and_fetch_news")
    return StockNewsService.auto_check_and_fetch_news(symbol) 