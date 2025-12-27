"""
Analytics API Routes

Tracks page views, session duration, and visitor behavior.
Stores in PostgreSQL for reliable analytics.

Publication: https://research.finsoeasy.com
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db
from app.api.routes.admin import get_current_admin, AdminUser

router = APIRouter()
logger = logging.getLogger(__name__)


class PageViewRequest(BaseModel):
    """Request to track a page view."""
    page_path: str
    page_title: Optional[str] = None
    referrer: Optional[str] = None
    session_id: str
    visitor_id: str


class UpdateDurationRequest(BaseModel):
    """Request to update time spent on page."""
    session_id: str
    page_path: str
    duration_seconds: int


class PageViewResponse(BaseModel):
    """Response after tracking page view."""
    success: bool
    view_id: int


def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_device_type(user_agent: str) -> str:
    """Determine device type from user agent."""
    ua_lower = user_agent.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        return "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        return "tablet"
    return "desktop"


@router.post("/analytics/pageview", response_model=PageViewResponse)
async def track_pageview(
    data: PageViewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Track a page view.
    Called by frontend when user navigates to a page.
    """
    user_agent = request.headers.get("user-agent", "")
    ip_address = get_client_ip(request)
    device_type = get_device_type(user_agent)
    
    # Insert page view
    result = await db.execute(
        text("""
            INSERT INTO page_views 
            (session_id, visitor_id, page_path, page_title, referrer, user_agent, ip_address, device_type, created_at)
            VALUES (:session_id, :visitor_id, :page_path, :page_title, :referrer, :user_agent, :ip_address, :device_type, :created_at)
            RETURNING id
        """),
        {
            "session_id": data.session_id,
            "visitor_id": data.visitor_id,
            "page_path": data.page_path,
            "page_title": data.page_title,
            "referrer": data.referrer,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "device_type": device_type,
            "created_at": datetime.utcnow()
        }
    )
    view_id = result.scalar()
    
    # Update or create visitor session
    await db.execute(
        text("""
            INSERT INTO visitor_sessions (visitor_id, first_seen, last_seen, total_visits)
            VALUES (:visitor_id, :now, :now, 1)
            ON CONFLICT (visitor_id) DO UPDATE SET
                last_seen = :now,
                total_visits = visitor_sessions.total_visits + 1
        """),
        {"visitor_id": data.visitor_id, "now": datetime.utcnow()}
    )
    
    logger.info(f"Page view tracked: {data.page_path} by {data.visitor_id[:8]}...")
    
    return PageViewResponse(success=True, view_id=view_id)


@router.post("/analytics/duration")
async def update_duration(
    data: UpdateDurationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update the duration spent on a page.
    Called by frontend when user leaves page or periodically.
    """
    await db.execute(
        text("""
            UPDATE page_views 
            SET duration_seconds = :duration, ended_at = :ended_at
            WHERE session_id = :session_id 
              AND page_path = :page_path 
              AND ended_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {
            "session_id": data.session_id,
            "page_path": data.page_path,
            "duration": data.duration_seconds,
            "ended_at": datetime.utcnow()
        }
    )
    
    return {"success": True}


@router.get("/admin/analytics/summary")
async def get_analytics_summary(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    days: int = 30
):
    """
    Get analytics summary for admin dashboard.
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Total views and unique visitors
    totals = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total_views,
                COUNT(DISTINCT visitor_id) as unique_visitors,
                COUNT(DISTINCT session_id) as total_sessions,
                AVG(duration_seconds) as avg_duration
            FROM page_views
            WHERE created_at >= :since
              AND visitor_id NOT IN (SELECT visitor_id FROM visitor_sessions WHERE is_blocked = true)
        """),
        {"since": since}
    )
    totals_row = totals.fetchone()
    
    # Views by page
    pages = await db.execute(
        text("""
            SELECT 
                page_path,
                COUNT(*) as views,
                COUNT(DISTINCT visitor_id) as unique_visitors,
                AVG(duration_seconds) as avg_duration
            FROM page_views
            WHERE created_at >= :since
              AND visitor_id NOT IN (SELECT visitor_id FROM visitor_sessions WHERE is_blocked = true)
            GROUP BY page_path
            ORDER BY views DESC
            LIMIT 20
        """),
        {"since": since}
    )
    pages_data = [
        {
            "page": row[0],
            "views": row[1],
            "unique_visitors": row[2],
            "avg_duration": round(row[3] or 0, 1)
        }
        for row in pages.fetchall()
    ]
    
    # Views by day
    daily = await db.execute(
        text("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as views,
                COUNT(DISTINCT visitor_id) as unique_visitors
            FROM page_views
            WHERE created_at >= :since
              AND visitor_id NOT IN (SELECT visitor_id FROM visitor_sessions WHERE is_blocked = true)
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """),
        {"since": since}
    )
    daily_data = [
        {"date": str(row[0]), "views": row[1], "unique_visitors": row[2]}
        for row in daily.fetchall()
    ]
    
    # Device breakdown
    devices = await db.execute(
        text("""
            SELECT 
                device_type,
                COUNT(*) as count
            FROM page_views
            WHERE created_at >= :since
              AND visitor_id NOT IN (SELECT visitor_id FROM visitor_sessions WHERE is_blocked = true)
            GROUP BY device_type
        """),
        {"since": since}
    )
    devices_data = {row[0]: row[1] for row in devices.fetchall()}
    
    return {
        "period_days": days,
        "totals": {
            "views": totals_row[0] or 0,
            "unique_visitors": totals_row[1] or 0,
            "sessions": totals_row[2] or 0,
            "avg_duration_seconds": round(totals_row[3] or 0, 1)
        },
        "pages": pages_data,
        "daily": daily_data,
        "devices": devices_data
    }


@router.get("/admin/analytics/visitors")
async def get_visitors(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 100
):
    """
    Get list of all visitors with their activity.
    """
    result = await db.execute(
        text("""
            SELECT 
                vs.visitor_id,
                vs.first_seen,
                vs.last_seen,
                vs.total_visits,
                vs.is_blocked,
                vs.notes,
                (SELECT ip_address FROM page_views WHERE visitor_id = vs.visitor_id ORDER BY created_at DESC LIMIT 1) as last_ip,
                (SELECT device_type FROM page_views WHERE visitor_id = vs.visitor_id ORDER BY created_at DESC LIMIT 1) as device
            FROM visitor_sessions vs
            ORDER BY vs.last_seen DESC
            LIMIT :limit
        """),
        {"limit": limit}
    )
    
    visitors = [
        {
            "visitor_id": row[0],
            "first_seen": row[1].isoformat() if row[1] else None,
            "last_seen": row[2].isoformat() if row[2] else None,
            "total_visits": row[3],
            "is_blocked": row[4],
            "notes": row[5],
            "last_ip": row[6],
            "device": row[7]
        }
        for row in result.fetchall()
    ]
    
    return {"count": len(visitors), "visitors": visitors}


@router.post("/admin/analytics/block-visitor")
async def block_visitor(
    visitor_id: str,
    notes: Optional[str] = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Block a visitor from analytics (e.g., yourself).
    Their data remains but is excluded from reports.
    """
    await db.execute(
        text("""
            UPDATE visitor_sessions 
            SET is_blocked = true, notes = :notes
            WHERE visitor_id = :visitor_id
        """),
        {"visitor_id": visitor_id, "notes": notes or "Blocked by admin"}
    )
    
    return {"success": True, "visitor_id": visitor_id, "blocked": True}


@router.post("/admin/analytics/unblock-visitor")
async def unblock_visitor(
    visitor_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Unblock a visitor."""
    await db.execute(
        text("""
            UPDATE visitor_sessions 
            SET is_blocked = false, notes = NULL
            WHERE visitor_id = :visitor_id
        """),
        {"visitor_id": visitor_id}
    )
    
    return {"success": True, "visitor_id": visitor_id, "blocked": False}


@router.get("/admin/analytics/visitor/{visitor_id}")
async def get_visitor_history(
    visitor_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed page view history for a specific visitor.
    """
    result = await db.execute(
        text("""
            SELECT 
                page_path, page_title, referrer, device_type, 
                duration_seconds, created_at, ip_address
            FROM page_views
            WHERE visitor_id = :visitor_id
            ORDER BY created_at DESC
            LIMIT 200
        """),
        {"visitor_id": visitor_id}
    )
    
    history = [
        {
            "page": row[0],
            "title": row[1],
            "referrer": row[2],
            "device": row[3],
            "duration": row[4],
            "timestamp": row[5].isoformat() if row[5] else None,
            "ip": row[6]
        }
        for row in result.fetchall()
    ]
    
    return {"visitor_id": visitor_id, "page_views": history}

