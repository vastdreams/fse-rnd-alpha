"""Redis configuration and initialization."""
from typing import Optional
from src.logging.logger import get_logger

logger = get_logger(__name__)


def _get_settings():
    """Lazy import of settings to avoid circular dependencies."""
    from config.settings import get_settings
    return get_settings()


def get_redis_url() -> Optional[str]:
    """
    Get Redis URL from settings.
    
    Returns:
        Redis URL or None if not configured
    """
    settings = _get_settings()
    
    # Check for Redis URL in settings
    if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
        return settings.REDIS_URL
    
    # Check environment variable
    import os
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        return redis_url
    
    return None


def is_redis_enabled() -> bool:
    """
    Check if Redis is enabled.
    
    Returns:
        True if Redis should be used
    """
    settings = _get_settings()
    
    # Check settings
    if hasattr(settings, 'REDIS_ENABLED'):
        return getattr(settings, 'REDIS_ENABLED', False)
    
    # Check environment variable
    import os
    redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower()
    return redis_enabled in ('true', '1', 'yes')


def initialize_redis_if_enabled():
    """
    Initialize Redis cache if enabled in configuration.
    
    This should be called at application startup.
    """
    if not is_redis_enabled():
        logger.info("Redis caching is disabled")
        return
    
    redis_url = get_redis_url()
    if not redis_url:
        logger.warning("Redis enabled but REDIS_URL not configured, using in-memory cache")
        return
    
    try:
        from src.ai.utils.gpt_cache import initialize_redis_cache
        initialize_redis_cache(redis_url=redis_url)
        logger.info(f"Redis cache initialized successfully: {redis_url}")
    except Exception as e:
        logger.warning(f"Failed to initialize Redis cache: {e}, falling back to in-memory cache")

