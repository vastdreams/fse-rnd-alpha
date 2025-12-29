"""
Subscribe API Routes

Handles newsletter subscriptions with PostgreSQL persistence.
Sends thank you emails to new subscribers via Resend.
Includes unsubscribe functionality with secure tokens.

Publication: https://research.finsoeasy.com
"""

import os
import logging
import resend
import hashlib
import base64
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Resend API configuration - set dynamically in function to ensure env is loaded
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

# Secret for generating unsubscribe tokens
UNSUBSCRIBE_SECRET = os.getenv("SECRET_KEY", "fse-research-secret-2025")


def generate_unsubscribe_token(email: str) -> str:
    """Generate a secure token for unsubscribe links."""
    data = f"{email.lower()}:{UNSUBSCRIBE_SECRET}"
    hash_bytes = hashlib.sha256(data.encode()).digest()
    return base64.urlsafe_b64encode(hash_bytes[:16]).decode().rstrip("=")


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Verify that an unsubscribe token is valid for the given email."""
    expected_token = generate_unsubscribe_token(email)
    return token == expected_token


def get_unsubscribe_url(email: str) -> str:
    """Generate the full unsubscribe URL for an email."""
    token = generate_unsubscribe_token(email)
    encoded_email = base64.urlsafe_b64encode(email.lower().encode()).decode().rstrip("=")
    return f"https://research.finsoeasy.com/unsubscribe?e={encoded_email}&t={token}"


class SubscribeRequest(BaseModel):
    email: EmailStr
    source: Optional[str] = "website"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profession: Optional[str] = None


class SubscribeResponse(BaseModel):
    success: bool
    message: str


class UnsubscribeRequest(BaseModel):
    email: str
    token: str


class SubscriberInfo(BaseModel):
    email: str
    source: str
    subscribed_at: str
    is_active: bool


def send_thank_you_email(to_email: str, first_name: Optional[str] = None) -> bool:
    """
    Send a welcome email to new newsletter subscriber via Resend.
    Includes R&D Alpha research highlights and unsubscribe link.
    """
    # Set API key dynamically to ensure env is loaded
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("Resend API key not configured, skipping email")
        return False
    
    resend.api_key = api_key
    
    try:
        greeting = f"Hi {first_name}," if first_name else "Hello,"
        unsubscribe_url = get_unsubscribe_url(to_email)
        
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
                                R&D Alpha
                            </div>
                            <div style="font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px;">
                                FSE Research & Investments
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h1 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 700; color: #f8fafc;">
                                Welcome to R&D Alpha
                            </h1>
                            
                            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.7; color: #cbd5e1;">
                                {greeting}
                            </p>
                            
                            <p style="margin: 0 0 28px 0; font-size: 16px; line-height: 1.7; color: #cbd5e1;">
                                Thank you for subscribing. You've joined a community of investors and researchers exploring <strong style="color: #f8fafc;">hidden alpha in R&D-intensive companies</strong>.
                            </p>
                            
                            <!-- Key Research Findings -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(99,102,241,0.15) 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #3b82f6;">
                                        <div style="font-size: 14px; font-weight: 600; color: #60a5fa; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;">
                                            📊 Our Key Findings
                                        </div>
                                        <table role="presentation" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding: 8px 0; color: #e2e8f0; font-size: 15px; line-height: 1.6;">
                                                    <strong style="color: #60a5fa;">~5% annual alpha</strong> — R&D-intensive portfolios outperform market benchmarks
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #e2e8f0; font-size: 15px; line-height: 1.6;">
                                                    <strong style="color: #60a5fa;">Hidden value</strong> — R&D is expensed, not capitalized, creating systematic undervaluation
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #e2e8f0; font-size: 15px; line-height: 1.6;">
                                                    <strong style="color: #60a5fa;">25-year backtest</strong> — Rigorous point-in-time testing with real SEC filings
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- What to Expect Box -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(6,182,212,0.15) 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #10b981;">
                                        <div style="font-size: 14px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;">
                                            What You'll Receive
                                        </div>
                                        <table role="presentation" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> Monthly research updates & new findings
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> R&D factor performance & market insights
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> Early access to whitepapers & tools
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
                                            Explore the Research
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 32px 40px; background-color: #0f172a; text-align: center; border-top: 1px solid #334155;">
                            <p style="margin: 0 0 8px 0; font-size: 14px; color: #94a3b8;">
                                Abhishek Sehgal
                            </p>
                            <p style="margin: 0 0 16px 0; font-size: 13px; color: #64748b;">
                                FSE Research and Investments
                            </p>
                            <div style="margin-bottom: 16px;">
                                <a href="https://research.finsoeasy.com" style="color: #10b981; font-size: 13px; text-decoration: none; margin: 0 8px;">Research</a>
                                <span style="color: #475569;">|</span>
                                <a href="https://research.finsoeasy.com/privacy" style="color: #64748b; font-size: 13px; text-decoration: none; margin: 0 8px;">Privacy</a>
                                <span style="color: #475569;">|</span>
                                <a href="https://research.finsoeasy.com/terms" style="color: #64748b; font-size: 13px; text-decoration: none; margin: 0 8px;">Terms</a>
                            </div>
                            <p style="margin: 0; font-size: 12px; color: #475569;">
                                © 2025 FSE Research and Investments. All rights reserved.
                            </p>
                        </td>
                    </tr>
                    
                </table>
                
                <!-- Unsubscribe -->
                <p style="margin: 20px 0 0 0; font-size: 12px; color: #64748b; text-align: center;">
                    Don't want these emails? <a href="{unsubscribe_url}" style="color: #94a3b8; text-decoration: underline;">Unsubscribe</a>
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
        """.strip()
        
        params = {
            "from": "R&D Alpha <abhishek@finsoeasy.com>",
            "to": [to_email],
            "subject": "Welcome to R&D Alpha — Factor-Based Investment Research",
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


@router.post("/unsubscribe", response_model=SubscribeResponse)
async def unsubscribe(request: UnsubscribeRequest, db: AsyncSession = Depends(get_db)):
    """
    Unsubscribe from the newsletter.
    Requires a valid token to prevent unauthorized unsubscribes.
    """
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
    """
    Verify an unsubscribe link (for the frontend to check before showing UI).
    """
    try:
        padded = e + "=" * (4 - len(e) % 4)
        email = base64.urlsafe_b64decode(padded).decode().lower()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    if not verify_unsubscribe_token(email, t):
        raise HTTPException(status_code=400, detail="Invalid link")
    
    return {"valid": True, "email": email}
