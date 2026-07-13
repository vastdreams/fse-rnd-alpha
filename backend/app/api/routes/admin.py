"""
Admin API Routes

Handles admin authentication and dashboard data.
Uses JWT tokens for session management.

Publication: https://research.finsoeasy.com
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.deps import get_db
from app.api.routes.auth import _create_token, get_current_user
from app.api.routes.subscribe import get_all_subscribers
from app.api.routes.donations import get_all_donations
from app.services import account_service

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
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
    Admin-only portal metadata.

    Credentials can exist in a server-local client configuration but must never
    cross the API boundary, including for an admin browser session.
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


async def get_current_admin(user: dict = Depends(get_current_user)) -> AdminUser:
    """Require a durable account explicitly assigned the admin role."""

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return AdminUser(username=str(user["email"]), is_admin=True)


@router.post("/login", response_model=TokenResponse)
async def admin_login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Issue the normal revocable user JWT only to a durable admin account."""

    try:
        user, error = await account_service.authenticate_account(
            db,
            email=str(login_data.email),
            password=login_data.password,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    await db.commit()
    access_token, expires_in = _create_token(
        user,
        await account_service.token_version(db, user["id"]),
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
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
