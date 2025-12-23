"""Sliding window rate limiter for SEC API requests."""
import time
from collections import deque
from threading import Lock
from typing import Optional
from src.logging.logger import get_logger

logger = get_logger(__name__)


class SlidingWindowRateLimiter:
    """
    Rate limiter using sliding window algorithm.
    Ensures no more than max_requests are made within window_seconds.
    
    SEC requirement: Maximum 10 requests per second.
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_times: deque = deque()
        self.lock = Lock()
        
        logger.info(f"Rate limiter initialized: {max_requests} requests per {window_seconds} seconds")
    
    def acquire(self) -> None:
        """
        Acquire permission to make a request.
        Will block if necessary to respect rate limits.
        """
        with self.lock:
            now = time.time()
            
            # Remove requests outside the window
            while self.request_times and self.request_times[0] <= now - self.window_seconds:
                self.request_times.popleft()
            
            # Check if we need to wait
            if len(self.request_times) >= self.max_requests:
                # Calculate how long to wait
                oldest_request_time = self.request_times[0]
                sleep_time = oldest_request_time + self.window_seconds - now
                
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                    now = time.time()
                    
                    # Clean up again after sleep
                    while self.request_times and self.request_times[0] <= now - self.window_seconds:
                        self.request_times.popleft()
            
            # Record this request
            self.request_times.append(now)
    
    def wait_if_needed(self) -> None:
        """Alias for acquire() for compatibility."""
        self.acquire()
    
    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.
        
        Returns:
            dict with current request count and remaining capacity
        """
        with self.lock:
            now = time.time()
            # Clean up old requests
            while self.request_times and self.request_times[0] <= now - self.window_seconds:
                self.request_times.popleft()
            
            return {
                "current_requests": len(self.request_times),
                "max_requests": self.max_requests,
                "remaining_capacity": max(0, self.max_requests - len(self.request_times)),
                "window_seconds": self.window_seconds,
            }


# Global rate limiter instance for SEC API
_sec_rate_limiter: Optional[SlidingWindowRateLimiter] = None


def get_sec_rate_limiter() -> SlidingWindowRateLimiter:
    """
    Get or create the global SEC API rate limiter.
    
    Returns:
        SlidingWindowRateLimiter instance
    """
    global _sec_rate_limiter
    
    if _sec_rate_limiter is None:
        _sec_rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=1.0)
    
    return _sec_rate_limiter


def reset_rate_limiter() -> None:
    """Reset the global rate limiter (useful for testing)."""
    global _sec_rate_limiter
    _sec_rate_limiter = None

