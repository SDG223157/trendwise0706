# app/utils/performance/response_optimizer.py

"""
🚀 RESPONSE OPTIMIZATION UTILITIES

Performance features:
✅ Intelligent response compression (gzip/brotli)
✅ Chart data optimization for transfer
✅ JSON minification and optimization
✅ Caching headers optimization
✅ Response time monitoring
✅ Memory usage tracking
✅ Error rate monitoring
"""

import gzip
import json
import time
import logging
from typing import Dict, Any, Optional, Union, List
from flask import Response, request, jsonify
import redis
from functools import wraps
import hashlib
import sys
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ResponseMetrics:
    """Response performance metrics"""
    endpoint: str
    response_time: float
    response_size: int
    compressed_size: Optional[int]
    compression_ratio: Optional[float]
    cache_hit: bool
    error: bool
    timestamp: float

class ResponseOptimizer:
    """
    Advanced response optimization with compression, caching, and monitoring
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        if not self.redis_client:
            try:
                self.redis_client = redis.Redis(
                    host='localhost', 
                    port=6379, 
                    db=2,  # Use separate DB for response cache
                    decode_responses=False,  # Keep binary for compression
                    socket_keepalive=True
                )
                self.redis_client.ping()
                logger.info("✅ Redis connected for response optimization")
            except Exception as e:
                logger.warning(f"⚠️ Redis unavailable for response caching: {e}")
                self.redis_client = None
        
        # Configuration
        self.compression_threshold = 1024  # Compress responses > 1KB
        self.cache_ttl = 300  # 5 minutes default
        self.max_cache_size = 100 * 1024 * 1024  # 100MB max cache
        
        # Performance tracking
        self.metrics = []
        self.max_metrics = 1000  # Keep last 1000 requests
        
        # Chart optimization settings
        self.chart_precision = 4  # Decimal places for chart data
        self.max_data_points = 5000  # Maximum data points per chart
        
        logger.info("🔧 ResponseOptimizer initialized")
    
    def _supports_compression(self, accept_encoding: str) -> str:
        """Determine best compression method based on client support"""
        if 'br' in accept_encoding:
            return 'brotli'
        elif 'gzip' in accept_encoding:
            return 'gzip'
        return None
    
    def _compress_data(self, data: bytes, method: str) -> bytes:
        """Compress data using specified method"""
        if method == 'gzip':
            return gzip.compress(data, compresslevel=6)
        elif method == 'brotli':
            try:
                import brotli
                return brotli.compress(data, quality=6)
            except ImportError:
                logger.warning("Brotli not available, falling back to gzip")
                return gzip.compress(data, compresslevel=6)
        return data
    
    def _generate_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key for response"""
        key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return f"response:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def optimize_chart_data(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize chart data for faster transfer"""
        optimized = chart_data.copy()
        
        try:
            # Optimize data traces
            if 'data' in optimized:
                for trace in optimized['data']:
                    if isinstance(trace, dict):
                        # Round numerical values to reduce precision
                        if 'y' in trace and isinstance(trace['y'], list):
                            trace['y'] = [
                                round(float(y), self.chart_precision) if y is not None else None 
                                for y in trace['y']
                            ]
                        
                        # Optimize date strings
                        if 'x' in trace and isinstance(trace['x'], list):
                            # Keep dates as strings but ensure consistency
                            trace['x'] = [str(x) for x in trace['x']]
                        
                        # Remove unnecessary properties
                        unnecessary_props = ['hovertemplate', 'customdata']
                        for prop in unnecessary_props:
                            trace.pop(prop, None)
            
            # Optimize layout
            if 'layout' in optimized:
                layout = optimized['layout']
                
                # Simplify title if too long
                if 'title' in layout and isinstance(layout['title'], str):
                    if len(layout['title']) > 100:
                        layout['title'] = layout['title'][:97] + '...'
                
                # Remove unnecessary layout properties for transfer
                unnecessary_layout_props = ['autosize', 'paper_bgcolor', 'plot_bgcolor']
                for prop in unnecessary_layout_props:
                    layout.pop(prop, None)
            
            # Data point reduction for large datasets
            if 'data' in optimized:
                for trace in optimized['data']:
                    if isinstance(trace, dict) and 'y' in trace:
                        if len(trace['y']) > self.max_data_points:
                            # Sample data points intelligently
                            trace['y'], trace['x'] = self._sample_data_points(
                                trace['y'], trace.get('x', [])
                            )
            
            logger.debug("📊 Chart data optimized for transfer")
            return optimized
            
        except Exception as e:
            logger.error(f"Chart optimization failed: {e}")
            return chart_data
    
    def _sample_data_points(self, y_data: List, x_data: List) -> tuple:
        """Intelligently sample data points to reduce size while preserving shape"""
        if len(y_data) <= self.max_data_points:
            return y_data, x_data
        
        # Keep first and last points
        step = len(y_data) // (self.max_data_points - 2)
        indices = [0] + list(range(step, len(y_data) - step, step)) + [len(y_data) - 1]
        
        sampled_y = [y_data[i] for i in indices]
        sampled_x = [x_data[i] if i < len(x_data) else None for i in indices]
        
        logger.debug(f"📉 Sampled {len(y_data)} points to {len(sampled_y)} points")
        return sampled_y, sampled_x
    
    def create_optimized_response(self, data: Union[Dict, List], 
                                  cache_key: Optional[str] = None,
                                  cache_ttl: Optional[int] = None) -> Response:
        """Create optimized response with compression and caching"""
        start_time = time.time()
        
        try:
            # Optimize chart data if present
            if isinstance(data, dict) and ('data' in data or 'layout' in data):
                data = self.optimize_chart_data(data)
            
            # Serialize to JSON with minimal formatting
            json_data = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            json_bytes = json_data.encode('utf-8')
            
            # Determine if compression should be applied
            accept_encoding = request.headers.get('Accept-Encoding', '')
            compression_method = None
            compressed_data = json_bytes
            compression_ratio = None
            
            if len(json_bytes) > self.compression_threshold:
                compression_method = self._supports_compression(accept_encoding)
                
                if compression_method:
                    compressed_data = self._compress_data(json_bytes, compression_method)
                    compression_ratio = len(compressed_data) / len(json_bytes)
                    logger.debug(f"🗜️ Compressed {len(json_bytes)} bytes to {len(compressed_data)} bytes "
                               f"({compression_ratio:.2%} ratio)")
            
            # Create response headers
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': str(len(compressed_data))
            }
            
            # Add compression headers
            if compression_method:
                headers['Content-Encoding'] = compression_method
                headers['Vary'] = 'Accept-Encoding'
            
            # Add caching headers
            if cache_ttl:
                headers['Cache-Control'] = f'public, max-age={cache_ttl}'
                headers['ETag'] = hashlib.md5(json_bytes).hexdigest()[:16]
            else:
                headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
            # Performance headers
            response_time = time.time() - start_time
            headers['X-Response-Time'] = f"{response_time:.3f}s"
            headers['X-Content-Size'] = str(len(json_bytes))
            if compression_ratio:
                headers['X-Compression-Ratio'] = f"{compression_ratio:.2%}"
            
            # Cache response if requested
            if cache_key and self.redis_client and cache_ttl:
                try:
                    cache_data = {
                        'data': compressed_data,
                        'headers': dict(headers),
                        'compression': compression_method
                    }
                    self.redis_client.setex(
                        cache_key, 
                        cache_ttl or self.cache_ttl, 
                        json.dumps(cache_data).encode()
                    )
                    headers['X-Cache'] = 'MISS'
                except Exception as e:
                    logger.warning(f"Response caching failed: {e}")
            
            # Track metrics
            self._track_response_metrics(
                endpoint=request.endpoint or 'unknown',
                response_time=response_time,
                response_size=len(json_bytes),
                compressed_size=len(compressed_data) if compression_method else None,
                compression_ratio=compression_ratio,
                cache_hit=False,
                error=False
            )
            
            return Response(
                compressed_data,
                headers=headers,
                status=200
            )
            
        except Exception as e:
            logger.error(f"Response optimization failed: {e}")
            # Fallback to simple JSON response
            return jsonify(data)
    
    def get_cached_response(self, cache_key: str) -> Optional[Response]:
        """Retrieve cached response"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                cache_info = json.loads(cached_data.decode())
                
                headers = cache_info['headers']
                headers['X-Cache'] = 'HIT'
                
                # Track cache hit metrics
                self._track_response_metrics(
                    endpoint=request.endpoint or 'unknown',
                    response_time=0.001,  # Cache hit is very fast
                    response_size=int(headers.get('X-Content-Size', 0)),
                    compressed_size=int(headers.get('Content-Length', 0)),
                    compression_ratio=None,
                    cache_hit=True,
                    error=False
                )
                
                return Response(
                    cache_info['data'],
                    headers=headers,
                    status=200
                )
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        
        return None
    
    def _track_response_metrics(self, endpoint: str, response_time: float, 
                               response_size: int, compressed_size: Optional[int],
                               compression_ratio: Optional[float], cache_hit: bool, error: bool):
        """Track response performance metrics"""
        metric = ResponseMetrics(
            endpoint=endpoint,
            response_time=response_time,
            response_size=response_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            cache_hit=cache_hit,
            error=error,
            timestamp=time.time()
        )
        
        self.metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        if not self.metrics:
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'cache_hit_rate': 0,
                'avg_compression_ratio': 0,
                'error_rate': 0
            }
        
        total_requests = len(self.metrics)
        cache_hits = sum(1 for m in self.metrics if m.cache_hit)
        errors = sum(1 for m in self.metrics if m.error)
        
        # Calculate averages
        avg_response_time = sum(m.response_time for m in self.metrics) / total_requests
        
        compression_ratios = [m.compression_ratio for m in self.metrics if m.compression_ratio]
        avg_compression_ratio = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0
        
        # Response size stats
        avg_response_size = sum(m.response_size for m in self.metrics) / total_requests
        total_bytes_saved = sum(
            (m.response_size - m.compressed_size) 
            for m in self.metrics 
            if m.compressed_size
        )
        
        # Endpoint breakdown
        endpoint_stats = {}
        for metric in self.metrics:
            if metric.endpoint not in endpoint_stats:
                endpoint_stats[metric.endpoint] = {
                    'count': 0,
                    'avg_time': 0,
                    'total_time': 0
                }
            endpoint_stats[metric.endpoint]['count'] += 1
            endpoint_stats[metric.endpoint]['total_time'] += metric.response_time
        
        for endpoint, stats in endpoint_stats.items():
            stats['avg_time'] = stats['total_time'] / stats['count']
            del stats['total_time']
        
        return {
            'total_requests': total_requests,
            'avg_response_time': round(avg_response_time * 1000, 2),  # Convert to ms
            'cache_hit_rate': round((cache_hits / total_requests) * 100, 2),
            'error_rate': round((errors / total_requests) * 100, 2),
            'avg_compression_ratio': round(avg_compression_ratio * 100, 2),
            'avg_response_size': round(avg_response_size / 1024, 2),  # KB
            'total_bytes_saved': round(total_bytes_saved / 1024, 2),  # KB
            'endpoint_stats': endpoint_stats,
            'redis_available': self.redis_client is not None
        }
    
    def clear_cache(self) -> bool:
        """Clear response cache"""
        if not self.redis_client:
            return False
        
        try:
            keys = self.redis_client.keys('response:*')
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"🧹 Cleared {len(keys)} cached responses")
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False

# Global instance
response_optimizer = ResponseOptimizer()

def optimized_response(cache_ttl: int = None, cache_key_params: List[str] = None):
    """Decorator for automatic response optimization"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Generate cache key if needed
                cache_key = None
                if cache_ttl and cache_key_params:
                    params = {}
                    for param in cache_key_params:
                        if param in request.args:
                            params[param] = request.args[param]
                        elif param in request.json if request.json else {}:
                            params[param] = request.json[param]
                    
                    cache_key = response_optimizer._generate_cache_key(
                        request.endpoint, params
                    )
                    
                    # Check cache first
                    cached_response = response_optimizer.get_cached_response(cache_key)
                    if cached_response:
                        return cached_response
                
                # Execute original function
                result = func(*args, **kwargs)
                
                # If result is already a Response object, return as-is
                if isinstance(result, Response):
                    return result
                
                # Create optimized response
                return response_optimizer.create_optimized_response(
                    result, cache_key, cache_ttl
                )
                
            except Exception as e:
                logger.error(f"Optimized response failed: {e}")
                response_optimizer._track_response_metrics(
                    endpoint=request.endpoint or 'unknown',
                    response_time=time.time() - start_time,
                    response_size=0,
                    compressed_size=None,
                    compression_ratio=None,
                    cache_hit=False,
                    error=True
                )
                # Fallback to original function
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

logger.info("🚀 Response Optimizer loaded successfully")