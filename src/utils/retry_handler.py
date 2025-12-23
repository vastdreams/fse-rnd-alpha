"""Comprehensive retry logic with error categorization."""
from functools import wraps
import time
from typing import Callable, TypeVar, Optional, List, Type
import requests
from requests.exceptions import (
    RequestException,
    HTTPError,
    Timeout,
    ConnectionError,
    RetryError
)
from src.logging.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class RetryableError(Exception):
    """Base class for retryable errors."""
    pass


class NonRetryableError(Exception):
    """Base class for non-retryable errors."""
    pass


def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exception: The exception to check
        
    Returns:
        True if retryable, False otherwise
    """
    # HTTP errors - retry on server errors and rate limits
    if isinstance(exception, HTTPError):
        if hasattr(exception, 'response') and exception.response:
            status_code = exception.response.status_code
            # Retry on: rate limit, server errors, gateway errors
            return status_code in [429, 500, 502, 503, 504]
        return True  # Retry on HTTP errors if we can't determine status
    
    # Network errors - always retry
    if isinstance(exception, (Timeout, ConnectionError)):
        return True
    
    # Request exceptions - retry
    if isinstance(exception, RequestException):
        return True
    
    # Non-retryable errors
    if isinstance(exception, NonRetryableError):
        return False
    
    # Default: don't retry unknown exceptions
    return False


def retry_with_backoff(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first)
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        exponential_base: Base for exponential backoff
        retryable_exceptions: List of exception types to retry on (default: auto-detect)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if error is retryable
                    if retryable_exceptions:
                        if not any(isinstance(e, exc_type) for exc_type in retryable_exceptions):
                            logger.debug(f"Non-retryable exception type: {type(e).__name__}")
                            raise
                    elif not is_retryable_error(e):
                        logger.debug(f"Non-retryable error: {type(e).__name__}: {e}")
                        raise
                    
                    # Don't retry if this was the last attempt
                    if attempt >= max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate wait time with exponential backoff
                    wait_time = min(
                        initial_wait * (exponential_base ** (attempt - 1)),
                        max_wait
                    )
                    
                    # Add jitter to prevent thundering herd
                    import random
                    jitter = random.uniform(0, wait_time * 0.1)
                    wait_time += jitter
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    
                    time.sleep(wait_time)
            
            # Should not reach here, but handle just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed after {max_attempts} attempts")
        
        return wrapper
    return decorator


def retry_on_rate_limit(
    max_attempts: int = 5,
    initial_wait: float = 4.0,
    max_wait: float = 300.0,  # 5 minutes max for rate limits
):
    """
    Special retry decorator for rate limit errors (429).
    Uses longer wait times appropriate for rate limits.
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_wait=initial_wait,
        max_wait=max_wait,
        exponential_base=2.0,
        retryable_exceptions=[HTTPError],
    )


def retry_on_network_error(
    max_attempts: int = 3,
    initial_wait: float = 2.0,
    max_wait: float = 30.0,
):
    """
    Special retry decorator for network errors.
    Uses shorter wait times for transient network issues.
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_wait=initial_wait,
        max_wait=max_wait,
        exponential_base=2.0,
        retryable_exceptions=[Timeout, ConnectionError, RequestException],
    )

