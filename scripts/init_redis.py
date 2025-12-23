"""Initialize Redis connection and test."""
# Setup path - must be first
import _setup_path  # noqa: F401

import sys
from config.settings import get_settings
from src.ai.utils.gpt_cache import initialize_redis_cache
from src.logging.logger import get_logger

logger = get_logger(__name__)


def init_redis():
    """Initialize Redis connection."""
    settings = get_settings()
    
    if not settings.REDIS_ENABLED:
        logger.info("Redis is disabled in settings. Skipping initialization.")
        return
    
    if not settings.REDIS_URL:
        logger.warning("REDIS_ENABLED is True but REDIS_URL is not set. Skipping.")
        return
    
    try:
        initialize_redis_cache(settings.REDIS_URL)
        logger.info("Redis initialized successfully")
        
        # Test connection
        from src.ai.utils.gpt_cache import get_gpt_cache
        cache = get_gpt_cache()
        cache.set("test", "test_response", None, "test-model")
        result = cache.get("test", None, "test-model")
        if result == "test_response":
            logger.info("Redis connection test successful")
        else:
            logger.warning("Redis connection test failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_redis()
