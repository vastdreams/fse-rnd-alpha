"""Middleware for collecting API metrics."""
from flask import request, g
from functools import wraps
from time import time
from src.monitoring.metrics import api_requests_total, api_request_duration
from src.logging.logger import get_logger

logger = get_logger(__name__)


def track_metrics(f):
    """Decorator to track API metrics."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time()
        
        try:
            response = f(*args, **kwargs)
            status_code = response[1] if isinstance(response, tuple) else 200
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time() - start_time
            
            # Record metrics
            endpoint = request.endpoint or request.path
            method = request.method
            
            api_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()
            
            api_request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        
        return response
    return decorated_function

