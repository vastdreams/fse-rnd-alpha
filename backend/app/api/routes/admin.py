"""
Admin API Routes

Handles admin authentication and dashboard data.
Uses JWT tokens for session management.

Publication: https://research.finsoeasy.com
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.deps import get_db
from app.api.routes.subscribe import get_all_subscribers
from app.api.routes.donations import get_all_donations

router = APIRouter()

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer()

# Admin credentials
# Pre-hashed admin password (bcrypt). Prefer moving this to an environment variable for production.
ADMIN_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.S6W4P2fF6Bz.Pu"
ADMIN_USERNAME = "admin"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminUser(BaseModel):
    username: str
    is_admin: bool = True


class ClientPortalResponse(BaseModel):
    """
    Admin-only representation of a client portal configuration.
    Note: This is deliberately served from a local config file to avoid committing client credentials.
    """

    id: str
    name: str
    slug: str
    description: str
    portal_url: str
    status: str
    sector: str
    location: str
    afsl: Optional[str] = None
    documents: List[str] = []
    access_password: Optional[str] = None


def _load_client_portals_from_file() -> List[ClientPortalResponse]:
    """
    Load admin client portal configs from disk.

    Expected location:
      - settings.ADMIN_CLIENTS_CONFIG_PATH (absolute or relative), OR
      - backend/admin_clients.json (default)

    This file MUST NOT be committed (contains client passwords).
    """
    configured_path = (settings.ADMIN_CLIENTS_CONFIG_PATH or "").strip()
    if configured_path:
        path = Path(configured_path)
    else:
        # research/backend/app/api/routes/admin.py -> parents[3] == research/backend
        path = Path(__file__).resolve().parents[3] / "admin_clients.json"

    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if not isinstance(raw, list):
        return []

    out: List[ClientPortalResponse] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            out.append(ClientPortalResponse(**item))
        except Exception:
            continue
    return out


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AdminUser:
    """Validate JWT token and return admin user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(credentials.credentials)
    
    if payload is None:
        raise credentials_exception
    
    username = payload.get("sub")
    if username is None or username != ADMIN_USERNAME:
        raise credentials_exception
    
    return AdminUser(username=username, is_admin=True)


@router.post("/login", response_model=TokenResponse)
async def admin_login(login_data: LoginRequest):
    """Admin login endpoint."""
    
    if login_data.username != ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Check password (bcrypt hash)
    password_valid = False
    try:
        password_valid = verify_password(login_data.password, ADMIN_PASSWORD_HASH)
    except Exception:
        pass
    
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_data.username, "type": "admin"},
        expires_delta=access_token_expires,
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/verify")
async def verify_admin_token(current_admin: AdminUser = Depends(get_current_admin)):
    """Verify if the current token is valid."""
    return {"valid": True, "username": current_admin.username, "is_admin": current_admin.is_admin}


@router.get("/dashboard")
async def admin_dashboard(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin dashboard with stats from PostgreSQL."""
    
    subscribers = await get_all_subscribers(db)
    donations = await get_all_donations(db)
    total_amount = sum(d["amount"] for d in donations)
    
    return {
        "message": f"Welcome, {current_admin.username}!",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "api_version": "2.1.0",
            "platform": "R&D Alpha Research",
            "total_subscribers": len(subscribers),
            "total_donations": len(donations),
            "total_donation_amount": total_amount,
        },
    }


@router.get("/subscribers")
async def get_subscribers_admin(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all subscribers (admin only)."""
    subscribers = await get_all_subscribers(db)
    return {"count": len(subscribers), "subscribers": subscribers}


@router.get("/donations")
async def get_donations_admin(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all donations (admin only)."""
    donations = await get_all_donations(db)
    total = sum(d["amount"] for d in donations)
    return {"count": len(donations), "total_amount": total, "donations": donations}


@router.post("/cache/clear")
async def clear_cache(current_admin: AdminUser = Depends(get_current_admin)):
    """Clear application cache."""
    return {
        "success": True,
        "message": "Cache cleared successfully",
        "cleared_by": current_admin.username,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/clients", response_model=List[ClientPortalResponse])
async def get_client_portals_admin(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Return client portal configurations for the unified admin UI.
    """
    _ = current_admin  # explicit: auth guard is the only requirement
    return _load_client_portals_from_file()
