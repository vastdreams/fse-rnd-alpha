"""
Subscribe API Routes

Handles newsletter subscriptions with PostgreSQL persistence.
Sends thank you emails to new subscribers.

Publication: https://research.finsoeasy.com
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
SMTP_USER = "abhishek@finsoeasy.com"
SMTP_PASSWORD = os.getenv("FINSOEASY_EMAIL_PASSWORD", "")


class SubscribeRequest(BaseModel):
    email: EmailStr
    source: Optional[str] = "website"
    name: Optional[str] = None
    profession: Optional[str] = None


class SubscribeResponse(BaseModel):
    success: bool
    message: str


class SubscriberInfo(BaseModel):
    email: str
    source: str
    subscribed_at: str
    is_active: bool


def send_thank_you_email(to_email: str) -> bool:
    """
    Send a thank you email to new subscriber.
    """
    if not SMTP_PASSWORD:
        logger.warning("SMTP password not configured, skipping email")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Welcome to R&D Alpha Research"
        msg["From"] = f"R&D Alpha Research <{SMTP_USER}>"
        msg["To"] = to_email
        
        text_content = """
Thank you for subscribing to R&D Alpha Research!

You're now part of a community exploring the relationship between R&D investment intensity and long-term stock returns.

What you'll receive:
- Research updates when we publish new findings
- Market insights on R&D factor performance
- Early access to new features and data

Visit our research platform: https://research.finsoeasy.com

Best regards,
Abhishek Sehgal
R&D Alpha Research
https://finsoeasy.com
        """.strip()
        
        html_content = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: system-ui, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #059669 0%, #0d9488 100%); padding: 32px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Welcome to R&D Alpha Research</h1>
    </div>
    <div style="background: #f8fafc; padding: 32px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
        <p style="font-size: 16px; margin-top: 0;">Thank you for subscribing!</p>
        <p>You're now part of a community exploring <strong>R&D investment intensity</strong> and <strong>long-term stock returns</strong>.</p>
        <h3 style="color: #059669;">What you'll receive:</h3>
        <ul><li>Research updates when we publish new findings</li><li>Market insights on R&D factor performance</li><li>Early access to new features and data</li></ul>
        <div style="text-align: center; margin: 32px 0;">
            <a href="https://research.finsoeasy.com" style="display: inline-block; background: #059669; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">Visit Research Platform</a>
        </div>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="color: #64748b; font-size: 14px;">Best regards,<br><strong>Abhishek Sehgal</strong><br>R&D Alpha Research</p>
    </div>
</body>
</html>
        """.strip()
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        
        logger.info(f"Thank you email sent to {to_email}")
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
            INSERT INTO subscribers (email, source, name, profession, subscribed_at, is_active)
            VALUES (:email, :source, :name, :profession, :subscribed_at, true)
        """),
        {
            "email": email,
            "source": request.source,
            "name": request.name,
            "profession": request.profession,
            "subscribed_at": datetime.utcnow()
        }
    )
    
    logger.info(f"New subscriber: {email} (source: {request.source})")
    
    # Send thank you email
    email_sent = send_thank_you_email(email)
    
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
            SELECT email, source, name, profession, subscribed_at, is_active 
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
            "name": row[2],
            "profession": row[3],
            "subscribed_at": row[4].isoformat() if row[4] else None,
            "is_active": row[5]
        }
        for row in rows
    ]
