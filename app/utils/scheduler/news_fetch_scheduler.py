#!/usr/bin/env python3
"""
News Fetch Scheduler

This service automatically runs the "Fetch Top 100" news functionality every 6 hours.
It replicates the same logic as the manual "Fetch Top 100" button but runs automatically.

Features:
- Runs every 6 hours automatically
- Fetches news for top 100 symbols
- Processes symbols in chunks to avoid overwhelming APIs
- Includes retry logic and error handling
- Integrates with existing news infrastructure
- Can be started/stopped via web interface
"""

import os
import threading
import time
import schedule
import logging
import requests
import random
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import List, Dict, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import NewsArticle
from app.utils.analysis.news_service import NewsAnalysisService

# Set up logging
logger = logging.getLogger(__name__)

class NewsFetchScheduler:
    """Automated scheduler for fetching top 100 news articles every 6 hours"""
    
    def __init__(self):
        """Initialize the news fetch scheduler"""
        self.running = False
        self.thread = None
        self.news_service = NewsAnalysisService()
        self.chunk_size = 5  # Process 5 symbols at a time
        self.articles_per_symbol = 2  # Fetch 2 articles per symbol for periodic fetch (346 stocks, 6 times daily)
        self.retry_attempts = 2  # Retry failed symbols up to 2 times
        
        # Progress tracking
        self.current_progress = {
            'is_active': False,
            'start_time': None,
            'total_symbols': 0,
            'symbols_processed': 0,
            'articles_fetched': 0,
            'symbols_failed': 0,
            'current_symbol': None,
            'current_operation': 'Idle',
            'failed_symbols': [],
            'duration_seconds': 0
        }
        
        # Last completed operation tracking (persists even when scheduler is stopped)
        self.last_completed_operation = {
            'completed_at': None,
            'total_symbols': 0,
            'symbols_processed': 0,
            'articles_fetched': 0,
            'symbols_failed': 0,
            'duration_seconds': 0,
            'failed_symbols': [],
            'status': 'never_run'  # 'never_run', 'success', 'error'
        }
        
        # Complete list of 346 symbols - matches frontend exactly
        self.DEFAULT_SYMBOLS = [
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
        
    def init_app(self, app):
        """Initialize with Flask app context"""
        self.app = app
        
    def start(self):
        """Start the automated news fetch scheduler"""
        if self.running:
            logger.warning("News fetch scheduler is already running")
            return False
            
        try:
            # Clear any existing jobs
            schedule.clear()
            
            # Schedule market-based timing (6 times daily)
            self._schedule_market_times()
            
            # Start the scheduler thread
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=False, name="NewsFetchScheduler")
            self.thread.start()
            
            logger.info("🚀 News fetch scheduler started - will run at market opening/closing times")
            
            # Run immediately when scheduler starts
            logger.info("⚡ Running initial fetch job immediately...")
            initial_thread = threading.Thread(
                target=self._run_initial_job, 
                daemon=False, 
                name="NewsSchedulerInitial"
            )
            initial_thread.start()
            logger.info("⚡ Initial fetch job started in background")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start news fetch scheduler: {str(e)}")
            self.running = False
            return False
    
    def stop(self):
        """Stop the automated news fetch scheduler"""
        if not self.running:
            logger.warning("News fetch scheduler is not running")
            return False
            
        try:
            self.running = False
            schedule.clear()
            
            if self.thread and self.thread.is_alive():
                # Give the thread time to finish current iteration
                self.thread.join(timeout=5)
            
            logger.info("🛑 News fetch scheduler stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping news fetch scheduler: {str(e)}")
            return False
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("📅 News fetch scheduler thread started")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)
        
        logger.info("📅 News fetch scheduler thread stopped")
    
    def _schedule_market_times(self):
        """Schedule news fetch at market opening and closing times"""
        # Define market times (in UTC for consistency)
        # Times are designed to capture pre-market, opening, and closing news
        
        # Asian Markets
        # Tokyo Stock Exchange: 00:00-06:00 UTC (9:00-15:00 JST)
        # Hong Kong/Shanghai: 01:30-08:00 UTC (9:30-16:00 HKT/CST)
        schedule.every().day.at("23:30").do(self._run_scheduled_job, market="Asian Pre-Market")  # 30 min before Asian open
        schedule.every().day.at("08:30").do(self._run_scheduled_job, market="Asian Close")       # 30 min after Asian close
        
        # European Markets  
        # London Stock Exchange: 08:00-16:30 UTC (GMT)
        # Frankfurt/Paris: 07:00-15:30 UTC (CET-1)
        schedule.every().day.at("07:30").do(self._run_scheduled_job, market="European Pre-Market") # 30 min before European open
        schedule.every().day.at("17:00").do(self._run_scheduled_job, market="European Close")      # 30 min after European close
        
        # US Markets
        # NYSE/NASDAQ: 14:30-21:00 UTC (9:30-16:00 EST)
        schedule.every().day.at("14:00").do(self._run_scheduled_job, market="US Pre-Market")       # 30 min before US open
        schedule.every().day.at("21:30").do(self._run_scheduled_job, market="US After-Hours")     # 30 min after US close
        
        logger.info("📅 Scheduled 6 daily runs:")
        logger.info("  🌏 23:30 UTC - Asian Pre-Market")
        logger.info("  🌏 08:30 UTC - Asian Close") 
        logger.info("  🌍 07:30 UTC - European Pre-Market")
        logger.info("  🌍 17:00 UTC - European Close")
        logger.info("  🌎 14:00 UTC - US Pre-Market")
        logger.info("  🌎 21:30 UTC - US After-Hours")

    def _run_scheduled_job(self, market="Unknown"):
        """Run the scheduled fetch job with proper Flask app context"""
        try:
            logger.info(f"⏰ Scheduled news fetch job triggered - {market}")
            
            # Ensure we have proper Flask app context
            if hasattr(self, 'app') and self.app:
                with self.app.app_context():
                    result = self.run_fetch_job()
                    logger.info(f"⏰ {market} job completed: {result}")
            else:
                # Fallback: try to get or create app context
                try:
                    from flask import current_app
                    result = self.run_fetch_job()
                    logger.info(f"⏰ {market} job completed: {result}")
                except RuntimeError:
                    # No app context available, create one
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        result = self.run_fetch_job()
                        logger.info(f"⏰ {market} job completed: {result}")
                        
        except Exception as e:
            logger.error(f"❌ Error in {market} fetch job: {str(e)}", exc_info=True)
    
    def _run_initial_job(self):
        """Run the initial fetch job when scheduler starts"""
        try:
            logger.info("⚡ Initial news fetch job triggered (scheduler start)")
            
            # Ensure we have proper Flask app context
            if hasattr(self, 'app') and self.app:
                with self.app.app_context():
                    result = self.run_fetch_job()
                    logger.info(f"⚡ Initial job completed: {result}")
            else:
                # Fallback: try to get or create app context
                try:
                    from flask import current_app
                    result = self.run_fetch_job()
                    logger.info(f"⚡ Initial job completed: {result}")
                except RuntimeError:
                    # No app context available, create one
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        result = self.run_fetch_job()
                        logger.info(f"⚡ Initial job completed: {result}")
                        
        except Exception as e:
            logger.error(f"❌ Error in initial fetch job: {str(e)}", exc_info=True)
    
    @contextmanager
    def get_db_session(self):
        """Get database session with proper Flask app context"""
        try:
            # Import here to avoid circular imports
            from flask import current_app
            from app import create_app, db
            
            # Get the current app or create one if needed
            try:
                app = current_app._get_current_object()
            except RuntimeError:
                # No app context available, create one
                app = create_app()
            
            # Run with proper application context
            with app.app_context():
                yield db.session
                
        except Exception as e:
            logger.error(f"Error getting database session: {str(e)}")
            raise
    
    def run_fetch_job(self):
        """Run the automated news fetch job"""
        try:
            logger.info("🤖 Starting automated news fetch job...")
            
            # Safety check: ensure news service is available
            if not hasattr(self, 'news_service') or self.news_service is None:
                logger.error("❌ News service not initialized!")
                return {
                    'status': 'error',
                    'message': 'News service not initialized'
                }
            
            start_time = datetime.now()
            
            # Initialize progress tracking
            self.current_progress.update({
                'is_active': True,
                'start_time': start_time,
                'total_symbols': len(self.DEFAULT_SYMBOLS),
                'symbols_processed': 0,
                'articles_fetched': 0,
                'symbols_failed': 0,
                'current_symbol': None,
                'current_operation': 'Initializing',
                'failed_symbols': [],
                'duration_seconds': 0
            })
            
            # Clean up articles with no content first
            self.current_progress['current_operation'] = 'Cleaning up empty articles'
            self._cleanup_empty_articles()
            
            # Shuffle symbols for variety
            self.current_progress['current_operation'] = 'Preparing symbols list'
            selected_symbols = self._shuffle_symbols(self.DEFAULT_SYMBOLS.copy())
            
            logger.info(f"📋 Selected {len(selected_symbols)} symbols for processing")
            logger.info(f"🎲 First 10 symbols: {selected_symbols[:10]}")
            
            # Process symbols in chunks
            all_articles = []
            failed_symbols = []
            processed_count = 0
            
            # Process in smaller chunks for better control
            chunk_size = 5  # Reduced from 10 for better reliability
            chunks = [selected_symbols[i:i + chunk_size] for i in range(0, len(selected_symbols), chunk_size)]
            
            logger.info(f"🔄 Processing {len(chunks)} chunks of {chunk_size} symbols each")
            self.current_progress['current_operation'] = f'Processing {len(chunks)} chunks of {chunk_size} symbols each'
            
            for chunk_idx, chunk in enumerate(chunks):
                chunk_start_time = datetime.now()
                logger.info(f"🔄 Processing chunk {chunk_idx + 1}/{len(chunks)}: {chunk}")
                logger.info(f"📊 Chunk has {len(chunk)} symbols")
                
                # Update progress for chunk
                self.current_progress['current_operation'] = f'Processing chunk {chunk_idx + 1}/{len(chunks)}'
                
                chunk_processed = 0
                chunk_failed = 0
                
                for symbol_idx, symbol in enumerate(chunk):
                    try:
                        # Update current symbol being processed
                        self.current_progress['current_symbol'] = symbol
                        self.current_progress['current_operation'] = f'Processing symbol {symbol} (chunk {chunk_idx + 1}/{len(chunks)})'
                        
                        # Update duration
                        elapsed = (datetime.now() - start_time).total_seconds()
                        self.current_progress['duration_seconds'] = elapsed
                        
                        logger.info(f"🎯 Processing symbol {symbol_idx + 1}/{len(chunk)} in chunk {chunk_idx + 1}: {symbol}")
                        
                        # Fetch articles for this symbol
                        articles = self._fetch_symbol_with_retry(symbol)
                        if articles:
                            all_articles.extend(articles)
                            chunk_processed += 1
                            processed_count += 1
                            
                            # Update progress counters
                            self.current_progress['symbols_processed'] = processed_count
                            self.current_progress['articles_fetched'] = len(all_articles)
                            
                            logger.info(f"✅ Symbol {symbol} added {len(articles)} articles (total: {len(all_articles)})")
                        else:
                            failed_symbols.append(symbol)
                            chunk_failed += 1
                            
                            # Update failed counters
                            self.current_progress['symbols_failed'] = len(failed_symbols)
                            self.current_progress['failed_symbols'] = failed_symbols[-10:]  # Keep last 10 for display
                            
                            logger.warning(f"⚠️ Symbol {symbol} yielded no articles")
                            
                    except Exception as e:
                        failed_symbols.append(symbol)
                        chunk_failed += 1
                        
                        # Update failed counters
                        self.current_progress['symbols_failed'] = len(failed_symbols)
                        self.current_progress['failed_symbols'] = failed_symbols[-10:]  # Keep last 10 for display
                        
                        logger.error(f"❌ Error processing symbol {symbol}: {str(e)}")
                
                chunk_end_time = datetime.now()
                chunk_duration = (chunk_end_time - chunk_start_time).total_seconds()
                logger.info(f"📊 Chunk {chunk_idx + 1} completed: {chunk_processed} success, {chunk_failed} failed, {chunk_duration:.1f}s")
                
                # Add a small delay between chunks to avoid overwhelming the system
                if chunk_idx < len(chunks) - 1:  # Don't sleep after the last chunk
                    self.current_progress['current_operation'] = 'Brief pause between chunks'
                    logger.info("⏳ Brief pause between chunks...")
                    time.sleep(1)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Mark completion
            self.current_progress.update({
                'is_active': False,
                'current_operation': 'Completed',
                'current_symbol': None,
                'duration_seconds': duration.total_seconds()
            })
            
            # Store completed operation results for historical tracking
            self.last_completed_operation.update({
                'completed_at': end_time,
                'total_symbols': len(self.DEFAULT_SYMBOLS),
                'symbols_processed': processed_count,
                'articles_fetched': len(all_articles),
                'symbols_failed': len(failed_symbols),
                'duration_seconds': duration.total_seconds(),
                'failed_symbols': failed_symbols[:10],  # Keep last 10 for display
                'status': 'success'
            })
            
            logger.info(f"🏁 Job completed in {duration.total_seconds():.1f} seconds")
            logger.info(f"📊 Final stats: {len(all_articles)} articles, {processed_count} symbols processed, {len(failed_symbols)} failed")
            
            if failed_symbols:
                logger.warning(f"❌ Failed symbols: {failed_symbols[:10]}{'...' if len(failed_symbols) > 10 else ''}")
            
            return {
                'status': 'success',
                'articles_fetched': len(all_articles),
                'symbols_processed': processed_count,
                'symbols_failed': len(failed_symbols),
                'duration_seconds': duration.total_seconds(),
                'failed_symbols': failed_symbols[:20]  # Limit for response size
            }
            
        except Exception as e:
            # Mark error in progress
            self.current_progress.update({
                'is_active': False,
                'current_operation': f'Error: {str(e)}',
                'current_symbol': None
            })
            
            # Store error status in last completed operation
            self.last_completed_operation.update({
                'completed_at': datetime.now(),
                'status': 'error',
                'error_message': str(e)
            })
            
            logger.error(f"❌ Critical error in fetch job: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _cleanup_empty_articles(self):
        """Clean up articles with no content and no insights"""
        try:
            with self.get_db_session() as session:
                # Find articles to delete
                articles_to_delete = session.query(NewsArticle).filter(
                    NewsArticle.content.is_(None),
                    NewsArticle.ai_insights.is_(None)
                ).all()
                
                if articles_to_delete:
                    for article in articles_to_delete:
                        session.delete(article)
                    
                    session.commit()
                    logger.info(f"🧹 Cleaned up {len(articles_to_delete)} empty articles")
                else:
                    logger.info("🧹 No empty articles to clean up")
                    
        except Exception as e:
            logger.error(f"Error cleaning up empty articles: {str(e)}")
    
    def _shuffle_symbols(self, symbols: List[str]) -> List[str]:
        """Shuffle symbols for variety in processing order"""
        random.shuffle(symbols)
        return symbols
    
    def _fetch_symbol_with_retry(self, symbol: str) -> List[Dict]:
        """Fetch articles for a symbol with retry logic using direct news service call"""
        logger.info(f"🔄 Starting fetch for symbol: {symbol}")
        
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"📡 Attempt {attempt + 1} for {symbol}")
                
                # Use the same direct call that the working manual fetch uses
                # This matches exactly what happens in the /news/api/fetch endpoint
                articles = self.news_service.fetch_and_analyze_news(
                    symbols=[symbol],
                    limit=self.articles_per_symbol,
                    timeout=30  # Increased timeout for better reliability
                )
                
                if articles:
                    logger.info(f"✅ Successfully fetched {len(articles)} articles for {symbol}")
                    return articles
                else:
                    logger.warning(f"⚠️ No articles found for {symbol} on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"❌ Error fetching {symbol} on attempt {attempt + 1}: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    sleep_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"⏳ Retrying {symbol} in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"💀 Failed to fetch {symbol} after {self.retry_attempts} attempts")
        
        return []
    
    def get_symbols(self) -> List[str]:
        """Get the list of symbols that will be processed"""
        return self.DEFAULT_SYMBOLS.copy()
    
    def get_progress(self) -> Dict:
        """Get current fetch progress and last completed operation"""
        # Create a copy to avoid external modification
        progress = self.current_progress.copy()
        
        # Calculate percentage if active
        if progress['is_active'] and progress['total_symbols'] > 0:
            progress['percentage'] = (progress['symbols_processed'] / progress['total_symbols']) * 100
        else:
            progress['percentage'] = 100.0 if not progress['is_active'] and progress['symbols_processed'] > 0 else 0.0
        
        # Format start time for JSON serialization
        if progress['start_time']:
            progress['start_time'] = progress['start_time'].isoformat()
        
        # Include last completed operation for historical display
        last_completed = self.last_completed_operation.copy()
        if last_completed['completed_at']:
            last_completed['completed_at'] = last_completed['completed_at'].isoformat()
        
        progress['last_completed_operation'] = last_completed
            
        return progress
    
    def run_now(self):
        """Manually trigger the news fetch job immediately"""
        try:
            logger.info("🚀 Manual news fetch job triggered")
            
            # Run the fetch job in a separate thread to avoid blocking
            def run_job():
                try:
                    logger.info(f"🎯 Starting manual job with {len(self.DEFAULT_SYMBOLS)} symbols")
                    result = self.run_fetch_job()
                    logger.info(f"🏁 Manual job completed: {result}")
                except Exception as e:
                    logger.error(f"Error in manual fetch job: {str(e)}", exc_info=True)
            
            # CHANGED: daemon=False to ensure thread completes
            thread = threading.Thread(target=run_job, daemon=False, name="NewsSchedulerManual")
            thread.start()
            
            logger.info(f"Manual news fetch thread started: {thread.name}, daemon={thread.daemon}")
            
            return {
                'success': True,
                'message': 'Manual news fetch job started',
                'total_symbols': len(self.DEFAULT_SYMBOLS)
            }
            
        except Exception as e:
            logger.error(f"Error starting manual fetch job: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_status(self):
        """Get current scheduler status"""
        next_run = None
        jobs_count = len(schedule.jobs)
        
        # Get next scheduled run time and details
        next_run_details = None
        if jobs_count > 0:
            next_job = schedule.next_run()
            if next_job:
                next_run = next_job.isoformat()
                
                # Determine which market session is next
                current_hour = datetime.now().hour
                if current_hour < 7:
                    next_run_details = "European Pre-Market (07:30 UTC)"
                elif current_hour < 8:
                    next_run_details = "Asian Close (08:30 UTC)"
                elif current_hour < 14:
                    next_run_details = "US Pre-Market (14:00 UTC)"
                elif current_hour < 17:
                    next_run_details = "European Close (17:00 UTC)"
                elif current_hour < 21:
                    next_run_details = "US After-Hours (21:30 UTC)"
                else:
                    next_run_details = "Asian Pre-Market (23:30 UTC)"
                
        return {
            "running": self.running,
            "next_run": next_run,
            "next_run_details": next_run_details,
            "jobs_count": jobs_count,
            "fetch_schedule": "Market-based (6 times daily)",
            "schedule_times": [
                "🌏 23:30 UTC - Asian Pre-Market",
                "🌏 08:30 UTC - Asian Close", 
                "🌍 07:30 UTC - European Pre-Market",
                "🌍 17:00 UTC - European Close",
                "🌎 14:00 UTC - US Pre-Market",
                "🌎 21:30 UTC - US After-Hours"
            ],
            "symbols_count": len(self.DEFAULT_SYMBOLS),
            "articles_per_symbol": self.articles_per_symbol,
            "chunk_size": self.chunk_size
        }

# Global instance
news_fetch_scheduler = NewsFetchScheduler() 