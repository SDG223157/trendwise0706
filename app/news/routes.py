# app/news/routes.py

import os
import re
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, session
from flask_login import login_required
from app.utils.analysis.news_service import NewsAnalysisService
from app.utils.analytics.news_analytics import NewsAnalytics
from datetime import datetime, timedelta
import logging
from http import HTTPStatus
# from app import admin_required
from functools import wraps
from flask import abort
from flask_login import current_user
from app.models import NewsArticle, ArticleSymbol
from openai import OpenAI
from app import db
# import httpx
# from app.utils.config.news_config import DEFAULT_SYMBOLS
import time
from sqlalchemy import or_, and_, desc, asc, func, text, Float
import markdown  # Add at top
from app.utils.symbol_utils import normalize_ticker
from app.utils.cache.api_cache import api_cache
from app.utils.cache.db_cache import db_cache
import requests
logger = logging.getLogger(__name__)
bp = Blueprint('news', __name__)


# Initialize services
news_service = NewsAnalysisService()

DEFAULT_SYMBOLS = [
    "SP:SPX", "DJ:DJI", "NASDAQ:IXIC", "NYSE:NYA", "AMEX:IWM",
    "FOREXCOM:US30", "FOREXCOM:US500", "FOREXCOM:US100", "FOREXCOM:USSMALL", "FOREXCOM:US2000",
    "LSE:UKX", "LSE:FTSE", "XETR:DAX", "EURONEXT:CAC40", "EURONEXT:AEX", "TVC:HSI", 
    "TSE:NI225", "HKEX:HSI", "SZSE:399300", "ASX:XJO", "TSX:TSX",
    "BITSTAMP:BTCUSD", "COMEX:GC1!","TVC:GOLD","FXCM:GOLD","TVC:USOIL","FXCM:OIL","TVC:SILVER",
     "NYMEX:CL1!", "COMEX:HG1!", "AMEX:TLT",
    "TVC:DXY", "FOREXCOM:EURUSD", "FOREXCOM:GBPUSD", "FOREXCOM:USDJPY", "FOREXCOM:USDCNH",
    "LSE:SHEL", "NYSE:TSM", "LSE:AZN", "TSE:7203", "NYSE:ASML",
    "TSE:6758", "TSE:6861", "LSE:HSBA", "TSE:7974", "NYSE:UL",
    "TSE:8306", "LSE:GSK", "NYSE:BP", "TSE:9432", "TSE:9984",
    "NYSE:RY", "LSE:RIO", "NYSE:BHP", "NYSE:TD", "NYSE:NVO",
    "TSE:8316", "NYSE:TTE", "NYSE:BTI", "NYSE:DEO", "TSE:8035",
    "NYSE:SAP", "NYSE:SAN", "TSE:6501", "NYSE:EADSY", "TSE:6902",
    "NYSE:PHG", "TSE:7267", "NYSE:SONY", "TSE:6367", "NYSE:VALE",
    "TSE:6503", "NYSE:ING", "NYSE:HSBC", "NYSE:BBD", "TSE:7751",
    "NYSE:SNY", "TSE:8766", "NYSE:SLB", "NYSE:NGG", "TSE:6702",
    "NYSE:BMO", "NYSE:BCS", "NYSE:PTR", "NYSE:CS", "NYSE:UBS",
    "NASDAQ:AAPL", "NASDAQ:MSFT", "NASDAQ:GOOGL", "NASDAQ:GOOG", "NASDAQ:AMZN",
    "NASDAQ:NVDA", "NASDAQ:META", "NASDAQ:TSLA", "NASDAQ:AVGO", "NASDAQ:ADBE",
    "NASDAQ:CSCO", "NASDAQ:NFLX", "NASDAQ:INTC", "NASDAQ:AMD", "NASDAQ:QCOM",
    "NYSE:CRM", "NYSE:BRK.A", "NYSE:V", "NYSE:MA", "NYSE:JPM",
    "NYSE:BAC", "NYSE:WFC", "NYSE:MS", "NYSE:GS", "NYSE:BLK",
    "NYSE:AXP", "NYSE:UNH", "NYSE:JNJ", "NYSE:LLY", "NYSE:PFE",
    "NYSE:MRK", "NYSE:ABT", "NYSE:TMO", "NYSE:DHR", "NYSE:BMY",
    "NYSE:ABBV", "NYSE:WMT", "NYSE:PG", "NYSE:KO", "NASDAQ:PEP",
    "NYSE:COST", "NYSE:MCD", "NYSE:NKE", "NYSE:DIS", "NASDAQ:CMCSA",
    "NYSE:HD", "NYSE:XOM", "NYSE:CVX", "NYSE:RTX", "NYSE:HON",
    "NYSE:UPS", "NYSE:CAT", "NYSE:GE", "NYSE:BA", "NYSE:LMT",
    "NYSE:MMM", "NYSE:T", "NYSE:VZ", "NASDAQ:TMUS", "NYSE:SQ",
    "NASDAQ:PYPL", "NYSE:SHOP", "NYSE:NOW", "NASDAQ:INTU", "NYSE:ORCL",
    "NASDAQ:WDAY", "NASDAQ:AMAT", "NASDAQ:MU", "NASDAQ:KLAC", "NASDAQ:LRCX",
    "NYSE:UBER", "NYSE:DASH", "NYSE:ABNB", "NYSE:PGR", "NYSE:MET",
    "NYSE:ALL", "NYSE:PLD", "NYSE:AMT", "NYSE:CCI", "NYSE:LIN",
    "NYSE:APD", "NYSE:ECL", "NYSE:NOC", "NYSE:GD", "NYSE:TDG",
    "NYSE:TGT", "NYSE:LOW", "NYSE:DG", "NASDAQ:EA", "NASDAQ:ATVI",
    "NYSE:SPOT", "NYSE:UNP", "NYSE:CSX", "NSE:FDX", "NYSE:VEEV",
    "NYSE:ZTS", "NASDAQ:ISRG", "NYSE:EL", "NYSE:CL", "NYSE:K",
    "NYSE:ACN", "NYSE:ADP", "NYSE:INFO", "NASDAQ:VRTX", "NASDAQ:REGN",
    "NASDAQ:GILD", "NYSE:NEE", "NYSE:DUK", "NYSE:SO",
    "HKEX:700", "HKEX:9988", "HKEX:1299", "HKEX:941", "HKEX:388",
    "HKEX:5", "HKEX:3690", "HKEX:2318", "HKEX:2628", "HKEX:1211",
    "HKEX:1810", "HKEX:2382", "HKEX:1024", "HKEX:9618", "HKEX:2269",
    "HKEX:2018", "HKEX:2020", "HKEX:1177", "HKEX:1928", "HKEX:883",
    "HKEX:1088", "HKEX:857", "HKEX:386", "HKEX:1", "HKEX:16",
    "HKEX:11", "HKEX:2", "HKEX:3", "HKEX:6", "HKEX:12",
    "HKEX:17", "HKEX:19", "HKEX:66", "HKEX:83", "HKEX:101",
    "HKEX:135", "HKEX:151", "HKEX:175", "HKEX:267", "HKEX:288",
    "HKEX:291", "HKEX:293", "HKEX:330", "HKEX:392", "HKEX:688",
    "HKEX:762", "HKEX:823", "HKEX:960", "HKEX:1038", "HKEX:1109",
    "SSE:600519", "SZSE:300750", "SZSE:000858", "SSE:601318", "SSE:600036",
    "SSE:601012", "SZSE:000333", "SZSE:000651", "SSE:600276", "SSE:601888",
    "SSE:603288", "SSE:603259", "SZSE:002594", "SSE:600104", "SSE:601166",
    "SSE:601658", "SSE:600887", "SZSE:000725", "SSE:601919", "SSE:600030",
    "SZSE:000001", "SZSE:300760", "SSE:601628", "SSE:600000", "SSE:600906",
    "SSE:601138", "SSE:600028", "SSE:601857", "SZSE:002352", "SZSE:002475",
    "SZSE:002415", "SSE:601899", "SSE:601375", "SSE:601668", "SSE:601766",
    "SSE:603501", "SSE:600570", "SSE:601728", "SZSE:002027", "SSE:600585",
    "SZSE:300059", "SSE:600018", "SSE:601211", "SZSE:000100", "SSE:600745",
    "SSE:601633", "SSE:601688", "SZSE:300122", "SSE:600029", "SSE:600016",
    "SSE:601398", "SSE:601288", "SSE:601988", "SSE:601328", "SSE:601998",
    "SZSE:000063", "SSE:601139", "SSE:600438", "SSE:600031", "SZSE:002311",
    "SSE:600584", "SZSE:300124", "SZSE:002024", "SZSE:002230", "SZSE:002241",
    "SZSE:300015", "SSE:600436", "SSE:601601", "SSE:600015", "SSE:601696",
    "SSE:601618", "SZSE:002013", "SZSE:000738", "SSE:600050", "SSE:600918",
    "SZSE:000776", "SSE:600845", "SSE:603345", "SSE:601877", "SSE:600171",
    "SSE:601818", "SSE:601390", "SSE:601186", "SSE:601088", "SSE:600062",
    "SSE:600958", "SSE:601901", "SZSE:000069", "SSE:601607", "SSE:601360",
    "SZSE:000625", "SSE:601225", "SSE:600999", "SSE:600837", "SSE:600660",
    "SSE:600690", "SSE:601336", "SSE:601066", "SSE:601995", "SSE:600919",
    "SSE:600298"
]

# Add at the top with other constants
FUTURES_MAPPING = {
    # Metals
    'GOLD': ['COMEX:GC1!', 'COMEX:GC', 'TVC:GOLD', 'FXCM:GOLD'],
    'SILVER': ['COMEX:SI1!', 'COMEX:SI', 'TVC:SILVER', 'FXCM:SILVER'],
    'COPPER': ['COMEX:HG1!', 'COMEX:HG', 'TVC:COPPER', 'FXCM:COPPER'],
    'PLATINUM': ['NYMEX:PL1!', 'NYMEX:PL', 'TVC:PLATINUM', 'FXCM:PLATINUM'],
    
    # Energy
    'OIL': ['NYMEX:CL1!', 'NYMEX:CL', 'NYMEX:WTI', 'TVC:USOIL', 'FXCM:OIL'],
    'BRENT': ['NYMEX:BZ1!', 'NYMEX:BZ'],
    'GAS': ['NYMEX:NG1!', 'NYMEX:NG'],
    
    # Agriculture
    'CORN': ['CBOT:ZC1!', 'CBOT:ZC'],
    'WHEAT': ['CBOT:ZW1!', 'CBOT:ZW'],
    'SOYBEANS': ['CBOT:ZS1!', 'CBOT:ZS'],
    'COFFEE': ['NYMEX:KC1!', 'NYMEX:KC'],
    
    # Indices Futures
    'SP500': ['CME:ES1!', 'SP:SPX'],
    'NASDAQ': ['CME:NQ1!', 'NASDAQ:IXIC'],
    'DOW': ['CBOT:YM1!', 'DJ:DJI']
}

# Add mapping for indices to include multiple exchange variants
INDICES_MAPPING = {
    'HSI': ['HKEX:HSI', 'TVC:HSI'],  # Hang Seng Index
    'GSPC': ['SP:SPX', 'TVC:SPX'],   # S&P 500
    'DJI': ['DJ:DJI', 'TVC:DJI'],    # Dow Jones Industrial Average
    'IXIC': ['NASDAQ:IXIC', 'TVC:NDX'], # NASDAQ Composite/100
    'N225': ['TSE:NI225', 'TVC:NI225'], # Nikkei 225
    'FTSE': ['LSE:UKX', 'TVC:UK100']   # FTSE 100
}

def init_analytics():
    """Initialize analytics with database session"""
    return NewsAnalytics(current_app.db.session)

@bp.route('/')
@login_required
def index():
    """News dashboard homepage."""
    try:
        period = request.args.get('period', 'day')
        symbol = request.args.get('symbol', 'all')
        days = 7 if period == 'week' else (30 if period == 'month' else 1)

        # Get latest articles
        latest_articles = NewsArticle.query.order_by(
            NewsArticle.published_at.desc()
        ).limit(10).all()

        # Get most mentioned symbols
        trending_symbols = news_service.get_trending_symbols(days=days)

        # Get sentiment distribution
        sentiment_data = news_service.get_overall_sentiment(days=days)
        
        # Fix the sentiment_summary structure to match what the template expects
        sentiment_summary = {
            'sentiment_distribution': {
                'positive': sentiment_data.get('positive', 0),
                'neutral': sentiment_data.get('neutral', 0),
                'negative': sentiment_data.get('negative', 0)
            },
            'overall_score': sentiment_data.get('overall_score', 0),
            'total_articles': sentiment_data.get('total_articles', 0)
        }

        return render_template(
            'news/analysis.html',
            latest_articles=latest_articles,
            trending_symbols=trending_symbols,
            sentiment_summary=sentiment_summary,
            period=period,
            symbol=symbol
        )
    except Exception as e:
        logger.error(f"Error in news index: {str(e)}")
        db.session.rollback()  # Rollback in case of error
        return render_template(
            'news/analysis.html',
            error=str(e),
            latest_articles=[],
            trending_symbols=[],
            sentiment_summary={
                'sentiment_distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
                'overall_score': 0,
                'total_articles': 0
            },
            period=request.args.get('period', 'day'),
            symbol=request.args.get('symbol', 'all')
        )

@bp.route('/fetch')
@login_required
def fetch():
    """Render the Fetch News page"""
    return render_template('news/fetch.html')
@bp.route('/sentiment')
def analysis():
    return render_template('news/sentiment.html')
@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Comprehensive search for news articles by symbol, keywords, or both"""
    # Get search parameters
    search_query = request.args.get('q', '').strip()  # Universal search query
    symbol = request.args.get('symbol', '').strip().upper()  # Specific symbol search
    keywords = request.args.get('keywords', '').strip()  # Specific keyword search
    
    if request.method == 'POST':
        search_query = request.form.get('q', '').strip()
        symbol = request.form.get('symbol', '').strip().upper()
        keywords = request.form.get('keywords', '').strip()
        
    logger.info(f"News search - Query: '{search_query}', Symbol: '{symbol}', Keywords: '{keywords}'")
    
    # Quick validation and redirect
    if 'q' in request.args and not search_query and not symbol and not keywords:
        return redirect(url_for('news.search'))
    
    # If no search terms provided, show the search form
    if not search_query and not symbol and not keywords:
        return render_template(
            'news/search.html',
            articles=None,
            pagination=None,
            search_params={'q': search_query, 'symbol': symbol, 'keywords': keywords},
            search_type='unified',
            min=min
        )

    # Initialize optimized search using search index
    from app.utils.search.optimized_news_search import OptimizedNewsSearch
    from app.models import NewsSearchIndex
    
    # Check if search index exists and has data
    search_index_count = NewsSearchIndex.query.count()
    if search_index_count == 0:
        logger.warning("⚠️ Search index is empty, falling back to original search")
        # Fall back to original search
        from app.utils.search.news_search import NewsSearch
        news_search = NewsSearch(db.session)
        
        try:
            # Parse search parameters efficiently
            search_params = _parse_unified_search_params(search_query, symbol, keywords, request.args)
            logger.info(f"Parsed search params (fallback): {search_params}")
            
            # Use original search method
            if search_params.get('search_type') == 'keyword':
                articles, total_count = news_search.advanced_search(
                    keywords=search_params.get('keywords', []),
                    sentiment=search_params.get('sentiment_filter'),
                    start_date=search_params.get('start_date'),
                    end_date=search_params.get('end_date'),
                    page=request.args.get('page', 1, type=int),
                    per_page=1
                )
                has_more = len(articles) >= 1
            else:
                articles, total_count, has_more = news_search.optimized_symbol_search(
                    symbols=search_params.get('symbols', []),
                    sentiment_filter=search_params.get('sentiment_filter'),
                    sort_order=search_params.get('sort_order', 'LATEST'),
                    date_filter=search_params.get('date_filter'),
                    region_filter=search_params.get('region_filter'),
                    processing_filter=search_params.get('processing_filter', 'all'),
                    page=request.args.get('page', 1, type=int),
                    per_page=1
                )
        except Exception as e:
            logger.error(f"Error in fallback search: {str(e)}")
            return render_template(
                'news/search.html',
                articles=[],
                pagination=None,
                search_params={'q': search_query, 'symbol': symbol, 'keywords': keywords},
                search_type='unified',
                error=f"Search error: {str(e)}",
                min=min
            )
    else:
        # Use optimized search index
        optimized_search = OptimizedNewsSearch(db.session)
        
        try:
            # Parse search parameters efficiently
            search_params = _parse_unified_search_params(search_query, symbol, keywords, request.args)
            logger.info(f"Parsed search params: {search_params}")
            
            # Debug logging for search parameters
            logger.info(f"🔍 Using optimized search index with {search_index_count} articles")
            logger.info(f"🔍 Search type: {search_params.get('search_type')}")
            logger.info(f"🔍 Search parameters: {search_params}")

            # Choose search method based on search type
            if search_params.get('search_type') == 'keyword':
                # Use keyword search with latest filter if detected
                articles, total_count, has_more = optimized_search.search_by_keywords(
                    keywords=search_params.get('keywords', []),
                    sentiment_filter=search_params.get('sentiment_filter'),
                    sort_order=search_params.get('sort_order', 'LATEST'),
                    date_filter=search_params.get('date_filter'),
                    page=request.args.get('page', 1, type=int),
                    per_page=1,
                    force_latest_filter=search_params.get('has_latest', False)
                )
            elif search_params.get('search_type') == 'mixed':
                # Use hybrid search - alternate between symbol and keyword results
                current_page = request.args.get('page', 1, type=int)
                
                # Alternate between symbol and keyword results
                if current_page % 2 == 1:  # Odd pages: show symbol results
                    symbol_page = (current_page + 1) // 2
                    articles, total_count, has_more = optimized_search.search_by_symbols(
                        symbols=search_params.get('symbols', []),
                        sentiment_filter=search_params.get('sentiment_filter'),
                        sort_order=search_params.get('sort_order', 'LATEST'),
                        date_filter=search_params.get('date_filter'),
                        region_filter=search_params.get('region_filter'),
                        processing_filter=search_params.get('processing_filter', 'all'),
                        page=symbol_page,
                        per_page=1
                    )
                else:  # Even pages: show keyword results
                    keyword_page = current_page // 2
                    # Set flag for "latest" keyword detection
                    if search_params.get('has_latest'):
                        optimized_search._has_latest_keyword = True
                        
                    articles, total_count, has_more = optimized_search.search_by_keywords(
                        keywords=search_params.get('keywords', []),
                        sentiment_filter=search_params.get('sentiment_filter'),
                        sort_order=search_params.get('sort_order', 'LATEST'),
                        date_filter=search_params.get('date_filter'),
                        page=keyword_page,
                        per_page=1
                    )
                
                # For mixed search, always show there are more results to encourage exploration
                has_more = True
                
            else:
                # Use symbol search (default)
                # Set flag for "latest" keyword detection
                if search_params.get('has_latest'):
                    optimized_search._has_latest_keyword = True
                    
                articles, total_count, has_more = optimized_search.search_by_symbols(
                    symbols=search_params.get('symbols', []),
                    sentiment_filter=search_params.get('sentiment_filter'),
                    sort_order=search_params.get('sort_order', 'LATEST'),
                    date_filter=search_params.get('date_filter'),
                    region_filter=search_params.get('region_filter'),
                    processing_filter=search_params.get('processing_filter', 'all'),
                    page=request.args.get('page', 1, type=int),
                    per_page=1
                )
        except Exception as e:
            logger.error(f"Error in optimized search: {str(e)}")
            return render_template(
                'news/search.html',
                articles=[],
                pagination=None,
                search_params={'q': search_query, 'symbol': symbol, 'keywords': keywords},
                search_type='unified',
                error=f"Search error: {str(e)}",
                min=min
            )
    
    try:
        # Create simplified pagination object
        class SimplePagination:
            def __init__(self, items, total, page, per_page, has_more):
                self.items = items
                self.total = total
                self.page = page
                self.per_page = per_page
                self.has_more = has_more
                self.pages = (total + per_page - 1) // per_page if total else 1
                self.has_prev = page > 1
                self.has_next = has_more
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
            
            def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
                """
                Iterate over the page numbers for pagination.
                Returns an iterator that yields page numbers or None for gaps.
                """
                last = self.pages
                
                # Early return for single page
                if last <= 1:
                    return []
                
                # Generate page numbers
                for num in range(1, last + 1):
                    if (num <= left_edge or  # Left edge
                        (self.page - left_current - 1 < num < self.page + right_current) or  # Around current
                        num > last - right_edge):  # Right edge
                        yield num
                    elif (num == left_edge + 1 or  # Gap after left edge
                          num == last - right_edge):  # Gap before right edge
                        yield None

        pagination = SimplePagination(
            items=articles,
            total=total_count,
            page=request.args.get('page', 1, type=int),
            per_page=1,
            has_more=has_more
        )

        logger.info(f"Search completed: {len(articles)} articles, has_more: {has_more}, type: {search_params.get('search_type', 'symbol')}")

        # Generate AI-powered suggestions if no results found
        ai_suggestions = None
        if not articles and (search_query or symbol or keywords):
            original_query = search_query or symbol or keywords
            try:
                ai_suggestions = _generate_ai_search_suggestions(original_query)
                logger.info(f"Generated {len(ai_suggestions)} AI suggestions for empty search: {original_query}")
            except Exception as e:
                logger.warning(f"Failed to generate AI suggestions: {str(e)}")

        return render_template(
            'news/search.html',
            articles=articles,
            pagination=pagination,
            search_params=search_params,
            search_type='unified',
            ai_suggestions=ai_suggestions,
            min=min
        )

    except Exception as e:
        logger.error(f"Error in search processing: {str(e)}")
        db.session.rollback()
        
        # Provide user-friendly error message
        error_message = "Search temporarily unavailable. Please try again."
        if "Connection refused" in str(e):
            error_message = "Search running in compatibility mode (cache unavailable)."
            logger.info("🔄 Search operating without Redis cache")
        
        # Generate AI suggestions even in error case if we have a query
        ai_suggestions = None
        if search_query or symbol or keywords:
            original_query = search_query or symbol or keywords
            try:
                ai_suggestions = _generate_ai_search_suggestions(original_query)
                logger.info(f"Generated {len(ai_suggestions)} AI suggestions for error case: {original_query}")
            except Exception as e:
                logger.warning(f"Failed to generate AI suggestions for error case: {str(e)}")

        return render_template(
            'news/search.html',
            articles=[],
            pagination=None,
            search_params={'q': search_query, 'symbol': symbol, 'keywords': keywords},
            search_type='unified',
            error=error_message,
            ai_suggestions=ai_suggestions,
            min=min
        )

def detect_region_from_query(query_text):
    """Detect region from search query text"""
    query_lower = query_text.lower()
    
    # Region keywords and aliases
    region_keywords = {
        'CHINA': ['china', 'chinese', 'chn', 'mainland', 'shanghai', 'shenzhen', 'sse', 'szse'],
        'HK': ['hong kong', 'hongkong', 'hk', 'hkex', 'hong-kong'],
        'US': ['usa', 'us', 'america', 'american', 'nasdaq', 'nyse', 'united states'],
        'UK': ['uk', 'britain', 'british', 'london', 'lse'],
        'JP': ['japan', 'japanese', 'tokyo', 'tse', 'nikkei'],
    }
    
    for region, keywords in region_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            return region
    
    return None

def extract_region_from_query(query_text):
    """Extract region from query and return cleaned query"""
    query_lower = query_text.lower()
    
    # Region keywords to remove from query
    region_keywords = {
        'CHINA': ['china', 'chinese', 'chn', 'mainland', 'shanghai', 'shenzhen'],
        'HK': ['hong kong', 'hongkong', 'hk', 'hong-kong'],
        'US': ['usa', 'us', 'america', 'american', 'united states'],
        'UK': ['uk', 'britain', 'british', 'london'],
        'JP': ['japan', 'japanese', 'tokyo', 'nikkei'],
    }
    
    detected_region = detect_region_from_query(query_text)
    
    if detected_region:
        # Remove region keywords from query
        cleaned_query = query_lower
        for keyword in region_keywords.get(detected_region, []):
            cleaned_query = cleaned_query.replace(keyword, '').strip()
        
        # Clean up extra spaces
        cleaned_query = ' '.join(cleaned_query.split())
        
        return cleaned_query, detected_region
    
    return query_text, None

def extract_sort_from_query(query_text):
    """Extract sort order from query and return cleaned query"""
    query_lower = query_text.lower()
    
    # Sort keywords
    sort_keywords = ['highest', 'lowest']
    detected_sort = None
    
    for keyword in sort_keywords:
        if keyword in query_lower:
            detected_sort = keyword.upper()
            # Remove the sort keyword from query
            cleaned_query = query_lower.replace(keyword, '').strip()
            # Clean up extra spaces
            cleaned_query = ' '.join(cleaned_query.split())
            return cleaned_query, detected_sort
    
    return query_text, None

def _parse_unified_search_params(search_query, symbol, keywords, args):
    """Parse and normalize unified search parameters with region detection"""
    search_params = {
        'q': search_query,
        'symbol': symbol,
        'keywords': keywords
    }
    
    # Detect and extract region and sort order from the search query
    detected_region = None
    detected_sort = None
    cleaned_query = search_query
    
    if search_query:
        # First extract region
        cleaned_query, detected_region = extract_region_from_query(search_query)
        # Then extract sort order from the cleaned query
        cleaned_query, detected_sort = extract_sort_from_query(cleaned_query)
        
    # Determine search type and extract terms
    extracted_symbols = []
    extracted_keywords = []
    search_type = 'symbol'  # default
    
    # Process universal search query (use cleaned query)
    if cleaned_query:
        query_parts = cleaned_query.split()
        for part in query_parts:
            # Check if it looks like a stock symbol
            if _is_likely_symbol(part):
                extracted_symbols.append(part.upper())
            else:
                extracted_keywords.append(part)
    
    # Add specific symbol if provided (but avoid duplicates)
    if symbol:
        symbol_parts = symbol.split()
        for part in symbol_parts:
            if part.upper() not in extracted_symbols:
                extracted_symbols.append(part.upper())
    
    # Add specific keywords if provided (but avoid duplicates)
    if keywords:
        keyword_parts = keywords.split()
        for part in keyword_parts:
            if part not in extracted_keywords:
                extracted_keywords.append(part)
    
    # Determine search type
    if extracted_symbols and extracted_keywords:
        search_type = 'mixed'
    elif extracted_keywords:
        search_type = 'keyword'
    elif extracted_symbols:
        search_type = 'symbol'
    
    # Parse symbol-specific parameters (for backward compatibility)
    if extracted_symbols:
        symbol_params = _parse_search_params(' '.join(extracted_symbols), args)
        search_params.update(symbol_params)
        search_params['symbols'] = extracted_symbols + symbol_params.get('symbols', [])
    else:
        search_params.update({
            'symbols': [],
            'region_filter': None,
            'sort_order': 'LATEST',
            'date_filter': None,
            'processing_filter': args.get('processing_filter', 'all'),
            'sentiment_filter': args.get('sentiment_filter'),
            'start_date': args.get('start_date'),
            'end_date': args.get('end_date')
        })
    
    # Override region_filter with detected region (if any)
    if detected_region:
        search_params['region_filter'] = detected_region
    
    # Override sort_order with detected sort (if any)
    if detected_sort:
        search_params['sort_order'] = detected_sort
    
    # Check for "latest" keyword specifically and remove it from keywords
    has_latest_keyword = any(keyword.lower() == 'latest' for keyword in extracted_keywords)
    if has_latest_keyword:
        search_params['has_latest'] = True
        # Remove "latest" from keywords list so it doesn't interfere with content search
        extracted_keywords = [kw for kw in extracted_keywords if kw.lower() != 'latest']
    
    # Add keyword parameters
    search_params['keywords'] = extracted_keywords
    search_params['search_type'] = search_type
    
    return search_params

def _parse_search_params(symbol, args):
    """Parse and normalize search parameters efficiently (for backward compatibility)"""
    search_params = {'symbol': symbol}
    
    # Parse symbol and extract special keywords
    if not symbol:
        return search_params
        
    symbol_parts = symbol.split()
    regions = ['CHINA', 'US', 'HK', 'OTHER']
    sorts = ['HIGHEST', 'LOWEST', 'LATEST']
    
    # Extract filters from symbol parts
    region_filter = next((p for p in symbol_parts if p in regions), None)
    sort_order = next((p for p in symbol_parts if p in sorts), 'LATEST')
    
    # Extract date filter
    date_filter = None
    for part in symbol_parts:
        if re.match(r'^\d{4}-\d{2}-\d{2}$', part):
            date_filter = part
            break
        elif part.upper().startswith('DATE:'):
            date_part = part[5:]
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_part):
                date_filter = date_part
                break

    # Clean symbol - remove special keywords
    special_keywords = regions + sorts + ([date_filter] if date_filter else [])
    clean_symbol_parts = [p for p in symbol_parts 
                         if p not in special_keywords and not p.upper().startswith('DATE:')]
    clean_symbol = ' '.join(clean_symbol_parts) if clean_symbol_parts else ''
    
    # Get symbol variants if we have a clean symbol
    symbols = []
    if clean_symbol:
        # Convert symbol formats
        if re.match(r'^\d{4}\.HK$', clean_symbol):
            clean_symbol = f"HKEX:{int(clean_symbol.replace('.HK', ''))}"
        elif clean_symbol.endswith('.SS'):
            clean_symbol = f"SSE:{clean_symbol.replace('.SS', '')}"
        elif clean_symbol.endswith('.SZ'):
            clean_symbol = f"SZSE:{clean_symbol.replace('.SZ', '')}"
        
        from app.utils.search.news_search import NewsSearch
        news_search = NewsSearch(db.session)
        symbols = news_search.get_symbol_variants(clean_symbol)
    
    # Build search parameters
    search_params.update({
        'symbols': symbols,
        'region_filter': region_filter,
        'sort_order': sort_order,
        'date_filter': date_filter,
        'processing_filter': args.get('processing_filter', 'all'),
        'sentiment_filter': args.get('sentiment_filter'),
        'start_date': args.get('start_date'),
        'end_date': args.get('end_date')
    })
    
    return search_params

def _is_likely_symbol(text):
    """Determine if a text string is likely a stock symbol - ENHANCED"""
    import re
    
    # Stock symbol patterns - ENHANCED to include bare Chinese/HK symbols
    patterns = [
        r'^[A-Z]{1,5}$',  # Simple 1-5 letter symbols (AAPL, MSFT)
        r'^[A-Z]+:[A-Z0-9]+$',  # Exchange:Symbol format (NASDAQ:AAPL, SSE:600585)
        r'^\d{4,6}\.HK$',  # Hong Kong format (0700.HK)
        r'^\d{6}\.S[SZ]$',  # Chinese format (600585.SS, 000001.SZ)
        r'^[A-Z]{1,4}\d*$',  # Mixed letter-number (QQQ, SPY)
        r'^\d{6}$',  # NEW: Bare Chinese symbols (600585, 000001)
        r'^\d{4}$',  # NEW: Bare Hong Kong symbols (0700, 2318)
        r'^\d{3}$',  # NEW: Short numeric symbols (700, 318)
    ]
    
    return any(re.match(pattern, text.upper()) for pattern in patterns)

def normalize_symbol_for_comparison(symbol):
    """
    Normalize symbols to handle different formats for the same stock.
    This helps match symbols like '600298.SS' with 'SSE:600298'.
    """
    if not symbol:
        return symbol
        
    symbol = symbol.upper().strip()
    
    # Handle Chinese stocks - convert Yahoo format to TradingView format
    if symbol.endswith('.SS'):  # Shanghai Stock Exchange
        base_symbol = symbol[:-3]  # Remove .SS
        return f"SSE:{base_symbol}"
    elif symbol.endswith('.SZ'):  # Shenzhen Stock Exchange  
        base_symbol = symbol[:-3]  # Remove .SZ
        return f"SZSE:{base_symbol}"
    elif symbol.endswith('.HK'):  # Hong Kong Stock Exchange
        base_symbol = symbol[:-3]  # Remove .HK
        return f"HKEX:{base_symbol}"
    elif symbol.endswith('.T'):  # Tokyo Stock Exchange
        base_symbol = symbol[:-2]  # Remove .T
        return f"TSE:{base_symbol}"
    elif symbol.endswith('.L'):  # London Stock Exchange
        base_symbol = symbol[:-2]  # Remove .L
        return f"LSE:{base_symbol}"
    
    # Handle US stocks - convert Yahoo format to TradingView format
    if '.' not in symbol and ':' not in symbol:
        # Plain symbol like AAPL, assume NASDAQ first, then NYSE
        # This is a simplification - in reality we'd need a lookup table
        return symbol  # Keep as-is for now, could be enhanced
    
    # Already in TradingView format or other format
    return symbol

def get_all_symbol_variants(symbol):
    """
    Get all possible variants of a symbol to check against the scheduler list.
    Returns a list of symbol variants that could match the same stock.
    """
    if not symbol:
        return [symbol]
        
    variants = []  # Don't include original first, we'll add it in the right order
    symbol = symbol.upper().strip()
    
    # If it's already in TradingView format, generate Yahoo format variants
    if ':' in symbol:
        variants.append(symbol)  # Original symbol first
        exchange, base = symbol.split(':', 1)
        if exchange == 'SSE':
            variants.append(f"{base}.SS")
        elif exchange == 'SZSE':
            variants.append(f"{base}.SZ")
        elif exchange == 'HKEX':
            variants.append(f"{base}.HK")
        elif exchange == 'TSE':
            variants.append(f"{base}.T")
        elif exchange == 'LSE':
            variants.append(f"{base}.L")
        elif exchange in ['NASDAQ', 'NYSE']:
            variants.append(base)  # Plain symbol
    else:
        # Handle different Yahoo format suffixes
        if symbol.endswith('.SS'):
            base_symbol = symbol[:-3]
            variants.append(f"SSE:{base_symbol}")
            variants.append(symbol)  # Original symbol
        elif symbol.endswith('.SZ'):
            base_symbol = symbol[:-3]
            variants.append(f"SZSE:{base_symbol}")
            variants.append(symbol)  # Original symbol
        elif symbol.endswith('.HK'):
            base_symbol = symbol[:-3]
            variants.append(f"HKEX:{base_symbol}")
            variants.append(symbol)  # Original symbol
        elif symbol.endswith('.T'):
            base_symbol = symbol[:-2]
            variants.append(f"TSE:{base_symbol}")
            variants.append(symbol)  # Original symbol
        elif symbol.endswith('.L'):
            base_symbol = symbol[:-2]
            variants.append(f"LSE:{base_symbol}")
            variants.append(symbol)  # Original symbol
        elif '.' not in symbol and ':' not in symbol:
            # Plain US symbol - use proper exchange lookup
            from app.utils.symbol_utils import get_us_stock_exchange
            correct_exchange = get_us_stock_exchange(symbol)
            variants.append(f"{correct_exchange}:{symbol}")  # Correct exchange first
            variants.append(symbol)  # Original symbol second
            # Also add the opposite exchange as fallback for safety
            other_exchange = 'NYSE' if correct_exchange == 'NASDAQ' else 'NASDAQ'
            variants.append(f"{other_exchange}:{symbol}")
        
        else:
            # For symbols that don't match any specific pattern, add original
            variants.append(symbol)
        
        # Also try the normalize_symbol_for_comparison function
        normalized = normalize_symbol_for_comparison(symbol)
        if normalized != symbol and normalized not in variants:
            variants.append(normalized)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for variant in variants:
        if variant not in seen:
            seen.add(variant)
            unique_variants.append(variant)
    
    return unique_variants

@bp.route('/api/fetch', methods=['POST'])
@login_required
def fetch_news():
    """Fetch and analyze news for specific symbols with smart limits"""
    try:
        # Check global news fetching control
        from app.utils.analysis.stock_news_service import StockNewsService
        if not StockNewsService.is_news_fetching_enabled():
            return jsonify({
                'status': 'error', 
                'message': 'News fetching is globally disabled. Please start the schedulers first.',
                'disabled': True
            }), HTTPStatus.FORBIDDEN
            
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), HTTPStatus.BAD_REQUEST
            
        symbols = data.get('symbols', [])
        if not symbols:
            return jsonify({'status': 'error', 'message': 'No symbols provided'}), HTTPStatus.BAD_REQUEST
            
        requested_limit = min(int(data.get('limit', 5)), 50)  # Default 5 articles for individual stock analysis (not in 346 list), cap at 50
        timeout = int(data.get('timeout', 30))  # Allow configurable timeout, default 30s
        force_full_limit = data.get('force_full_limit', False)  # Allow override of smart limiting
        
        # Get the full 346 symbols list from the scheduler to check against
        try:
            from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
            scheduler_symbols = news_fetch_scheduler.get_symbols()
        except Exception as e:
            logger.warning(f"Could not get scheduler symbols, using fallback: {str(e)}")
            # Fallback to the smaller list if scheduler is not available
            scheduler_symbols = DEFAULT_SYMBOLS
        
        # Apply smart limiting logic with symbol normalization
        smart_limits = {}
        for symbol in symbols:
            # Get all possible variants of this symbol
            symbol_variants = get_all_symbol_variants(symbol)
            
            # Check if any variant matches a scheduler symbol
            is_in_scheduler = any(variant in scheduler_symbols for variant in symbol_variants)
            
            if is_in_scheduler and not force_full_limit:
                # Symbol (or its variant) is already processed by automated scheduler - skip fetching
                smart_limits[symbol] = 0
                matching_variant = next(variant for variant in symbol_variants if variant in scheduler_symbols)
                logger.info(f"Symbol {symbol} matches scheduler symbol {matching_variant} - skipping fetch (already processed automatically)")
            else:
                # Symbol is NOT in scheduler list OR user forced full limit - allow full requested limit
                smart_limits[symbol] = requested_limit
                if is_in_scheduler and force_full_limit:
                    logger.info(f"Symbol {symbol} is in scheduler but force_full_limit=True - allowing {smart_limits[symbol]} articles")
                else:
                    logger.info(f"Symbol {symbol} (variants: {symbol_variants}) is NOT in scheduler list - allowing {smart_limits[symbol]} articles")
        
        logger.info(f"Fetching news for symbols: {symbols}, smart limits: {smart_limits}")
        
        try:
            # Apply smart limiting by processing symbols individually if needed
            all_articles = []
            
            for symbol in symbols:
                symbol_limit = smart_limits[symbol]
                
                # Skip fetching if limit is 0 (symbol is in scheduler)
                if symbol_limit == 0:
                    logger.info(f"Skipping {symbol} - already processed by automated scheduler")
                    continue
                
                # Add a timeout to the news service call
                articles = news_service.fetch_and_analyze_news(
                    symbols=[symbol], 
                    limit=symbol_limit,
                    timeout=timeout
                )
                
                if articles:
                    all_articles.extend(articles)
                    logger.info(f"Fetched {len(articles)} articles for {symbol} (limit: {symbol_limit})")
                else:
                    logger.warning(f"No articles found for symbol: {symbol}")
            
            if not all_articles and len(symbols) > 0:
                # Check if symbols were skipped due to being in scheduler
                skipped_symbols = [symbol for symbol in symbols if smart_limits[symbol] == 0]
                if skipped_symbols:
                    logger.warning(f"All symbols were skipped (in scheduler): {skipped_symbols}")
                    return jsonify({
                        'status': 'success',
                        'message': f'All symbols are in the automated scheduler and were skipped to avoid duplication. Use "Override smart limiting" if you want to fetch them anyway.',
                        'articles': [],
                        'smart_limits_applied': smart_limits,
                        'skipped_symbols': skipped_symbols
                    })
                else:
                    logger.warning(f"No articles found for any symbols: {symbols}")
                    return jsonify({
                        'status': 'success',
                        'message': 'No articles found',
                        'articles': [],
                        'smart_limits_applied': smart_limits
                    })
            
            return jsonify({
                'status': 'success',
                'message': f'Successfully fetched {len(all_articles)} articles',
                'articles': all_articles,
                'smart_limits_applied': smart_limits,
                'scheduler_symbols_count': len(scheduler_symbols)
            })
        except Exception as service_error:
            logger.error(f"News service error for symbols {symbols}: {str(service_error)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'News service error: {str(service_error)}',
                'symbols': symbols
            }), HTTPStatus.SERVICE_UNAVAILABLE
            
    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch news: {str(e)}',
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/batch-fetch', methods=['POST'])
@login_required
def batch_fetch():
    """Batch fetch news articles with smart limiting"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), HTTPStatus.BAD_REQUEST
        
        chunk_size = 5  # Process 5 symbols at a time
        symbols = data.get('symbols', DEFAULT_SYMBOLS[:10]) 
        requested_articles_per_symbol = min(int(data.get('limit', 2)), 5)
        
        # Get the full 346 symbols list from the scheduler to check against
        try:
            from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
            scheduler_symbols = news_fetch_scheduler.get_symbols()
        except Exception as e:
            logger.warning(f"Could not get scheduler symbols for batch fetch, using fallback: {str(e)}")
            # Fallback to the smaller list if scheduler is not available
            scheduler_symbols = DEFAULT_SYMBOLS
        
        # Apply smart limiting logic for batch processing
        smart_limits = {}
        for symbol in symbols:
            # Get all possible variants of this symbol
            symbol_variants = get_all_symbol_variants(symbol)
            
            # Check if any variant matches a scheduler symbol
            is_in_scheduler = any(variant in scheduler_symbols for variant in symbol_variants)
            
            if is_in_scheduler:
                # Symbol (or its variant) is already processed by automated scheduler - skip fetching
                smart_limits[symbol] = 0
                matching_variant = next(variant for variant in symbol_variants if variant in scheduler_symbols)
                logger.info(f"Batch: Symbol {symbol} matches scheduler symbol {matching_variant} - skipping fetch (already processed automatically)")
            else:
                # Symbol is NOT in scheduler list - allow full requested limit
                smart_limits[symbol] = requested_articles_per_symbol
                logger.info(f"Batch: Symbol {symbol} (variants: {symbol_variants}) is NOT in scheduler list - allowing {smart_limits[symbol]} articles")
        
        logger.info(f"Batch fetch with smart limits: {len(symbols)} symbols, limits: {smart_limits}")
        
        # Delete articles with no content and no insights
        try:
            articles_to_delete = NewsArticle.query.filter(
                NewsArticle.content.is_(None),
                NewsArticle.ai_insights.is_(None)
            ).all()
            
            for article in articles_to_delete:
                db.session.delete(article)
            
            db.session.commit()
            logger.info(f"Deleted {len(articles_to_delete)} articles with no content and insights")
        except Exception as e:
            logger.error(f"Error deleting empty articles: {str(e)}")
            db.session.rollback()
        
        all_articles = []
        chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        for chunk in chunks:
            for symbol in chunk:
                try:
                    symbol_limit = smart_limits[symbol]
                    
                    # Skip fetching if limit is 0 (symbol is in scheduler)
                    if symbol_limit == 0:
                        logger.info(f"Batch: Skipping {symbol} - already processed by automated scheduler")
                        continue
                    
                    articles = news_service.fetch_and_analyze_news(
                        symbols=[symbol], 
                        limit=symbol_limit
                    )
                    if articles:
                        all_articles.extend(articles)
                        logger.info(f"Batch: Fetched {len(articles)} articles for {symbol} (limit: {symbol_limit})")
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {str(e)}")
                    continue
        
        return jsonify({
            'status': 'success',
            'articles': all_articles,
            'total': len(all_articles),
            'smart_limits_applied': smart_limits,
            'scheduler_symbols_count': len(scheduler_symbols)
        })
        
    except Exception as e:
        logger.error(f"Batch fetch error: {str(e)}")
        return jsonify({'error': str(e)}), 500

from datetime import datetime

def initialize_articles(cutoff_time: str) -> None:
    """
    Initialize AI fields for articles created after a specific timestamp.
    
    Args:
        cutoff_time (str): The timestamp in the format 'YYYY-MM-DD HH:MM:SS'.
                          Articles created after this time will have their AI fields set to None.
    """
    try:
        # Convert the cutoff_time string to a datetime object
        cutoff_datetime = datetime.strptime(cutoff_time, "%Y-%m-%d %H:%M:%S")
        
        # Update articles created after the cutoff time
        articles_updated = NewsArticle.query.filter(
            NewsArticle.created_at >= cutoff_datetime
        ).update({
            NewsArticle.ai_summary: None,
            NewsArticle.ai_insights: None,
            NewsArticle.ai_sentiment_rating: None
        })
        
        # Commit the changes to the database
        db.session.commit()
        logger.info(f"Initialized {articles_updated} articles created after {cutoff_time} with None values for AI fields")
    except Exception as e:
        logger.error(f"Error initializing articles: {str(e)}")
        db.session.rollback()
        raise
@bp.route('/api/get-articles-to-update', methods=['GET'])
@login_required
def get_articles_to_update():
    try:
        # Fetch articles that have BOTH missing AI fields AND full content
        missing_fields_articles = NewsArticle.query.filter(
            # Must have missing AI fields
            db.or_(
                NewsArticle.ai_summary.is_(None),
                NewsArticle.ai_insights.is_(None),
                NewsArticle.ai_sentiment_rating.is_(None)
            ),
            # AND must have substantial content to process
            NewsArticle.content.isnot(None),
            db.func.length(db.func.trim(NewsArticle.content)) > 20
        ).all()
        
        # Still count irregular articles separately for reporting,
        # but don't include them in the total to process
        irregular_articles = NewsArticle.query.filter(
            db.or_(
                NewsArticle.ai_summary.contains('Keyword 1'),
                NewsArticle.ai_summary.contains('Point 1'),
                NewsArticle.ai_insights.contains('Insight 1'),
                NewsArticle.ai_insights.contains('Implication 1')
            )
        ).all()

        # Return the count of articles to be updated
        return jsonify({
            'status': 'success',
            'count': len(missing_fields_articles),
            'missing_fields_count': len(missing_fields_articles),
            'irregular_count': len(irregular_articles),
            'process_irregular': False,  # Flag indicating we don't process irregular content in batch
            'criteria': 'missing_ai_fields_and_full_content'  # Indicate the criteria used
        })
    except Exception as e:
        logger.error(f"Error getting articles to update: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@bp.route('/api/latest-articles-wrapup', methods=['GET'])
@login_required
def get_latest_articles_wrapup():
    try:
        # Fetch the latest 10 articles
        articles = NewsArticle.query.order_by(NewsArticle.published_at.desc()).limit(10).all()

        wrapup_results = []

        for article in articles:
            wrapup_results.append({
                'id': article.id,
                'title': article.title,
                'url': article.url,
                'published_at': article.published_at.strftime("%Y-%m-%d %H:%M:%S"),
                'wrapup': article.brief_summary or "No summary available."  # Use brief_summary
            })

        return jsonify({
            'status': 'success',
            'articles': wrapup_results
        })

    except Exception as e:
        logger.error(f"Error in get_latest_articles_wrapup: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
@bp.route('/api/reset-ai-summaries', methods=['POST'])
@login_required
def reset_ai_summaries():
    """Reset AI summaries for the latest N articles"""
    try:
        data = request.get_json()
        num_articles = data.get('num_articles', 10)
        
        # Validate input
        if not isinstance(num_articles, int) or num_articles <= 0:
            return jsonify({'error': 'Invalid number of articles'}), 400
        
        # Get the latest N articles that have AI summaries
        articles_to_reset = NewsArticle.query.filter(
            or_(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None),
                NewsArticle.ai_sentiment_rating.isnot(None)
            )
        ).order_by(NewsArticle.published_at.desc()).limit(num_articles).all()
        
        reset_count = 0
        for article in articles_to_reset:
            # Reset AI fields to null
            article.ai_summary = None
            article.ai_insights = None
            article.ai_sentiment_rating = None
            article.ai_processed_at = None
            reset_count += 1
        
        # Commit changes
        db.session.commit()
        
        logger.info(f"Reset AI summaries for {reset_count} articles")
        
        return jsonify({
            'success': True,
            'reset_count': reset_count,
            'message': f'Successfully reset AI summaries for {reset_count} articles'
        })
        
    except Exception as e:
        logger.error(f"Error resetting AI summaries: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/update-summaries', methods=['POST'])
@login_required
def update_ai_summaries():
    try:
        import requests

        OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

        # Validate API key
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not found in environment variables")
            return jsonify({'status': 'error', 'message': 'API key not configured'}), 500

        # Create OpenAI client for OpenRouter
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )

        # Only fetch articles that have BOTH missing AI fields AND full content
        articles = NewsArticle.query.filter(
            # Must have missing AI fields
            db.or_(
                NewsArticle.ai_summary.is_(None),
                NewsArticle.ai_insights.is_(None),
                NewsArticle.ai_sentiment_rating.is_(None)
            ),
            # AND must have substantial content to process
            NewsArticle.content.isnot(None),
            db.func.length(db.func.trim(NewsArticle.content)) > 20
        ).order_by(NewsArticle.id.desc()).limit(10).all()
        
        logger.info(f"Processing {len(articles)} articles with missing AI fields AND full content")
        
        processed = 0
        results = []

        for article in articles:
            try:
                # Validate article content
                if not article.content or len(article.content.strip()) < 10:
                    logger.warning(f"Article {article.id} has insufficient content")
                    results.append({
                        'id': article.id,
                        'title': article.title,
                        'success': False,
                        'reason': 'Insufficient content'
                    })
                    continue

                # Truncate content if too long (OpenRouter has limits)
                content = article.content.strip()
                if len(content) > 4000:  # Conservative limit
                    content = content[:4000] + "..."
                    logger.info(f"Truncated content for article {article.id} to 4000 characters")

                # CHECK CACHE FIRST for complete AI analysis
                cached_analysis = api_cache.get_ai_complete_analysis(content)
                if cached_analysis and (cached_analysis['summary'] or cached_analysis['insights'] or cached_analysis['sentiment_rating'] is not None):
                    logger.debug(f"🎯 AI analysis cache hit for article {article.id}")
                    
                    # Apply cached results
                    if not article.ai_summary and cached_analysis['summary']:
                        article.ai_summary = cached_analysis['summary']
                    if not article.ai_insights and cached_analysis['insights']:
                        article.ai_insights = cached_analysis['insights']
                    if article.ai_sentiment_rating is None and cached_analysis['sentiment_rating'] is not None:
                        article.ai_sentiment_rating = cached_analysis['sentiment_rating']
                    
                    db.session.commit()
                    processed += 1
                    results.append({
                        'id': article.id,
                        'title': article.title,
                        'ai_sentiment_rating': article.ai_sentiment_rating,
                        'success': True,
                        'cached': True
                    })
                    continue

                ai_summary = None
                ai_insights = None
                ai_sentiment_rating = None
                
                if not article.ai_summary:
                    summary_payload = {
                        "model": "anthropic/claude-3.5-sonnet",  # Using Claude Sonnet 3.5 for AI processing
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""Generate summary with STRICT markdown formatting:
**Key Concepts/Keywords**  
- Keyword 1  
- Keyword 2  

**Key Points**  
- Point 1  
- Point 2  

**Context**  
- Background 1  
- Background 2  

Use proper line breaks between list items. Article: {article.content}"""
                            }
                        ],
                        "max_tokens": 500  # Standard limits for Claude Sonnet 3.5
                    }
                    
                    logger.debug(f"Sending summary request for article {article.id}")
                    
                    completion = client.chat.completions.create(
                        extra_headers={
                            "HTTP-Referer": "https://trendwise.com",  # Optional. Site URL for rankings on openrouter.ai.
                            "X-Title": "TrendWise AI Analysis"  # Optional. Site title for rankings on openrouter.ai.
                        },
                        model=summary_payload["model"],
                        messages=summary_payload["messages"],
                        max_tokens=summary_payload["max_tokens"],
                        temperature=summary_payload["temperature"],
                        timeout=30
                    )
                    
                    ai_summary = completion.choices[0].message.content
                    logger.debug(f"Summary completed for article {article.id}")

                if not article.ai_insights:
                    insights_payload = {
                        "model": "anthropic/claude-3.5-sonnet",
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""Generate insights with STRICT markdown formatting:
**Key Insights**  
- Insight 1  
- Insight 2  

**Market Implications**  
- Implication 1  
- Implication 2  

**Conclusion**  
- Brief conclusion  

Use proper line breaks between list items. Article: {article.content}"""
                            }
                        ],
                        "max_tokens": 500  # Standard limits for Claude Sonnet 3.5
                    }
                    
                    logger.debug(f"Sending insights request for article {article.id}")
                    
                    completion = client.chat.completions.create(
                        extra_headers={
                            "HTTP-Referer": "https://trendwise.com",  # Optional. Site URL for rankings on openrouter.ai.
                            "X-Title": "TrendWise AI Analysis"  # Optional. Site title for rankings on openrouter.ai.
                        },
                        model=insights_payload["model"],
                        messages=insights_payload["messages"],
                        max_tokens=insights_payload["max_tokens"],
                        temperature=insights_payload["temperature"],
                        timeout=30
                    )
                    
                    ai_insights = completion.choices[0].message.content
                    logger.debug(f"Insights completed for article {article.id}")

                if article.ai_sentiment_rating is None:
                    sentiment_payload = {
                        "model": "anthropic/claude-3.5-sonnet",
                        "messages": [
                            {
                                "role": "user",
                                "content": f"Analyze the market sentiment of this article and provide a single number rating from -100 (extremely bearish) to 100 (extremely bullish). Only return the number: {article.content}"
                            }
                        ],
                        "max_tokens": 500  # Standard limits for Claude Sonnet 3.5
                    }
                    
                    logger.debug(f"Sending sentiment request for article {article.id}")
                    
                    completion = client.chat.completions.create(
                        extra_headers={
                            "HTTP-Referer": "https://trendwise.com",  # Optional. Site URL for rankings on openrouter.ai.
                            "X-Title": "TrendWise AI Analysis"  # Optional. Site title for rankings on openrouter.ai.
                        },
                        model=sentiment_payload["model"],
                        messages=sentiment_payload["messages"],
                        max_tokens=sentiment_payload["max_tokens"],
                        temperature=sentiment_payload["temperature"],
                        timeout=30
                    )
                    
                    try:
                        rating_text = completion.choices[0].message.content.strip()
                        rating = int(rating_text)
                        ai_sentiment_rating = max(min(rating, 100), -100)
                        logger.debug(f"Sentiment completed for article {article.id}: {ai_sentiment_rating}")
                    except ValueError:
                        logger.error(f"Could not parse sentiment rating for article {article.id}: {rating_text}")
                        ai_sentiment_rating = 0

                # Calculate total content length to verify if processing was successful
                total_content = ""
                if ai_summary:
                    total_content += ai_summary
                if ai_insights:
                    total_content += ai_insights
                if ai_sentiment_rating is not None:
                    total_content += str(ai_sentiment_rating)
                
                # Only save if total content length is adequate (at least 100 characters)
                if len(total_content) >= 100:
                    if ai_summary:
                        article.ai_summary = ai_summary
                    if ai_insights:
                        article.ai_insights = ai_insights
                    if ai_sentiment_rating is not None:
                        article.ai_sentiment_rating = ai_sentiment_rating
                        
                    db.session.commit()
                    
                    # CACHE THE AI ANALYSIS RESULTS
                    analysis_data = {
                        'summary': ai_summary,
                        'insights': ai_insights,
                        'sentiment_rating': ai_sentiment_rating
                    }
                    api_cache.set_ai_complete_analysis(content, analysis_data, expire=86400)  # 24 hours
                    logger.debug(f"💾 Cached AI analysis for article {article.id}")
                    
                    processed += 1
                    results.append({
                        'id': article.id,
                        'title': article.title,
                        'ai_sentiment_rating': article.ai_sentiment_rating,
                        'success': True,
                        'reprocessed': False
                    })
                    logger.info(f"Successfully processed article {article.id}")
                else:
                    logger.warning(f"AI processing for article {article.id} yielded insufficient content ({len(total_content)} characters). Skipping.")
                    results.append({
                        'id': article.id,
                        'title': article.title,
                        'success': False,
                        'reason': 'Insufficient AI-generated content length'
                    })

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error processing article {article.id}: {str(e)}")
                db.session.rollback()
                results.append({
                    'id': article.id,
                    'title': article.title if hasattr(article, 'title') else 'Unknown',
                    'success': False,
                    'reason': f'Request error: {str(e)}'
                })
                continue
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {str(e)}")
                db.session.rollback()
                results.append({
                    'id': article.id,
                    'title': article.title if hasattr(article, 'title') else 'Unknown',
                    'success': False,
                    'reason': str(e)
                })
                continue

        return jsonify({
            'status': 'success',
            'processed': processed,
            'articles': results
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/sentiment')
@login_required
def get_sentiment():
    """Get sentiment analysis data"""
    try:
        symbol = request.args.get('symbol')
        days = min(int(request.args.get('days', 7)), 90)
        
        if not symbol:
            return jsonify({
                'status': 'error',
                'message': 'Missing required symbol parameter'
            }), HTTPStatus.BAD_REQUEST

        symbol_upper = symbol.upper()
        symbol_filter = None  # Initialize symbol_filter
        
        # Handle special cases
        if symbol_upper == 'ALL':
            pass  # Keep existing behavior for 'all'
        else:
            # Handle index symbols (^HSI, ^GSPC, etc.)
            indices_key = None
            if symbol_upper.startswith('^'):
                clean_symbol = symbol_upper[1:]  # Remove the ^ prefix
                if clean_symbol in INDICES_MAPPING:
                    indices_key = clean_symbol
                    logger.info(f"Sentiment API: Found index symbol ^{indices_key}")
            # Also check if the symbol is one of the index variants
            else:
                for key, variants in INDICES_MAPPING.items():
                    if symbol_upper in variants:
                        indices_key = key
                        logger.info(f"Sentiment API: Found index variant {symbol_upper} for index {key}")
                        break
            
            # Handle futures symbols like GC=F
            futures_key = None
            
            # Check if it's GC=F (gold futures) or other direct futures format
            if symbol_upper == 'GC=F':
                futures_key = 'GOLD'
            elif symbol_upper == 'SI=F':
                futures_key = 'SILVER'
            elif symbol_upper == 'HG=F':
                futures_key = 'COPPER'
            elif symbol_upper == 'CL=F' or symbol_upper == 'OIL':
                futures_key = 'OIL'
            elif symbol_upper == 'BZ=F':
                futures_key = 'BRENT'
            elif symbol_upper == 'NG=F':
                futures_key = 'GAS'
            # Check if directly using a known futures key
            elif symbol_upper in FUTURES_MAPPING:
                futures_key = symbol_upper
            # Check if the symbol is one of the values in FUTURES_MAPPING
            else:
                for key, symbols_list in FUTURES_MAPPING.items():
                    if symbol_upper in symbols_list:
                        futures_key = key
                        break
            
            # Check if it's a futures commodity
            if futures_key:
                futures_symbols = FUTURES_MAPPING[futures_key]
                symbol_filter = [ArticleSymbol.symbol == sym for sym in futures_symbols]
            # Check if it's an index with multiple variants
            elif indices_key:
                index_symbols = INDICES_MAPPING[indices_key]
                symbol_filter = [ArticleSymbol.symbol == sym for sym in index_symbols]
            elif ':' not in symbol_upper:
                # Try to match with any exchange prefix or without prefix
                symbol_filter = [
                    ArticleSymbol.symbol == f"NASDAQ:{symbol_upper}",
                    ArticleSymbol.symbol == f"NYSE:{symbol_upper}",
                    ArticleSymbol.symbol == f"HKEX:{symbol_upper}",
                    ArticleSymbol.symbol == f"SSE:{symbol_upper}",     # Shanghai Stock Exchange
                    ArticleSymbol.symbol == f"SZSE:{symbol_upper}",    # Shenzhen Stock Exchange
                    ArticleSymbol.symbol == f"LSE:{symbol_upper}",     # London Stock Exchange
                    ArticleSymbol.symbol == f"TSE:{symbol_upper}",     # Tokyo Stock Exchange
                    ArticleSymbol.symbol == f"TSX:{symbol_upper}",     # Toronto Stock Exchange
                    ArticleSymbol.symbol == f"ASX:{symbol_upper}",     # Australian Securities Exchange
                    ArticleSymbol.symbol == f"AMEX:{symbol_upper}",    # American Stock Exchange
                    ArticleSymbol.symbol == f"EURONEXT:{symbol_upper}", # European Exchange
                    ArticleSymbol.symbol == f"XETR:{symbol_upper}",    # German Exchange
                    ArticleSymbol.symbol == f"SP:{symbol_upper}",      # S&P
                    ArticleSymbol.symbol == f"DJ:{symbol_upper}",      # Dow Jones
                    ArticleSymbol.symbol == f"FOREXCOM:{symbol_upper}", # Forex
                    ArticleSymbol.symbol == f"BITSTAMP:{symbol_upper}", # Crypto
                    ArticleSymbol.symbol == f"COMEX:{symbol_upper}",   # Commodities Exchange
                    ArticleSymbol.symbol == f"NYMEX:{symbol_upper}",   # NY Mercantile Exchange
                    ArticleSymbol.symbol == f"TVC:{symbol_upper}",     # TradingView
                    ArticleSymbol.symbol == symbol_upper
                ]
            else:
                symbol_filter = [ArticleSymbol.symbol == symbol_upper]

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for SQL
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get daily sentiment scores
        daily_data = news_service.get_sentiment_timeseries(
            symbol=symbol,
            days=days,
            symbol_filter=symbol_filter
        )
        
        # Calculate overall statistics
        total_sentiment = 0
        total_articles = 0
        highest_day = {'date': None, 'value': -100}
        lowest_day = {'date': None, 'value': 100}
        
        for date, data in daily_data.items():
            if data['article_count'] > 0:
                total_articles += data['article_count']
                total_sentiment += data['average_sentiment'] * data['article_count']
                
                if data['average_sentiment'] > highest_day['value']:
                    highest_day = {'date': date, 'value': data['average_sentiment']}
                if data['average_sentiment'] < lowest_day['value']:
                    lowest_day = {'date': date, 'value': data['average_sentiment']}
        
        average_sentiment = round(total_sentiment / total_articles, 2) if total_articles > 0 else 0
        
        return jsonify({
            'status': 'success',
            'data': {
                'average_sentiment': average_sentiment,
                'daily_sentiment': daily_data,
                'highest_day': highest_day,
                'lowest_day': lowest_day,
                'total_articles': total_articles
            }
        })
    except Exception as e:
        logger.error(f"Error getting sentiment data: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/trending')
@login_required
def get_trending():
    """Get trending topics"""
    try:
        days = int(request.args.get('days', 7))
        topics = news_service.get_trending_topics(days=days)
        return jsonify(topics)
    except Exception as e:
        logger.error(f"Error getting trending topics: {str(e)}")
        return jsonify({'error': 'Failed to get trending topics'}), 500

# @bp.route('/api/news/sentiment')
# @login_required
# def get_sentiment():
#     """Get sentiment analysis for specified parameters"""
#     try:
#         analytics = init_analytics()
        
#         symbol = request.args.get('symbol')
#         days = min(int(request.args.get('days', 7)), 90)  # Cap at 90 days
#         include_metrics = request.args.get('include_metrics', 'true').lower() == 'true'
        
#         analysis = analytics.get_sentiment_analysis(
#             symbol=symbol,
#             days=days,
#             include_metrics=include_metrics
#         )
        
#         return jsonify({
#             'status': 'success',
#             'data': analysis
#         })
        
#     except Exception as e:
#         logger.error(f"Error getting sentiment analysis: {str(e)}", exc_info=True)
#         return jsonify({
#             'status': 'error',
#             'message': 'Failed to get sentiment analysis'
#         }), HTTPStatus.INTERNAL_SERVER_ERROR

# @bp.route('/api/news/trending')
# @login_required
# def get_trending():
#     """Get trending topics analysis"""
#     try:
#         analytics = init_analytics()
#         days = min(int(request.args.get('days', 7)), 30)  # Cap at 30 days
        
#         topics = analytics.get_trending_topics(days=days)
        
#         return jsonify({
#             'status': 'success',
#             'data': topics
#         })
        
#     except Exception as e:
#         logger.error(f"Error getting trending topics: {str(e)}", exc_info=True)
#         return jsonify({
#             'status': 'error',
#             'message': 'Failed to get trending topics'
#         }), HTTPStatus.INTERNAL_SERVER_ERROR

# @bp.route('/api/news/correlations')
# @login_required
# def get_correlations():
#     """Get symbol correlations"""
#     try:
#         analytics = init_analytics()
        
#         symbol = request.args.get('symbol')
#         if not symbol:
#             return jsonify({
#                 'status': 'error',
#                 'message': 'Symbol is required'
#             }), HTTPStatus.BAD_REQUEST
            
#         days = min(int(request.args.get('days', 30)), 90)  # Cap at 90 days
        
#         correlations = analytics.get_symbol_correlations(
#             symbol=symbol,
#             days=days
#         )
        
#         return jsonify({
#             'status': 'success',
#             'data': correlations
#         })
        
#     except Exception as e:
#         logger.error(f"Error getting correlations: {str(e)}", exc_info=True)
#         return jsonify({
#             'status': 'error',
#             'message': 'Failed to get correlations'
#         }), HTTPStatus.INTERNAL_SERVER_ERROR

def _get_search_params():
    """Extract and validate search parameters from request"""
    now = datetime.now()
    
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(50, int(request.args.get('per_page', 20)))
    except (TypeError, ValueError):
        page = 1
        per_page = 20

    keyword = request.args.get('keyword')
    keyword = None if keyword in ['None', '', None] else keyword

    symbol = request.args.get('symbol')
    symbol = None if symbol in ['None', '', None] else symbol

    return {
        'keyword': keyword,
        'symbol': symbol,
        'start_date': request.args.get('start_date') or (now - timedelta(days=30)).strftime("%Y-%m-%d"),
        'end_date': request.args.get('end_date') or now.strftime("%Y-%m-%d"),
        'sentiment': request.args.get('sentiment') or None,
        'page': page,
        'per_page': per_page,
        'include_analytics': request.args.get('include_analytics', 'false').lower() == 'true'
    }
@bp.teardown_request
def cleanup(exception):
    """Cleanup resources after each request"""
    try:
        if hasattr(news_service, 'close'):
            news_service.close()
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
        
@bp.route('/api/symbol-suggest')
@login_required
def symbol_suggest():
    symbol = request.args.get('symbol', '')
    if not symbol:
        return jsonify({'suggestions': []})
    
    suggested_symbol = get_tradingview_symbol(symbol)
    return jsonify({'suggestions': [{'symbol': suggested_symbol}]})

def get_tradingview_symbol(symbol):
    """Convert stock symbol to TradingView format using comprehensive exchange mapping"""
    from app.utils.symbol_utils import normalize_ticker
    
    # Use the improved normalize_ticker function with 'search' purpose
    # This will properly convert symbols to TradingView format with correct exchanges
    return normalize_ticker(symbol, purpose='search')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)  # HTTP 403 Forbidden
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/articles/manage')
@admin_required
def manage_articles():
    """Show editable table of articles"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        search = request.args.get('search', '')

        # Get paginated articles
        query = NewsArticle.query
        
        if search:
            search = f"%{search}%"
            query = query.filter(NewsArticle.title.ilike(search))
            
        articles = query.order_by(NewsArticle.published_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            'news/manage_articles.html',
            articles=articles,
            search=search
        )

    except Exception as e:
        logger.error(f"Error managing articles: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/articles/update/<int:article_id>', methods=['GET', 'POST'])
@admin_required
def update_article(article_id):
    """Update article content"""
    try:
        article = NewsArticle.query.get_or_404(article_id)
        
        # Handle GET request to fetch article data
        if request.method == 'GET':
            return jsonify({
                'title': article.title,
                'content': article.content,
                'ai_summary': article.ai_summary,
                'ai_insights': article.ai_insights,
                'ai_sentiment_rating': article.ai_sentiment_rating
            })

        # Handle POST request to update article
        data = request.get_json()

        # Update fields if provided
        if 'title' in data:
            article.title = data['title']
        if 'content' in data:
            article.content = data['content']
        if 'ai_summary' in data:
            article.ai_summary = data['ai_summary']
        if 'ai_insights' in data:
            article.ai_insights = data['ai_insights']
        if 'ai_sentiment_rating' in data:
            article.ai_sentiment_rating = float(data['ai_sentiment_rating'])

        db.session.commit()
        return jsonify({'status': 'success'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating article {article_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/articles/view/<int:article_id>')
@admin_required
def view_article(article_id):
    """View article details"""
    try:
        article = NewsArticle.query.get_or_404(article_id)
        return render_template(
            'news/view_article.html',
            article=article
        )
    except Exception as e:
        logger.error(f"Error viewing article {article_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/articles/clear-content/<int:article_id>', methods=['POST'])
@admin_required
def clear_article_content(article_id):
    """Clear only article content, keep AI fields"""
    try:
        article = NewsArticle.query.get_or_404(article_id)
        article.content = None
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing article {article_id} content: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/articles/clear-all-content', methods=['POST'])
@admin_required
def clear_all_content():
    """Clear content from all articles but preserve AI fields"""
    try:
        # Get search parameter to maintain filter if exists
        search = request.args.get('search', '')
        query = NewsArticle.query

        if search:
            search = f"%{search}%"
            query = query.filter(NewsArticle.title.ilike(search))

        # Update all matching articles
        articles = query.all()
        count = 0
        for article in articles:
            if article.content is not None:
                article.content = None
                count += 1
            if article.sentiment_label is not None:
                article.sentiment_label = None
                count += 1
            if article.sentiment_score is not None:
                article.sentiment_score = None
                count += 1
            if article.sentiment_explanation is not None:
                article.sentiment_explanation = None
                count += 1
            if article.brief_summary is not None:
                article.brief_summary = None
                count += 1
            if article.key_points is not None:
                article.key_points = None
                count += 1
            if article.market_impact_summary is not None:
                article.market_impact_summary = None
                count += 1

        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'Cleared content from {count} articles'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing all content: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/articles/delete/<int:article_id>', methods=['POST'])
@admin_required
def delete_article(article_id):
    """Delete an article"""
    try:
        article = NewsArticle.query.get_or_404(article_id)
        db.session.delete(article)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting article {article_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/irregular-ai-content')
@login_required
@admin_required
def irregular_ai_content():
    """Display articles with irregular AI content for review and reprocessing"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # Find articles with potentially irregular AI processing
        query = NewsArticle.query.filter(
            db.or_(
                # Short or invalid content
                db.and_(NewsArticle.ai_summary.isnot(None), db.func.length(NewsArticle.ai_summary) < 100),
                db.and_(NewsArticle.ai_insights.isnot(None), db.func.length(NewsArticle.ai_insights) < 100),
                # Error markers in content
                db.and_(NewsArticle.ai_summary.isnot(None), NewsArticle.ai_summary.contains('error')),
                db.and_(NewsArticle.ai_insights.isnot(None), NewsArticle.ai_insights.contains('error')),
                # Summary contains placeholders left unchanged
                db.and_(NewsArticle.ai_summary.isnot(None), NewsArticle.ai_summary.contains('Keyword 1')),
                db.and_(NewsArticle.ai_insights.isnot(None), NewsArticle.ai_insights.contains('Insight 1'))
            ),
            NewsArticle.content.isnot(None)
        ).order_by(NewsArticle.id.desc())
        
        # Paginate results
        articles = query.paginate(page=page, per_page=per_page)
        
        return render_template(
            'news/irregular_ai_content.html',
            articles=articles
        )
        
    except Exception as e:
        logger.error(f"Error displaying irregular AI content: {str(e)}")
        return render_template(
            'news/irregular_ai_content.html',
            error=str(e),
            articles=None
        )

@bp.route('/api/reprocess-article/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def reprocess_article(article_id):
    """Reprocess AI content for a single article"""
    try:
        import requests
        
        # Get the article
        article = NewsArticle.query.get_or_404(article_id)
        
        if not article.content:
            return jsonify({
                'status': 'error',
                'message': 'Cannot reprocess article with no content'
            }), 400
        
        OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

        # Create OpenAI client for OpenRouter
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # Process summary
        summary_payload = {
            "model": "anthropic/claude-3.5-sonnet",  # Using Claude Sonnet 3.5 for AI processing
            "messages": [
                {
                    "role": "user",
                    "content": f"""Generate summary with STRICT markdown formatting:
**Key Concepts/Keywords**  
- Keyword 1  
- Keyword 2  

**Key Points**  
- Point 1  
- Point 2  

**Context**  
- Background 1  
- Background 2  

Use proper line breaks between list items. Article: {article.content}"""
                }
            ],
            "max_tokens": 500  # Standard limits for Claude Sonnet 3.5
        }
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "TrendWise AI Analysis"  # Optional. Site title for rankings on openrouter.ai.
            },
            model=summary_payload["model"],
            messages=summary_payload["messages"],
            max_tokens=summary_payload["max_tokens"]
        )
        ai_summary = completion.choices[0].message.content
        
        # Process insights
        insights_payload = {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {
                    "role": "user",
                    "content": f"""Generate insights with STRICT markdown formatting:
**Key Insights**  
- Insight 1  
- Insight 2  

**Market Implications**  
- Implication 1  
- Implication 2  

**Conclusion**  
- Brief conclusion  

Use proper line breaks between list items. Article: {article.content}"""
                }
            ],
            "max_tokens": 500  # Standard limits for Claude Sonnet 3.5
        }
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "TrendWise AI Analysis"  # Optional. Site title for rankings on openrouter.ai.
            },
            model=insights_payload["model"],
            messages=insights_payload["messages"],
            max_tokens=insights_payload["max_tokens"],
            temperature=insights_payload["temperature"],
            timeout=30
        )
        ai_insights = completion.choices[0].message.content
        
        # Process sentiment
        sentiment_payload = {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {
                    "role": "user",
                    "content": f"Analyze the market sentiment of this article and provide a single number rating from -100 (extremely bearish) to 100 (extremely bullish). Only return the number: {article.content}"
                }
            ],
            "max_tokens": 500  # Standard limits for Claude Sonnet 3.5
        }
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "TrendWise AI Analysis"  # Optional. Site title for rankings on openrouter.ai.
            },
            model=sentiment_payload["model"],
            messages=sentiment_payload["messages"],
            max_tokens=sentiment_payload["max_tokens"],
            temperature=sentiment_payload["temperature"],
            timeout=30
        )
        
        try:
            rating = int(completion.choices[0].message.content.strip())
            ai_sentiment_rating = max(min(rating, 100), -100)
        except ValueError:
            logger.error(f"Could not parse sentiment rating for article {article.id}")
            ai_sentiment_rating = 0
        
        # Calculate total content length to verify if processing was successful
        total_content = ai_summary + ai_insights + str(ai_sentiment_rating)
        
        if len(total_content) < 100:
            return jsonify({
                'status': 'error',
                'message': 'Generated AI content is too short - processing may have failed'
            }), 400
        
        # Update the article
        article.ai_summary = ai_summary
        article.ai_insights = ai_insights
        article.ai_sentiment_rating = ai_sentiment_rating
        
        # Save changes
        db.session.commit()
        
        # Return success
        return jsonify({
            'status': 'success',
            'message': 'Article successfully reprocessed',
            'article': {
                'id': article.id,
                'title': article.title,
                'ai_summary': article.ai_summary,
                'ai_insights': article.ai_insights,
                'ai_sentiment_rating': article.ai_sentiment_rating
            }
        })
        
    except Exception as e:
        logger.error(f"Error reprocessing article {article_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/check-articles-for-symbol/<symbol>')
@login_required
@admin_required
def check_articles_for_symbol(symbol):
    """Check articles for a specific symbol to see if any content or insights were fetched."""
    try:
        # Query articles related to the symbol
        articles = (NewsArticle.query
                   .join(ArticleSymbol)
                   .filter(ArticleSymbol.symbol == symbol)
                   .order_by(NewsArticle.published_at.desc())
                   .limit(10)
                   .all())
        
        if not articles:
            return jsonify({
                'symbol': symbol,
                'found': False,
                'message': f'No articles found for symbol {symbol}'
            })
        
        # Check content and insights status
        results = []
        for article in articles:
            results.append({
                'id': article.id,
                'title': article.title,
                'published_at': article.published_at.isoformat() if article.published_at else None,
                'has_content': bool(article.content and len(article.content.strip()) > 0),
                'content_length': len(article.content) if article.content else 0,
                'has_ai_summary': bool(article.ai_summary),
                'has_ai_insights': bool(article.ai_insights),
                'ai_sentiment_rating': article.ai_sentiment_rating,
                'url': article.url
            })
        
        return jsonify({
            'symbol': symbol,
            'found': True,
            'total_articles': len(articles),
            'articles': results
        })
        
    except Exception as e:
        logger.error(f"Error checking articles for symbol {symbol}: {str(e)}")
        return jsonify({
            'symbol': symbol,
            'found': False,
            'error': str(e)
        }), 500

# Scheduler management routes
@bp.route('/scheduler')
@login_required
@admin_required
def scheduler_status():
    """Display the automated scheduler management page"""
    return render_template('news/scheduler_status.html')

@bp.route('/api/scheduler/status')
@login_required
@admin_required
def get_scheduler_status():
    """Get the current status of the automated news AI scheduler"""
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        status = news_scheduler.get_status()
        
        # Add total count of ALL articles that need processing (not just the batch limit)
        with news_scheduler.get_db_session() as session:
            total_unprocessed_count = news_scheduler.get_total_unprocessed_count(session)
            status['unprocessed_articles_count'] = total_unprocessed_count
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/scheduler/start', methods=['POST'])
@login_required
@admin_required
def start_scheduler():
    """Start both AI processing and news fetch schedulers AND enable all news fetching"""
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        from app.utils.analysis.stock_news_service import StockNewsService
        
        # CRITICAL: Enable ALL news fetching activities globally
        StockNewsService.enable_news_fetching()
        
        # Start AI processing scheduler
        news_scheduler.start()
        
        # Start news fetch scheduler
        fetch_success = news_fetch_scheduler.start()
        
        messages = ['All news fetching activities enabled globally.']
        messages.append('AI processing scheduler started! Initial processing job is running now, then scheduled every 3 minutes.')
        
        if fetch_success:
            messages.append('News fetch scheduler started! Initial fetch job is running now, then scheduled every 6 hours.')
        else:
            messages.append('Warning: News fetch scheduler failed to start.')
        
        return jsonify({
            'success': True,
            'message': ' '.join(messages),
            'initial_run': True,
            'global_news_fetching_enabled': True,
            'ai_scheduler_started': True,
            'fetch_scheduler_started': fetch_success
        })
        
    except Exception as e:
        logger.error(f"Error starting schedulers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/scheduler/stop', methods=['POST'])
@login_required
@admin_required
def stop_scheduler():
    """Stop both AI processing and news fetch schedulers AND disable all news fetching"""
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        from app.utils.analysis.stock_news_service import StockNewsService
        
        # Stop AI processing scheduler
        news_scheduler.stop()
        
        # Stop news fetch scheduler
        fetch_success = news_fetch_scheduler.stop()
        
        # CRITICAL: Disable ALL news fetching activities globally
        StockNewsService.disable_news_fetching()
        
        messages = ['AI processing scheduler stopped successfully.']
        
        if fetch_success:
            messages.append('News fetch scheduler stopped successfully.')
        else:
            messages.append('Warning: News fetch scheduler failed to stop.')
            
        messages.append('All news fetching activities disabled globally.')
        
        return jsonify({
            'success': True,
            'message': ' '.join(messages),
            'ai_scheduler_stopped': True,
            'fetch_scheduler_stopped': fetch_success,
            'global_news_fetching_disabled': True
        })
        
    except Exception as e:
        logger.error(f"Error stopping schedulers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/scheduler/run-now', methods=['POST'])
@login_required
@admin_required
def run_scheduler_now():
    """Manually trigger the scheduler to run immediately"""
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        
        # Run the processing job in a background thread to avoid blocking the request
        import threading
        
        def run_job():
            try:
                news_scheduler.run_processing_job()
            except Exception as e:
                logger.error(f"Error in manual scheduler run: {str(e)}")
        
        thread = threading.Thread(target=run_job, daemon=False, name="ManualAIProcessing")
        thread.start()
        
        logger.info(f"Manual AI processing job thread started: {thread.name}, daemon={thread.daemon}")
        
        return jsonify({
            'success': True,
            'message': 'Processing job started in background'
        })
        
    except Exception as e:
        logger.error(f"Error manually running scheduler: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/scheduler/start-ai-only', methods=['POST'])
@login_required
@admin_required
def start_ai_scheduler_only():
    """Start only the AI processing scheduler (not news fetch)"""
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        from app.utils.analysis.stock_news_service import StockNewsService
        
        # Enable news fetching globally (required for AI processing to work)
        StockNewsService.enable_news_fetching()
        
        # Start only AI processing scheduler
        news_scheduler.start()
        
        return jsonify({
            'success': True,
            'message': 'AI processing scheduler started! Initial processing job is running now, then scheduled every 3 minutes.',
            'initial_run': True,
            'ai_scheduler_started': True,
            'news_fetching_enabled': True
        })
        
    except Exception as e:
        logger.error(f"Error starting AI scheduler only: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/scheduler/stop-ai-only', methods=['POST'])
@login_required
@admin_required
def stop_ai_scheduler_only():
    """Stop only the AI processing scheduler (leave news fetch running if active)"""
    try:
        from app.utils.scheduler.news_scheduler import news_scheduler
        
        # Stop only AI processing scheduler
        news_scheduler.stop()
        
        return jsonify({
            'success': True,
            'message': 'AI processing scheduler stopped successfully. News fetch scheduler remains unchanged.',
            'ai_scheduler_stopped': True
        })
        
    except Exception as e:
        logger.error(f"Error stopping AI scheduler only: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== NEWS FETCH SCHEDULER ROUTES =====

@bp.route('/fetch-scheduler')
@login_required
@admin_required
def fetch_scheduler_status():
    """News fetch scheduler status page"""
    return render_template('news/fetch_scheduler_status.html')

@bp.route('/api/fetch-scheduler/start', methods=['POST'])
@login_required
@admin_required
def start_fetch_scheduler():
    """Start the automated news fetch scheduler"""
    try:
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        
        success = news_fetch_scheduler.start()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'News fetch scheduler started! Initial fetch job is running now, then scheduled every 6 hours.',
                'initial_run': True,
                'scheduler_status': news_fetch_scheduler.get_status()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to start news fetch scheduler'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting fetch scheduler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fetch-scheduler/stop', methods=['POST'])
@login_required
@admin_required
def stop_fetch_scheduler():
    """Stop the automated news fetch scheduler"""
    try:
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        
        success = news_fetch_scheduler.stop()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'News fetch scheduler stopped successfully',
                'scheduler_status': news_fetch_scheduler.get_status()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to stop news fetch scheduler'
            }), 500
            
    except Exception as e:
        logger.error(f"Error stopping fetch scheduler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fetch-scheduler/status', methods=['GET'])
@login_required
@admin_required
def get_fetch_scheduler_status():
    """Get the current status of the news fetch scheduler"""
    try:
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        
        status = news_fetch_scheduler.get_status()
        
        return jsonify({
            'status': 'success',
            'scheduler_status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting fetch scheduler status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fetch-scheduler/run-now', methods=['POST'])
@login_required
@admin_required
def run_fetch_scheduler_now():
    """Manually trigger the news fetch job immediately with intelligent time-based market selection"""
    try:
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        
        # Get market session from request or use intelligent auto-selection
        data = request.get_json() or {}
        market_session = data.get('market_session', 'auto')  # Default to intelligent selection
        
        # Run the job with intelligent market session selection
        result = news_fetch_scheduler.run_now(market_session=market_session)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'market_session': result['market_session'],
                'total_symbols': result['total_symbols'],
                'time_based_selection': result.get('time_based_selection', False),
                'estimated_duration': f"{result['total_symbols'] * 1.5:.0f} seconds"
            })
        else:
            return jsonify({
                'status': 'error',
                'error': result['error']
            }), 500
        
    except Exception as e:
        logger.error(f"Error manually running fetch scheduler: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/api/fetch-scheduler/progress', methods=['GET'])
@login_required
@admin_required
def get_fetch_scheduler_progress():
    """Get current progress of the news fetch job"""
    try:
        from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
        
        progress = news_fetch_scheduler.get_progress()
        
        return jsonify({
            'status': 'success',
            'progress': progress
        })
        
    except Exception as e:
        logger.error(f"Error getting fetch scheduler progress: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/api/optimization/status', methods=['GET'])
@login_required
def get_optimization_status():
    """Get current news optimization status and statistics"""
    try:
        from app.utils.analysis.stock_news_service import StockNewsService, NewsOptimizationConfig
        
        # Get basic status
        status = {
            'news_fetching_enabled': StockNewsService.is_news_fetching_enabled(),
            'smart_thresholds_available': True,
            'cache_available': False
        }
        
        # Check cache availability
        from app.utils.cache.news_cache import NewsCache
        cache = NewsCache()
        status['cache_available'] = cache.is_available()
        
        # Get configuration details
        config = {
            'default_thresholds': {
                'recent_news_threshold': NewsOptimizationConfig.RECENT_NEWS_THRESHOLD,
                'stale_news_threshold': NewsOptimizationConfig.STALE_NEWS_THRESHOLD,
                'minimal_news_threshold': NewsOptimizationConfig.MINIMAL_NEWS_THRESHOLD
            },
            'high_frequency_stocks': list(NewsOptimizationConfig.HIGH_FREQUENCY_STOCKS),
            'cache_duration': NewsOptimizationConfig.NEWS_CHECK_CACHE_DURATION
        }
        
        # Get optimization stats for recent analysis
        recent_symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else None
        if recent_symbols and recent_symbols != ['']:
            stats = StockNewsService.get_news_optimization_stats(recent_symbols)
        else:
            stats = StockNewsService.get_news_optimization_stats()
        
        return jsonify({
            'status': 'success',
            'data': {
                'system_status': status,
                'configuration': config,
                'optimization_stats': stats,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting optimization status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get optimization status: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/optimization/clear-cache', methods=['POST'])
@login_required
def clear_optimization_cache():
    """Clear news optimization cache"""
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol')  # Optional: clear for specific symbol
        
        from app.utils.analysis.stock_news_service import StockNewsService
        StockNewsService.clear_news_check_cache(symbol)
        
        return jsonify({
            'status': 'success',
            'message': f'Cache cleared for {symbol if symbol else "all symbols"}',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear cache: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/optimization/check-symbol', methods=['POST'])
@login_required
def check_symbol_optimization():
    """Check news optimization status for a specific symbol"""
    try:
        data = request.get_json()
        if not data or not data.get('symbol'):
            return jsonify({
                'status': 'error',
                'message': 'Symbol is required'
            }), HTTPStatus.BAD_REQUEST
        
        symbol = data['symbol']
        use_smart_thresholds = data.get('use_smart_thresholds', True)
        hours_threshold = data.get('hours_threshold')
        force_check = data.get('force_check', False)
        
        from app.utils.analysis.stock_news_service import StockNewsService
        
        # NEW: Check if symbol is in automated 346 symbols scheduler
        scheduler_check = StockNewsService._check_if_symbol_in_scheduler(symbol)
        
        # Check news status (only if not in scheduler)
        news_status = StockNewsService.check_recent_news_status(
            symbol=symbol,
            hours_threshold=hours_threshold,
            use_smart_thresholds=use_smart_thresholds
        )
        
        # Check daily fetch allowance (only relevant for non-scheduler symbols)
        fetch_allowance = {'allow_fetch': True, 'reason': 'in_scheduler'}
        if not scheduler_check['in_scheduler']:
            fetch_allowance = StockNewsService.check_daily_fetch_allowance(symbol)
        
        # Get fetch record stats (only relevant for non-scheduler symbols)
        fetch_stats = StockNewsService.get_fetch_record_stats(symbol)
        
        # Run the full auto-check to see what would happen
        auto_check_result = StockNewsService.auto_check_and_fetch_news(
            symbol=symbol, 
            force_check=force_check, 
            use_smart_thresholds=use_smart_thresholds
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'symbol': symbol,
                'scheduler_check': scheduler_check,
                'news_status': news_status,
                'fetch_allowance': fetch_allowance,
                'fetch_stats': fetch_stats,
                'auto_check_result': auto_check_result,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking symbol optimization: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to check symbol: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/optimization/check-scheduler-symbol', methods=['POST'])
@login_required
def check_scheduler_symbol():
    """Check if a symbol is in the automated 346 symbols list"""
    try:
        data = request.get_json()
        if not data or not data.get('symbol'):
            return jsonify({
                'status': 'error',
                'message': 'Symbol is required'
            }), HTTPStatus.BAD_REQUEST
            
        symbol = data['symbol']
        
        from app.utils.analysis.stock_news_service import StockNewsService
        
        # Check if symbol is in automated scheduler
        scheduler_check = StockNewsService._check_if_symbol_in_scheduler(symbol)
        
        return jsonify({
            'status': 'success',
            'data': {
                'symbol': symbol,
                'scheduler_check': scheduler_check,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking scheduler symbol: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to check scheduler symbol: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/fetch-records/<symbol>', methods=['GET'])
@login_required
def get_fetch_records(symbol):
    """Get fetch record statistics for a symbol"""
    try:
        date = request.args.get('date')  # Optional date parameter
        
        from app.utils.analysis.stock_news_service import StockNewsService
        stats = StockNewsService.get_fetch_record_stats(symbol, date)
        
        return jsonify({
            'status': 'success',
            'data': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting fetch records: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get fetch records: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/fetch-records/<symbol>', methods=['DELETE'])
@login_required
def clear_fetch_records(symbol):
    """Clear fetch records for a symbol"""
    try:
        data = request.get_json() or {}
        date = data.get('date')  # Optional date parameter
        
        from app.utils.analysis.stock_news_service import StockNewsService
        success = StockNewsService.clear_fetch_record(symbol, date)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Fetch records cleared for {symbol}',
                'symbol': symbol,
                'date': date,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to clear fetch records'
            }), HTTPStatus.INTERNAL_SERVER_ERROR
        
    except Exception as e:
        logger.error(f"Error clearing fetch records: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear fetch records: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/fetch-allowance/<symbol>', methods=['GET'])
@login_required
def check_fetch_allowance(symbol):
    """Check if a symbol is allowed to be fetched today"""
    try:
        from app.utils.analysis.stock_news_service import StockNewsService
        allowance = StockNewsService.check_daily_fetch_allowance(symbol)
        
        return jsonify({
            'status': 'success',
            'data': {
                'symbol': symbol,
                'allowance': allowance,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking fetch allowance: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to check fetch allowance: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@bp.route('/api/search', methods=['GET', 'POST'])
@login_required
def api_search():
    """API endpoint for advanced news search with JSON response"""
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            search_query = data.get('q', '').strip()
            symbols = data.get('symbols', [])
            keywords = data.get('keywords', [])
            search_type = data.get('search_type', 'auto')  # auto, symbol, keyword, mixed
        else:
            search_query = request.args.get('q', '').strip()
            symbols = request.args.getlist('symbols') or []
            keywords = request.args.getlist('keywords') or []
            search_type = request.args.get('search_type', 'auto')
        
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(50, int(request.args.get('per_page', 20)))
        
        logger.info(f"API Search - Query: '{search_query}', Symbols: {symbols}, Keywords: {keywords}, Type: {search_type}")
        
        # Initialize search
        from app.utils.search.optimized_news_search import OptimizedNewsSearch
        optimized_search = OptimizedNewsSearch(db.session)
        
        # Auto-determine search type if not specified
        if search_type == 'auto':
            if symbols and keywords:
                search_type = 'mixed'
            elif keywords:
                search_type = 'keyword'
            elif symbols:
                search_type = 'symbol'
            elif search_query:
                # Parse search query to determine type
                query_parts = search_query.split()
                has_symbols = any(_is_likely_symbol(part) for part in query_parts)
                has_keywords = any(not _is_likely_symbol(part) for part in query_parts)
                
                if has_symbols and has_keywords:
                    search_type = 'mixed'
                elif has_keywords:
                    search_type = 'keyword'
                else:
                    search_type = 'symbol'
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'No search terms provided'
                }), 400
        
        # ⚡ STANDALONE AI SEARCH: All data available without joins
        if search_type == 'keyword':
            search_keywords = keywords or search_query.split()
            # Check if "latest" keyword was used for 3-day filtering
            has_latest = any(kw.lower() == 'latest' for kw in search_keywords)
            articles, total_count, has_more = optimized_search.search_by_keywords(
                keywords=search_keywords,
                sentiment_filter=request.args.get('sentiment'),
                sort_order=request.args.get('sort', 'LATEST'),
                date_filter=request.args.get('date'),
                page=page,
                per_page=per_page,
                force_latest_filter=has_latest
            )
            
        elif search_type == 'symbol':
            search_symbols = symbols or [part for part in search_query.split() if _is_likely_symbol(part)]
            articles, total_count, has_more = optimized_search.search_by_symbols(
                symbols=search_symbols,
                sentiment_filter=request.args.get('sentiment'),
                sort_order=request.args.get('sort', 'LATEST'),
                date_filter=request.args.get('date'),
                region_filter=request.args.get('region'),
                processing_filter=request.args.get('processing', 'all'),
                page=page,
                per_page=per_page
            )
            
        elif search_type == 'mixed':
            # Extract symbols and keywords from query if not provided
            if search_query and not symbols and not keywords:
                query_parts = search_query.split()
                symbols = [part for part in query_parts if _is_likely_symbol(part)]
                keywords = [part for part in query_parts if not _is_likely_symbol(part)]
            
            # 🚀 OPTIMIZED MIXED SEARCH: Use advanced_search for better performance
            articles, total_count = optimized_search.advanced_search(
                keywords=keywords if keywords else None,
                symbols=symbols if symbols else None,
                sentiment=request.args.get('sentiment'),
                start_date=request.args.get('start_date'),
                end_date=request.args.get('end_date'),
                sources=request.args.getlist('sources') if request.args.getlist('sources') else None,
                page=page,
                per_page=per_page
            )
            has_more = len(articles) >= per_page
            
        else:
            return jsonify({
                'status': 'error',
                'message': f'Invalid search type: {search_type}'
            }), 400
        
        return jsonify({
            'status': 'success',
            'data': {
                'articles': articles,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'has_more': has_more,
                    'pages': (total_count + per_page - 1) // per_page if total_count else 1
                },
                'search_info': {
                    'query': search_query,
                    'symbols': symbols,
                    'keywords': keywords,
                    'type': search_type,
                    'total_results': total_count
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in API search: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Search failed. Please try again.'
        }), 500

@bp.route('/api/enhanced-search', methods=['GET'])
@login_required
def api_enhanced_search():
    """Enhanced search API with acronym expansion and relevance scoring"""
    try:
        from app.utils.search.acronym_expansion import acronym_expansion_service
        
        query = request.args.get('q', '').strip()
        limit = min(50, int(request.args.get('limit', 20)))
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Search query is required'
            }), 400
        
        # Get expanded search results
        results = acronym_expansion_service.get_expanded_search_results(query, limit)
        
        # Get expansion details
        expansion_info = acronym_expansion_service.expand_query(query)
        
        logger.info(f"Enhanced search for '{query}': {len(results)} results, "
                   f"expanded to: {expansion_info['expanded']}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'query': query,
                'results': results,
                'expansion_info': expansion_info,
                'total_results': len(results)
            }
        })
        
    except Exception as e:
        logger.error(f"Enhanced search API error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Enhanced search failed'
        }), 500

@bp.route('/api/suggestions', methods=['GET'])
def api_search_suggestions():
    """
    Get intelligent search suggestions based on user input.
    
    Query Parameters:
    - q: Search query (required)
    - limit: Maximum number of suggestions (default: 10)
    - user_id: User ID for personalization (optional)
    - session_id: Session ID for tracking (optional)
    - context: Include context information (default: true)
    
    Returns:
    JSON response with suggestions and metadata
    """
    try:
        from app.utils.search.intelligent_suggestions import intelligent_suggestion_service
        
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        user_id = request.args.get('user_id')
        session_id = request.args.get('session_id')
        include_context = request.args.get('context', 'true').lower() == 'true'
        
        # Convert user_id to int if provided
        if user_id:
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = None
        
        # Get suggestions
        suggestions = intelligent_suggestion_service.get_search_suggestions(
            query=query,
            user_id=user_id,
            session_id=session_id,
            limit=limit,
            include_context=include_context
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'query': query,
                'suggestions': suggestions,
                'count': len(suggestions)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in search suggestions API: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get search suggestions'
        }), 500


@bp.route('/api/suggestions/click', methods=['POST'])
def api_suggestion_click():
    """
    Track when a user clicks on a search suggestion.
    
    Request Body:
    - query: Original search query
    - selected_suggestion: The suggestion that was clicked
    - user_id: User ID (optional)
    - session_id: Session ID (optional)
    
    Returns:
    JSON response confirming the tracking
    """
    try:
        from app.utils.search.intelligent_suggestions import intelligent_suggestion_service
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'JSON data required'
            }), 400
        
        query = data.get('query', '')
        selected_suggestion = data.get('selected_suggestion', '')
        user_id = data.get('user_id')
        session_id = data.get('session_id')
        
        if not query or not selected_suggestion:
            return jsonify({
                'status': 'error',
                'message': 'Query and selected_suggestion are required'
            }), 400
        
        # Convert user_id to int if provided
        if user_id:
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = None
        
        # Track the click
        intelligent_suggestion_service.track_suggestion_click(
            query=query,
            selected_suggestion=selected_suggestion,
            user_id=user_id,
            session_id=session_id
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Suggestion click tracked successfully'
        })
        
    except Exception as e:
        logger.error(f"Error tracking suggestion click: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to track suggestion click'
        }), 500


@bp.route('/api/keywords/extract', methods=['POST'])
def api_extract_keywords():
    """
    Extract keywords from a batch of articles.
    
    Request Body:
    - limit: Number of articles to process (default: 100)
    - skip_processed: Skip already processed articles (default: true)
    
    Returns:
    JSON response with extraction statistics
    """
    try:
        from app.utils.ai.keyword_extraction_service import keyword_extraction_service
        
        data = request.get_json() or {}
        limit = data.get('limit', 100)
        skip_processed = data.get('skip_processed', True)
        
        # Process articles
        stats = keyword_extraction_service.process_articles_batch(
            limit=limit,
            skip_processed=skip_processed
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'extraction_stats': stats,
                'message': f"Processed {stats['processed']} articles, extracted {stats['keywords_extracted']} keywords"
            }
        })
        
    except Exception as e:
        logger.error(f"Error in keyword extraction API: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to extract keywords'
        }), 500


@bp.route('/api/keywords/trending', methods=['GET'])
def api_trending_keywords():
    """
    Get trending keywords from recent articles.
    
    Query Parameters:
    - days: Number of days to look back (default: 7)
    - limit: Maximum number of keywords (default: 20)
    
    Returns:
    JSON response with trending keywords
    """
    try:
        from app.utils.ai.keyword_extraction_service import keyword_extraction_service
        
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 20))
        
        trending_keywords = keyword_extraction_service.get_trending_keywords(
            days=days,
            limit=limit
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'trending_keywords': trending_keywords,
                'period_days': days,
                'count': len(trending_keywords)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting trending keywords: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get trending keywords'
        }), 500


@bp.route('/api/analytics/suggestions', methods=['GET'])
def api_suggestion_analytics():
    """
    Get analytics about suggestion usage.
    
    Query Parameters:
    - days: Number of days to analyze (default: 30)
    - limit: Maximum number of results (default: 50)
    
    Returns:
    JSON response with suggestion analytics
    """
    try:
        from app.utils.search.intelligent_suggestions import intelligent_suggestion_service
        
        days = int(request.args.get('days', 30))
        limit = int(request.args.get('limit', 50))
        
        analytics = intelligent_suggestion_service.get_suggestion_analytics(
            days=days,
            limit=limit
        )
        
        return jsonify({
            'status': 'success',
            'data': analytics
        })
        
    except Exception as e:
        logger.error(f"Error getting suggestion analytics: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get suggestion analytics'
        }), 500

@bp.route('/api/search-suggestions', methods=['POST'])
@login_required
def api_ai_search_suggestions():
    """
    Generate AI-powered search suggestions for empty search results.
    Returns a list of intelligent suggestions with different categories.
    """
    try:
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({
                'status': 'error',
                'message': 'Query is required'
            }), 400
        
        query = data['query'].strip()
        suggestions = _generate_ai_search_suggestions(query)
        
        return jsonify({
            'status': 'success',
            'data': {
                'query': query,
                'suggestions': suggestions,
                'total': len(suggestions)
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating AI search suggestions: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate suggestions'
        }), 500

@bp.route('/snapshot')
@login_required
def analysis_snapshot():
    """Analysis snapshot page with interactive Plotly charts"""
    try:
        # Get filter parameters
        days = min(int(request.args.get('days', 30)), 90)  # Cap at 90 days
        symbol = request.args.get('symbol', 'all')
        region = request.args.get('region', 'all')
        
        # Generate analytics data for charts
        analytics_data = _generate_analytics_data(days, symbol, region)
        
        return render_template(
            'news/analysis_snapshot.html',
            analytics_data=analytics_data,
            days=days,
            symbol=symbol,
            region=region
        )
        
    except Exception as e:
        logger.error(f"Error rendering analysis snapshot: {str(e)}")
        return render_template(
            'news/analysis_snapshot.html',
            error=str(e),
            analytics_data={},
            days=30,
            symbol='all',
            region='all'
        )

@bp.route('/api/analytics-data', methods=['GET'])
@login_required  
def api_analytics_data():
    """API endpoint for analytics data used by Plotly charts"""
    try:
        days = min(int(request.args.get('days', 30)), 90)
        symbol = request.args.get('symbol', 'all')
        region = request.args.get('region', 'all')
        chart_type = request.args.get('chart_type', 'all')
        
        analytics_data = _generate_analytics_data(days, symbol, region, chart_type)
        
        return jsonify({
            'status': 'success',
            'data': analytics_data
        })
        
    except Exception as e:
        logger.error(f"Error generating analytics data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def _generate_analytics_data(days, symbol='all', region='all', chart_type='all'):
    """Generate comprehensive analytics data for Plotly charts"""
    try:
        from datetime import datetime, timedelta
        import pandas as pd
        import plotly.graph_objects as go
        import plotly.express as px
        from plotly.subplots import make_subplots
        import json
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Initialize data structure
        analytics = {
            'sentiment_timeline': None,
            'top_symbols': None,
            'article_volume': None,
            'sentiment_distribution': None,
            'regional_analysis': None,
            'keyword_trends': None,
            'summary_stats': {}
        }
        
        # Base query for articles in date range
        base_query = NewsArticle.query.filter(
            NewsArticle.published_at >= start_date,
            NewsArticle.published_at <= end_date
        )
        
        # Apply symbol filter
        if symbol != 'all':
            base_query = base_query.join(ArticleSymbol).filter(
                ArticleSymbol.symbol.ilike(f'%{symbol}%')
            )
        
        articles = base_query.all()
        
        if not articles:
            return analytics
        
        # Generate summary statistics
        analytics['summary_stats'] = {
            'total_articles': len(articles),
            'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'symbol_filter': symbol,
            'region_filter': region,
            'avg_sentiment': sum(a.ai_sentiment_rating for a in articles if a.ai_sentiment_rating is not None) / max(1, len([a for a in articles if a.ai_sentiment_rating is not None]))
        }
        
        # 1. Sentiment Timeline Chart
        if chart_type in ['all', 'sentiment_timeline']:
            sentiment_data = []
            current_date = start_date
            
            while current_date <= end_date:
                day_articles = [a for a in articles if a.published_at.date() == current_date.date()]
                day_sentiments = [a.ai_sentiment_rating for a in day_articles if a.ai_sentiment_rating is not None]
                
                if day_sentiments:
                    avg_sentiment = sum(day_sentiments) / len(day_sentiments)
                    sentiment_data.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'sentiment': avg_sentiment,
                        'article_count': len(day_articles),
                        'positive_count': len([s for s in day_sentiments if s > 20]),
                        'neutral_count': len([s for s in day_sentiments if -20 <= s <= 20]),
                        'negative_count': len([s for s in day_sentiments if s < -20])
                    })
                else:
                    sentiment_data.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'sentiment': 0,
                        'article_count': 0,
                        'positive_count': 0,
                        'neutral_count': 0,
                        'negative_count': 0
                    })
                
                current_date += timedelta(days=1)
            
            # Create sentiment timeline chart
            fig = go.Figure()
            
            dates = [d['date'] for d in sentiment_data]
            sentiments = [d['sentiment'] for d in sentiment_data]
            article_counts = [d['article_count'] for d in sentiment_data]
            
            # Add sentiment line
            fig.add_trace(go.Scatter(
                x=dates,
                y=sentiments,
                mode='lines+markers',
                name='Average Sentiment',
                line=dict(color='#667eea', width=3),
                marker=dict(size=8, color='#667eea'),
                hovertemplate='<b>%{x}</b><br>Sentiment: %{y:.1f}<br><extra></extra>'
            ))
            
            # Add article volume as secondary y-axis
            fig.add_trace(go.Bar(
                x=dates,
                y=article_counts,
                name='Article Volume',
                yaxis='y2',
                opacity=0.3,
                marker_color='#f093fb',
                hovertemplate='<b>%{x}</b><br>Articles: %{y}<br><extra></extra>'
            ))
            
            fig.update_layout(
                title=dict(
                    text=f'Sentiment Timeline - Last {days} Days',
                    x=0.5,
                    font=dict(size=20, family='Inter, sans-serif')
                ),
                xaxis=dict(
                    title='Date',
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.1)'
                ),
                yaxis=dict(
                    title='Average Sentiment',
                    range=[-100, 100],
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.1)'
                ),
                yaxis2=dict(
                    title='Article Count',
                    overlaying='y',
                    side='right',
                    showgrid=False
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, sans-serif'),
                hovermode='x unified',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            analytics['sentiment_timeline'] = json.loads(fig.to_json())
        
        # 2. Top Symbols Chart
        if chart_type in ['all', 'top_symbols']:
            symbol_counts = {}
            symbol_sentiments = {}
            
            for article in articles:
                if hasattr(article, 'symbols') and article.symbols:
                    for symbol in article.symbols:
                        symbol_name = symbol.symbol if hasattr(symbol, 'symbol') else str(symbol)
                        if symbol_name not in symbol_counts:
                            symbol_counts[symbol_name] = 0
                            symbol_sentiments[symbol_name] = []
                        
                        symbol_counts[symbol_name] += 1
                        if article.ai_sentiment_rating is not None:
                            symbol_sentiments[symbol_name].append(article.ai_sentiment_rating)
            
            # Get top 20 symbols by article count
            top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:20]
            
            if top_symbols:
                symbols = [s[0] for s in top_symbols]
                counts = [s[1] for s in top_symbols]
                avg_sentiments = []
                
                for symbol in symbols:
                    if symbol_sentiments[symbol]:
                        avg_sentiment = sum(symbol_sentiments[symbol]) / len(symbol_sentiments[symbol])
                    else:
                        avg_sentiment = 0
                    avg_sentiments.append(avg_sentiment)
                
                # Create color scale based on sentiment
                colors = []
                for sentiment in avg_sentiments:
                    if sentiment > 20:
                        colors.append('#22C55E')  # Green for positive
                    elif sentiment < -20:
                        colors.append('#EF4444')  # Red for negative
                    else:
                        colors.append('#6B7280')  # Gray for neutral
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=symbols,
                        y=counts,
                        marker_color=colors,
                        hovertemplate='<b>%{x}</b><br>Articles: %{y}<br>Avg Sentiment: %{customdata:.1f}<br><extra></extra>',
                        customdata=avg_sentiments
                    )
                ])
                
                fig.update_layout(
                    title=dict(
                        text=f'Top Symbols by Article Volume',
                        x=0.5,
                        font=dict(size=20, family='Inter, sans-serif')
                    ),
                    xaxis=dict(
                        title='Symbol',
                        tickangle=45,
                        showgrid=False
                    ),
                    yaxis=dict(
                        title='Article Count',
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.1)'
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Inter, sans-serif')
                )
                
                analytics['top_symbols'] = json.loads(fig.to_json())
        
        # 3. Article Volume by Hour
        if chart_type in ['all', 'article_volume']:
            hourly_counts = {}
            for hour in range(24):
                hourly_counts[hour] = 0
            
            for article in articles:
                if article.published_at:
                    hour = article.published_at.hour
                    hourly_counts[hour] += 1
            
            hours = list(range(24))
            counts = [hourly_counts[h] for h in hours]
            hour_labels = [f"{h:02d}:00" for h in hours]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=hour_labels,
                    y=counts,
                    marker_color='#4facfe',
                    hovertemplate='<b>%{x}</b><br>Articles: %{y}<br><extra></extra>'
                )
            ])
            
            fig.update_layout(
                title=dict(
                    text='Article Volume by Hour of Day',
                    x=0.5,
                    font=dict(size=20, family='Inter, sans-serif')
                ),
                xaxis=dict(
                    title='Hour of Day',
                    showgrid=False
                ),
                yaxis=dict(
                    title='Article Count',
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.1)'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, sans-serif')
            )
            
            analytics['article_volume'] = json.loads(fig.to_json())
        
        # 4. Sentiment Distribution Pie Chart
        if chart_type in ['all', 'sentiment_distribution']:
            sentiments = [a.ai_sentiment_rating for a in articles if a.ai_sentiment_rating is not None]
            
            if sentiments:
                positive_count = len([s for s in sentiments if s > 20])
                neutral_count = len([s for s in sentiments if -20 <= s <= 20])
                negative_count = len([s for s in sentiments if s < -20])
                
                fig = go.Figure(data=[
                    go.Pie(
                        labels=['Positive', 'Neutral', 'Negative'],
                        values=[positive_count, neutral_count, negative_count],
                        marker=dict(colors=['#22C55E', '#6B7280', '#EF4444']),
                        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<br><extra></extra>'
                    )
                ])
                
                fig.update_layout(
                    title=dict(
                        text='Sentiment Distribution',
                        x=0.5,
                        font=dict(size=20, family='Inter, sans-serif')
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Inter, sans-serif'),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.1,
                        xanchor="center",
                        x=0.5
                    )
                )
                
                analytics['sentiment_distribution'] = json.loads(fig.to_json())
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error in _generate_analytics_data: {str(e)}")
        return {}

def _generate_ai_search_suggestions(query):
    """Generate AI-powered search suggestions for a query that returned no results"""
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.warning("OpenRouter API key not available for search suggestions")
            return _get_fallback_suggestions(query)
        
        # Create OpenAI client for OpenRouter
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        prompt = f"""The user searched for "{query}" in a financial news database but got no results. 

Generate 5-8 alternative search terms that are more likely to find relevant financial news articles. Consider:
- Synonyms and related financial terms
- Company symbols vs company names
- Industry sectors and categories
- Financial events and terminology
- Broader or more specific terms

Return ONLY a JSON array of suggestions with this format:
[
    {{"term": "alternative search term", "type": "synonym", "reason": "brief explanation"}},
    {{"term": "another term", "type": "symbol", "reason": "brief explanation"}}
]

Types should be: "synonym", "symbol", "industry", "broader", "specific", "related"

Original query: "{query}"
"""
        
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",
                "X-Title": "TrendWise Search Suggestions"
            },
            model="anthropic/claude-3.5-sonnet",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7,
            timeout=15
        )
        
        content = completion.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            import json
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                suggestions = json.loads(json_str)
                
                # Validate and clean suggestions
                valid_suggestions = []
                for suggestion in suggestions:
                    if isinstance(suggestion, dict) and 'term' in suggestion:
                        valid_suggestions.append({
                            'term': suggestion['term'].strip(),
                            'type': suggestion.get('type', 'related'),
                            'reason': suggestion.get('reason', 'Alternative search term')
                        })
                
                if valid_suggestions:
                    logger.info(f"Generated {len(valid_suggestions)} AI suggestions for query: {query}")
                    return valid_suggestions
                    
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse AI suggestions response: {str(e)}")
        
        # Fallback to manual suggestions if AI parsing fails
        return _get_fallback_suggestions(query)
        
    except Exception as e:
        logger.warning(f"AI suggestion generation failed: {str(e)}")
        return _get_fallback_suggestions(query)

def _get_fallback_suggestions(query):
    """Generate fallback search suggestions using rule-based logic"""
    suggestions = []
    query_lower = query.lower()
    
    # Financial term mappings
    financial_mappings = {
        'ai': ['artificial intelligence', 'machine learning', 'technology', 'NVDA', 'GOOGL'],
        'artificial intelligence': ['ai', 'machine learning', 'tech stocks', 'automation'],
        'electric vehicle': ['EV', 'TSLA', 'automotive', 'clean energy'], 
        'ev': ['electric vehicle', 'TSLA', 'automotive', 'battery'],
        'crypto': ['cryptocurrency', 'bitcoin', 'blockchain', 'MSTR'],
        'bitcoin': ['cryptocurrency', 'crypto', 'digital currency', 'BTC'],
        'earnings': ['quarterly results', 'financial results', 'profit', 'revenue'],
        'merger': ['acquisition', 'M&A', 'takeover', 'deal'],
        'ipo': ['initial public offering', 'new listing', 'public offering'],
        'dividend': ['yield', 'payout', 'distribution', 'income'],
        'oil': ['energy', 'petroleum', 'crude', 'XOM', 'CVX'],
        'gold': ['precious metals', 'commodities', 'GLD', 'mining'],
        'china': ['chinese stocks', 'asia', 'emerging markets', 'BABA'],
        'fed': ['federal reserve', 'interest rates', 'monetary policy', 'FOMC'],
        'inflation': ['CPI', 'price increase', 'economic data', 'monetary policy']
    }
    
    # Check for direct mappings
    for key, alternatives in financial_mappings.items():
        if key in query_lower:
            for alt in alternatives:
                suggestions.append({
                    'term': alt,
                    'type': 'related',
                    'reason': f'Related to {key}'
                })
            break
    
    # Add broader search suggestions
    broader_terms = ['earnings', 'market news', 'financial results', 'stock analysis']
    for term in broader_terms:
        if term.lower() not in query_lower:
            suggestions.append({
                'term': term,
                'type': 'broader',
                'reason': 'Broader financial topic'
            })
    
    # Add popular symbols if query might be a company name
    if len(query.split()) <= 3 and not any(char.isdigit() for char in query):
        popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']
        for symbol in popular_symbols[:3]:
            suggestions.append({
                'term': symbol,
                'type': 'symbol',
                'reason': 'Popular stock symbol'
            })
    
    return suggestions[:6]  # Limit to 6 suggestions