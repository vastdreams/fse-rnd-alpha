"""
PATH: backend/app/api/routes/subscribe/endpoints.py
PURPOSE: Subscribe, unsubscribe, and subscriber count route endpoints
"""

import base64
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db
from app.api.routes.subscribe.models import (
    SubscribeRequest, SubscribeResponse, UnsubscribeRequest
)
from app.api.routes.subscribe.tokens import verify_unsubscribe_token
from app.api.routes.subscribe.email import send_thank_you_email

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(request: SubscribeRequest, db: AsyncSession = Depends(get_db)):
    """Subscribe to R&D Alpha research updates."""
    email = request.email.lower()
    
    # Check if already subscribed
    result = await db.execute(
        text("SELECT id FROM subscribers WHERE email = :email"),
        {"email": email}
    )
    existing = result.fetchone()
    
    if existing:
        return SubscribeResponse(
            success=True,
            message="You're already subscribed! Check your inbox for our latest updates."
        )
    
    # Insert new subscriber
    await db.execute(
        text("""
            INSERT INTO subscribers (email, source, first_name, last_name, profession, subscribed_at, is_active)
            VALUES (:email, :source, :first_name, :last_name, :profession, :subscribed_at, true)
        """),
        {
            "email": email,
            "source": request.source,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "profession": request.profession,
            "subscribed_at": datetime.utcnow()
        }
    )
    
    logger.info(f"New subscriber: {email} (source: {request.source})")
    
    # Send welcome email via Resend
    email_sent = send_thank_you_email(email, request.first_name)
    
    if email_sent:
        return SubscribeResponse(
            success=True,
            message="Thank you for subscribing! Check your inbox for a welcome email."
        )
    else:
        return SubscribeResponse(
            success=True,
            message="Thank you for subscribing! You'll receive our research updates."
        )


@router.get("/subscribers/count")
async def get_subscriber_count(db: AsyncSession = Depends(get_db)):
    """Get total subscriber count."""
    result = await db.execute(text("SELECT COUNT(*) FROM subscribers WHERE is_active = true"))
    count = result.scalar()
    return {"count": count}


@router.post("/unsubscribe", response_model=SubscribeResponse)
async def unsubscribe(request: UnsubscribeRequest, db: AsyncSession = Depends(get_db)):
    """Unsubscribe from the newsletter. Requires a valid token."""
    # Decode email from base64
    try:
        # Add padding if needed
        padded = request.email + "=" * (4 - len(request.email) % 4)
        email = base64.urlsafe_b64decode(padded).decode().lower()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Verify token
    if not verify_unsubscribe_token(email, request.token):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token")
    
    # Check if subscriber exists
    result = await db.execute(
        text("SELECT id, is_active FROM subscribers WHERE email = :email"),
        {"email": email}
    )
    subscriber = result.fetchone()
    
    if not subscriber:
        return SubscribeResponse(
            success=True,
            message="Email not found in our list."
        )
    
    if not subscriber[1]:  # is_active is False
        return SubscribeResponse(
            success=True,
            message="You have already been unsubscribed."
        )
    
    # Mark as inactive (soft delete)
    await db.execute(
        text("UPDATE subscribers SET is_active = false WHERE email = :email"),
        {"email": email}
    )
    await db.commit()
    
    logger.info(f"User unsubscribed: {email}")
    
    return SubscribeResponse(
        success=True,
        message="You have been successfully unsubscribed. We're sorry to see you go!"
    )


@router.get("/unsubscribe/verify")
async def verify_unsubscribe(e: str, t: str):
    """Verify an unsubscribe link (for the frontend to check before showing UI)."""
    try:
        padded = e + "=" * (4 - len(e) % 4)
        email = base64.urlsafe_b64decode(padded).decode().lower()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    if not verify_unsubscribe_token(email, t):
        raise HTTPException(status_code=400, detail="Invalid link")
    
    return {"valid": True, "email": email}
