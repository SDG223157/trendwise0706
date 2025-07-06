from time import sleep
from random import random
from flask import Blueprint, render_template, request, make_response, jsonify, redirect, url_for, flash
from datetime import datetime
import yfinance as yf
import logging
import sys
import re
import os
import traceback
from flask_login import login_required, current_user
from app.utils.analyzer.stock_analyzer import create_stock_visualization, create_stock_visualization_old
import pandas as pd
from app.utils.analysis.stock_news_service import StockNewsService
from sqlalchemy import inspect
from app import db
from sqlalchemy import text
from flask import send_file
import pandas as pd
import io
from functools import wraps
from flask import abort
from datetime import datetime, timedelta
from app.utils.data.data_service import DataService, RateLimiter
 
import random  # Make sure this is imported
from time import sleep
from datetime import datetime, timedelta
from sqlalchemy import inspect
import traceback
import threading
import queue
import json
from app.utils.config.analyze_config import ANALYZE_CONFIG
# from flask_login import current_user

# StockNewsService is now used as a static class (no instance needed)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create Blueprint
bp = Blueprint('main', __name__)

# Add this decorator function to check for admin privileges
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden access
        return f(*args, **kwargs)
    return decorated_function

def verify_ticker(symbol):
    """Verify ticker with cached yfinance data and get company name"""
    try:
        logger.info(f"Verifying ticker: {symbol}")
        
        # Try cached company info first (much faster!)
        from app.utils.cache.company_info_cache import company_info_cache
        info = company_info_cache.get_basic_company_info(symbol)
        
        if not info:
            # Fallback to direct yfinance call if cache fails
            logger.debug(f"Cache miss for {symbol}, using direct yfinance")
            ticker = yf.Ticker(symbol)
            info = ticker.info
        
        if info:
            if 'longName' in info:
                return True, info['longName']
            elif 'shortName' in info:
                return True, info['shortName']
            return True, symbol
                
        return False, None
    except Exception as e:
        logger.error(f"Error verifying ticker {symbol}: {str(e)}")
        return False, None


def load_tickers():
    """Load tickers from TypeScript file"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, '..', 'tickers.ts')
        
        logger.debug(f"Current directory: {current_dir}")
        logger.debug(f"Looking for tickers.ts at: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"Tickers file not found at: {file_path}")
            file_path = os.path.join(os.getcwd(), 'tickers.ts')
            logger.debug(f"Trying current directory: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error("Tickers file not found in current directory either")
                return [], {}
        
        logger.info(f"Found tickers.ts at: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.debug(f"Read {len(content)} characters from tickers.ts")
            
        pattern = r'{[^}]*symbol:\s*"([^"]*)",[^}]*name:\s*"([^"]*)"[^}]*}'
        matches = re.finditer(pattern, content)
        
        TICKERS = []
        TICKER_DICT = {}
        
        for match in matches:
            symbol, name = match.groups()
            ticker_obj = {"symbol": symbol, "name": name}
            TICKERS.append(ticker_obj)
            TICKER_DICT[symbol] = name
        
        logger.info(f"Successfully loaded {len(TICKERS)} tickers")
        logger.debug(f"First few tickers: {TICKERS[:3]}")
        
        return TICKERS, TICKER_DICT
        
    except Exception as e:
        logger.error(f"Error loading tickers: {str(e)}")
        logger.error(traceback.format_exc())
        return [], {}

# Load tickers at module level
TICKERS, TICKER_DICT = load_tickers()

@bp.route('/')
def index():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', now=datetime.now(), max_date=today)


def normalize_ticker(symbol):
    """Normalize ticker symbols to their proper format."""
    # Common index mappings
    index_mappings = {
        'HSI': '^HSI',     # Hang Seng Index
        'GSPC': '^GSPC',   # S&P 500
        'DJI': '^DJI',     # Dow Jones Industrial Average
        'IXIC': '^IXIC',   # NASDAQ Composite
        'N225': '^N225',   # Nikkei 225
        'FTSE': '^FTSE', 
        'VIX':  '^VIX',  
        'US10Y':  '^TNX',  
        # FTSE 100 Index
    }
    
    # Futures mappings
    futures_mappings = {
        # Metals
        'GOLD': 'GC=F',     # Gold Futures
        'SILVER': 'SI=F',    # Silver Futures
        'COPPER': 'HG=F',    # Copper Futures
        'PLATINUM': 'PL=F',  # Platinum Futures
        'PALLADIUM': 'PA=F', # Palladium Futures
        
        # Energy
        'OIL': 'CL=F',      # Crude Oil Futures
        'BRENT': 'BZ=F',    # Brent Crude Oil Futures
        'NATGAS': 'NG=F',   # Natural Gas Futures
        'HEATOIL': 'HO=F',  # Heating Oil Futures
        'GASOLINE': 'RB=F',  # RBOB Gasoline Futures
        
        # Agriculture
        'CORN': 'ZC=F',     # Corn Futures
        'WHEAT': 'ZW=F',    # Wheat Futures
        'SOYBEAN': 'ZS=F',  # Soybean Futures
        'COFFEE': 'KC=F',   # Coffee Futures
        'SUGAR': 'SB=F',    # Sugar Futures
        'COTTON': 'CT=F',   # Cotton Futures
        'COCOA': 'CC=F',    # Cocoa Futures
        'LUMBER': 'LBS=F',  # Lumber Futures
        'CATTLE': 'LE=F',   # Live Cattle Futures
        'HOGS': 'HE=F',     # Lean Hogs Futures
        
        # Financial
        'ES': 'ES=F',       # E-mini S&P 500 Futures
        'NQ': 'NQ=F',       # E-mini NASDAQ 100 Futures
        'RTY': 'RTY=F',     # E-mini Russell 2000 Futures
        'YM': 'YM=F',       # E-mini Dow Futures
        'VIX': 'VX=F',      # VIX Futures
        
        # Bonds/Rates
        'ZB': 'ZB=F',       # U.S. Treasury Bond Futures
        'ZN': 'ZN=F',       # 10-Year T-Note Futures
        'ZF': 'ZF=F',       # 5-Year T-Note Futures
        'ZT': 'ZT=F',       # 2-Year T-Note Futures
        
        # Currency
        'EURODOLLAR': 'GE=F',  # Euro FX Futures (EU)
        'GBPDOLLAR': '6B=F',   # British Pound Futures (UK)
        'JPYDOLLAR': '6J=F',   # Japanese Yen Futures (Japan)
        'CADDOLLAR': '6C=F',   # Canadian Dollar Futures (Canada)
        'AUDDOLLAR': '6A=F',   # Australian Dollar Futures (Australia)
        'CHFDOLLAR': '6S=F',   # Swiss Franc Futures (Switzerland)
        'CNHDOLLAR': 'CNH=F',  # Offshore Chinese Yuan Futures (China)
        'KRWDOLLAR': 'KRW=F',  # South Korean Won Futures (South Korea)
        'INRDOLLAR': 'INR=F',  # Indian Rupee Futures (India)
        'MXNDOLLAR': '6M=F',   # Mexican Peso Futures (Mexico)
        'BRLdollar': 'BRL=F',  # Brazilian Real Futures (Brazil)
        'SEKDOLLAR': 'SEK=F',  # Swedish Krona Futures (Sweden)
        'NZDDOLLAR': '6N=F',   # New Zealand Dollar Futures (New Zealand)
        'SGDDOLLAR': 'SGD=F',  # Singapore Dollar Futures (Singapore)
        'HKDDOLLAR': 'HKD=F',  # Hong Kong Dollar Futures (Hong Kong)
        'TWDDOLLAR': 'TWD=F',  # Taiwan Dollar Futures (Taiwan)
        'RUBDOLLAR': 'RUB=F',  # Russian Ruble Futures (Russia)
        'TRYDOLLAR': 'TRY=F',  # Turkish Lira Futures (Turkey)
        'PLNDOLLAR': 'PLN=F',  # Polish Zloty Futures (Poland)
        'IDRDOLLAR': 'IDR=F',  # Indonesian Rupiah Futures (Indonesia)
        'ZAEDOLLAR': 'ZAR=F',  # South African Rand Futures (South Africa)
        
        # Alternative search terms for currencies
        'POUND': '6B=F',       # Alternative for GBP
        'GBP': '6B=F',         # Alternative for British Pound
        'YEN': '6J=F',         # Alternative for JPY
        'JPY': '6J=F',         # Alternative for Japanese Yen
        'EURO': 'GE=F',        # Alternative for EUR
        'EUR': 'GE=F',         # Alternative for Euro
        'CAD': '6C=F',         # Alternative for Canadian Dollar
        'AUD': '6A=F',         # Alternative for Australian Dollar
        'CHF': '6S=F',         # Alternative for Swiss Franc
        'CNH': 'CNH=F',        # Alternative for Chinese Yuan
        'YUAN': 'CNH=F',       # Alternative for Chinese Yuan
        'RMB': 'CNH=F',        # Alternative for Chinese Yuan
        'KRW': 'KRW=F',        # Alternative for Korean Won
        'WON': 'KRW=F',        # Alternative for Korean Won
        'INR': 'INR=F',        # Alternative for Indian Rupee
        'RUPEE': 'INR=F',      # Alternative for Indian Rupee
        'MXN': '6M=F',         # Alternative for Mexican Peso
        'PESO': '6M=F',        # Alternative for Mexican Peso
        'BRL': 'BRL=F',        # Alternative for Brazilian Real
        'REAL': 'BRL=F',       # Alternative for Brazilian Real
        'SEK': 'SEK=F',        # Alternative for Swedish Krona
        'KRONA': 'SEK=F',      # Alternative for Swedish Krona
        'NZD': '6N=F',         # Alternative for New Zealand Dollar
        'KIWI': '6N=F',        # Alternative for New Zealand Dollar
        'SGD': 'SGD=F',        # Alternative for Singapore Dollar
        'HKD': 'HKD=F',        # Alternative for Hong Kong Dollar
        'TWD': 'TWD=F',        # Alternative for Taiwan Dollar
        'RUB': 'RUB=F',        # Alternative for Russian Ruble
        'RUBLE': 'RUB=F',      # Alternative for Russian Ruble
        'TRY': 'TRY=F',        # Alternative for Turkish Lira
        'LIRA': 'TRY=F',       # Alternative for Turkish Lira
        'PLN': 'PLN=F',        # Alternative for Polish Zloty
        'ZLOTY': 'PLN=F',      # Alternative for Polish Zloty
        'IDR': 'IDR=F',        # Alternative for Indonesian Rupiah
        'RUPIAH': 'IDR=F',     # Alternative for Indonesian Rupiah
        'ZAR': 'ZAR=F',        # Alternative for South African Rand
        'RAND': 'ZAR=F'        # Alternative for South African Rand
    }
    
    # ETF and asset mappings
    asset_mappings = {
        'NDQ': ['QQQ'],               # NASDAQ-100 ETF
        'SPX': ['SPY'],               # S&P 500 ETF
        'DJX': ['DIA'],               # Dow Jones ETF
        'FTSE': ['ISF.L', '^FTSE'],   # FTSE 100 ETF and Index
        'BTC': ['BTC-USD', 'BTC'],    # Bitcoin price and BTC Trust
        'ETH': ['ETH-USD', 'ETHE'],   # Ethereum and its ETF
        'GOLD': ['GC=F', 'GLD'], 
        'DXY':  ['DX-Y.NYB','US Dollar Index']
    }
    
    # Convert to uppercase for consistent matching
    symbol = symbol.upper()
    clean_symbol = symbol[1:] if symbol.startswith('^') else symbol
    
    # Get all variations for the symbol
    variations = []
    
    # Check futures first (for commodities)
    if clean_symbol in futures_mappings:
        variations.append(futures_mappings[clean_symbol])
    
    # Check if it's a known index
    if clean_symbol in index_mappings:
        variations.append(index_mappings[clean_symbol])
    
    # Check asset mappings for multiple variations
    if clean_symbol in asset_mappings:
        variations.extend(asset_mappings[clean_symbol])
        
    # If no mappings found, return original symbol
    return variations if variations else [symbol]

@bp.route('/search_ticker', methods=['GET'])
def search_ticker():
    query = request.args.get('query', '').upper()
    if not query or len(query) < 1:
        return jsonify([])
    
    try:
        search_results = []
        logger.info(f"Searching for ticker: {query}")
        
        # List of variations to try
        variations = [query]
        
        # Process exchange suffixes first
        exchange_suffix = None
        
        # Shanghai Stock Exchange (.SS)
        if (query.startswith('60') or query.startswith('68') or 
            query.startswith('51') or query.startswith('56') or
            query.startswith('58')) and len(query) == 6:
            exchange_suffix = '.SS'
            
        # Shenzhen Stock Exchange (.SZ)
        elif (query.startswith('00') or query.startswith('30')) and len(query) == 6:
            exchange_suffix = '.SZ'
            
        # Hong Kong Exchange (.HK)
        elif len(query) == 4 and query.isdigit():
            exchange_suffix = '.HK'

        # Check with exchange suffix if applicable
        if exchange_suffix:
            symbol_to_check = f"{query}{exchange_suffix}"
            is_valid, company_name = verify_ticker(symbol_to_check)
            
            if is_valid:
                # If symbol exists in TICKER_DICT, use that name instead
                if symbol_to_check in TICKER_DICT:
                    company_name = TICKER_DICT[symbol_to_check]
                
                if symbol_to_check.upper() != company_name.upper():  # Only add if symbol and name are different
                    search_results.append({
                        'symbol': symbol_to_check,
                        'name': company_name,
                        'source': 'verified',
                        'type': determine_asset_type(symbol_to_check, company_name)
                    })
                    logger.info(f"Found verified stock: {symbol_to_check}")
        
        # If no results from exchange suffix, try normalized variations
        if not search_results:
            normalized_variations = normalize_ticker(query)
            variations.extend([v for v in normalized_variations if v != query])
            
            for variant in variations:
                if variant != f"{query}{exchange_suffix}":  # Skip if already checked with exchange suffix
                    try:
                        is_valid, company_name = verify_ticker(variant)
                        if is_valid:
                            # If symbol exists in TICKER_DICT, use that name instead
                            if variant in TICKER_DICT:
                                company_name = TICKER_DICT[variant]
                                
                            if variant.upper() != company_name.upper():  # Only add if symbol and name are different
                                result = {
                                    'symbol': variant,
                                    'name': company_name,
                                    'source': 'verified',
                                    'type': determine_asset_type(variant, company_name)
                                }
                                search_results.append(result)
                                logger.info(f"Found verified asset: {variant}")
                    except Exception as e:
                        logger.warning(f"Error checking symbol {variant}: {str(e)}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for result in search_results:
            if result['symbol'] not in seen:
                seen.add(result['symbol'])
                unique_results.append(result)
        search_results = unique_results
                
        # Only proceed with local search if no verified stock was found
        if not search_results:
            # Add partial matches from local data
            if len(search_results) < 5:
                partial_matches = []
                for variant in variations:
                    matches = [
                        {'symbol': ticker['symbol'], 
                         'name': ticker['name'], 
                         'source': 'local',
                         'type': determine_asset_type(ticker['symbol'], ticker['name'])}
                        for ticker in TICKERS
                        if (variant in ticker['symbol'].upper() or 
                            variant in ticker['name'].upper()) and 
                            ticker['symbol'] not in seen and
                            ticker['symbol'].upper() != ticker['name'].upper()
                    ]
                    partial_matches.extend(matches)
                
                # Add partial matches up to limit
                for match in partial_matches:
                    if match['symbol'] not in seen:
                        seen.add(match['symbol'])
                        search_results.append(match)
                        if len(search_results) >= 5:
                            break
        
        # FALLBACK: If still no results, try enhanced vague search
        if not search_results:
            try:
                from app.utils.search.enhanced_ticker_search import enhanced_search
                logger.info(f"No results from original search, trying enhanced vague search for '{query}'")
                
                enhanced_results = enhanced_search.search_as_dict(query, limit=5)
                
                # Filter and format enhanced results
                for result in enhanced_results:
                    if result['symbol'].upper() != result['name'].upper():
                        formatted_result = {
                            'symbol': result['symbol'],
                            'name': result['name'],
                            'source': 'enhanced',
                            'type': result['type'],
                            'exchange': result.get('exchange', ''),
                            'country': result.get('country', ''),
                            'score': result.get('score', 0)
                        }
                        search_results.append(formatted_result)
                        
                logger.info(f"Enhanced vague search found {len(search_results)} fallback results")
                        
            except Exception as e:
                logger.warning(f"Enhanced vague search fallback failed: {str(e)}")
            
        return jsonify(search_results[:5])
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify([])

def determine_asset_type(symbol: str, name: str) -> str:
    """Determine the type of asset based on symbol and name."""
    symbol = symbol.upper()
    name = name.upper()
    
    if symbol.endswith('.HK'):
        return 'Hong Kong Stock'
    elif symbol.endswith('.SS'):
        return 'Shanghai Stock'
    elif symbol.endswith('.SZ'):
        return 'Shenzhen Stock'
    elif symbol.startswith('^'):
        return 'Index'
    elif symbol.endswith('=F'):
        return 'Futures'
    elif '-USD' in symbol:
        if symbol[:-4] in ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'ADA', 'DOT']:
            return 'Crypto'
        else:
            return 'Currency'
    elif any(currency in symbol for currency in ['HKD', 'CNH', 'JPY', 'EUR', 'GBP', 'AUD', 'CAD', 'CHF']):
        return 'Currency'
    elif 'ETF' in name:
        return 'ETF'
    elif 'TRUST' in name:
        return 'Trust'
    return None

@bp.route('/analyze_json', methods=['POST'])
@login_required
def analyze_json():
    try:
        ticker_input = request.form.get('ticker', '').split()[0].upper()
        logger.info(f"Analyzing ticker (JSON): {ticker_input}")
        
        if not ticker_input:
            return jsonify({'success': False, 'error': "Ticker symbol is required"}), 400
        
        end_date = request.form.get('end_date')
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
                logger.info(f"Using end date: {end_date}")
            except ValueError:
                return jsonify({'success': False, 'error': "Invalid date format. Please use YYYY-MM-DD format"}), 400
        
        lookback_days = int(request.form.get('lookback_days', 365))
        if lookback_days < 30 or lookback_days > 10000:
            return jsonify({'success': False, 'error': "Lookback days must be between 30 and 10000"}), 400
        
        crossover_days = int(request.form.get('crossover_days', 365))
        if crossover_days < 30 or crossover_days > 1000:
            return jsonify({'success': False, 'error': "Crossover days must be between 30 and 1000"}), 400
        
        # 🔄 AUTO NEWS CHECK: Check for recent news and trigger background fetching if needed
        try:
            from app.utils.analysis.stock_news_service import StockNewsService
            news_result = StockNewsService.auto_check_and_fetch_news(ticker_input)
            logger.info(f"Auto news check for {ticker_input}: {news_result['status']}")
        except Exception as e:
            logger.warning(f"Auto news check failed for {ticker_input}: {str(e)}")
            news_result = {'status': 'error', 'message': str(e)}
        
        fig = create_stock_visualization_old(
            ticker_input,
            end_date=end_date,
            lookback_days=lookback_days,
            crossover_days=crossover_days
        )
        
        # Convert the figure to JSON string and then back to Python objects
        # This handles the NumPy array serialization correctly
        fig_json = json.loads(fig.to_json())
        
        # Return success response with figure data
        return jsonify({
            'success': True,
            'ticker': ticker_input,
            'data': fig_json['data'],
            'layout': fig_json['layout'],
            'news_status': news_result  # Include news check result
        })
        
    except Exception as e:
        error_msg = f"Error analyzing {ticker_input}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500
@bp.route('/quick_analyze_json', methods=['POST'])
def quick_analyze_json():
    try:
        ticker_input = request.form.get('ticker', '').split()[0].upper()
        logger.info(f"Quick analyzing ticker (JSON): {ticker_input}")
        
        if not ticker_input:
            return jsonify({'success': False, 'error': "Ticker symbol is required"}), 400
            
        # 🔄 AUTO NEWS CHECK: Check for recent news and trigger background fetching if needed
        try:
            from app.utils.analysis.stock_news_service import StockNewsService
            news_result = StockNewsService.auto_check_and_fetch_news(ticker_input)
            logger.info(f"Auto news check for {ticker_input}: {news_result['status']}")
        except Exception as e:
            logger.warning(f"Auto news check failed for {ticker_input}: {str(e)}")
            news_result = {'status': 'error', 'message': str(e)}
            
        # Use default values for quick analysis
        fig = create_stock_visualization_old(
            ticker_input,
            end_date=None,  # Use current date
            lookback_days=ANALYZE_CONFIG['lookback_days'],  # Default lookback
            crossover_days=ANALYZE_CONFIG['crossover_days']  # Default crossover
        )
        
        # Convert the figure to JSON string and then back to Python objects
        fig_json = json.loads(fig.to_json())
        
        # Check if user is authenticated
        user_authenticated = current_user.is_authenticated
        
        # Return success response with figure data
        return jsonify({
            'success': True,
            'ticker': ticker_input,
            'data': fig_json['data'],
            'layout': fig_json['layout'],
            'user_authenticated': user_authenticated,
            'news_status': news_result  # Include news check result
        })
        
    except Exception as e:
        error_msg = f"Error analyzing {ticker_input}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500
@bp.route('/quick_analyze', methods=['POST'])
def quick_analyze():
    try:
        ticker_input = request.form.get('ticker', '').split()[0].upper()
        if not ticker_input:
            raise ValueError("Ticker symbol is required")
            
        # 🔄 AUTO NEWS CHECK: Check for recent news and trigger background fetching if needed
        try:
            from app.utils.analysis.stock_news_service import StockNewsService
            news_result = StockNewsService.auto_check_and_fetch_news(ticker_input)
            logger.info(f"Auto news check for {ticker_input}: {news_result['status']}")
        except Exception as e:
            logger.warning(f"Auto news check failed for {ticker_input}: {str(e)}")
            news_result = {'status': 'error', 'message': str(e)}
            
        # Use default values for quick analysis
        fig = create_stock_visualization_old(
            ticker_input,
            end_date=None,  # Use current date
            lookback_days=ANALYZE_CONFIG['lookback_days'],  # Default lookback
            crossover_days=ANALYZE_CONFIG['crossover_days']  # Default crossover
        )
        
        # Create HTML content with navigation buttons
        nav_buttons = [
            {'url': url_for('main.index'), 'text': 'Home', 'class': 'blue-500'},
            {'url': url_for('news.search', symbol=ticker_input), 'text': 'News', 'class': 'green-500'}
        ]
        
        # Generate HTML for navigation buttons
        nav_buttons_html = ''.join([
            f'<a href="{button["url"]}" '
            f'class="px-4 py-2 bg-{button["class"]} text-white rounded-md hover:bg-{button["class"]}/80 '
            f'transition-colors">{button["text"]}</a>'
            for button in nav_buttons
        ])
        
        # Add Tailwind CSS CDN
        tailwind_css = '<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">'
        
        # Get the plotly figure HTML
        plot_html = fig.to_html(
            full_html=True,
            include_plotlyjs=True,
            config={'responsive': True}
        )
        
        # Table expansion CSS and HTML
        table_expansion_css = '''
        <style>
        /* Table expansion modal styles */
        .table-modal {
            display: none;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(3px);
        }

        .table-modal-content {
            background-color: #fefefe;
            margin: 2% auto;
            padding: 20px;
            border: none;
            border-radius: 12px;
            width: 95%;
            max-width: 1200px;
            max-height: 90%;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            position: relative;
        }

        .table-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
        }

        .table-modal-title {
            font-size: 24px;
            font-weight: 600;
            color: #2c3e50;
            margin: 0;
        }

        .table-modal-close {
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }

        .table-modal-close:hover {
            background: #c0392b;
            transform: scale(1.1);
        }

        .expanded-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 14px;
        }

        .expanded-table th,
        .expanded-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
            word-wrap: break-word;
            max-width: 300px;
        }

        .expanded-table th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
            position: sticky;
            top: 0;
            z-index: 10;
        }

        .expanded-table tr:hover {
            background-color: #f8f9fa;
        }

        .expanded-table tr:nth-child(even) {
            background-color: #fdfdfd;
        }

        .mobile-table-hint {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 1000;
            animation: fadeInOut 6s ease-in-out;
        }

        @keyframes fadeInOut {
            0%, 100% { opacity: 0; }
            10%, 90% { opacity: 1; }
        }

        @media (max-width: 768px) {
            .table-modal-content {
                margin: 5% auto;
                width: 98%;
                padding: 15px;
            }

            .expanded-table {
                font-size: 12px;
            }

            .expanded-table th,
            .expanded-table td {
                padding: 8px 10px;
                max-width: 200px;
            }
        }
        </style>
        '''

        table_expansion_html = '''
        <!-- Table Expansion Modal -->
        <div id="table-modal" class="table-modal">
            <div class="table-modal-content">
                <div class="table-modal-header">
                    <h3 id="table-modal-title" class="table-modal-title">Table Details</h3>
                    <button class="table-modal-close" onclick="closeTableModal()">&times;</button>
                </div>
                <div id="table-modal-body">
                    <!-- Expanded table content will be inserted here -->
                </div>
            </div>
        </div>
        '''

        table_expansion_js = '''
        <script>
        // Mobile table expansion functionality
        let plotlyData = null;

        function initTableExpansion() {
            // Store the Plotly data
            const plotlyDiv = document.getElementById('plotly-div') || document.querySelector('.plotly-graph-div');
            if (plotlyDiv && plotlyDiv.data) {
                plotlyData = plotlyDiv.data;
                setupTableClickHandlers();
            } else {
                // Retry after a delay if Plotly isn't ready
                setTimeout(initTableExpansion, 1000);
            }
        }

        function setupTableClickHandlers() {
            setTimeout(() => {
                const plotlyDiv = document.getElementById('plotly-div') || document.querySelector('.plotly-graph-div');
                if (!plotlyDiv) return;
                
                // Find table elements
                const tableElements = plotlyDiv.querySelectorAll('g.trace.table, .table');
                tableElements.forEach((tableElement, index) => {
                    if (!tableElement.hasAttribute('data-clickable-added')) {
                        tableElement.setAttribute('data-clickable-added', 'true');
                        tableElement.style.cursor = 'pointer';
                        
                        const eventHandler = function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            showTableModal(index);
                        };
                        
                        tableElement.addEventListener('click', eventHandler);
                        tableElement.addEventListener('touchend', eventHandler);
                        
                        // Add visual feedback
                        tableElement.addEventListener('touchstart', function() {
                            this.style.opacity = '0.8';
                        });
                        
                        tableElement.addEventListener('touchcancel', function() {
                            this.style.opacity = '1';
                        });
                    }
                });
                
                // Show mobile hint
                showMobileHint();
            }, 1500);
        }

        function showMobileHint() {
            const hint = document.createElement('div');
            hint.className = 'mobile-table-hint';
            hint.textContent = '💡 Tap any table to see all details';
            document.body.appendChild(hint);
            
            setTimeout(() => {
                if (hint.parentNode) {
                    hint.parentNode.removeChild(hint);
                }
            }, 6000);
        }

        function showTableModal(tableIndex) {
            const modal = document.getElementById('table-modal');
            const modalTitle = document.getElementById('table-modal-title');
            const modalBody = document.getElementById('table-modal-body');
            
            if (!modal || !modalTitle || !modalBody || !plotlyData) {
                console.error('Modal elements or data not found');
                return;
            }
            
            modalBody.innerHTML = '';
            
            // Find the table data
            let tableData = null;
            let tableCount = 0;
            for (let i = 0; i < plotlyData.length; i++) {
                if (plotlyData[i].type === 'table') {
                    if (tableCount === tableIndex) {
                        tableData = plotlyData[i];
                        break;
                    }
                    tableCount++;
                }
            }
            
            if (!tableData) {
                modalBody.innerHTML = '<p>Table data not found.</p>';
                modal.style.display = 'block';
                return;
            }
            
            // Determine table title
            let tableTitle = 'Table Details';
            if (tableData.header && tableData.header.values) {
                const firstHeader = tableData.header.values[0];
                if (typeof firstHeader === 'string') {
                    if (firstHeader.includes('Metric')) {
                        tableTitle = 'Analysis Summary';
                    } else if (firstHeader.includes('Entry Date')) {
                        tableTitle = 'Trading Signal Analysis';
                    } else if (firstHeader.includes('Symbol') || firstHeader.includes('Company')) {
                        tableTitle = 'Company Information';
                    } else if (firstHeader.includes('Financial')) {
                        tableTitle = 'Financial Metrics';
                    } else if (firstHeader.includes('Growth')) {
                        tableTitle = 'Growth Analysis';
                    }
                }
            }
            
            modalTitle.textContent = tableTitle;
            
            // Create expanded table
            const expandedTable = document.createElement('table');
            expandedTable.className = 'expanded-table';
            
            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            
            if (tableData.header && tableData.header.values) {
                tableData.header.values.forEach(headerText => {
                    const th = document.createElement('th');
                    th.textContent = headerText.replace(/<[^>]*>/g, '');
                    headerRow.appendChild(th);
                });
            }
            thead.appendChild(headerRow);
            expandedTable.appendChild(thead);
            
            // Create body
            const tbody = document.createElement('tbody');
            
            if (tableData.cells && tableData.cells.values) {
                const numColumns = tableData.cells.values.length;
                const numRows = tableData.cells.values[0] ? tableData.cells.values[0].length : 0;
                
                for (let rowIndex = 0; rowIndex < numRows; rowIndex++) {
                    const row = document.createElement('tr');
                    
                    for (let colIndex = 0; colIndex < numColumns; colIndex++) {
                        const td = document.createElement('td');
                        const cellValue = tableData.cells.values[colIndex][rowIndex];
                        td.textContent = cellValue ? cellValue.toString().replace(/<[^>]*>/g, '') : '';
                        row.appendChild(td);
                    }
                    
                    tbody.appendChild(row);
                }
            }
            
            expandedTable.appendChild(tbody);
            modalBody.appendChild(expandedTable);
            
            modal.style.display = 'block';
        }

        function closeTableModal() {
            const modal = document.getElementById('table-modal');
            if (modal) {
                modal.style.display = 'none';
            }
        }

        // Event listeners
        window.addEventListener('click', function(e) {
            const modal = document.getElementById('table-modal');
            if (modal && e.target === modal) {
                modal.style.display = 'none';
            }
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const modal = document.getElementById('table-modal');
                if (modal && modal.style.display === 'block') {
                    modal.style.display = 'none';
                }
            }
        });

        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', initTableExpansion);
        
        // News status functionality

        </script>
        '''
        
        # News status button removed per user request
        news_status_button = ''
        
        # Insert Tailwind CSS, table expansion CSS, modal HTML, and navigation buttons
        html_content = plot_html.replace(
            '</head>',
            f'{tailwind_css}{table_expansion_css}</head>'
        ).replace(
            '</body>',
            f'{table_expansion_html}<div class="fixed top-4 left-4 flex space-x-4" style="z-index:1001;">{nav_buttons_html}{news_status_button}</div>{table_expansion_js}</body>'
        )
        
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        return response
        
    except Exception as e:
        error_msg = f"Error analyzing {ticker_input}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return f'<div class="text-red-500">Error: {error_msg}</div>', 500

@bp.route('/analyze', methods=['POST'])
@login_required
def analyze():
    try:
        ticker_input = request.form.get('ticker', '').split()[0].upper()
        logger.info(f"Analyzing ticker: {ticker_input}")
        
        if not ticker_input:
            raise ValueError("Ticker symbol is required")
        
        end_date = request.form.get('end_date')
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
                logger.info(f"Using end date: {end_date}")
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD format")
        
        lookback_days = int(request.form.get('lookback_days', 365))
        if lookback_days < 30 or lookback_days > 10000:
            raise ValueError("Lookback days must be between 30 and 10000")
        
        crossover_days = int(request.form.get('crossover_days', 365))
        if crossover_days < 30 or crossover_days > 1000:
            raise ValueError("Crossover days must be between 30 and 1000")
        
        # 🔄 AUTO NEWS CHECK: Check for recent news and trigger background fetching if needed
        try:
            from app.utils.analysis.stock_news_service import StockNewsService
            news_result = StockNewsService.auto_check_and_fetch_news(ticker_input)
            logger.info(f"Auto news check for {ticker_input}: {news_result['status']}")
        except Exception as e:
            logger.warning(f"Auto news check failed for {ticker_input}: {str(e)}")
            news_result = {'status': 'error', 'message': str(e)}
        
        fig = create_stock_visualization_old(
            ticker_input,
            end_date=end_date,
            lookback_days=lookback_days,
            crossover_days=crossover_days
        )
        
        # Create HTML content with navigation buttons
        nav_buttons = [
            {'url': url_for('main.index'), 'text': 'Home', 'class': 'blue-500'},
            {'url': url_for('news.search', symbol=ticker_input), 'text': 'News', 'class': 'green-500'}
        ]
        
        # Generate HTML for navigation buttons
        nav_buttons_html = ''.join([
            f'<a href="{button["url"]}" '
            f'class="px-4 py-2 bg-{button["class"]} text-white rounded-md hover:bg-{button["class"]}/80 '
            f'transition-colors">{button["text"]}</a>'
            for button in nav_buttons
        ])
        
        # Add Tailwind CSS CDN
        tailwind_css = '<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">'
        
        # Get the plotly figure HTML
        plot_html = fig.to_html(
            full_html=True,
            include_plotlyjs=True,
            config={'responsive': True}
        )
        
        # Table expansion CSS and HTML
        table_expansion_css = '''
        <style>
        /* Table expansion modal styles */
        .table-modal {
            display: none;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(3px);
        }

        .table-modal-content {
            background-color: #fefefe;
            margin: 2% auto;
            padding: 20px;
            border: none;
            border-radius: 12px;
            width: 95%;
            max-width: 1200px;
            max-height: 90%;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            position: relative;
        }

        .table-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
        }

        .table-modal-title {
            font-size: 24px;
            font-weight: 600;
            color: #2c3e50;
            margin: 0;
        }

        .table-modal-close {
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }

        .table-modal-close:hover {
            background: #c0392b;
            transform: scale(1.1);
        }

        .expanded-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 14px;
        }

        .expanded-table th,
        .expanded-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
            word-wrap: break-word;
            max-width: 300px;
        }

        .expanded-table th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
            position: sticky;
            top: 0;
            z-index: 10;
        }

        .expanded-table tr:hover {
            background-color: #f8f9fa;
        }

        .expanded-table tr:nth-child(even) {
            background-color: #fdfdfd;
        }

        .mobile-table-hint {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 1000;
            animation: fadeInOut 6s ease-in-out;
        }

        @keyframes fadeInOut {
            0%, 100% { opacity: 0; }
            10%, 90% { opacity: 1; }
        }

        @media (max-width: 768px) {
            .table-modal-content {
                margin: 5% auto;
                width: 98%;
                padding: 15px;
            }

            .expanded-table {
                font-size: 12px;
            }

            .expanded-table th,
            .expanded-table td {
                padding: 8px 10px;
                max-width: 200px;
            }
        }
        </style>
        '''

        table_expansion_html = '''
        <!-- Table Expansion Modal -->
        <div id="table-modal" class="table-modal">
            <div class="table-modal-content">
                <div class="table-modal-header">
                    <h3 id="table-modal-title" class="table-modal-title">Table Details</h3>
                    <button class="table-modal-close" onclick="closeTableModal()">&times;</button>
                </div>
                <div id="table-modal-body">
                    <!-- Expanded table content will be inserted here -->
                </div>
            </div>
        </div>
        '''

        table_expansion_js = '''
        <script>
        // Mobile table expansion functionality
        let plotlyData = null;

        function initTableExpansion() {
            // Store the Plotly data
            const plotlyDiv = document.getElementById('plotly-div') || document.querySelector('.plotly-graph-div');
            if (plotlyDiv && plotlyDiv.data) {
                plotlyData = plotlyDiv.data;
                setupTableClickHandlers();
            } else {
                // Retry after a delay if Plotly isn't ready
                setTimeout(initTableExpansion, 1000);
            }
        }

        function setupTableClickHandlers() {
            setTimeout(() => {
                const plotlyDiv = document.getElementById('plotly-div') || document.querySelector('.plotly-graph-div');
                if (!plotlyDiv) return;
                
                // Find table elements
                const tableElements = plotlyDiv.querySelectorAll('g.trace.table, .table');
                tableElements.forEach((tableElement, index) => {
                    if (!tableElement.hasAttribute('data-clickable-added')) {
                        tableElement.setAttribute('data-clickable-added', 'true');
                        tableElement.style.cursor = 'pointer';
                        
                        const eventHandler = function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            showTableModal(index);
                        };
                        
                        tableElement.addEventListener('click', eventHandler);
                        tableElement.addEventListener('touchend', eventHandler);
                        
                        // Add visual feedback
                        tableElement.addEventListener('touchstart', function() {
                            this.style.opacity = '0.8';
                        });
                        
                        tableElement.addEventListener('touchcancel', function() {
                            this.style.opacity = '1';
                        });
                    }
                });
                
                // Show mobile hint
                showMobileHint();
            }, 1500);
        }

        function showMobileHint() {
            const hint = document.createElement('div');
            hint.className = 'mobile-table-hint';
            hint.textContent = '💡 Tap any table to see all details';
            document.body.appendChild(hint);
            
            setTimeout(() => {
                if (hint.parentNode) {
                    hint.parentNode.removeChild(hint);
                }
            }, 6000);
        }

        function showTableModal(tableIndex) {
            const modal = document.getElementById('table-modal');
            const modalTitle = document.getElementById('table-modal-title');
            const modalBody = document.getElementById('table-modal-body');
            
            if (!modal || !modalTitle || !modalBody || !plotlyData) {
                console.error('Modal elements or data not found');
                return;
            }
            
            modalBody.innerHTML = '';
            
            // Find the table data
            let tableData = null;
            let tableCount = 0;
            for (let i = 0; i < plotlyData.length; i++) {
                if (plotlyData[i].type === 'table') {
                    if (tableCount === tableIndex) {
                        tableData = plotlyData[i];
                        break;
                    }
                    tableCount++;
                }
            }
            
            if (!tableData) {
                modalBody.innerHTML = '<p>Table data not found.</p>';
                modal.style.display = 'block';
                return;
            }
            
            // Determine table title
            let tableTitle = 'Table Details';
            if (tableData.header && tableData.header.values) {
                const firstHeader = tableData.header.values[0];
                if (typeof firstHeader === 'string') {
                    if (firstHeader.includes('Metric')) {
                        tableTitle = 'Analysis Summary';
                    } else if (firstHeader.includes('Entry Date')) {
                        tableTitle = 'Trading Signal Analysis';
                    } else if (firstHeader.includes('Symbol') || firstHeader.includes('Company')) {
                        tableTitle = 'Company Information';
                    } else if (firstHeader.includes('Financial')) {
                        tableTitle = 'Financial Metrics';
                    } else if (firstHeader.includes('Growth')) {
                        tableTitle = 'Growth Analysis';
                    }
                }
            }
            
            modalTitle.textContent = tableTitle;
            
            // Create expanded table
            const expandedTable = document.createElement('table');
            expandedTable.className = 'expanded-table';
            
            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            
            if (tableData.header && tableData.header.values) {
                tableData.header.values.forEach(headerText => {
                    const th = document.createElement('th');
                    th.textContent = headerText.replace(/<[^>]*>/g, '');
                    headerRow.appendChild(th);
                });
            }
            thead.appendChild(headerRow);
            expandedTable.appendChild(thead);
            
            // Create body
            const tbody = document.createElement('tbody');
            
            if (tableData.cells && tableData.cells.values) {
                const numColumns = tableData.cells.values.length;
                const numRows = tableData.cells.values[0] ? tableData.cells.values[0].length : 0;
                
                for (let rowIndex = 0; rowIndex < numRows; rowIndex++) {
                    const row = document.createElement('tr');
                    
                    for (let colIndex = 0; colIndex < numColumns; colIndex++) {
                        const td = document.createElement('td');
                        const cellValue = tableData.cells.values[colIndex][rowIndex];
                        td.textContent = cellValue ? cellValue.toString().replace(/<[^>]*>/g, '') : '';
                        row.appendChild(td);
                    }
                    
                    tbody.appendChild(row);
                }
            }
            
            expandedTable.appendChild(tbody);
            modalBody.appendChild(expandedTable);
            
            modal.style.display = 'block';
        }

        function closeTableModal() {
            const modal = document.getElementById('table-modal');
            if (modal) {
                modal.style.display = 'none';
            }
        }

        // Event listeners
        window.addEventListener('click', function(e) {
            const modal = document.getElementById('table-modal');
            if (modal && e.target === modal) {
                modal.style.display = 'none';
            }
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const modal = document.getElementById('table-modal');
                if (modal && modal.style.display === 'block') {
                    modal.style.display = 'none';
                }
            }
        });

        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', initTableExpansion);
        

        </script>
        '''
        
        # News status button removed per user request
        news_status_button = ''
        
        # Insert Tailwind CSS, table expansion CSS, modal HTML, and navigation buttons
        html_content = plot_html.replace(
            '</head>',
            f'{tailwind_css}{table_expansion_css}</head>'
        ).replace(
            '</body>',
            f'{table_expansion_html}<div class="fixed top-4 left-4 flex space-x-4" style="z-index:1001;">{nav_buttons_html}{news_status_button}</div>{table_expansion_js}</body>'
        )
        
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        return response
        
    except Exception as e:
        error_msg = f"Error analyzing {ticker_input}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return f'<div class="text-red-500">Error: {error_msg}</div>', 500

@bp.route('/tables')
@admin_required
def tables():
    """Show database tables in document tree structure"""
    try:
        logger.info('Accessing database tables view')
        
        # Get all tables from database
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        logger.info(f'Found {len(tables)} tables in database')
        
        # Organize tables by type
        historical_tables = []
        financial_tables = []
        other_tables = []
        
        for table in tables:
            try:
                table_info = {
                    'name': table
                }
                
                if table.startswith('his_'):
                    ticker = table.replace('his_', '').upper()
                    historical_tables.append({
                        **table_info,
                        'ticker': ticker,
                        'type': 'Historical Data'
                    })
                    
                elif table.startswith('roic_'):
                    ticker = table.replace('roic_', '').upper()
                    financial_tables.append({
                        **table_info,
                        'ticker': ticker,
                        'type': 'Financial Data'
                    })
                    
                else:
                    other_tables.append({
                        **table_info,
                        'type': 'Other'
                    })
                    
            except Exception as table_error:
                logger.error(f"Error processing table {table}: {str(table_error)}")
                continue

        return render_template(
            'tables.html',
            historical_tables=historical_tables,
            financial_tables=financial_tables,
            other_tables=other_tables
        )
        
    except Exception as e:
        error_msg = f"Error fetching database tables: {str(e)}"
        logger.error(f"{error_msg}")
        return render_template('tables.html', error=error_msg)

@bp.route('/delete_table/<table_name>', methods=['POST'])
@admin_required
def delete_table(table_name):
    """Delete a table from database"""
    try:
        logger.info(f'Attempting to delete table: {table_name}')
        
        # Check if table exists
        inspector = inspect(db.engine)
        if table_name not in inspector.get_table_names():
            logger.error(f'Table {table_name} not found')
            return jsonify({'success': False, 'error': 'Table not found'}), 404

        # Use backticks to properly escape table name
        query = text(f'DROP TABLE `{table_name}`')
        db.session.execute(query)
        db.session.commit()
        
        logger.info(f'Successfully deleted table: {table_name}')
        return jsonify({'success': True, 'message': f'Table {table_name} deleted successfully'})
        
    except Exception as e:
        error_msg = f"Error deleting table {table_name}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': error_msg}), 500

@bp.route('/table-content/<table_name>')
@admin_required
def show_table_content(table_name):
    """Show the content of a specific table with sorting and pagination"""
    try:
        # Get sort parameters from URL
        sort_column = request.args.get('sort', 'Date')  # Default sort by Date
        sort_direction = request.args.get('direction', 'desc')  # Default descending
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)  # 50 items per page

        # Calculate offset
        offset = (page - 1) * per_page

        # Count total rows
        count_query = text(f'SELECT COUNT(*) FROM `{table_name}`')
        total_rows = db.session.execute(count_query).scalar()
        total_pages = (total_rows + per_page - 1) // per_page

        # Get all column names
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        # If sort column not in columns, use first column
        if sort_column not in columns and columns:
            sort_column = columns[0]

        # Build query with sorting and pagination
        query = text(f'''
            SELECT * FROM `{table_name}`
            ORDER BY `{sort_column}` {sort_direction}
            LIMIT :limit OFFSET :offset
        ''')
        
        # Execute query and fetch results
        result = db.session.execute(query, {'limit': per_page, 'offset': offset})
        
        # Convert results to list of dictionaries
        data = []
        for row in result:
            row_dict = {}
            for idx, col in enumerate(columns):
                row_dict[col] = row[idx]
            data.append(row_dict)
        
        return render_template(
            'table_content.html',
            table_name=table_name,
            columns=columns,
            data=data,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            sort_column=sort_column,
            sort_direction=sort_direction,
            total_rows=total_rows
        )
        
    except Exception as e:
        error_msg = f"Error fetching content for table {table_name}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return render_template('table_content.html', error=error_msg)


@bp.route('/export/<table_name>/<format>')
@admin_required
def export_table(table_name, format):
    """Export table data in CSV or Excel format"""
    try:
        # Get all data from table
        query = text(f'SELECT * FROM `{table_name}`')
        result = db.session.execute(query)
        
        # Get column names
        columns = result.keys()
        
        # Convert to DataFrame
        df = pd.DataFrame([dict(row) for row in result], columns=columns)
        
        # Create buffer for file
        buffer = io.BytesIO()
        
        if format == 'csv':
            # Export as CSV
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'{table_name}.csv'
            )
            
        elif format == 'excel':
            # Export as Excel
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{table_name}.xlsx'
            )
        
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        error_msg = f"Error exporting table {table_name}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500


@bp.route('/delete_all_historical', methods=['POST'])
@admin_required
def delete_all_historical():
    """Delete all historical data tables"""
    try:
        logger.info('Attempting to delete all historical data tables')
        
        # Get all tables from database
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Filter for historical tables
        historical_tables = [table for table in tables if table.startswith('his_')]
        
        if not historical_tables:
            return jsonify({
                'success': False, 
                'error': 'No historical tables found'
            }), 404
        
        # Delete each historical table
        deleted_count = 0
        errors = []
        
        for table in historical_tables:
            try:
                query = text(f'DROP TABLE `{table}`')
                db.session.execute(query)
                deleted_count += 1
            except Exception as table_error:
                error_msg = f"Error deleting table {table}: {str(table_error)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Commit the transaction
        db.session.commit()
        
        # Prepare response message
        if deleted_count == len(historical_tables):
            message = f'Successfully deleted all {deleted_count} historical tables'
            logger.info(message)
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            message = f'Partially completed: Deleted {deleted_count} out of {len(historical_tables)} tables'
            if errors:
                message += f'. Errors: {"; ".join(errors)}'
            logger.warning(message)
            return jsonify({
                'success': True,
                'message': message
            })
            
    except Exception as e:
        error_msg = f"Error deleting historical tables: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

    
@bp.route('/delete_all_financial', methods=['POST'])
@admin_required
def delete_all_financial():
    """Delete all financial data tables"""
    try:
        logger.info('Attempting to delete all financial data tables')
        
        # Get all tables from database
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Filter for financial tables
        financial_tables = [table for table in tables if table.startswith('roic_')]
        
        if not financial_tables:
            return jsonify({
                'success': False, 
                'error': 'No financial tables found'
            }), 404
        
        # Delete each financial table
        deleted_count = 0
        errors = []
        
        for table in financial_tables:
            try:
                query = text(f'DROP TABLE `{table}`')
                db.session.execute(query)
                deleted_count += 1
            except Exception as table_error:
                error_msg = f"Error deleting table {table}: {str(table_error)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Commit the transaction
        db.session.commit()
        
        # Prepare response message
        if deleted_count == len(financial_tables):
            message = f'Successfully deleted all {deleted_count} financial tables'
            logger.info(message)
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            message = f'Partially completed: Deleted {deleted_count} out of {len(financial_tables)} tables'
            if errors:
                message += f'. Errors: {"; ".join(errors)}'
            logger.warning(message)
            return jsonify({
                'success': True,
                'message': message
            })
            
    except Exception as e:
        error_msg = f"Error deleting financial tables: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


from flask import Response
import json
import queue
import threading

# Create a queue for progress updates
# Add/update these routes in routes.py

# Create a queue for progress updates
# progress_queue = queue.Queue()

# def send_progress_update(current, total, message=None):
#     """Helper function to send progress updates"""
#     progress_queue.put({
#         'current': current,
#         'total': total,
#         'message': message
#     })
#     logger.debug(f'Progress update queued: {current}/{total} - {message}')  # Debug log

# @bp.route('/create_progress')
# def progress():
#     """SSE endpoint for progress updates"""
#     def generate():
#         while True:
#             try:
#                 # Get progress update from queue with timeout
#                 progress_data = progress_queue.get(timeout=60)
#                 logger.debug(f'Sending progress update: {progress_data}')  # Debug log
#                 yield f"data: {json.dumps(progress_data)}\n\n"
#             except queue.Empty:
#                 logger.debug('Progress queue timeout')  # Debug log
#                 break
#             except Exception as e:
#                 logger.error(f'Error in progress generator: {str(e)}')
#                 break
                
#     return Response(generate(), mimetype='text/event-stream')

@bp.route('/create_all_historical', methods=['POST'])
@admin_required
def create_all_historical():
    """Create historical data tables for tickers that don't exist in database"""
    try:
        logger.info('Attempting to create missing historical data tables')
        
        # Load tickers
        try:
            tickers, _ = load_tickers()
            logger.info(f'Successfully loaded {len(tickers)} tickers')
        except Exception as e:
            logger.error(f'Error loading tickers: {str(e)}')
            return jsonify({
                'success': False,
                'error': f'Failed to load tickers: {str(e)}'
            }), 500

        if not tickers:
            logger.error('No tickers found in tickers.ts')
            return jsonify({
                'success': False,
                'error': 'No tickers found in tickers.ts'
            }), 404
            
        # Get DataService instance
        try:
            from app.utils.data.data_service import DataService
            data_service = DataService()
        except Exception as e:
            logger.error(f'Error initializing DataService: {str(e)}')
            return jsonify({
                'success': False,
                'error': f'Failed to initialize data service: {str(e)}'
            }), 500
            
        # Get list of existing tables
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # Filter out tickers that already have tables
        missing_tickers = []
        for ticker_obj in tickers:
            ticker = ticker_obj['symbol']
            cleaned_ticker = data_service.clean_ticker_for_table_name(ticker)
            table_name = f"his_{cleaned_ticker}"
            if table_name not in existing_tables:
                missing_tickers.append(ticker_obj)
                
        logger.info(f'Found {len(missing_tickers)} missing historical tables to create')
        
        if not missing_tickers:
            return jsonify({
                'success': True,
                'message': 'All historical tables already exist'
            })
            
        # Get date range for historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*10)
            
        # Process missing tickers
        def process_tickers():
            created_count = 0
            errors = []
            skipped = []
            total = len(missing_tickers)
            rate_limiter = RateLimiter(calls_per_second=2)

            for i, ticker_obj in enumerate(missing_tickers, 1):
                try:
                    
                    ticker = ticker_obj['symbol']
                    send_progress_update(i, total, f'Processing {ticker}...')
                    
                    # Add rate limiting
                    rate_limiter.wait()
                    
                    # Skip certain types of symbols
                    if any(x in ticker for x in ['^', '/', '\\']):
                        skipped.append(f"{ticker} (invalid symbol)")
                        logger.info(f'Skipping invalid symbol: {ticker}')
                        continue
                        
                    success = data_service.store_historical_data_with_retry(
                        ticker,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )
                    
                    if success:
                        created_count += 1
                        send_progress_update(i, total, f'Created table for {ticker}')
                    else:
                        errors.append(f"Failed to create table for {ticker}")
                        send_progress_update(i, total, f'Failed to create table for {ticker}')
                        
                except Exception as ticker_error:
                    error_msg = f"Error processing {ticker}: {str(ticker_error)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    send_progress_update(i, total, error_msg)
                    # Add a small delay after errors
                    sleep(2)

                # Add a small random delay between requests
                sleep(random.uniform(0.1, 0.3))
            
            # Send final summary
            summary = []
            if created_count > 0:
                summary.append(f'Successfully created {created_count} missing tables')
            if errors:
                summary.append(f'Encountered {len(errors)} errors')
            if skipped:
                summary.append(f'Skipped {len(skipped)} invalid symbols')
            
            send_progress_update(total, total, '. '.join(summary))
        
        # Start processing in background thread
        thread = threading.Thread(target=process_tickers)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Started creating missing tables'
        })
            
    except Exception as e:
        error_msg = f"Error in create_all_historical: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# First ensure these imports are at the top of routes.py
import json
import queue
import gc
import threading
from datetime import datetime
from time import sleep
import traceback
from flask import jsonify, Response
from sqlalchemy import inspect

# Progress queue for SSE updates
progress_queue = queue.Queue()

def send_progress_update(current, total, message=None):
    """Helper function to send progress updates"""
    progress_queue.put({
        'current': current,
        'total': total,
        'message': message
    })
    logger.debug(f'Progress update: {current}/{total} - {message}')

@bp.route('/create_all_financial', methods=['POST'])
@admin_required
def create_all_financial():
    """Create financial data tables for tickers that don't exist in database"""
    try:
        logger.info('Attempting to create missing financial data tables')
        
        # Load tickers
        try:
            tickers, _ = load_tickers()
            logger.info(f'Successfully loaded {len(tickers)} tickers')
        except Exception as e:
            logger.error(f'Error loading tickers: {str(e)}')
            return jsonify({
                'success': False,
                'error': f'Failed to load tickers: {str(e)}'
            }), 500

        if not tickers:
            logger.error('No tickers found in tickers.ts')
            return jsonify({
                'success': False,
                'error': 'No tickers found in tickers.ts'
            }), 404
            
        # Initialize DataService
        try:
            from app.utils.data.data_service import DataService
            data_service = DataService()
        except Exception as e:
            logger.error(f'Error initializing DataService: {str(e)}')
            return jsonify({
                'success': False,
                'error': f'Failed to initialize data service: {str(e)}'
            }), 500
            
        # Get list of existing tables
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # Filter out non-US stocks and tickers that already have tables
        missing_tickers = []
        for ticker_obj in tickers:
            ticker = ticker_obj['symbol']
            cleaned_ticker = data_service.clean_ticker_for_table_name(ticker)
            table_name = f"roic_{cleaned_ticker}"
            if table_name not in existing_tables:
                    missing_tickers.append(ticker_obj)
                    
        logger.info(f'Found {len(missing_tickers)} missing financial tables to create')
        
        if not missing_tickers:
            return jsonify({
                'success': True,
                'message': 'All financial tables already exist'
            })

        # In create_all_financial() route, update the process_tickers function:

        def process_tickers():
            created_count = 0
            errors = []
            total = len(missing_tickers)
            current = 0
            
            end_year = str(datetime.now().year)
            start_year = str(int(end_year) - 10)
            
            # Configuration for batching
            BATCH_SIZE = 10  # Increased from 5 to 10
            BATCH_DELAY = 30  # Reduced from 60 to 30 seconds
            ERROR_DELAY = 10  # Reduced from 30 to 10 seconds
            
            # Process tickers in batches
            for i in range(0, total, BATCH_SIZE):
                batch = missing_tickers[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
                
                msg = f"Processing batch {batch_num} of {total_batches}..."
                logger.info(msg)
                send_progress_update(current, total, msg)
                
                for ticker_obj in batch:
                    try:
                        current += 1
                        ticker = ticker_obj['symbol']
                        
                        msg = f'Processing {ticker} ({current}/{total})...'
                        logger.info(msg)
                        send_progress_update(current, total, msg)
                        
                        success = data_service.store_financial_data(
                            ticker,
                            start_year=start_year,
                            end_year=end_year
                        )
                        
                        if success:
                            created_count += 1
                            msg = f'✓ Created financial table for {ticker}'
                        else:
                            msg = f'✗ Failed to create table for {ticker}'
                            errors.append(ticker)
                            
                        logger.info(msg)
                        send_progress_update(current, total, msg)
                        
                        # Short delay between tickers
                        sleep(1)  # Reduced from 2 seconds
                        
                    except Exception as e:
                        error_msg = f"Error processing {ticker}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(ticker)
                        send_progress_update(current, total, f'✗ {error_msg}')
                        sleep(ERROR_DELAY)
                
                # After each batch
                if batch_num < total_batches:
                    msg = f'Completed batch {batch_num}. Pausing for {BATCH_DELAY} seconds...'
                    logger.info(msg)
                    send_progress_update(current, total, msg)
                    sleep(BATCH_DELAY)
            
            # Final summary
            final_msg = []
            if created_count > 0:
                final_msg.append(f'✓ Created {created_count} tables')
            if errors:
                final_msg.append(f'✗ Failed: {len(errors)} tables')
            
            send_progress_update(total, total, ' | '.join(final_msg))
                
        # Start processing in background thread
        thread = threading.Thread(target=process_tickers)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Started creating missing tables'
        })
            
    except Exception as e:
        error_msg = f"Error in create_all_financial: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/create_progress')
def progress():
    """SSE endpoint for progress updates"""
    def generate():
        while True:
            try:
                # Get progress update from queue with timeout
                progress_data = progress_queue.get(timeout=60)
                logger.debug(f'Sending progress update: {progress_data}')
                yield f"data: {json.dumps(progress_data)}\n\n"
            except queue.Empty:
                logger.debug('Progress queue timeout')
                break
            except Exception as e:
                logger.error(f'Error in progress generator: {str(e)}')
                break
                
    return Response(generate(), mimetype='text/event-stream')

# Add direct user activities route as a workaround
@bp.route("/admin-user-activities")
@login_required
@admin_required
def admin_user_activities():
    """Workaround for user activities page"""
    try:
        from app.models import UserActivity, User
        page = request.args.get("page", 1, type=int)
        per_page = 50
        
        # Filter parameters
        user_id = request.args.get("user_id", type=int)
        activity_type = request.args.get("activity_type")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        
        # Base query
        query = UserActivity.query.join(User)
        
        # Apply filters
        if user_id:
            query = query.filter(UserActivity.user_id == user_id)
        if activity_type:
            query = query.filter(UserActivity.activity_type == activity_type)
        if date_from:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(UserActivity.timestamp >= date_from)
        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d")
            date_to = date_to + timedelta(days=1)  # Include the entire day
            query = query.filter(UserActivity.timestamp < date_to)
        
        # Get users for filter dropdown
        users = User.query.order_by(User.username).all()
        
        # Get activity types for filter dropdown
        # Hardcode to only show login and logout in filter dropdown
        activity_types = ['login', 'logout']
        
        # Paginate the results
        activities = query.order_by(UserActivity.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template(
            "admin/user_activities.html",
            activities=activities,
            users=users,
            activity_types=activity_types,
            user_id=user_id,
            activity_type=activity_type,
            date_from=date_from.strftime("%Y-%m-%d") if date_from else "",
            date_to=date_to.strftime("%Y-%m-%d") if date_to and isinstance(date_to, datetime) else ""
        )
        
    except Exception as e:
        logger.error(f"Error loading user activities: {str(e)}")
        return f"<h1>Error Loading User Activities</h1><p>Error: {str(e)}</p>"

@bp.route('/debug-routes')
def debug_routes():
    """Debug route to show all registered URLs"""
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append(f"{rule.endpoint}: {rule.rule}")
    return "<br>".join(sorted(routes))

# Workaround admin user management route
@bp.route('/admin/users')
@login_required
@admin_required
def admin_manage_users():
    """Admin page to view and manage users - workaround route"""
    try:
        from app.models import User
        page = request.args.get("page", 1, type=int)
        per_page = 25
        
        # Filter parameters
        search = request.args.get("search", "").strip()
        email_filter = request.args.get("email_filter", "").strip()
        status_filter = request.args.get("status_filter", "")
        role_filter = request.args.get("role_filter", "")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        
        # Base query
        query = User.query
        
        # Apply search filter (username or email)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                User.username.ilike(search_pattern) | 
                User.email.ilike(search_pattern) |
                User.first_name.ilike(search_pattern) |
                User.last_name.ilike(search_pattern)
            )
        
        # Apply email domain filter
        if email_filter:
            query = query.filter(User.email.ilike(f"%{email_filter}%"))
        
        # Apply status filter
        if status_filter == "active":
            query = query.filter(User.is_active == True)
        elif status_filter == "inactive":
            query = query.filter(User.is_active == False)
        
        # Apply role filter
        if role_filter == "admin":
            query = query.filter(User.is_admin == True)
        elif role_filter == "user":
            query = query.filter(User.is_admin == False)
        elif role_filter == "google":
            query = query.filter(User.is_google_user == True)
        
        # Apply date range filter
        if date_from:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(User.created_at >= date_from_obj)
        if date_to:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            date_to_obj = date_to_obj + timedelta(days=1)  # Include the entire day
            query = query.filter(User.created_at < date_to_obj)
        
        # Get statistics
        total_users = User.query.count()
        active_users = User.query.filter(User.is_active == True).count()
        admin_users = User.query.filter(User.is_admin == True).count()
        google_users = User.query.filter(User.is_google_user == True).count()
        
        # Check for testform.xyz users
        testform_users = User.query.filter(User.email.ilike('%testform.xyz')).count()
        
        # Paginate the results
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template(
            "admin/manage_users.html",
            users=users,
            search=search,
            email_filter=email_filter,
            status_filter=status_filter,
            role_filter=role_filter,
            date_from=date_from,
            date_to=date_to,
            total_users=total_users,
            active_users=active_users,
            admin_users=admin_users,
            google_users=google_users,
            testform_users=testform_users
        )
        
    except Exception as e:
        logger.error(f"Error loading users: {str(e)}")
        return f"<h1>Error Loading Users</h1><p>Error: {str(e)}</p>"

@bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    """Delete a specific user - workaround route"""
    try:
        from app.models import User
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting yourself
        if user.id == current_user.id:
            flash("You cannot delete your own account.", "error")
            return redirect(url_for("main.admin_manage_users"))
        
        # Store user info for logging
        username = user.username
        email = user.email
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f"User '{username}' ({email}) has been successfully deleted.", "success")
        logger.info(f"Admin {current_user.username} deleted user {username} ({email})")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        flash(f"Error deleting user: {str(e)}", "error")
    
    return redirect(url_for("main.admin_manage_users"))

@bp.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def admin_toggle_user_status(user_id):
    """Toggle user active status - workaround route"""
    try:
        from app.models import User
        user = User.query.get_or_404(user_id)
        
        # Prevent deactivating yourself
        if user.id == current_user.id:
            flash("You cannot deactivate your own account.", "error")
            return redirect(url_for("main.admin_manage_users"))
        
        # Toggle status
        user.is_active = not user.is_active
        db.session.commit()
        
        status = "activated" if user.is_active else "deactivated"
        flash(f"User '{user.username}' has been {status}.", "success")
        logger.info(f"Admin {current_user.username} {status} user {user.username}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling user status {user_id}: {str(e)}")
        flash(f"Error updating user status: {str(e)}", "error")
    
    return redirect(url_for("main.admin_manage_users"))

@bp.route('/admin/users/bulk-action', methods=['POST'])
@login_required
@admin_required
def admin_bulk_user_action():
    """Perform bulk actions on users - workaround route"""
    try:
        from app.models import User
        action = request.form.get('action')
        user_ids = request.form.getlist('user_ids[]')
        
        if not user_ids:
            flash("No users selected.", "error")
            return redirect(url_for("main.admin_manage_users"))
        
        user_ids = [int(uid) for uid in user_ids]
        
        # Prevent actions on yourself
        if current_user.id in user_ids:
            flash("You cannot perform bulk actions on your own account.", "error")
            return redirect(url_for("main.admin_manage_users"))
        
        if action == 'delete':
            users = User.query.filter(User.id.in_(user_ids)).all()
            usernames = [user.username for user in users]
            
            for user in users:
                db.session.delete(user)
            
            db.session.commit()
            flash(f"Successfully deleted {len(users)} users: {', '.join(usernames)}", "success")
            logger.info(f"Admin {current_user.username} bulk deleted users: {usernames}")
            
        elif action == 'deactivate':
            User.query.filter(User.id.in_(user_ids)).update({'is_active': False})
            db.session.commit()
            flash(f"Successfully deactivated {len(user_ids)} users.", "success")
            logger.info(f"Admin {current_user.username} bulk deactivated {len(user_ids)} users")
            
        elif action == 'activate':
            User.query.filter(User.id.in_(user_ids)).update({'is_active': True})
            db.session.commit()
            flash(f"Successfully activated {len(user_ids)} users.", "success")
            logger.info(f"Admin {current_user.username} bulk activated {len(user_ids)} users")
            
        elif action == 'delete_testform':
            # Special action to delete all testform.xyz users
            testform_users = User.query.filter(User.email.ilike('%testform.xyz')).all()
            testform_emails = [user.email for user in testform_users]
            
            for user in testform_users:
                db.session.delete(user)
            
            db.session.commit()
            flash(f"Successfully deleted {len(testform_users)} testform.xyz users: {', '.join(testform_emails)}", "success")
            logger.info(f"Admin {current_user.username} deleted all testform.xyz users: {testform_emails}")
        
        else:
            flash("Invalid action.", "error")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error performing bulk action: {str(e)}")
        flash(f"Error performing bulk action: {str(e)}", "error")
    
    return redirect(url_for("main.admin_manage_users"))

# Simple admin dashboard workaround
@bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard - workaround route"""
    return render_template("admin/index.html")

# Stock News API Routes
@bp.route('/api/stock/<symbol>/news-status')
@login_required
def get_stock_news_status(symbol):
    """Get news processing status for a stock symbol"""
    try:
        # Use new service to check recent news status
        status = StockNewsService.check_recent_news_status(symbol)
        return jsonify({
            'symbol': symbol,
            'has_recent_news': status['has_recent_news'],
            'latest_article_age_hours': status['latest_article_age_hours'],
            'total_recent_articles': status['total_recent_articles'],
            'should_fetch': status['should_fetch']
        })
    except Exception as e:
        logger.error(f"Error getting news status for {symbol}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/stock/<symbol>/recent-news')
@login_required
def get_stock_recent_news(symbol):
    """Get recent news articles for a stock symbol"""
    try:
        from app.utils.search.news_search import NewsSearch
        from app.models import NewsArticle, ArticleSymbol
        from app import db
        
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50 articles
        
        # Get symbol variants for comprehensive search
        news_search = NewsSearch(db.session)
        symbol_variants = news_search.get_symbol_variants(symbol)
        
        # Query recent articles with any of the symbol variants
        recent_articles = db.session.query(NewsArticle).join(ArticleSymbol).filter(
            ArticleSymbol.symbol.in_(symbol_variants)
        ).order_by(NewsArticle.published_at.desc()).limit(limit).all()
        
        articles = [article.to_dict() for article in recent_articles]
        
        return jsonify({
            'symbol': symbol,
            'articles': articles,
            'count': len(articles),
            'symbol_variants': symbol_variants[:3]  # Show first 3 variants used
        })
    except Exception as e:
        logger.error(f"Error getting recent news for {symbol}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/stock/<symbol>/fetch-news', methods=['POST'])
@login_required
def trigger_stock_news_fetch(symbol):
    """Manually trigger news fetch for a stock symbol"""
    try:
        # Always use the new auto check and fetch method
        result = StockNewsService.auto_check_and_fetch_news(symbol)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error triggering news fetch for {symbol}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/analysis-summary', methods=['POST'])
@login_required
def get_analysis_summary():
    """Get cached analysis summary for immediate display"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper()
        lookback_days = int(data.get('lookback_days', 365))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Check for cached analysis results
        from app.utils.cache.optimized_long_period_cache import long_period_cache
        cached_analysis = long_period_cache.get_progressive_analysis(ticker, lookback_days, end_date)
        
        if cached_analysis:
            return jsonify({
                'cached': True,
                'score': cached_analysis.get('score'),
                'trend': cached_analysis.get('trend'),
                'period': f"{lookback_days} days",
                'last_updated': cached_analysis.get('last_updated')
            })
        
        return jsonify({'cached': False})
        
    except Exception as e:
        logger.error(f"Error getting analysis summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/basic-chart', methods=['POST'])
@login_required 
def get_basic_chart():
    """Get basic price chart for immediate display"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper()
        lookback_days = int(data.get('lookback_days', 365))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        from app.utils.cache.optimized_long_period_cache import long_period_cache
        
        # Check for cached compressed chart data
        cached_chart = long_period_cache.get_compressed_chart_data(ticker, lookback_days, end_date)
        if cached_chart:
            return jsonify(cached_chart)
        
        # Generate basic chart with compressed data
        from app.utils.data.data_service import DataService
        data_service = DataService()
        
        # For long periods, use weekly data for faster loading
        if lookback_days > 365:
            # Get recent 3 months daily + older weekly data
            end_dt = pd.to_datetime(end_date)
            recent_start = end_dt - timedelta(days=90)
            
            # Get recent daily data (last 3 months)
            recent_data = data_service.get_historical_data(
                ticker, recent_start.strftime('%Y-%m-%d'), end_date
            )
            
            # Get older data and resample to weekly
            old_start = end_dt - timedelta(days=lookback_days)
            old_data = data_service.get_historical_data(
                ticker, old_start.strftime('%Y-%m-%d'), recent_start.strftime('%Y-%m-%d')
            )
            
            if not old_data.empty:
                # Resample to weekly for faster rendering
                old_data_weekly = old_data.resample('W').agg({
                    'Open': 'first',
                    'High': 'max', 
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
                
                # Combine data
                combined_data = pd.concat([old_data_weekly, recent_data]).sort_index()
            else:
                combined_data = recent_data
        else:
            # For shorter periods, use full daily data
            combined_data = data_service.get_historical_data(
                ticker, (pd.to_datetime(end_date) - timedelta(days=lookback_days)).strftime('%Y-%m-%d'), end_date
            )
        
        if combined_data.empty:
            return jsonify({'error': 'No data available'}), 404
        
        # Create basic chart with just price line
        chart_data = {
            'data': [
                {
                    'x': combined_data.index.strftime('%Y-%m-%d').tolist(),
                    'y': combined_data['Close'].tolist(),
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': f'{ticker} Price',
                    'line': {'color': '#1f77b4', 'width': 2}
                }
            ],
            'layout': {
                'title': f'{ticker} - Basic Price Chart',
                'xaxis': {'title': 'Date'},
                'yaxis': {'title': 'Price'},
                'height': 400,
                'showlegend': False
            }
        }
        
        # Cache the compressed chart
        long_period_cache.set_compressed_chart_data(ticker, lookback_days, end_date, chart_data)
        
        return jsonify(chart_data)
        
    except Exception as e:
        logger.error(f"Error generating basic chart: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/enhanced-chart', methods=['POST'])
@login_required
def get_enhanced_chart():
    """Get enhanced chart with technical indicators"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper()
        lookback_days = int(data.get('lookback_days', 365))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get the data using optimized service
        from app.utils.data.data_service import DataService
        data_service = DataService()
        
        historical_data = data_service.get_historical_data(
            ticker,
            (pd.to_datetime(end_date) - timedelta(days=lookback_days + 30)).strftime('%Y-%m-%d'),
            end_date
        )
        
        if historical_data.empty:
            return jsonify({'error': 'No data available'}), 404
        
        # Add basic technical indicators
        historical_data['SMA20'] = historical_data['Close'].rolling(window=20).mean()
        historical_data['SMA50'] = historical_data['Close'].rolling(window=50).mean()
        
        # Create enhanced chart
        chart_data = {
            'data': [
                {
                    'x': historical_data.index.strftime('%Y-%m-%d').tolist(),
                    'y': historical_data['Close'].tolist(),
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': f'{ticker} Price',
                    'line': {'color': '#1f77b4', 'width': 2}
                },
                {
                    'x': historical_data.index.strftime('%Y-%m-%d').tolist(),
                    'y': historical_data['SMA20'].tolist(),
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': 'SMA 20',
                    'line': {'color': '#ff7f0e', 'width': 1}
                },
                {
                    'x': historical_data.index.strftime('%Y-%m-%d').tolist(),
                    'y': historical_data['SMA50'].tolist(),
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': 'SMA 50',
                    'line': {'color': '#2ca02c', 'width': 1}
                }
            ],
            'layout': {
                'title': f'{ticker} - Technical Analysis',
                'xaxis': {'title': 'Date'},
                'yaxis': {'title': 'Price'},
                'height': 500,
                'showlegend': True
            }
        }
        
        return jsonify(chart_data)
        
    except Exception as e:
        logger.error(f"Error generating enhanced chart: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/full-analysis', methods=['POST'])
@login_required
def get_full_analysis():
    """Get complete analysis dashboard"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper()
        lookback_days = int(data.get('lookback_days', 365))
        crossover_days = int(data.get('crossover_days', 364))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Use the existing create_stock_visualization function
        from app.utils.analyzer.stock_analyzer import create_stock_visualization
        
        fig = create_stock_visualization(
            ticker=ticker,
            end_date=end_date,
            lookback_days=lookback_days,
            crossover_days=crossover_days
        )
        
        # Convert to JSON
        analysis_data = fig.to_dict()
        
        # Cache the progressive analysis result
        from app.utils.cache.optimized_long_period_cache import long_period_cache
        progressive_data = {
            'score': None,  # Extract from analysis if available
            'trend': None,  # Extract from analysis if available
            'last_updated': datetime.now().isoformat()
        }
        long_period_cache.set_progressive_analysis(ticker, lookback_days, end_date, progressive_data)
        
        return jsonify(analysis_data)
        
    except Exception as e:
        logger.error(f"Error generating full analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/company-info/<ticker>', methods=['GET'])
@login_required
def get_company_info_api(ticker):
    """Get cached company information for a ticker"""
    try:
        from app.utils.cache.company_info_cache import company_info_cache
        
        # Get query parameters
        categories = request.args.get('categories', '').split(',') if request.args.get('categories') else None
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        if refresh:
            company_info = company_info_cache.refresh_company_info(ticker, categories)
        else:
            company_info = company_info_cache.get_company_info(ticker, categories)
        
        if not company_info:
            return jsonify({'error': f'No company information found for {ticker}'}), 404
        
        # Remove internal metadata before returning
        filtered_info = {k: v for k, v in company_info.items() if not k.startswith('_')}
        
        return jsonify({
            'ticker': ticker.upper(),
            'info': filtered_info,
            'cache_stats': company_info_cache.get_cache_stats(ticker)
        })
        
    except Exception as e:
        logger.error(f"Error getting company info for {ticker}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/company-info/basic/<ticker>', methods=['GET'])
@login_required
def get_basic_company_info_api(ticker):
    """Get essential company information (optimized for common use)"""
    try:
        from app.utils.cache.company_info_cache import company_info_cache
        
        company_info = company_info_cache.get_basic_company_info(ticker)
        
        if not company_info:
            return jsonify({'error': f'No basic company information found for {ticker}'}), 404
        
        # Format for display
        formatted_info = {
            'name': company_info.get('longName', company_info.get('shortName', 'N/A')),
            'sector': company_info.get('sector', 'N/A'),
            'industry': company_info.get('industry', 'N/A'),
            'country': company_info.get('country', 'N/A'),
            'employees': company_info.get('fullTimeEmployees', 'N/A'),
            'market_cap': company_info.get('marketCap'),
            'pe_ratio': company_info.get('forwardPE'),
            'website': company_info.get('website', 'N/A')
        }
        
        return jsonify({
            'ticker': ticker.upper(),
            'basic_info': formatted_info,
            'cached': True
        })
        
    except Exception as e:
        logger.error(f"Error getting basic company info for {ticker}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/company-info/market-data/<ticker>', methods=['GET'])
@login_required
def get_market_data_api(ticker):
    """Get real-time market data (short cache)"""
    try:
        from app.utils.cache.company_info_cache import company_info_cache
        
        market_data = company_info_cache.get_market_data(ticker)
        
        if not market_data:
            return jsonify({'error': f'No market data found for {ticker}'}), 404
        
        return jsonify({
            'ticker': ticker.upper(),
            'market_data': market_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting market data for {ticker}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/company-info/bulk-cache', methods=['POST'])
@login_required
def bulk_cache_company_info():
    """Bulk cache company information for multiple tickers"""
    try:
        data = request.get_json()
        tickers = data.get('tickers', [])
        batch_size = data.get('batch_size', 10)
        
        if not tickers:
            return jsonify({'error': 'No tickers provided'}), 400
        
        if len(tickers) > 100:
            return jsonify({'error': 'Maximum 100 tickers allowed per request'}), 400
        
        from app.utils.cache.company_info_cache import company_info_cache
        results = company_info_cache.bulk_cache_company_info(tickers, batch_size)
        
        successful = sum(results.values())
        
        return jsonify({
            'total_tickers': len(tickers),
            'successful': successful,
            'failed': len(tickers) - successful,
            'success_rate': f"{(successful/len(tickers)*100):.1f}%",
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in bulk cache operation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/company-info/cache-stats', methods=['GET'])
@login_required
def get_cache_stats():
    """Get cache statistics"""
    try:
        ticker = request.args.get('ticker')
        
        from app.utils.cache.company_info_cache import company_info_cache
        stats = company_info_cache.get_cache_stats(ticker)
        
        return jsonify({
            'cache_stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/company-info/warm-cache', methods=['POST'])
@login_required
def warm_popular_stocks_cache():
    """Warm cache with popular stocks for better performance"""
    try:
        # Get popular stocks from the tickers file
        popular_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK-A',
            'JNJ', 'V', 'WMT', 'PG', 'JPM', 'UNH', 'MA', 'HD', 'DIS', 'BAC',
            'ADBE', 'CRM', 'NFLX', 'XOM', 'KO', 'PEP', 'COST', 'TMO', 'ABT',
            'CSCO', 'AVGO', 'ACN', 'LLY', 'CMCSA', 'DHR', 'TXN', 'NEE', 'VZ'
        ]
        
        from app.utils.cache.company_info_cache import company_info_cache
        results = company_info_cache.bulk_cache_company_info(popular_tickers, batch_size=5)
        
        successful = sum(results.values())
        
        return jsonify({
            'message': 'Cache warming completed',
            'total_stocks': len(popular_tickers),
            'cached_successfully': successful,
            'success_rate': f"{(successful/len(popular_tickers)*100):.1f}%",
            'failed_tickers': [ticker for ticker, success in results.items() if not success]
        })
        
    except Exception as e:
        logger.error(f"Error warming cache: {str(e)}")
        return jsonify({'error': str(e)}), 500

