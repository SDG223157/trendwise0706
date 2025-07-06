"""
Optimized Data Service for Long-Period Analysis
Handles both short periods (≤365 days) and long periods (>365 days) efficiently.

Performance Strategy:
- Short periods (≤365 days): Redis cache + yfinance API
- Long periods (>365 days): Database storage + intelligent caching + progressive loading
- Ultra-long periods (>3000 days): Compressed storage + data sampling
"""

import yfinance as yf
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from app.utils.cache.enhanced_stock_cache import enhanced_stock_cache
from app.utils.data.data_service import DataService

logger = logging.getLogger(__name__)

class OptimizedDataService(DataService):
    """
    Optimized data service with intelligent strategy selection based on period length.
    
    Strategy Selection:
    - ≤365 days: Standard caching (Redis + yfinance)
    - 366-1000 days: Database with monthly partitioning
    - 1001-3000 days: Database with quarterly partitioning + compression
    - >3000 days: Database with progressive loading + data sampling
    """
    
    def __init__(self):
        super().__init__()
        self.db_engine = self._create_database_engine()
        self.lock = threading.Lock()
        
        # Performance thresholds
        self.SHORT_PERIOD_THRESHOLD = 365
        self.MEDIUM_PERIOD_THRESHOLD = 1000
        self.LONG_PERIOD_THRESHOLD = 3000
        
        # Cache configurations
        self.CACHE_CONFIGS = {
            'short': {'expire': 3600, 'partition': None},           # 1 hour, no partitioning
            'medium': {'expire': 7200, 'partition': 'monthly'},     # 2 hours, monthly partitions
            'long': {'expire': 14400, 'partition': 'quarterly'},    # 4 hours, quarterly partitions
            'ultra': {'expire': 86400, 'partition': 'yearly'}       # 24 hours, yearly partitions
        }
    
    def _create_database_engine(self):
        """Create database engine for long-term data storage"""
        try:
            connection_string = (
                f"mysql+pymysql://{os.getenv('MYSQL_USER')}:"
                f"{os.getenv('MYSQL_PASSWORD')}@"
                f"{os.getenv('MYSQL_HOST')}:"
                f"{os.getenv('MYSQL_PORT', '3306')}/"
                f"{os.getenv('MYSQL_DATABASE')}"
            )
            engine = create_engine(
                connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            logger.info("✅ Database engine created for long-period data storage")
            return engine
        except Exception as e:
            logger.error(f"❌ Failed to create database engine: {str(e)}")
            return None

    def get_historical_data_optimized(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Main entry point for optimized historical data retrieval.
        Automatically selects the best strategy based on period length.
        """
        start_time = time.time()
        
        # Format ticker and calculate period
        ticker = self.format_yahoo_symbol(ticker)
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        lookback_days = (end_dt - start_dt).days
        
        # Log the strategy selection
        strategy = self._get_strategy_name(lookback_days)
        logger.info(f"🎯 Strategy selected for {ticker} ({lookback_days} days): {strategy}")
        
        # Route to appropriate method based on period length
        if lookback_days <= self.SHORT_PERIOD_THRESHOLD:
            data = self._get_short_period_data(ticker, start_date, end_date)
        elif lookback_days <= self.MEDIUM_PERIOD_THRESHOLD:
            data = self._get_medium_period_data(ticker, start_date, end_date, lookback_days)
        elif lookback_days <= self.LONG_PERIOD_THRESHOLD:
            data = self._get_long_period_data_db(ticker, start_date, end_date, lookback_days)
        else:
            data = self._get_ultra_long_period_data(ticker, start_date, end_date, lookback_days)
        
        duration = time.time() - start_time
        
        if data is not None and not data.empty:
            logger.info(f"✅ Data retrieved for {ticker}: {len(data)} rows in {duration:.2f}s ({strategy})")
        else:
            logger.error(f"❌ Failed to retrieve data for {ticker} using {strategy}")
        
        return data

    def _get_strategy_name(self, lookback_days: int) -> str:
        """Get human-readable strategy name"""
        if lookback_days <= self.SHORT_PERIOD_THRESHOLD:
            return "Short-term (Cache + API)"
        elif lookback_days <= self.MEDIUM_PERIOD_THRESHOLD:
            return "Medium-term (Database + Monthly partitions)"
        elif lookback_days <= self.LONG_PERIOD_THRESHOLD:
            return "Long-term (Database + Quarterly partitions)"
        else:
            return "Ultra-long (Database + Progressive loading)"

    def _get_short_period_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Handle short periods (≤365 days) using existing optimized caching
        """
        return super().get_historical_data(ticker, start_date, end_date)

    def _get_medium_period_data(self, ticker: str, start_date: str, end_date: str, lookback_days: int) -> pd.DataFrame:
        """
        Handle medium periods (366-1000 days) using database with monthly partitioning
        """
        cache_key = f"medium_period:{ticker}:{start_date}:{end_date}"
        
        # Try cache first
        cached_data = enhanced_stock_cache.get_json(cache_key)
        if cached_data:
            logger.info(f"🎯 Medium-period cache hit for {ticker}")
            return self._reconstruct_dataframe(cached_data)
        
        # Try database
        db_data = self._get_from_database(ticker, start_date, end_date, 'monthly')
        if db_data is not None and not db_data.empty:
            logger.info(f"🗄️ Medium-period database hit for {ticker}")
            # Cache the result
            enhanced_stock_cache.set_json(cache_key, self._serialize_dataframe(db_data), 
                                       expire=self.CACHE_CONFIGS['medium']['expire'])
            return db_data
        
        # Fetch from API and store in database
        logger.info(f"🔄 Fetching medium-period data from API for {ticker}")
        api_data = self._fetch_from_api_with_retry(ticker, start_date, end_date)
        
        if api_data is not None and not api_data.empty:
            # Store in database with monthly partitioning
            self._store_in_database(ticker, api_data, 'monthly')
            # Cache the result
            enhanced_stock_cache.set_json(cache_key, self._serialize_dataframe(api_data),
                                       expire=self.CACHE_CONFIGS['medium']['expire'])
        
        return api_data

    def _get_long_period_data_db(self, ticker: str, start_date: str, end_date: str, lookback_days: int) -> pd.DataFrame:
        """
        Handle long periods (1001-3000 days) using database with quarterly partitioning
        """
        cache_key = f"long_period:{ticker}:{start_date}:{end_date}"
        
        # Try cache first
        cached_data = enhanced_stock_cache.get_json(cache_key)
        if cached_data:
            logger.info(f"🎯 Long-period cache hit for {ticker}")
            return self._reconstruct_dataframe(cached_data)
        
        # Try database with quarterly partitions
        db_data = self._get_from_database(ticker, start_date, end_date, 'quarterly')
        if db_data is not None and not db_data.empty:
            logger.info(f"🗄️ Long-period database hit for {ticker}")
            # Cache with compression
            compressed_data = self._compress_dataframe(db_data)
            enhanced_stock_cache.set_json(cache_key, compressed_data,
                                       expire=self.CACHE_CONFIGS['long']['expire'])
            return db_data
        
        # For long periods, use progressive fetching to avoid timeouts
        logger.info(f"🔄 Progressive fetching for long-period data: {ticker}")
        api_data = self._progressive_fetch(ticker, start_date, end_date)
        
        if api_data is not None and not api_data.empty:
            # Store in database with quarterly partitioning
            self._store_in_database(ticker, api_data, 'quarterly')
            # Cache with compression
            compressed_data = self._compress_dataframe(api_data)
            enhanced_stock_cache.set_json(cache_key, compressed_data,
                                       expire=self.CACHE_CONFIGS['long']['expire'])
        
        return api_data

    def _get_ultra_long_period_data(self, ticker: str, start_date: str, end_date: str, lookback_days: int) -> pd.DataFrame:
        """
        Handle ultra-long periods (>3000 days) using database with progressive loading and sampling
        """
        cache_key = f"ultra_period:{ticker}:{start_date}:{end_date}"
        
        # Try cache first
        cached_data = enhanced_stock_cache.get_json(cache_key)
        if cached_data:
            logger.info(f"🎯 Ultra-long-period cache hit for {ticker}")
            return self._reconstruct_dataframe(cached_data)
        
        # Try database with yearly partitions
        db_data = self._get_from_database(ticker, start_date, end_date, 'yearly')
        if db_data is not None and not db_data.empty:
            logger.info(f"🗄️ Ultra-long-period database hit for {ticker}")
            # Apply intelligent sampling for performance
            sampled_data = self._apply_intelligent_sampling(db_data, lookback_days)
            enhanced_stock_cache.set_json(cache_key, self._serialize_dataframe(sampled_data),
                                       expire=self.CACHE_CONFIGS['ultra']['expire'])
            return sampled_data
        
        # For ultra-long periods, use parallel fetching with sampling
        logger.info(f"🔄 Parallel progressive fetching for ultra-long period: {ticker}")
        api_data = self._parallel_progressive_fetch(ticker, start_date, end_date)
        
        if api_data is not None and not api_data.empty:
            # Store in database with yearly partitioning
            self._store_in_database(ticker, api_data, 'yearly')
            # Apply intelligent sampling and cache
            sampled_data = self._apply_intelligent_sampling(api_data, lookback_days)
            enhanced_stock_cache.set_json(cache_key, self._serialize_dataframe(sampled_data),
                                       expire=self.CACHE_CONFIGS['ultra']['expire'])
            return sampled_data
        
        return api_data

    def _get_from_database(self, ticker: str, start_date: str, end_date: str, partition_type: str) -> Optional[pd.DataFrame]:
        """
        Retrieve data from database using appropriate partitioning strategy
        """
        if not self.db_engine:
            return None
        
        try:
            table_name = self._get_table_name(ticker, partition_type)
            
            # Check if table exists
            if not self._table_exists(table_name):
                return None
            
            # Query data within date range
            query = text(f"""
                SELECT * FROM {table_name} 
                WHERE Date >= :start_date AND Date <= :end_date
                ORDER BY Date
            """)
            
            df = pd.read_sql(query, self.db_engine, params={
                'start_date': start_date,
                'end_date': end_date
            })
            
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                logger.debug(f"📊 Retrieved {len(df)} rows from database table {table_name}")
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Database query failed for {ticker}: {str(e)}")
            return None

    def _store_in_database(self, ticker: str, data: pd.DataFrame, partition_type: str) -> bool:
        """
        Store data in database using appropriate partitioning strategy
        """
        if not self.db_engine or data.empty:
            return False
        
        try:
            table_name = self._get_table_name(ticker, partition_type)
            
            # Prepare data for storage
            data_copy = data.copy()
            data_copy.reset_index(inplace=True)
            
            # Store in database
            data_copy.to_sql(
                table_name,
                self.db_engine,
                if_exists='replace',
                index=False,
                chunksize=1000
            )
            
            logger.info(f"💾 Stored {len(data_copy)} rows in database table {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store data in database for {ticker}: {str(e)}")
            return False

    def _progressive_fetch(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch data progressively in chunks to avoid timeouts
        """
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Split into 1-year chunks
        chunk_size = 365
        chunks = []
        current_start = start_dt
        
        while current_start < end_dt:
            current_end = min(current_start + timedelta(days=chunk_size), end_dt)
            
            logger.info(f"📥 Fetching chunk: {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}")
            
            chunk_data = self._fetch_from_api_with_retry(
                ticker, 
                current_start.strftime('%Y-%m-%d'), 
                current_end.strftime('%Y-%m-%d')
            )
            
            if chunk_data is not None and not chunk_data.empty:
                chunks.append(chunk_data)
            
            current_start = current_end + timedelta(days=1)
            time.sleep(0.1)  # Rate limiting
        
        # Combine all chunks
        if chunks:
            combined_data = pd.concat(chunks)
            combined_data = combined_data.sort_index()
            combined_data = combined_data[~combined_data.index.duplicated(keep='first')]
            logger.info(f"📊 Combined {len(chunks)} chunks into {len(combined_data)} rows")
            return combined_data
        
        return pd.DataFrame()

    def _parallel_progressive_fetch(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch data using parallel workers for ultra-long periods
        """
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Split into 6-month chunks for parallel processing
        chunk_size = 180
        chunk_params = []
        current_start = start_dt
        
        while current_start < end_dt:
            current_end = min(current_start + timedelta(days=chunk_size), end_dt)
            chunk_params.append((ticker, current_start.strftime('%Y-%m-%d'), current_end.strftime('%Y-%m-%d')))
            current_start = current_end + timedelta(days=1)
        
        logger.info(f"🔄 Parallel fetching {len(chunk_params)} chunks using ThreadPoolExecutor")
        
        chunks = []
        with ThreadPoolExecutor(max_workers=3) as executor:  # Limit concurrent requests
            # Submit all tasks
            future_to_chunk = {
                executor.submit(self._fetch_from_api_with_retry, *params): params 
                for params in chunk_params
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                params = future_to_chunk[future]
                try:
                    chunk_data = future.result()
                    if chunk_data is not None and not chunk_data.empty:
                        chunks.append(chunk_data)
                        logger.debug(f"✅ Chunk completed: {params[1]} to {params[2]}")
                except Exception as e:
                    logger.error(f"❌ Chunk failed {params[1]} to {params[2]}: {str(e)}")
        
        # Combine and clean data
        if chunks:
            combined_data = pd.concat(chunks)
            combined_data = combined_data.sort_index()
            combined_data = combined_data[~combined_data.index.duplicated(keep='first')]
            logger.info(f"📊 Parallel fetch completed: {len(combined_data)} rows from {len(chunks)} chunks")
            return combined_data
        
        return pd.DataFrame()

    def _apply_intelligent_sampling(self, data: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
        """
        Apply intelligent sampling for ultra-long periods to improve performance
        
        Sampling strategy:
        - Recent 1 year: Keep all daily data
        - 1-5 years ago: Keep weekly data (every 7th day)
        - >5 years ago: Keep monthly data (every 30th day)
        """
        if len(data) <= 2000:  # No sampling needed for reasonable datasets
            return data
        
        today = pd.Timestamp.now()
        cutoff_1_year = today - timedelta(days=365)
        cutoff_5_years = today - timedelta(days=365 * 5)
        
        # Recent data (daily)
        recent_data = data[data.index >= cutoff_1_year]
        
        # Medium-term data (weekly)
        medium_data = data[(data.index >= cutoff_5_years) & (data.index < cutoff_1_year)]
        if not medium_data.empty:
            medium_data = medium_data.iloc[::7]  # Every 7th day
        
        # Historical data (monthly)
        historical_data = data[data.index < cutoff_5_years]
        if not historical_data.empty:
            historical_data = historical_data.iloc[::30]  # Every 30th day
        
        # Combine sampled data
        sampled_data = pd.concat([historical_data, medium_data, recent_data])
        sampled_data = sampled_data.sort_index()
        
        logger.info(f"📊 Intelligent sampling: {len(data)} → {len(sampled_data)} rows "
                   f"({len(sampled_data)/len(data)*100:.1f}% reduction)")
        
        return sampled_data

    def _fetch_from_api_with_retry(self, ticker: str, start_date: str, end_date: str, max_retries: int = 3) -> pd.DataFrame:
        """
        Fetch data from API with enhanced retry logic
        """
        for attempt in range(max_retries):
            try:
                ticker_obj = yf.Ticker(ticker)
                df = ticker_obj.history(start=start_date, end=end_date)
                
                if not df.empty:
                    # Clean and validate data
                    df = self._clean_data(df)
                    return df
                else:
                    logger.warning(f"Empty data returned for {ticker} (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.warning(f"API fetch failed for {ticker} (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"❌ All API fetch attempts failed for {ticker}")
        return pd.DataFrame()

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate fetched data"""
        # Remove timezone information
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        # Fill missing values
        if 'Dividends' in df.columns:
            df['Dividends'] = df['Dividends'].fillna(0)
        if 'Stock Splits' in df.columns:
            df['Stock Splits'] = df['Stock Splits'].fillna(0)
        
        # Remove rows with missing close prices
        df = df.dropna(subset=['Close'])
        
        return df

    def _get_table_name(self, ticker: str, partition_type: str) -> str:
        """Generate table name based on ticker and partition type"""
        clean_ticker = self.clean_ticker_for_table_name(ticker)
        return f"hist_{clean_ticker}_{partition_type}"

    def _table_exists(self, table_name: str) -> bool:
        """Check if table exists in database"""
        try:
            inspector = inspect(self.db_engine)
            return table_name in inspector.get_table_names()
        except:
            return False

    def _serialize_dataframe(self, df: pd.DataFrame) -> Dict:
        """Serialize DataFrame for caching"""
        return {
            'data': df.to_dict('records'),
            'index': df.index.strftime('%Y-%m-%d').tolist(),
            'columns': df.columns.tolist(),
            'cached_at': datetime.now().isoformat()
        }

    def _reconstruct_dataframe(self, cached_data: Dict) -> pd.DataFrame:
        """Reconstruct DataFrame from cached data"""
        df = pd.DataFrame(cached_data['data'])
        df.index = pd.to_datetime(cached_data['index'])
        df.columns = cached_data['columns']
        return df

    def _compress_dataframe(self, df: pd.DataFrame) -> Dict:
        """Compress DataFrame for long-term caching"""
        # For large datasets, store only essential columns
        essential_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        compressed_df = df[essential_columns].copy()
        
        return self._serialize_dataframe(compressed_df)

    def get_performance_stats(self, ticker: str) -> Dict:
        """Get performance statistics for a ticker"""
        try:
            stats = {
                'database_tables': [],
                'cache_keys': [],
                'total_cached_rows': 0,
                'total_db_rows': 0
            }
            
            # Check database tables
            if self.db_engine:
                inspector = inspect(self.db_engine)
                tables = inspector.get_table_names()
                clean_ticker = self.clean_ticker_for_table_name(ticker)
                
                for table in tables:
                    if table.startswith(f"hist_{clean_ticker}"):
                        stats['database_tables'].append(table)
                        # Count rows
                        try:
                            result = self.db_engine.execute(text(f"SELECT COUNT(*) FROM {table}"))
                            row_count = result.scalar()
                            stats['total_db_rows'] += row_count
                        except:
                            pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting performance stats: {str(e)}")
            return {}

# Create global instance
optimized_data_service = OptimizedDataService() 