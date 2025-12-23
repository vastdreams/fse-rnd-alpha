"""GPT API response caching module (Redis-ready structure)."""
from typing import Optional, Dict, Any
from hashlib import sha256
import json
from src.logging.logger import get_logger

logger = get_logger(__name__)


class GPTCache:
    """
    GPT API response cache.
    
    Currently uses in-memory cache, but structured for Redis migration.
    """
    
    def __init__(self, use_redis: bool = False, redis_client=None):
        """
        Initialize cache.
        
        Args:
            use_redis: Whether to use Redis (requires redis_client)
            redis_client: Redis client instance (if use_redis=True)
        """
        self.use_redis = use_redis
        self.redis_client = redis_client
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
    
    def _generate_cache_key(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> str:
        """Generate cache key from prompt and parameters."""
        cache_string = f"{prompt}|||{system_prompt or ''}|||{model or ''}"
        return f"gpt_cache:{sha256(cache_string.encode()).hexdigest()}"
    
    def get(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> Optional[str]:
        """
        Get cached response.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            model: Model name (optional)
            
        Returns:
            Cached response or None
        """
        cache_key = self._generate_cache_key(prompt, system_prompt, model)
        
        if self.use_redis and self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    logger.debug(f"Cache hit (Redis) for prompt hash: {cache_key[:16]}...")
                    return data.get("response")
            except Exception as e:
                logger.warning(f"Redis cache get failed: {e}")
        else:
            # In-memory cache
            if cache_key in self._memory_cache:
                cached_data = self._memory_cache[cache_key]
                logger.debug(f"Cache hit (memory) for prompt hash: {cache_key[:16]}...")
                return cached_data.get("response")
        
        return None
    
    def set(
        self,
        prompt: str,
        response: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        ttl: int = 86400  # 24 hours default
    ):
        """
        Cache response.
        
        Args:
            prompt: User prompt
            response: GPT response
            system_prompt: System prompt (optional)
            model: Model name (optional)
            ttl: Time to live in seconds
        """
        cache_key = self._generate_cache_key(prompt, system_prompt, model)
        
        cache_data = {
            "response": response,
            "prompt_hash": cache_key,
            "model": model,
        }
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(cache_data)
                )
                logger.debug(f"Cached response (Redis) for prompt hash: {cache_key[:16]}...")
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")
        else:
            # In-memory cache (with size limit)
            if len(self._memory_cache) > 1000:
                # Remove oldest entries (simple FIFO)
                oldest_key = next(iter(self._memory_cache))
                del self._memory_cache[oldest_key]
            
            self._memory_cache[cache_key] = cache_data
            logger.debug(f"Cached response (memory) for prompt hash: {cache_key[:16]}...")
    
    def clear(self):
        """Clear all cached responses."""
        if self.use_redis and self.redis_client:
            try:
                # Clear all keys matching pattern
                keys = self.redis_client.keys("gpt_cache:*")
                if keys:
                    self.redis_client.delete(*keys)
                logger.info("Cleared Redis cache")
            except Exception as e:
                logger.warning(f"Redis cache clear failed: {e}")
        else:
            self._memory_cache.clear()
            logger.info("Cleared in-memory cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys("gpt_cache:*")
                return {
                    "cache_type": "redis",
                    "cached_items": len(keys),
                }
            except Exception as e:
                logger.warning(f"Failed to get Redis cache stats: {e}")
                return {"cache_type": "redis", "error": str(e)}
        else:
            return {
                "cache_type": "memory",
                "cached_items": len(self._memory_cache),
            }


# Global cache instance
_cache_instance: Optional[GPTCache] = None


def get_gpt_cache(use_redis: bool = False, redis_client=None) -> GPTCache:
    """
    Get GPT cache instance (singleton).
    
    Args:
        use_redis: Whether to use Redis
        redis_client: Redis client (required if use_redis=True)
        
    Returns:
        GPTCache instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = GPTCache(use_redis=use_redis, redis_client=redis_client)
    
    return _cache_instance


def initialize_redis_cache(redis_url: Optional[str] = None):
    """
    Initialize Redis cache.
    
    Args:
        redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
    """
    try:
        import redis
        if redis_url:
            client = redis.from_url(redis_url)
        else:
            # Try default connection
            client = redis.Redis(host='localhost', port=6379, db=0)
        
        # Test connection
        client.ping()
        
        global _cache_instance
        _cache_instance = GPTCache(use_redis=True, redis_client=client)
        logger.info("Redis cache initialized successfully")
        
    except ImportError:
        logger.warning("Redis library not available. Install with: pip install redis")
    except Exception as e:
        logger.warning(f"Failed to initialize Redis cache: {e}")
        logger.info("Falling back to in-memory cache")

