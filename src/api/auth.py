"""Authentication and authorization for Flask API."""
from functools import wraps
from flask import request, jsonify, g
from config.settings import get_settings
from src.logging.logger import get_logger
import os
from datetime import datetime, timedelta

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

logger = get_logger(__name__)
settings = get_settings()

# API Key authentication (simple for MVP)
# In production, use JWT tokens or OAuth2

API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"


def get_api_key():
    """Extract API key from request header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    elif auth_header.startswith("ApiKey "):
        return auth_header[7:]
    return request.headers.get("X-API-Key") or request.args.get("api_key")


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not REQUIRE_AUTH:
            # Authentication disabled in development
            return f(*args, **kwargs)
        
        api_key = get_api_key()
        if not api_key:
            return jsonify({
                "error": "Authentication Required",
                "message": "API key is required. Provide it in Authorization header or X-API-Key header."
            }), 401
        
        if api_key not in API_KEYS:
            logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({
                "error": "Invalid API Key",
                "message": "The provided API key is invalid."
            }), 401
        
        g.api_key = api_key
        return f(*args, **kwargs)
    return decorated_function


def optional_api_key(f):
    """Decorator for optional API key (for rate limit differentiation)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = get_api_key()
        if api_key and api_key in API_KEYS:
            g.api_key = api_key
            g.authenticated = True
        else:
            g.authenticated = False
        return f(*args, **kwargs)
    return decorated_function


# JWT token generation (for future use)
def generate_jwt_token(user_id: str, expires_in: int = 3600) -> str:
    """Generate JWT token for user."""
    if not JWT_AVAILABLE:
        raise ImportError("PyJWT not installed. Install with: pip install PyJWT")
    
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and return payload."""
    if not JWT_AVAILABLE:
        raise ImportError("PyJWT not installed. Install with: pip install PyJWT")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
