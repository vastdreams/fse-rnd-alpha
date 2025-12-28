"""
Subscribe API Routes

Handles newsletter subscriptions with PostgreSQL persistence.
Sends thank you emails to new subscribers via Resend.

Publication: https://research.finsoeasy.com
"""

import os
import logging
import resend
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Resend API configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
resend.api_key = RESEND_API_KEY


class SubscribeRequest(BaseModel):
    email: EmailStr
    source: Optional[str] = "website"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profession: Optional[str] = None


class SubscribeResponse(BaseModel):
    success: bool
    message: str


class SubscriberInfo(BaseModel):
    email: str
    source: str
    subscribed_at: str
    is_active: bool


def send_thank_you_email(to_email: str, first_name: Optional[str] = None) -> bool:
    """
    Send a thank you email to new subscriber via Resend.
    """
    if not RESEND_API_KEY:
        logger.warning("Resend API key not configured, skipping email")
        return False
    
    try:
        greeting = f"Hi {first_name}," if first_name else "Hi there,"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 20px; background: #f1f5f9;">
    <div style="background: linear-gradient(135deg, #059669 0%, #0d9488 100%); padding: 40px 32px; border-radius: 16px 16px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">Welcome to R&D Alpha</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 16px;">Factor-Based Investment Research</p>
    </div>
    <div style="background: white; padding: 32px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 16px 16px;">
        <p style="font-size: 16px; margin-top: 0;">{greeting}</p>
        <p>Thank you for subscribing to R&D Alpha Research! You're now part of a community exploring the relationship between <strong>R&D investment intensity</strong> and <strong>long-term stock returns</strong>.</p>
        
        <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin: 24px 0;">
            <h3 style="color: #059669; margin-top: 0; font-size: 16px;">What you'll receive:</h3>
            <ul style="margin: 0; padding-left: 20px;">
                <li style="margin-bottom: 8px;">Research updates when we publish new findings</li>
                <li style="margin-bottom: 8px;">Market insights on R&D factor performance</li>
                <li style="margin-bottom: 0;">Early access to new features and data</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="https://research.finsoeasy.com" style="display: inline-block; background: linear-gradient(135deg, #059669 0%, #0d9488 100%); color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">Explore the Research</a>
        </div>
        
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="color: #64748b; font-size: 14px; margin-bottom: 0;">Best regards,<br><strong>Abhishek Sehgal</strong><br>R&D Alpha Research<br><a href="https://finsoeasy.com" style="color: #059669;">finsoeasy.com</a></p>
    </div>
    <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 16px;">
        © 2025 R&D Alpha Research. All rights reserved.
    </p>
</body>
</html>
        """.strip()
        
        params = {
            "from": "R&D Alpha Research <abhishek@finsoeasy.com>",
            "to": [to_email],
            "subject": "Welcome to R&D Alpha Research 🚀",
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Welcome email sent to {to_email}, id: {response.get('id', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(request: SubscribeRequest, db: AsyncSession = Depends(get_db)):
    """
    Subscribe to R&D Alpha research updates.
    Stores in PostgreSQL and sends a thank you email.
    """
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


async def add_subscriber_to_db(db: AsyncSession, email: str, source: str = "donation") -> bool:
    """
    Add an email to the subscriber list (called from donations webhook).
    Returns True if newly added, False if already existed.
    """
    email = email.lower()
    
    result = await db.execute(
        text("SELECT id FROM subscribers WHERE email = :email"),
        {"email": email}
    )
    existing = result.fetchone()
    
    if existing:
        logger.info(f"Subscriber {email} already exists")
        return False
    
    await db.execute(
        text("""
            INSERT INTO subscribers (email, source, subscribed_at, is_active)
            VALUES (:email, :source, :subscribed_at, true)
        """),
        {
            "email": email,
            "source": source,
            "subscribed_at": datetime.utcnow()
        }
    )
    await db.commit()
    
    logger.info(f"Auto-subscribed donor: {email} (source: {source})")
    return True


@router.get("/subscribers/count")
async def get_subscriber_count(db: AsyncSession = Depends(get_db)):
    """Get total subscriber count."""
    result = await db.execute(text("SELECT COUNT(*) FROM subscribers WHERE is_active = true"))
    count = result.scalar()
    return {"count": count}


async def get_all_subscribers(db: AsyncSession) -> List[dict]:
    """Get all active subscribers (used by admin routes)."""
    result = await db.execute(
        text("""
            SELECT email, source, first_name, last_name, profession, subscribed_at, is_active 
            FROM subscribers 
            WHERE is_active = true 
            ORDER BY subscribed_at DESC
        """)
    )
    rows = result.fetchall()
    return [
        {
            "email": row[0],
            "source": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "profession": row[4],
            "subscribed_at": row[5].isoformat() if row[5] else None,
            "is_active": row[6]
        }
        for row in rows
    ]
