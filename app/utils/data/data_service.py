# app/data/data_service.py

import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.utils.config.metrics_config import METRICS_MAP, CAGR_METRICS
from sqlalchemy import create_engine, inspect, text
import os
import logging
import re
from app.utils.visualization.visualization_service import is_stock
from app.utils.cache.stock_cache import stock_cache
from app.utils.cache.optimized_long_period_cache import long_period_cache

from time import sleep
from functools import wraps
import random
import time
import traceback

# Configure logger
logger = logging.getLogger(__name__)

def retry_with_backoff(retries: int = 3, backoff_in_seconds: float = 1.0):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:
                        raise e
                    wait_time = backoff_in_seconds * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

class RateLimiter:
    def __init__(self, calls_per_second=2):
        self.calls_per_second = calls_per_second
        self.last_call_time = 0

    def wait(self):
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        time_to_wait = (1.0 / self.calls_per_second) - time_since_last_call
        
        if time_to_wait > 0:
            sleep(time_to_wait)
            
        self.last_call_time = time.time()

class DataService:
    def __init__(self):
        """Initialize DataService with API and database configuration"""
        self.API_KEY = os.getenv("ROIC_API_KEY", "")
        self.BASE_URL = "https://api.roic.ai/v1/rql"
        self.METRICS = METRICS_MAP
        self.CAGR_METRICS = CAGR_METRICS
        
        # Database configuration
        self.engine = create_engine(
            f"mysql+pymysql://{os.getenv('MYSQL_USER')}:"
            f"{os.getenv('MYSQL_PASSWORD')}@"
            f"{os.getenv('MYSQL_HOST')}:"
            f"{os.getenv('MYSQL_PORT', '3306')}/"
            f"{os.getenv('MYSQL_DATABASE')}"
        )

        self.cache = stock_cache
        self.long_cache = long_period_cache

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in database"""
        try:
            inspector = inspect(self.engine)
            return table_name in inspector.get_table_names()
        except Exception as e:
            print(f"Error checking table existence: {e}")
            return False

    def store_dataframe(self, df: pd.DataFrame, table_name: str) -> bool:
        """Store DataFrame in database"""
        try:
            df.to_sql(
                name=table_name,
                con=self.engine,
                index=True,
                if_exists='replace',
                chunksize=10000
            )
            print(f"Successfully stored data in table: {table_name}")
            return True
        except Exception as e:
            print(f"Error storing DataFrame in table {table_name}: {e}")
            return False

    def clean_ticker_for_table_name(self, ticker: str) -> str:
        """
        Clean ticker symbol for use in table name.
        Removes special characters and converts to valid table name format.
        
        Parameters:
        -----------
        ticker : str
            Original ticker symbol
        
        Returns:
        --------
        str
            Cleaned ticker symbol safe for use in table names
        """
        # Replace any non-alphanumeric characters with underscore
        cleaned = ''.join(c if c.isalnum() else '_' for c in ticker)
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        # Convert to lowercase
        cleaned = cleaned.lower()
        # If the cleaned string is empty, use a default
        if not cleaned:
            cleaned = 'unknown'
        return cleaned
    
    def check_for_corporate_actions_in_data(self, df: pd.DataFrame) -> bool:
        """
        Check if DataFrame contains any corporate actions (stock splits or dividends)
        
        Parameters:
        -----------
        df : pd.DataFrame
            DataFrame containing historical data with Dividends and Stock Splits columns
            
        Returns:
        --------
        bool
            True if corporate actions are found, False otherwise
        """
        try:
            # Check for dividends (any non-zero value)
            has_dividends = False
            if 'Dividends' in df.columns:
                has_dividends = (df['Dividends'] > 0).any()
            
            # Check for stock splits (any non-zero value)
            has_splits = False
            if 'Stock Splits' in df.columns:
                has_splits = (df['Stock Splits'] > 0).any()
            
            if has_dividends or has_splits:
                logger.info(f"Corporate actions detected: Dividends={has_dividends}, Stock Splits={has_splits}")
                if has_dividends:
                    dividend_dates = df[df['Dividends'] > 0].index.tolist()
                    logger.info(f"Dividend dates: {[d.strftime('%Y-%m-%d') for d in dividend_dates]}")
                if has_splits:
                    split_dates = df[df['Stock Splits'] > 0].index.tolist()
                    logger.info(f"Stock split dates: {[d.strftime('%Y-%m-%d') for d in split_dates]}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for corporate actions: {e}")
            return False
    
    def format_yahoo_symbol(self, symbol):
        """Format a stock symbol for Yahoo Finance (supports HK, SS, SZ, US)"""
        s = symbol.upper()
        if s.isdigit() and len(s) == 4:
            return s.zfill(4) + '.HK'
        if s.isdigit() and len(s) == 6 and s.startswith('6'):
            return s + '.SS'
        if s.isdigit() and len(s) == 6 and (s.startswith('0') or s.startswith('3')):
            return s + '.SZ'
        return s

    @retry_with_backoff(retries=3, backoff_in_seconds=0.1)
    def get_historical_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Retrieve historical stock data with optimized caching for long periods.
        
        Strategy:
        1. For periods > 1 year: Use partitioned caching
        2. For shorter periods: Use standard caching
        3. Always ensure fresh data for current day
        """
        # Format ticker for Yahoo
        ticker = self.format_yahoo_symbol(ticker)
        
        # Calculate lookback period
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        lookback_days = (end_dt - start_dt).days
        
        # Check if this is a long-period analysis (> 365 days)
        if lookback_days > 365:
            return self._get_long_period_data(ticker, lookback_days, end_date)
        else:
            return self._get_standard_period_data(ticker, start_date, end_date)
    
    def _get_long_period_data(self, ticker: str, lookback_days: int, end_date: str) -> pd.DataFrame:
        """Handle long-period data retrieval with partitioned caching"""
        start_time = time.time()
        
        # SPECIAL HANDLING FOR SP500 (^GSPC) - Check SP500 data cache first
        if ticker == '^GSPC':
            try:
                from app.utils.cache.sp500_data_cache import sp500_data_cache
                
                end_dt = pd.to_datetime(end_date)
                start_dt = end_dt - timedelta(days=lookback_days + 10)  # Add buffer for weekends
                start_date_str = start_dt.strftime('%Y-%m-%d')
                
                # Check SP500 data cache first
                cached_sp500_data = sp500_data_cache.get_sp500_data(start_date_str, end_date)
                if cached_sp500_data is not None and not cached_sp500_data.empty:
                    duration = time.time() - start_time
                    logger.info(f"🎯 Long-period SP500 data cache hit for {ticker} ({duration*1000:.1f}ms, {len(cached_sp500_data)} rows)")
                    return cached_sp500_data
                    
            except Exception as cache_error:
                logger.warning(f"⚠️ SP500 long-period data cache lookup failed: {str(cache_error)}")
        
        # For non-SP500 tickers, try partitioned cache first
        if ticker != '^GSPC':
            cached_data, was_cached = self.long_cache.get_partitioned_data(ticker, lookback_days, end_date)
            
            if cached_data is not None:
                duration = time.time() - start_time
                logger.info(f"🎯 Long-period partitioned cache hit for {ticker} ({duration*1000:.1f}ms, {len(cached_data)} rows)")
                return cached_data
        
        # Fetch fresh data if not cached
        logger.info(f"🔄 Fetching long-period data for {ticker} ({lookback_days} days)")
        
        end_dt = pd.to_datetime(end_date)
        start_dt = end_dt - timedelta(days=lookback_days + 10)  # Add buffer for weekends
        
        df = self._get_data_from_yfinance_direct(ticker, start_dt.strftime('%Y-%m-%d'), end_date)
        
        if df is not None and not df.empty:
            # Cache using appropriate strategy
            if ticker == '^GSPC':
                # Use SP500 data cache for ^GSPC
                try:
                    from app.utils.cache.sp500_data_cache import sp500_data_cache
                    sp500_data_cache.set_sp500_data(start_dt.strftime('%Y-%m-%d'), end_date, df)
                    logger.debug(f"💾 Long-period SP500 data cached for {ticker}")
                except Exception as cache_error:
                    logger.warning(f"⚠️ Failed to cache long-period SP500 data: {str(cache_error)}")
            else:
                # Cache using partitioned strategy for other tickers
                self.long_cache.set_partitioned_data(ticker, df, lookback_days, end_date)
            
            duration = time.time() - start_time
            logger.info(f"✅ Long-period data fetched and cached for {ticker} ({duration*1000:.1f}ms, {len(df)} rows)")
            
        return df
    
    def _get_standard_period_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Handle standard period data retrieval with existing caching"""
        # Convert dates to datetime for comparison
        end_dt = pd.to_datetime(end_date)
        today = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
        
        # SPECIAL HANDLING FOR SP500 (^GSPC) - Use dedicated SP500 data cache
        if ticker == '^GSPC':
            try:
                from app.utils.cache.sp500_data_cache import sp500_data_cache
                
                # Check SP500 data cache first
                cached_sp500_data = sp500_data_cache.get_sp500_data(start_date, end_date)
                if cached_sp500_data is not None and not cached_sp500_data.empty:
                    logger.debug(f"🎯 SP500 data cache hit for {ticker} ({start_date} to {end_date})")
                    return cached_sp500_data
                    
            except Exception as cache_error:
                logger.warning(f"⚠️ SP500 data cache lookup failed: {str(cache_error)}")
        
        # If end date is today, always fetch fresh data
        if end_dt.date() >= today.date():
            logger.debug(f"🔄 End date is current day, fetching fresh data for {ticker}")
            # Add 1 day to ensure we get latest price
            adjusted_end_date = (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            df = self._get_data_from_yfinance_direct(ticker, start_date, adjusted_end_date)
            
            if df is not None and not df.empty:
                # Cache with shorter expiration for current day data
                if ticker == '^GSPC':
                    # Use SP500 data cache for ^GSPC
                    try:
                        from app.utils.cache.sp500_data_cache import sp500_data_cache
                        sp500_data_cache.set_sp500_data(start_date, end_date, df)
                        logger.debug(f"💾 SP500 data cached for {ticker}")
                    except Exception as cache_error:
                        logger.warning(f"⚠️ Failed to cache SP500 data: {str(cache_error)}")
                else:
                    # Use regular stock cache for other tickers
                    stock_cache.set_stock_data(ticker, start_date, end_date, df.to_dict('records'), expire=300)  # 5 minutes
                
            return df
        
        # For historical data, check cache first (non-SP500 tickers)
        if ticker != '^GSPC':
            cached_data = stock_cache.get_stock_data(ticker, start_date, end_date)
            if cached_data is not None:
                logger.debug(f"🎯 Stock data cache hit for {ticker} ({start_date} to {end_date})")
                # Convert cached dict back to DataFrame
                df = pd.DataFrame(cached_data)
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                return df
        
        # Fetch from yfinance if not cached
        logger.debug(f"🔄 Cache miss, fetching data from yfinance for {ticker}")
        df = self._get_data_from_yfinance_direct(ticker, start_date, end_date)
        
        if df is not None and not df.empty:
            # Cache the result
            if ticker == '^GSPC':
                # Use SP500 data cache for ^GSPC
                try:
                    from app.utils.cache.sp500_data_cache import sp500_data_cache
                    sp500_data_cache.set_sp500_data(start_date, end_date, df)
                    logger.debug(f"💾 SP500 data cached for {ticker}")
                except Exception as cache_error:
                    logger.warning(f"⚠️ Failed to cache SP500 data: {str(cache_error)}")
            else:
                # Use regular stock cache for other tickers
                stock_cache.set_stock_data(ticker, start_date, end_date, df.to_dict('records'), expire=3600)  # 1 hour
            
        return df

    def _get_data_from_yfinance_direct(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get historical data directly from yfinance with enhanced validation.
        """
        try:
            # Create yfinance Ticker object
            ticker_obj = yf.Ticker(ticker)
            
            # Convert end_date to datetime for comparison
            end_dt = pd.to_datetime(end_date)
            today = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
            
            # If fetching current data, add 1 day to ensure latest prices
            if end_dt.date() >= today.date():
                adjusted_end = (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
                logger.debug(f"📅 Adjusted end date from {end_date} to {adjusted_end} for latest data")
                end_date = adjusted_end
            
            # Get data for date range with retry on empty result
            df = pd.DataFrame()
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    df = ticker_obj.history(start=start_date, end=end_date)
                    if not df.empty:
                        break
                    logger.warning(f"Empty data on attempt {attempt + 1} for {ticker}")
                    time.sleep(0.5)  # Brief pause before retry
                except Exception as e:
                    logger.warning(f"yfinance error on attempt {attempt + 1} for {ticker}: {str(e)}")
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(1.0)  # Longer pause on error
            
            if df.empty:
                logger.error(f"No data available for {ticker} from {start_date} to {end_date}")
                return pd.DataFrame()
            
            # Data validation and cleaning
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns for {ticker}: {missing_columns}")
                return pd.DataFrame()
            
            # Validate data range
            if len(df) < 5:
                logger.warning(f"Insufficient data points for {ticker}: {len(df)} rows")
                return pd.DataFrame()
            
            # Clean and process data
            df = df.dropna(subset=['Close'])  # Remove rows with missing close prices
            if 'Dividends' in df.columns:
                df['Dividends'] = df['Dividends'].fillna(0)
            if 'Stock Splits' in df.columns:
                df['Stock Splits'] = df['Stock Splits'].fillna(0)
            
            # Remove timezone information for consistency
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            # Sort by date
            df = df.sort_index()
            
            logger.debug(f"✅ Successfully retrieved {len(df)} rows for {ticker} from {start_date} to {end_date}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return pd.DataFrame()

    def get_financial_data(self, ticker: str, metric_description: str, 
                        start_year: str, end_year: str) -> pd.Series:
        """
        Get financial data from MySQL database or ROIC API if not exists/incomplete.
        REDIS CACHED: Checks cache first to avoid expensive API calls.
        """
        # TRY CACHE FIRST
        cached_data = stock_cache.get_financial_data(ticker, metric_description, start_year, end_year)
        if cached_data is not None:
            logger.debug(f"🎯 Financial data cache hit for {ticker} {metric_description} ({start_year}-{end_year})")
            return pd.Series(cached_data['values'], index=cached_data['years'], name=metric_description)
        
        cleaned_ticker = self.clean_ticker_for_table_name(ticker)
        table_name = f"roic_{cleaned_ticker}"
        MAX_MISSING_YEARS_TOLERANCE = 2 
        # company_name = yf.Ticker(ticker).info['longName']
        
        try:
            # First try to get data from database
            # if "^" in ticker or "-" in ticker or "=" in ticker:
            #     return None
            if not is_stock(ticker):
                return None
            # if company_name:
            # # Check for excluded terms using regex (case insensitive)
            #     excluded_terms = r'shares|etf|index|trust'
            #     if re.search(excluded_terms, company_name, re.IGNORECASE):
            #         return None
                
            
            if self.table_exists(table_name):
                print(f"Getting financial data for {ticker} from database")
                df = pd.read_sql_table(table_name, self.engine)
                
                metric_field = self.METRICS.get(metric_description.lower())
                if metric_field in df.columns:
                    df['fiscal_year'] = df['fiscal_year'].astype(int)
                    
                    # Filter for requested years
                    mask = (df['fiscal_year'] >= int(start_year)) & (df['fiscal_year'] <= int(end_year))
                    filtered_df = df[mask]
                    
                    # Check if we have all the years we need
                    requested_years = set(range(int(start_year), int(end_year) + 1))
                    actual_years = set(filtered_df['fiscal_year'].values)
                    missing_years = requested_years - actual_years
                    
                    result_series = pd.Series(
                            filtered_df[metric_field].values,
                            index=filtered_df['fiscal_year'],
                            name=metric_description
                        )
                    
                    # CACHE THE RESULT
                    stock_cache.set_financial_data(ticker, metric_description, start_year, end_year, result_series, expire=7200)  # 2 hours
                    logger.debug(f"💾 Cached financial data for {ticker} {metric_description} ({start_year}-{end_year})")
                    
                    return result_series
                    # if len(missing_years) == 0:
                    # if len(missing_years) <= MAX_MISSING_YEARS_TOLERANCE:
                    #     return pd.Series(
                    #         filtered_df[metric_field].values,
                    #         index=filtered_df['fiscal_year'],
                    #         name=metric_description
                    #     )
                    # else:
                    #     print(f"Incomplete data for {ticker}, fetching from API")
                    #     # If data is incomplete, fetch all data and update database
                    #     success = self.store_financial_data(ticker, start_year, end_year)
                    #     if success:
                    #         df = pd.read_sql_table(table_name, self.engine)
                    #         df['fiscal_year'] = df['fiscal_year'].astype(int)
                    #         mask = (df['fiscal_year'] >= int(start_year)) & (df['fiscal_year'] <= int(end_year))
                    #         filtered_df = df[mask]
                    #         return pd.Series(
                    #             filtered_df[metric_field].values,
                    #             index=filtered_df['fiscal_year'],
                    #             name=metric_description
                    #         )

            # If not in database, store it first
            print(f"Data not found in database for {ticker}, fetching from API")
            success = self.store_financial_data(ticker, start_year, end_year)
            if success:
                df = pd.read_sql_table(table_name, self.engine)
                metric_field = self.METRICS.get(metric_description.lower())
                df['fiscal_year'] = df['fiscal_year'].astype(int)
                mask = (df['fiscal_year'] >= int(start_year)) & (df['fiscal_year'] <= int(end_year))
                filtered_df = df[mask]
                result_series = pd.Series(
                    filtered_df[metric_field].values,
                    index=filtered_df['fiscal_year'],
                    name=metric_description
                )
                
                # CACHE THE RESULT
                stock_cache.set_financial_data(ticker, metric_description, start_year, end_year, result_series, expire=7200)  # 2 hours
                logger.debug(f"💾 Cached new financial data for {ticker} {metric_description} ({start_year}-{end_year})")
                
                return result_series
            else:
                return None
                
        except Exception as e:
            print(f"Error in get_financial_data for {ticker}: {str(e)}")
            return None
    
    def store_historical_data(self, ticker: str, start_date: str = None, end_date: str = None) -> bool:
        """
        Fetch and store historical price data from yfinance.
        Uses custom date range if provided, otherwise defaults to 10 years of data.
        
        Parameters:
        -----------
        ticker : str
            Stock ticker symbol
        start_date : str, optional
            Start date in YYYY-MM-DD format
        end_date : str, optional
            End date in YYYY-MM-DD format
        
        Returns:
        --------
        bool
            Success status of the operation
        """
        try:
            print(f"Fetching historical data for {ticker} from yfinance")
            ticker_obj = yf.Ticker(ticker)
            
            # Get the latest trading day (last Friday if weekend)
            latest_trading_day = pd.Timestamp.now()
            while latest_trading_day.weekday() > 4:  # 5 = Saturday, 6 = Sunday
                latest_trading_day -= pd.Timedelta(days=1)
                
            # If no dates specified, use default 10 year range
            if start_date is None or end_date is None:
                end_date = latest_trading_day.strftime('%Y-%m-%d')
                start_date = (latest_trading_day - pd.DateOffset(years=20)).strftime('%Y-%m-%d')
                df = ticker_obj.history(start=start_date)
            else:
                # Use specified date range but ensure end_date isn't beyond latest trading day
                end_date = min(pd.to_datetime(end_date), latest_trading_day).strftime('%Y-%m-%d')
                df = ticker_obj.history(start=start_date, end=end_date)
            
            if df.empty:
                print(f"No historical data found for {ticker}")
                return False
            
            # Process the data
            df.index = df.index.tz_localize(None)
            cleaned_ticker = self.clean_ticker_for_table_name(ticker)
            table_name = f"his_{cleaned_ticker}"
            
            # Store in database
            return self.store_dataframe(df, table_name)
                    
        except Exception as e:
            print(f"Error storing historical data for {ticker}: {e}")
            return False
    
    
    def calculate_roic(self, income_stmt, balance_sheet, date):
        """Calculate ROIC = (Operating Income - Tax) / (Total Assets - Total Current Liabilities)"""
        try:
            operating_income = 0
            if 'Operating Income' in income_stmt.index:
                operating_income = float(income_stmt.loc['Operating Income', date] or 0)
            
            income_tax = 0
            if 'Income Tax Expense' in income_stmt.index:
                income_tax = float(income_stmt.loc['Income Tax Expense', date] or 0)
            
            total_assets = 0
            total_current_liabilities = 0
            
            if date in balance_sheet.columns:
                if 'Total Assets' in balance_sheet.index:
                    total_assets = float(balance_sheet.loc['Total Assets', date] or 0)
                if 'Total Current Liabilities' in balance_sheet.index:
                    total_current_liabilities = float(balance_sheet.loc['Total Current Liabilities', date] or 0)
            
            numerator = operating_income - income_tax
            denominator = total_assets - total_current_liabilities
            
            if denominator and denominator != 0:
                roic = (numerator / denominator) * 100
                return float(f"{roic:.15f}")
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating ROIC: {str(e)}")
            return 0.0

    
    def store_financial_data(self, ticker: str, start_year: str = None, end_year: str = None) -> bool:
        """Fetch and store financial data, first try ROIC API then fallback to yfinance"""
        try:
            logger.info(f"Fetching financial data for {ticker}")
            
            if not start_year or not end_year:
                current_year = datetime.now().year
                end_year = str(current_year)
                start_year = str(current_year - 10)

            # Try ROIC API first
            all_metrics_data = []
            try:
                logger.info(f"Trying ROIC API for {ticker}")
                for metric_description in self.METRICS:
                    metric_field = self.METRICS[metric_description]
                    query = f"get({metric_field}(fa_period_reference=range('{start_year}', '{end_year}'))) for('{ticker}')"
                    url = f"{self.BASE_URL}?query={query}&apikey={self.API_KEY}"

                    response = requests.get(url)
                    response.raise_for_status()
                    
                    df = pd.DataFrame(response.json())
                    if not df.empty:
                        df.columns = df.iloc[0]
                        df = df.drop(0).reset_index(drop=True)
                        all_metrics_data.append(df)
                        logger.info(f"Got {metric_description} from ROIC for {ticker}")
                    sleep(1)

                if all_metrics_data:
                    combined_df = pd.concat(all_metrics_data, axis=1)
                    combined_df = combined_df.loc[:,~combined_df.columns.duplicated()]
                    logger.info(f"Successfully got all ROIC data for {ticker}")
                    
                    cleaned_ticker = self.clean_ticker_for_table_name(ticker)
                    table_name = f"roic_{cleaned_ticker}"
                    success = self.store_dataframe(combined_df, table_name)
                    if success:
                        logger.info(f"Stored ROIC data for {ticker}")
                        return True
                else:
                    logger.warning(f"No data from ROIC for {ticker}")
                    
            except Exception as e:
                logger.warning(f"ROIC API failed for {ticker}: {str(e)}, trying yfinance")
                success = False

            # Try yfinance if ROIC failed
            try:
                logger.info(f"Getting data from yfinance for {ticker}")
                yf_ticker = yf.Ticker(ticker)
                
                # Check if this ticker is valid using cached company info
                from app.utils.cache.company_info_cache import company_info_cache
                basic_info = company_info_cache.get_basic_company_info(ticker)
                if not basic_info and not basic_info.get('longName') and not basic_info.get('shortName'):
                    logger.warning(f"No valid company found for ticker {ticker}")
                    return False
                
                financial_data = []
                
                # Get all required financial statements
                income_stmt = yf_ticker.income_stmt
                balance_sheet = yf_ticker.balance_sheet
                cash_flow = yf_ticker.cash_flow
                
                # Log statement information for debugging
                logger.info(f"Cash Flow shape: {cash_flow.shape if cash_flow is not None else None}")
                logger.info(f"Cash Flow dates: {cash_flow.columns.tolist() if cash_flow is not None else None}")
                logger.info(f"Cash Flow items: {cash_flow.index.tolist() if cash_flow is not None else None}")
                
                if cash_flow is not None and not cash_flow.empty:
                    logger.info(f"Processing cash flow data for {ticker}")
                    for date in cash_flow.columns:
                        year_data = {
                            'fiscal_year': date.year,
                            'period_label': 'Q4',
                            'period_end_date': date.strftime('%Y-%m-%d')
                        }
                        
                        # Operating Cash Flow
                        if 'Operating Income' in income_stmt.index:
                            try:
                                cf = float(cash_flow.loc['Operating Income', date] or 0)
                                year_data['is_oper_income'] = cf
                                # logger.info(f"Got Operating Cash Flow for {ticker} at {date}: {cf}")
                            except Exception as e:
                                # logger.error(f"Error getting Operating Cash Flow for {ticker} at {date}: {str(e)}")
                                year_data['is_oper_income'] = 0
                                
                        # Capital Expenditures
                        if 'Capital Expenditure' in cash_flow.index:
                            try:
                                capex = float(cash_flow.loc['Capital Expenditure', date] or 0)
                                year_data['cf_cap_expenditures'] = capex
                                # logger.info(f"Got Capital Expenditure for {ticker} at {date}: {capex}")
                            except Exception as e:
                                logger.error(f"Error getting Capital Expenditure for {ticker} at {date}: {str(e)}")
                                year_data['cf_cap_expenditures'] = 0
                        
                        # Get other financial metrics if income statement exists
                        if income_stmt is not None and not income_stmt.empty and date in income_stmt.columns:
                            # Total Revenue
                            if 'Total Revenue' in income_stmt.index:
                                revenue = float(income_stmt.loc['Total Revenue', date] or 0)
                                year_data['is_sales_and_services_revenues'] = revenue
                            
                            # Net Income
                            if 'Net Income' in income_stmt.index:
                                net_income = float(income_stmt.loc['Net Income', date] or 0)
                                year_data['is_net_income'] = net_income
                            
                            # EPS
                            if 'Basic EPS' in income_stmt.index:
                                eps = float(income_stmt.loc['Basic EPS', date] or 0)
                                year_data['eps'] = float(f"{eps:.15f}")
                            
                            # Operating Margin
                            if 'Operating Income' in income_stmt.index and 'Total Revenue' in income_stmt.index:
                                revenue = float(income_stmt.loc['Total Revenue', date] or 0)
                                operating_income = float(income_stmt.loc['Operating Income', date] or 0)
                                if revenue != 0:
                                    year_data['oper_margin'] = float(f"{(operating_income / revenue * 100):.15f}")
                                else:
                                    year_data['oper_margin'] = 0.0
                            
                            # Calculate ROIC
                            year_data['return_on_inv_capital'] = self.calculate_roic(income_stmt, balance_sheet, date)
                            
                            # Diluted Shares
                            if 'Diluted Average Shares' in income_stmt.index:
                                shares = float(income_stmt.loc['Diluted Average Shares', date] or 0)
                                year_data['is_sh_for_diluted_eps'] = shares
                        
                        financial_data.append(year_data)
                else:
                    logger.warning(f"No cash flow data available for {ticker}")

                if not financial_data:
                    logger.warning(f"No financial data found in yfinance for {ticker}")
                    return False
                
                # Convert to DataFrame
                df = pd.DataFrame(financial_data)
                
                # Ensure all required columns exist
                required_columns = [
                    'fiscal_year',
                    'period_label',
                    'period_end_date',
                    'is_sales_and_services_revenues',
                    'is_oper_income',
                    'is_net_income',
                    'eps',
                    'oper_margin',
                    'cf_cap_expenditures',
                    'return_on_inv_capital',
                    'is_sh_for_diluted_eps'
                ]
                
                for col in required_columns:
                    if col not in df.columns:
                        if col in ['fiscal_year', 'period_label', 'period_end_date']:
                            continue
                        df[col] = 0.0
                
                # Sort by fiscal year ascending
                df = df.sort_values('fiscal_year', ascending=True)
                df.reset_index(drop=True, inplace=True)
                
                # Reorder columns
                df = df[required_columns]
                
                # Store in database
                cleaned_ticker = self.clean_ticker_for_table_name(ticker)
                table_name = f"roic_{cleaned_ticker}"
                
                success = self.store_dataframe(df, table_name)
                if success:
                    logger.info(f"Successfully stored yfinance data for {ticker}")
                return success
                
            except Exception as e:
                logger.error(f"Both ROIC and yfinance failed for {ticker}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
                    
        except Exception as e:
            logger.error(f"Error storing financial data for {ticker}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        
    def get_analysis_dates(self, end_date: str, lookback_type: str, 
                            lookback_value: int) -> str:
            """
            Calculate start date based on lookback period

            Parameters:
            -----------
            end_date : str
                End date in YYYY-MM-DD format
            lookback_type : str
                Type of lookback period ('quarters' or 'days')
            lookback_value : int
                Number of quarters or days to look back

            Returns:
            --------
            str
                Start date in YYYY-MM-DD format
            """
            try:
                # Handle None or empty end_date
                if not end_date:
                    end_date = datetime.now().strftime("%Y-%m-%d")
                    
                # Validate date format
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                except ValueError:
                    print(f"Invalid date format: {end_date}, using current date")
                    end_dt = datetime.now()
                    
                if lookback_type == 'quarters':
                    start_dt = end_dt - relativedelta(months=3*lookback_value)
                else:  # days
                    start_dt = end_dt - relativedelta(days=lookback_value)
                    
                return start_dt.strftime("%Y-%m-%d")
                
            except Exception as e:
                print(f"Error calculating analysis dates: {str(e)}")
                raise

    def create_metrics_table(self, ticker: str, metrics: list, 
                           start_year: str, end_year: str) -> pd.DataFrame:
        """
        Creates a combined table of all metrics with selective growth rates.
        If no data is available, returns None without showing table header.

        Parameters:
        -----------
        ticker : str
            Stock ticker symbol
        metrics : list
            List of metrics to fetch
        start_year : str
            Start year in YYYY format
        end_year : str
            End year in YYYY format

        Returns:
        --------
        pd.DataFrame or None
            DataFrame containing metrics and growth rates or None if no data available
        """
        data = {}
        growth_rates = {}

        # Check if any metrics have data before creating table
        has_data = False
        for metric in metrics:
            metric = metric.lower()
            series = self.get_financial_data(ticker.upper(), metric, start_year, end_year)
            
            if series is not None:
                has_data = True
                data[metric] = series

                # Calculate CAGR only for specified metrics
                if metric in self.CAGR_METRICS:
                    try:
                        first_value = series.iloc[0]
                        last_value = series.iloc[-1]
                        num_years = len(series) - 1
                        if num_years > 0 and first_value > 0 and last_value > 0:
                            growth_rate = ((last_value / first_value) ** (1 / num_years) - 1) * 100
                            growth_rates[metric] = growth_rate
                    except Exception as e:
                        print(f"Error calculating CAGR for {metric}: {str(e)}")
                        growth_rates[metric] = None

        # If no data was found for any metrics, return None without creating table
        if not has_data:
            return None

        try:
            # Create main DataFrame with metrics
            df = pd.DataFrame(data).T

            # Add growth rates column only for specified metrics
            df['CAGR %'] = None  # Initialize with None
            for metric in self.CAGR_METRICS:
                if metric in growth_rates and metric in df.index:
                    df.at[metric, 'CAGR %'] = growth_rates[metric]

            return df
        except Exception as e:
            print(f"Error creating metrics table: {str(e)}")
            return None

    def calculate_returns(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate daily returns for a price series

        Parameters:
        -----------
        df : pd.DataFrame
            DataFrame containing price data

        Returns:
        --------
        pd.Series
            Series containing daily returns
        """
        try:
            if 'Close' not in df.columns:
                raise ValueError("Price data must contain 'Close' column")
                
            returns = df['Close'].pct_change()
            returns.fillna(0, inplace=True)
            return returns
            
        except Exception as e:
            print(f"Error calculating returns: {str(e)}")
            raise

    @retry_with_backoff(retries=3)
    def store_historical_data_with_retry(self, ticker, start_date, end_date):
        rate_limiter = RateLimiter(calls_per_second=2)
        rate_limiter.wait()
        return self.store_historical_data(ticker, start_date, end_date)
    @retry_with_backoff(retries=3)
    def store_financial_data_with_retry(self, ticker: str, start_year: str = None, end_year: str = None) -> bool:
        """Store financial data with retry mechanism"""
        rate_limiter = RateLimiter(calls_per_second=1)  # Limit to 1 call per second
        rate_limiter.wait()
        return self.store_financial_data(ticker, start_year, end_year)
