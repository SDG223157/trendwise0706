from .news_cache import NewsCache
from typing import Optional, Dict, List, Any
import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class APICache(NewsCache):
    """Extended cache for API responses and external service calls"""
    
    def __init__(self):
        super().__init__()
        self.api_prefix = "api"
        self.ai_prefix = "ai"
        self.roic_prefix = "roic"
        
    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash for content to use as cache key"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    # AI Processing Results Caching
    def get_ai_summary(self, content_hash: str) -> Optional[str]:
        """Get cached AI summary by content hash"""
        cache_key = f"{self.ai_prefix}:summary:{content_hash}"
        result = self.get_json(cache_key)
        return result.get('summary') if result else None
    
    def set_ai_summary(self, content: str, summary: str, expire: int = 604800) -> bool:
        """Cache AI summary (7 days default)"""
        content_hash = self._generate_content_hash(content)
        cache_key = f"{self.ai_prefix}:summary:{content_hash}"
        data = {
            'summary': summary,
            'content_hash': content_hash,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    def get_ai_insights(self, content_hash: str) -> Optional[str]:
        """Get cached AI insights by content hash"""
        cache_key = f"{self.ai_prefix}:insights:{content_hash}"
        result = self.get_json(cache_key)
        return result.get('insights') if result else None
    
    def set_ai_insights(self, content: str, insights: str, expire: int = 604800) -> bool:
        """Cache AI insights (7 days default)"""
        content_hash = self._generate_content_hash(content)
        cache_key = f"{self.ai_prefix}:insights:{content_hash}"
        data = {
            'insights': insights,
            'content_hash': content_hash,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    def get_ai_sentiment(self, content_hash: str) -> Optional[int]:
        """Get cached AI sentiment rating by content hash"""
        cache_key = f"{self.ai_prefix}:sentiment:{content_hash}"
        result = self.get_json(cache_key)
        return result.get('sentiment_rating') if result else None
    
    def set_ai_sentiment(self, content: str, sentiment_rating: int, expire: int = 604800) -> bool:
        """Cache AI sentiment rating (7 days default)"""
        content_hash = self._generate_content_hash(content)
        cache_key = f"{self.ai_prefix}:sentiment:{content_hash}"
        data = {
            'sentiment_rating': sentiment_rating,
            'content_hash': content_hash,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, data, expire)
    
    def get_ai_complete_analysis(self, content: str) -> Optional[Dict]:
        """Get complete AI analysis if all parts are cached"""
        content_hash = self._generate_content_hash(content)
        
        summary = self.get_ai_summary(content_hash)
        insights = self.get_ai_insights(content_hash)
        sentiment = self.get_ai_sentiment(content_hash)
        
        if summary or insights or sentiment is not None:
            return {
                'summary': summary,
                'insights': insights,
                'sentiment_rating': sentiment,
                'content_hash': content_hash,
                'cache_hit': True
            }
        return None
    
    def set_ai_complete_analysis(self, content: str, analysis_data: Dict, expire: int = 604800) -> bool:
        """Cache complete AI analysis"""
        success = True
        if analysis_data.get('summary'):
            success &= self.set_ai_summary(content, analysis_data['summary'], expire)
        if analysis_data.get('insights'):
            success &= self.set_ai_insights(content, analysis_data['insights'], expire)
        if analysis_data.get('sentiment_rating') is not None:
            success &= self.set_ai_sentiment(content, analysis_data['sentiment_rating'], expire)
        return success
    
    # ROIC API Response Caching
    def get_roic_data(self, ticker: str, year: str) -> Optional[Dict]:
        """Get cached ROIC data"""
        cache_key = f"{self.roic_prefix}:data:{ticker}:{year}"
        return self.get_json(cache_key)
    
    def set_roic_data(self, ticker: str, year: str, data: Dict, expire: int = 86400) -> bool:
        """Cache ROIC data (24 hours default)"""
        cache_key = f"{self.roic_prefix}:data:{ticker}:{year}"
        cached_data = {
            **data,  # Spread the data
            'ticker': ticker,
            'year': year,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, cached_data, expire)
    
    def get_roic_metric(self, ticker: str, metric: str, years: str) -> Optional[Dict]:
        """Get cached ROIC API response"""
        cache_key = f"{self.roic_prefix}:metric:{ticker}:{metric}:{years}"
        return self.get_json(cache_key)
    
    def set_roic_metric(self, ticker: str, metric: str, years: str, data: Dict, expire: int = 86400) -> bool:
        """Cache ROIC API response (24 hours default)"""
        cache_key = f"{self.roic_prefix}:metric:{ticker}:{metric}:{years}"
        cached_data = {
            'data': data,
            'ticker': ticker,
            'metric': metric,
            'years': years,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, cached_data, expire)
    
    # Generic API Response Caching
    def get_api_response(self, service: str, endpoint: str, params_hash: str) -> Optional[Dict]:
        """Get cached API response for any service"""
        cache_key = f"{self.api_prefix}:{service}:{endpoint}:{params_hash}"
        return self.get_json(cache_key)
    
    def set_api_response(self, service: str, endpoint: str, params: Dict, response: Dict, expire: int = 3600) -> bool:
        """Cache API response for any service"""
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
        cache_key = f"{self.api_prefix}:{service}:{endpoint}:{params_hash}"
        
        cached_data = {
            'response': response,
            'params': params,
            'service': service,
            'endpoint': endpoint,
            'cached_at': datetime.now().isoformat()
        }
        return self.set_json(cache_key, cached_data, expire)
    
    # Rate Limiting Support
    def get_rate_limit_info(self, service: str, endpoint: str) -> Optional[Dict]:
        """Get rate limiting information for an API"""
        cache_key = f"{self.api_prefix}:rate_limit:{service}:{endpoint}"
        return self.get_json(cache_key)
    
    def set_rate_limit_info(self, service: str, endpoint: str, limit_info: Dict, expire: int = 3600) -> bool:
        """Cache rate limiting information"""
        cache_key = f"{self.api_prefix}:rate_limit:{service}:{endpoint}"
        limit_info['updated_at'] = datetime.now().isoformat()
        return self.set_json(cache_key, limit_info, expire)
    
    def increment_api_calls(self, service: str, endpoint: str) -> int:
        """Increment and track API call count"""
        cache_key = f"{self.api_prefix}:calls:{service}:{endpoint}:count"
        
        if not self.is_available():
            return 1
            
        try:
            # This would use Redis INCR command for atomic increment
            current_count = self.get_json(cache_key) or {'count': 0}
            current_count['count'] += 1
            current_count['last_call'] = datetime.now().isoformat()
            
            # Reset daily (24 hour expiry)
            self.set_json(cache_key, current_count, expire=86400)
            return current_count['count']
        except Exception as e:
            logger.error(f"Error incrementing API calls: {str(e)}")
            return 1
    
    # News Data Aggregation Caching
    def get_processed_articles_count(self, symbol: str) -> Optional[Dict]:
        """Get cached article processing status for a symbol"""
        cache_key = f"news:processing_status:{symbol}"
        return self.get_json(cache_key)
    
    def set_processed_articles_count(self, symbol: str, stats: Dict, expire: int = 1800) -> bool:
        """Cache article processing status (30 minutes default)"""
        cache_key = f"news:processing_status:{symbol}"
        stats['updated_at'] = datetime.now().isoformat()
        return self.set_json(cache_key, stats, expire)
    
    def get_symbol_news_summary(self, symbol: str, days: int = 7) -> Optional[Dict]:
        """Get cached news summary for a symbol"""
        cache_key = f"news:summary:{symbol}:{days}d"
        return self.get_json(cache_key)
    
    def set_symbol_news_summary(self, symbol: str, summary: Dict, days: int = 7, expire: int = 3600) -> bool:
        """Cache news summary for a symbol (1 hour default)"""
        cache_key = f"news:summary:{symbol}:{days}d"
        summary['cached_at'] = datetime.now().isoformat()
        return self.set_json(cache_key, summary, expire)
    
    # Cache Performance Monitoring
    def get_cache_performance_stats(self) -> Dict:
        """Get cache performance statistics"""
        if not self.is_available():
            return {'cache_available': False}
        
        try:
            stats = {
                'cache_available': True,
                'ai_cache_hits': 0,  # Would be tracked in production
                'api_cache_hits': 0,
                'total_requests': 0,
                'hit_rate': 0,
                'timestamp': datetime.now().isoformat()
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting cache performance stats: {str(e)}")
            return {'cache_available': False, 'error': str(e)}
    
    # Bulk Operations
    def invalidate_ai_cache(self, content_hash: str = None):
        """Invalidate AI processing cache"""
        if content_hash:
            patterns = [
                f"{self.ai_prefix}:summary:{content_hash}",
                f"{self.ai_prefix}:insights:{content_hash}",
                f"{self.ai_prefix}:sentiment:{content_hash}"
            ]
        else:
            patterns = [f"{self.ai_prefix}:*"]
        
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def invalidate_api_cache(self, service: str = None):
        """Invalidate API response cache for a service or all services"""
        pattern = f"{self.api_prefix}:{service}:*" if service else f"{self.api_prefix}:*"
        self.delete_pattern(pattern)

# Global instance
api_cache = APICache() 