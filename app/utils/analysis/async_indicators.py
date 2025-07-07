# app/utils/analysis/async_indicators.py

"""
🚀 ASYNCHRONOUS TECHNICAL INDICATORS SERVICE

High-performance technical indicator calculations with:
✅ Async/await support for non-blocking operations
✅ Memory-efficient chunked processing
✅ Redis caching for calculated indicators
✅ Background processing with ThreadPoolExecutor
✅ Batch calculation optimization
✅ Error handling and graceful degradation
"""

import asyncio
import time
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from functools import lru_cache
import redis
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class IndicatorResult:
    """Enhanced result container for technical indicators"""
    name: str
    values: List[float]
    parameters: Dict[str, Any]
    calculation_time: float
    data_points: int
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)

class AsyncTechnicalIndicators:
    """
    Asynchronous technical indicators calculator with advanced performance optimizations
    """
    
    def __init__(self, max_workers: int = 4, redis_client=None):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Redis caching setup
        self.redis_client = redis_client
        if not self.redis_client:
            try:
                self.redis_client = redis.Redis(
                    host='localhost', 
                    port=6379, 
                    db=1,  # Use separate DB for indicators
                    decode_responses=True,
                    socket_keepalive=True,
                    socket_keepalive_options={}
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis connected for indicator caching")
            except Exception as e:
                logger.warning(f"⚠️ Redis unavailable for indicator caching: {e}")
                self.redis_client = None
        
        # Performance tracking
        self.calculation_stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_time': 0.0,
            'avg_time': 0.0
        }
        
        # Cache settings
        self.cache_ttl = 3600  # 1 hour
        self.chunk_size = 1000  # Process data in chunks
        
        logger.info(f"🔧 AsyncTechnicalIndicators initialized with {max_workers} workers")
    
    def _generate_cache_key(self, indicator: str, data_hash: str, **params) -> str:
        """Generate unique cache key for indicator calculation"""
        param_str = json.dumps(params, sort_keys=True)
        key_data = f"{indicator}:{data_hash}:{param_str}"
        return f"indicator:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def _hash_data(self, data: Union[pd.Series, List[float]]) -> str:
        """Generate hash for data to use in caching"""
        if isinstance(data, pd.Series):
            data_str = str(data.values.tolist()[:10]) + str(data.values.tolist()[-10:]) + str(len(data))
        else:
            data_str = str(data[:10]) + str(data[-10:]) + str(len(data))
        return hashlib.md5(data_str.encode()).hexdigest()[:16]
    
    async def _get_cached_result(self, cache_key: str) -> Optional[IndicatorResult]:
        """Get cached indicator result"""
        if not self.redis_client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            cached_data = await loop.run_in_executor(
                None, self.redis_client.get, cache_key
            )
            
            if cached_data:
                data = json.loads(cached_data)
                self.calculation_stats['cache_hits'] += 1
                logger.debug(f"📦 Cache hit for {cache_key}")
                return IndicatorResult(**data)
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        return None
    
    async def _set_cached_result(self, cache_key: str, result: IndicatorResult) -> None:
        """Cache indicator result"""
        if not self.redis_client:
            return
        
        try:
            loop = asyncio.get_event_loop()
            data = json.dumps(result.to_dict())
            await loop.run_in_executor(
                None, self.redis_client.setex, cache_key, self.cache_ttl, data
            )
            logger.debug(f"💾 Cached result for {cache_key}")
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    async def calculate_sma_async(self, data: Union[pd.Series, List[float]], 
                                  period: int = 20) -> IndicatorResult:
        """Calculate Simple Moving Average asynchronously"""
        start_time = time.time()
        data_hash = self._hash_data(data)
        cache_key = self._generate_cache_key('sma', data_hash, period=period)
        
        # Check cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Convert to numpy array for faster processing
            if isinstance(data, pd.Series):
                data_array = data.values
            else:
                data_array = np.array(data)
            
            # Run calculation in thread pool
            loop = asyncio.get_event_loop()
            result_values = await loop.run_in_executor(
                self.executor, self._calculate_sma_sync, data_array, period
            )
            
            calculation_time = time.time() - start_time
            result = IndicatorResult(
                name='SMA',
                values=result_values.tolist(),
                parameters={'period': period},
                calculation_time=calculation_time,
                data_points=len(data_array),
                success=True
            )
            
            # Cache result
            await self._set_cached_result(cache_key, result)
            
            # Update stats
            self._update_stats(calculation_time)
            
            return result
            
        except Exception as e:
            calculation_time = time.time() - start_time
            logger.error(f"SMA calculation failed: {e}")
            return IndicatorResult(
                name='SMA',
                values=[],
                parameters={'period': period},
                calculation_time=calculation_time,
                data_points=len(data) if data else 0,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_sma_sync(self, data: np.ndarray, period: int) -> np.ndarray:
        """Synchronous SMA calculation optimized with numpy"""
        result = np.full(len(data), np.nan)
        
        if len(data) < period:
            return result
        
        # Use pandas rolling for efficiency
        series = pd.Series(data)
        sma_values = series.rolling(window=period, min_periods=1).mean()
        
        return sma_values.values
    
    async def calculate_ema_async(self, data: Union[pd.Series, List[float]], 
                                  period: int = 20) -> IndicatorResult:
        """Calculate Exponential Moving Average asynchronously"""
        start_time = time.time()
        data_hash = self._hash_data(data)
        cache_key = self._generate_cache_key('ema', data_hash, period=period)
        
        # Check cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            if isinstance(data, pd.Series):
                data_array = data.values
            else:
                data_array = np.array(data)
            
            loop = asyncio.get_event_loop()
            result_values = await loop.run_in_executor(
                self.executor, self._calculate_ema_sync, data_array, period
            )
            
            calculation_time = time.time() - start_time
            result = IndicatorResult(
                name='EMA',
                values=result_values.tolist(),
                parameters={'period': period},
                calculation_time=calculation_time,
                data_points=len(data_array),
                success=True
            )
            
            await self._set_cached_result(cache_key, result)
            self._update_stats(calculation_time)
            
            return result
            
        except Exception as e:
            calculation_time = time.time() - start_time
            logger.error(f"EMA calculation failed: {e}")
            return IndicatorResult(
                name='EMA',
                values=[],
                parameters={'period': period},
                calculation_time=calculation_time,
                data_points=len(data) if data else 0,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_ema_sync(self, data: np.ndarray, period: int) -> np.ndarray:
        """Optimized EMA calculation with numpy"""
        alpha = 2.0 / (period + 1.0)
        result = np.full(len(data), np.nan)
        
        if len(data) == 0:
            return result
        
        # Initialize first value
        result[0] = data[0]
        
        # Calculate EMA iteratively
        for i in range(1, len(data)):
            if np.isnan(data[i]):
                result[i] = result[i-1]
            else:
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        
        return result
    
    async def calculate_rsi_async(self, data: Union[pd.Series, List[float]], 
                                  period: int = 14) -> IndicatorResult:
        """Calculate Relative Strength Index asynchronously"""
        start_time = time.time()
        data_hash = self._hash_data(data)
        cache_key = self._generate_cache_key('rsi', data_hash, period=period)
        
        # Check cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            if isinstance(data, pd.Series):
                data_array = data.values
            else:
                data_array = np.array(data)
            
            loop = asyncio.get_event_loop()
            result_values = await loop.run_in_executor(
                self.executor, self._calculate_rsi_sync, data_array, period
            )
            
            calculation_time = time.time() - start_time
            result = IndicatorResult(
                name='RSI',
                values=result_values.tolist(),
                parameters={'period': period},
                calculation_time=calculation_time,
                data_points=len(data_array),
                success=True
            )
            
            await self._set_cached_result(cache_key, result)
            self._update_stats(calculation_time)
            
            return result
            
        except Exception as e:
            calculation_time = time.time() - start_time
            logger.error(f"RSI calculation failed: {e}")
            return IndicatorResult(
                name='RSI',
                values=[],
                parameters={'period': period},
                calculation_time=calculation_time,
                data_points=len(data) if data else 0,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_rsi_sync(self, data: np.ndarray, period: int) -> np.ndarray:
        """Optimized RSI calculation"""
        if len(data) < period + 1:
            return np.full(len(data), np.nan)
        
        # Calculate price changes
        deltas = np.diff(data)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate initial averages
        avg_gains = np.full(len(data), np.nan)
        avg_losses = np.full(len(data), np.nan)
        
        # Initial average
        avg_gains[period] = np.mean(gains[:period])
        avg_losses[period] = np.mean(losses[:period])
        
        # Rolling averages using smoothing
        for i in range(period + 1, len(data)):
            avg_gains[i] = (avg_gains[i-1] * (period - 1) + gains[i-1]) / period
            avg_losses[i] = (avg_losses[i-1] * (period - 1) + losses[i-1]) / period
        
        # Calculate RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def calculate_bollinger_bands_async(self, data: Union[pd.Series, List[float]], 
                                              period: int = 20, std_dev: float = 2.0) -> IndicatorResult:
        """Calculate Bollinger Bands asynchronously"""
        start_time = time.time()
        data_hash = self._hash_data(data)
        cache_key = self._generate_cache_key('bollinger', data_hash, period=period, std_dev=std_dev)
        
        # Check cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            if isinstance(data, pd.Series):
                data_array = data.values
            else:
                data_array = np.array(data)
            
            loop = asyncio.get_event_loop()
            result_values = await loop.run_in_executor(
                self.executor, self._calculate_bollinger_sync, data_array, period, std_dev
            )
            
            calculation_time = time.time() - start_time
            result = IndicatorResult(
                name='Bollinger_Bands',
                values=result_values,
                parameters={'period': period, 'std_dev': std_dev},
                calculation_time=calculation_time,
                data_points=len(data_array),
                success=True
            )
            
            await self._set_cached_result(cache_key, result)
            self._update_stats(calculation_time)
            
            return result
            
        except Exception as e:
            calculation_time = time.time() - start_time
            logger.error(f"Bollinger Bands calculation failed: {e}")
            return IndicatorResult(
                name='Bollinger_Bands',
                values={'upper': [], 'middle': [], 'lower': []},
                parameters={'period': period, 'std_dev': std_dev},
                calculation_time=calculation_time,
                data_points=len(data) if data else 0,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_bollinger_sync(self, data: np.ndarray, period: int, std_dev: float) -> Dict[str, List[float]]:
        """Optimized Bollinger Bands calculation"""
        # Calculate SMA (middle band)
        series = pd.Series(data)
        sma = series.rolling(window=period, min_periods=1).mean()
        std = series.rolling(window=period, min_periods=1).std()
        
        # Calculate bands
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band.fillna(method='bfill').tolist(),
            'middle': sma.fillna(method='bfill').tolist(),
            'lower': lower_band.fillna(method='bfill').tolist()
        }
    
    async def calculate_macd_async(self, data: Union[pd.Series, List[float]], 
                                   fast_period: int = 12, slow_period: int = 26, 
                                   signal_period: int = 9) -> IndicatorResult:
        """Calculate MACD asynchronously"""
        start_time = time.time()
        data_hash = self._hash_data(data)
        cache_key = self._generate_cache_key('macd', data_hash, 
                                             fast_period=fast_period, 
                                             slow_period=slow_period, 
                                             signal_period=signal_period)
        
        # Check cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            if isinstance(data, pd.Series):
                data_array = data.values
            else:
                data_array = np.array(data)
            
            loop = asyncio.get_event_loop()
            result_values = await loop.run_in_executor(
                self.executor, self._calculate_macd_sync, 
                data_array, fast_period, slow_period, signal_period
            )
            
            calculation_time = time.time() - start_time
            result = IndicatorResult(
                name='MACD',
                values=result_values,
                parameters={
                    'fast_period': fast_period, 
                    'slow_period': slow_period, 
                    'signal_period': signal_period
                },
                calculation_time=calculation_time,
                data_points=len(data_array),
                success=True
            )
            
            await self._set_cached_result(cache_key, result)
            self._update_stats(calculation_time)
            
            return result
            
        except Exception as e:
            calculation_time = time.time() - start_time
            logger.error(f"MACD calculation failed: {e}")
            return IndicatorResult(
                name='MACD',
                values={'macd': [], 'signal': [], 'histogram': []},
                parameters={
                    'fast_period': fast_period, 
                    'slow_period': slow_period, 
                    'signal_period': signal_period
                },
                calculation_time=calculation_time,
                data_points=len(data) if data else 0,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_macd_sync(self, data: np.ndarray, fast_period: int, 
                            slow_period: int, signal_period: int) -> Dict[str, List[float]]:
        """Optimized MACD calculation"""
        # Calculate EMAs
        fast_ema = self._calculate_ema_sync(data, fast_period)
        slow_ema = self._calculate_ema_sync(data, slow_period)
        
        # Calculate MACD line
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line (EMA of MACD)
        signal_line = self._calculate_ema_sync(macd_line, signal_period)
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return {
            'macd': np.nan_to_num(macd_line).tolist(),
            'signal': np.nan_to_num(signal_line).tolist(),
            'histogram': np.nan_to_num(histogram).tolist()
        }
    
    async def calculate_batch_async(self, data: Union[pd.Series, List[float]], 
                                    indicators: List[Dict[str, Any]]) -> Dict[str, IndicatorResult]:
        """Calculate multiple indicators in parallel"""
        start_time = time.time()
        
        tasks = []
        for indicator_config in indicators:
            indicator_type = indicator_config.get('type')
            params = indicator_config.get('params', {})
            
            if indicator_type == 'sma':
                task = self.calculate_sma_async(data, **params)
            elif indicator_type == 'ema':
                task = self.calculate_ema_async(data, **params)
            elif indicator_type == 'rsi':
                task = self.calculate_rsi_async(data, **params)
            elif indicator_type == 'bollinger':
                task = self.calculate_bollinger_bands_async(data, **params)
            elif indicator_type == 'macd':
                task = self.calculate_macd_async(data, **params)
            else:
                logger.warning(f"Unknown indicator type: {indicator_type}")
                continue
            
            tasks.append((indicator_config.get('name', indicator_type), task))
        
        # Execute all tasks concurrently
        results = {}
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for i, (name, _) in enumerate(tasks):
            if i < len(completed_tasks):
                if isinstance(completed_tasks[i], Exception):
                    logger.error(f"Batch calculation failed for {name}: {completed_tasks[i]}")
                    results[name] = IndicatorResult(
                        name=name,
                        values=[],
                        parameters={},
                        calculation_time=0,
                        data_points=0,
                        success=False,
                        error_message=str(completed_tasks[i])
                    )
                else:
                    results[name] = completed_tasks[i]
        
        total_time = time.time() - start_time
        logger.info(f"✅ Batch calculation completed in {total_time:.3f}s for {len(results)} indicators")
        
        return results
    
    def _update_stats(self, calculation_time: float):
        """Update calculation statistics"""
        self.calculation_stats['total_calculations'] += 1
        self.calculation_stats['total_time'] += calculation_time
        self.calculation_stats['avg_time'] = (
            self.calculation_stats['total_time'] / 
            self.calculation_stats['total_calculations']
        )
        self.calculation_stats['cache_misses'] += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        cache_hit_rate = 0
        total_requests = self.calculation_stats['cache_hits'] + self.calculation_stats['cache_misses']
        if total_requests > 0:
            cache_hit_rate = (self.calculation_stats['cache_hits'] / total_requests) * 100
        
        return {
            **self.calculation_stats,
            'cache_hit_rate': round(cache_hit_rate, 2),
            'redis_available': self.redis_client is not None,
            'max_workers': self.max_workers
        }
    
    async def clear_cache(self) -> bool:
        """Clear all cached indicators"""
        if not self.redis_client:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            # Get all indicator cache keys
            keys = await loop.run_in_executor(
                None, self.redis_client.keys, 'indicator:*'
            )
            
            if keys:
                await loop.run_in_executor(
                    None, self.redis_client.delete, *keys
                )
                logger.info(f"🧹 Cleared {len(keys)} cached indicators")
            
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

# Global instance for easy access
async_indicators = AsyncTechnicalIndicators()

# Convenience functions for common operations
async def calculate_basic_indicators(data: Union[pd.Series, List[float]]) -> Dict[str, IndicatorResult]:
    """Calculate basic set of indicators (SMA20, SMA50, RSI)"""
    indicators = [
        {'type': 'sma', 'name': 'SMA_20', 'params': {'period': 20}},
        {'type': 'sma', 'name': 'SMA_50', 'params': {'period': 50}},
        {'type': 'rsi', 'name': 'RSI_14', 'params': {'period': 14}}
    ]
    
    return await async_indicators.calculate_batch_async(data, indicators)

async def calculate_advanced_indicators(data: Union[pd.Series, List[float]]) -> Dict[str, IndicatorResult]:
    """Calculate advanced set of indicators"""
    indicators = [
        {'type': 'ema', 'name': 'EMA_12', 'params': {'period': 12}},
        {'type': 'ema', 'name': 'EMA_26', 'params': {'period': 26}},
        {'type': 'macd', 'name': 'MACD', 'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}},
        {'type': 'bollinger', 'name': 'BB', 'params': {'period': 20, 'std_dev': 2.0}},
        {'type': 'rsi', 'name': 'RSI', 'params': {'period': 14}}
    ]
    
    return await async_indicators.calculate_batch_async(data, indicators)

logger.info("🚀 Async Technical Indicators service loaded successfully")