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
    Send a welcome email to new newsletter subscriber via Resend.
    Branded as FSE Research and Investments.
    """
    if not RESEND_API_KEY:
        logger.warning("Resend API key not configured, skipping email")
        return False
    
    try:
        greeting = f"Hi {first_name}," if first_name else "Hello,"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f172a;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 560px; background-color: #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 48px 40px 32px 40px; text-align: center; border-bottom: 1px solid #334155;">
                            <div style="font-size: 28px; font-weight: 800; color: #f8fafc; letter-spacing: -0.5px; margin-bottom: 8px;">
                                FSE Research
                            </div>
                            <div style="font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px;">
                                Research & Investments
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h1 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 700; color: #f8fafc;">
                                Welcome to our Newsletter
                            </h1>
                            
                            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.7; color: #cbd5e1;">
                                {greeting}
                            </p>
                            
                            <p style="margin: 0 0 28px 0; font-size: 16px; line-height: 1.7; color: #cbd5e1;">
                                Thank you for subscribing. You're now on the list to receive our latest research updates, market insights, and investment analysis.
                            </p>
                            
                            <!-- What to Expect Box -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(6,182,212,0.15) 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #10b981;">
                                        <div style="font-size: 14px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;">
                                            What to Expect
                                        </div>
                                        <table role="presentation" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> Original research & analysis
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> Market insights & commentary
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> Investment ideas & strategies
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> Early access to new publications
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- CTA Button -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <a href="https://research.finsoeasy.com" style="display: inline-block; background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%); color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 36px; border-radius: 8px;">
                                            View Latest Research
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 32px 40px; background-color: #0f172a; text-align: center;">
                            <p style="margin: 0 0 8px 0; font-size: 14px; color: #94a3b8;">
                                Abhishek Sehgal
                            </p>
                            <p style="margin: 0 0 16px 0; font-size: 13px; color: #64748b;">
                                FSE Research and Investments
                            </p>
                            <a href="https://finsoeasy.com" style="color: #10b981; font-size: 13px; text-decoration: none;">
                                finsoeasy.com
                            </a>
                        </td>
                    </tr>
                    
                </table>
                
                <!-- Bottom Text -->
                <p style="margin: 24px 0 0 0; font-size: 12px; color: #475569; text-align: center;">
                    © 2025 FSE Research and Investments. All rights reserved.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
        """.strip()
        
        params = {
            "from": "FSE Research <abhishek@finsoeasy.com>",
            "to": [to_email],
            "subject": "Welcome to FSE Research Newsletter",
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
