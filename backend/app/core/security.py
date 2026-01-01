"""
PATH: backend/app/core/security.py
PURPOSE:
  - Security middleware and utilities
  - Rate limiting, headers, request validation

ROLE IN ARCHITECTURE:
  - Security layer for all API requests

NOTES FOR FUTURE AI:
  - All security headers are applied via middleware
  - Rate limiting uses in-memory store (upgrade to Redis for multi-instance)
"""

import time
import hashlib
import secrets
from collections import defaultdict
from typing import Callable, Optional
from functools import wraps

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


# ==============================================================================
# Rate Limiting
# ==============================================================================

class RateLimiter:
    """
    Token bucket rate limiter.
    
    Tracks requests per IP and enforces limits.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 20
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        
        # Track requests: {ip: [(timestamp, count), ...]}
        self._minute_buckets: dict[str, list] = defaultdict(list)
        self._hour_buckets: dict[str, list] = defaultdict(list)
        self._burst_tracker: dict[str, float] = {}
    
    def _clean_old_entries(self, bucket: list, window_seconds: int) -> list:
        """Remove entries older than the window."""
        cutoff = time.time() - window_seconds
        return [entry for entry in bucket if entry[0] > cutoff]
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, considering proxy headers."""
        # Check for forwarded headers (when behind reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (original client)
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        """
        Check if request is within rate limits.
        
        Returns:
            (allowed: bool, headers: dict) - Whether request is allowed and rate limit headers
        """
        ip = self._get_client_ip(request)
        now = time.time()
        
        # Clean old entries
        self._minute_buckets[ip] = self._clean_old_entries(self._minute_buckets[ip], 60)
        self._hour_buckets[ip] = self._clean_old_entries(self._hour_buckets[ip], 3600)
        
        # Count requests
        minute_count = len(self._minute_buckets[ip])
        hour_count = len(self._hour_buckets[ip])
        
        # Check burst (requests within 1 second)
        last_request = self._burst_tracker.get(ip, 0)
        burst_blocked = (now - last_request) < (1.0 / self.burst_limit)
        
        # Build rate limit headers
        headers = {
            "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
            "X-RateLimit-Remaining-Minute": str(max(0, self.requests_per_minute - minute_count - 1)),
            "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
            "X-RateLimit-Remaining-Hour": str(max(0, self.requests_per_hour - hour_count - 1)),
        }
        
        # Check limits
        if minute_count >= self.requests_per_minute:
            headers["Retry-After"] = "60"
            return False, headers
        
        if hour_count >= self.requests_per_hour:
            headers["Retry-After"] = "3600"
            return False, headers
        
        if burst_blocked:
            headers["Retry-After"] = "1"
            return False, headers
        
        # Record this request
        self._minute_buckets[ip].append((now, 1))
        self._hour_buckets[ip].append((now, 1))
        self._burst_tracker[ip] = now
        
        return True, headers


# Global rate limiter instance
# Very permissive limits for the research platform (internal use)
# Frontend makes ~20+ concurrent API calls on page load across multiple endpoints
rate_limiter = RateLimiter(
    requests_per_minute=1000,  # ~17 requests/second average
    requests_per_hour=20000,   # Allow heavy usage for research
    burst_limit=500            # Allow massive burst for page loads
)


# ==============================================================================
# Security Headers Middleware
# ==============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    
    Headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID for tracing
        request_id = secrets.token_hex(8)
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (only in production with HTTPS)
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy (relaxed for API)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' https://research.finsoeasy.com"
        )
        
        # Request ID for tracing
        response.headers["X-Request-ID"] = request_id
        
        # Remove server identification
        response.headers["Server"] = "R&D-Alpha"
        
        return response


# ==============================================================================
# Rate Limiting Middleware
# ==============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces rate limiting on all requests.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/health", "/", "/api"]:
            return await call_next(request)
        
        # Check rate limit
        allowed, headers = rate_limiter.check_rate_limit(request)
        
        if not allowed:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": headers.get("Retry-After", "60")
                }
            )
            for key, value in headers.items():
                response.headers[key] = value
            return response
        
        # Process request and add rate limit headers
        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# ==============================================================================
# Input Validation
# ==============================================================================

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent injection attacks.
    
    - Strips whitespace
    - Limits length
    - Removes null bytes
    - Escapes special characters
    """
    if not isinstance(value, str):
        return str(value)[:max_length]
    
    # Remove null bytes
    value = value.replace("\x00", "")
    
    # Strip and limit length
    value = value.strip()[:max_length]
    
    return value


def validate_ticker(ticker: str) -> str:
    """Validate and sanitize stock ticker symbol."""
    ticker = sanitize_string(ticker, max_length=10).upper()
    
    # Only allow alphanumeric and common ticker characters
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    if not all(c in allowed for c in ticker):
        raise ValueError(f"Invalid ticker format: {ticker}")
    
    return ticker


def validate_window_type(window_type: str) -> str:
    """Validate rolling window type parameter."""
    allowed = {"1yr", "3yr", "5yr", "10yr", "20yr"}
    window_type = sanitize_string(window_type, max_length=10).lower()
    
    if window_type not in allowed:
        raise ValueError(f"Invalid window type. Must be one of: {allowed}")
    
    return window_type


# ==============================================================================
# API Key Authentication (Optional)
# ==============================================================================

class APIKeyValidator:
    """
    Optional API key authentication.
    
    Usage:
        # In route:
        api_key: str = Depends(api_key_validator)
    """
    
    def __init__(self, required: bool = False):
        self.required = required
        # In production, load valid keys from secure storage
        self._valid_keys: set[str] = set()
    
    def add_key(self, key: str) -> None:
        """Add a valid API key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        self._valid_keys.add(key_hash)
    
    def validate(self, api_key: Optional[str]) -> bool:
        """Validate an API key."""
        if not api_key:
            return not self.required
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return key_hash in self._valid_keys
    
    async def __call__(self, request: Request) -> Optional[str]:
        """FastAPI dependency for API key validation."""
        api_key = request.headers.get("X-API-Key")
        
        if not self.validate(api_key):
            if self.required:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing API key",
                    headers={"WWW-Authenticate": "ApiKey"}
                )
        
        return api_key


# Global API key validator (currently optional)
api_key_validator = APIKeyValidator(required=False)


# ==============================================================================
# Request Logging
# ==============================================================================

def log_request(request: Request, response_status: int, duration_ms: float) -> dict:
    """
    Generate structured log entry for a request.
    
    Excludes sensitive information.
    """
    return {
        "event": "api_request",
        "method": request.method,
        "path": request.url.path,
        "status": response_status,
        "duration_ms": round(duration_ms, 2),
        "client_ip": rate_limiter._get_client_ip(request),
        "user_agent": request.headers.get("User-Agent", "unknown")[:100],
        "referer": request.headers.get("Referer", "")[:200],
    }

