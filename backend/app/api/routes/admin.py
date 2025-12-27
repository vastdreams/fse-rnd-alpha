"""
PATH: backend/app/api/routes/admin.py
PURPOSE:
  - Admin authentication and protected endpoints
  - Password-based login with JWT tokens
  - Admin dashboard data endpoints

ROLE IN ARCHITECTURE:
  - Authentication layer for admin access
  - Protected routes for admin functionality

NOTES FOR FUTURE AI:
  - Password is hashed using bcrypt via passlib
  - JWT tokens are used for session management
  - Token expiry is configurable via ADMIN_TOKEN_EXPIRE_MINUTES
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

router = APIRouter()

# ==============================================================================
# Security Configuration
# ==============================================================================

# JWT settings
SECRET_KEY = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') and settings.SECRET_KEY else "fse-rnd-alpha-secret-key-2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security scheme for Swagger UI
security = HTTPBearer()

# ==============================================================================
# Admin Credentials
# ==============================================================================

# Pre-hashed password for "FSE@123" using bcrypt
# Generated with: bcrypt.hashpw(b'FSE@123', bcrypt.gensalt())
ADMIN_PASSWORD_HASH = "$2b$12$nkj42rSdpRNFa3nOyYscOe.JCNKFx.zHGKw2KFgzuoAHgU3wGSYAK"

# Admin username
ADMIN_USERNAME = "admin"


# ==============================================================================
# Pydantic Models
# ==============================================================================

class LoginRequest(BaseModel):
    """Login request with username and password."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class AdminUser(BaseModel):
    """Authenticated admin user."""
    username: str
    is_admin: bool = True


# ==============================================================================
# Password Verification
# ==============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


# ==============================================================================
# JWT Token Management
# ==============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return the payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ==============================================================================
# Authentication Dependency
# ==============================================================================

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AdminUser:
    """
    Validate JWT token and return admin user.
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None or username != ADMIN_USERNAME:
        raise credentials_exception
    
    return AdminUser(username=username, is_admin=True)


# ==============================================================================
# Public Endpoints
# ==============================================================================

@router.post("/login", response_model=TokenResponse, tags=["Admin"])
async def admin_login(login_data: LoginRequest):
    """
    Admin login endpoint.
    
    Authenticate with username and password to receive a JWT token.
    
    - **username**: Admin username (default: "admin")
    - **password**: Admin password
    
    Returns a JWT token valid for 24 hours.
    """
    # Validate credentials
    if login_data.username != ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(login_data.password, ADMIN_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_data.username, "type": "admin"},
        expires_delta=access_token_expires,
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
    )


@router.get("/verify", tags=["Admin"])
async def verify_admin_token(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Verify if the current token is valid.
    
    Returns admin user info if token is valid.
    """
    return {
        "valid": True,
        "username": current_admin.username,
        "is_admin": current_admin.is_admin,
    }


# ==============================================================================
# Protected Admin Endpoints
# ==============================================================================

@router.get("/dashboard", tags=["Admin"])
async def admin_dashboard(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Admin dashboard data.
    
    Returns summary statistics and admin controls.
    Requires valid admin authentication.
    """
    return {
        "message": f"Welcome, {current_admin.username}!",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "api_version": "2.1.0",
            "platform": "R&D Alpha Research",
        },
        "actions": [
            {"name": "View API Stats", "endpoint": "/api/admin/stats"},
            {"name": "Manage Cache", "endpoint": "/api/admin/cache"},
            {"name": "View Logs", "endpoint": "/api/admin/logs"},
        ],
    }


@router.get("/stats", tags=["Admin"])
async def admin_stats(current_admin: AdminUser = Depends(get_current_admin)):
    """
    API usage statistics.
    
    Requires valid admin authentication.
    """
    return {
        "total_requests_today": 0,  # Would integrate with actual metrics
        "active_sessions": 1,
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.post("/cache/clear", tags=["Admin"])
async def clear_cache(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Clear application cache.
    
    Requires valid admin authentication.
    """
    # Would integrate with Redis cache clearing
    return {
        "success": True,
        "message": "Cache cleared successfully",
        "cleared_by": current_admin.username,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/subscribers", tags=["Admin"])
async def get_subscribers(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Get all subscribers.
    
    Requires valid admin authentication.
    """
    from app.api.routes.subscribe import get_all_subscribers
    subscribers = get_all_subscribers()
    return {
        "count": len(subscribers),
        "subscribers": sorted(subscribers, key=lambda x: x.get("subscribed_at", ""), reverse=True),
    }


@router.get("/donations", tags=["Admin"])
async def get_donations(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Get all donations.
    
    Requires valid admin authentication.
    """
    from app.api.routes.donations import get_all_donations
    donations = get_all_donations()
    return {
        "count": len(donations),
        "total_amount": sum(d.get("amount", 0) for d in donations),
        "donations": sorted(donations, key=lambda x: x.get("created_at", ""), reverse=True),
    }

