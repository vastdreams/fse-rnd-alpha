"""
PATH: backend/app/core/security.py
PURPOSE: Security middleware (headers, rate limiting), input validation, optional API key auth
EXPORTS: RateLimiter, SecurityHeadersMiddleware, RateLimitMiddleware, APIKeyValidator, sanitize_string, validate_ticker, validate_window_type, log_request
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


class RateLimiter:
    """Token bucket rate limiter. Tracks requests per IP and enforces limits."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 20,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self._minute_buckets: dict[str, list] = defaultdict(list)
        self._hour_buckets: dict[str, list] = defaultdict(list)
        self._burst_tracker: dict[str, float] = {}

    def _clean_old_entries(self, bucket: list, window_seconds: int) -> list:
        cutoff = time.time() - window_seconds
        return [entry for entry in bucket if entry[0] > cutoff]

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        ip = self._get_client_ip(request)
        now = time.time()
        self._minute_buckets[ip] = self._clean_old_entries(self._minute_buckets[ip], 60)
        self._hour_buckets[ip] = self._clean_old_entries(self._hour_buckets[ip], 3600)
        minute_count = len(self._minute_buckets[ip])
        hour_count = len(self._hour_buckets[ip])
        last_request = self._burst_tracker.get(ip, 0)
        burst_blocked = (now - last_request) < (1.0 / self.burst_limit)
        headers = {
            "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
            "X-RateLimit-Remaining-Minute": str(max(0, self.requests_per_minute - minute_count - 1)),
            "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
            "X-RateLimit-Remaining-Hour": str(max(0, self.requests_per_hour - hour_count - 1)),
        }
        if minute_count >= self.requests_per_minute:
            headers["Retry-After"] = "60"
            return False, headers
        if hour_count >= self.requests_per_hour:
            headers["Retry-After"] = "3600"
            return False, headers
        if burst_blocked:
            headers["Retry-After"] = "1"
            return False, headers
        self._minute_buckets[ip].append((now, 1))
        self._hour_buckets[ip].append((now, 1))
        self._burst_tracker[ip] = now
        return True, headers


# Permissive limits for internal research platform
rate_limiter = RateLimiter(
    requests_per_minute=1000,
    requests_per_hour=20000,
    burst_limit=500,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers (nosniff, DENY framing, HSTS, CSP, etc.) to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = secrets.token_hex(8)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' https://research.finsoeasy.com"
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["Server"] = "R&D-Alpha"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces rate limiting on all requests (currently bypassed; Nginx handles it)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Rate limiting handled by Nginx — skip application-level enforcement
        return await call_next(request)

        allowed, headers = rate_limiter.check_rate_limit(request)
        if not allowed:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": headers.get("Retry-After", "60"),
                },
            )
            for key, value in headers.items():
                response.headers[key] = value
            return response
        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        return response


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input: strip, limit length, remove null bytes."""
    if not isinstance(value, str):
        return str(value)[:max_length]
    value = value.replace("\x00", "")
    return value.strip()[:max_length]


def validate_ticker(ticker: str) -> str:
    """Validate and sanitize stock ticker symbol (alphanumeric + . and -)."""
    ticker = sanitize_string(ticker, max_length=10).upper()
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    if not all(c in allowed for c in ticker):
        raise ValueError(f"Invalid ticker format: {ticker}")
    return ticker


def validate_window_type(window_type: str) -> str:
    """Validate rolling window type parameter (1yr/3yr/5yr/10yr/20yr)."""
    allowed = {"1yr", "3yr", "5yr", "10yr", "20yr"}
    window_type = sanitize_string(window_type, max_length=10).lower()
    if window_type not in allowed:
        raise ValueError(f"Invalid window type. Must be one of: {allowed}")
    return window_type


class APIKeyValidator:
    """Optional API key authentication via X-API-Key header."""

    def __init__(self, required: bool = False):
        self.required = required
        self._valid_keys: set[str] = set()

    def add_key(self, key: str) -> None:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        self._valid_keys.add(key_hash)

    def validate(self, api_key: Optional[str]) -> bool:
        if not api_key:
            return not self.required
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return key_hash in self._valid_keys

    async def __call__(self, request: Request) -> Optional[str]:
        api_key = request.headers.get("X-API-Key")
        if not self.validate(api_key):
            if self.required:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing API key",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
        return api_key


api_key_validator = APIKeyValidator(required=False)


def log_request(request: Request, response_status: int, duration_ms: float) -> dict:
    """Generate structured log entry for a request (excludes sensitive info)."""
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
