"""Logging utilities with support for structured logging."""
import logging
import sys
from config.settings import get_settings

settings = get_settings()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Uses structured JSON logging in production, standard logging in development.
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    # Use structured logging if enabled
    if settings.USE_JSON_LOGGING:
        from src.logging.structured_logger import get_structured_logger
        return get_structured_logger(name, use_json=True)
    
    # Standard logging
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    
    # Set log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    return logger
