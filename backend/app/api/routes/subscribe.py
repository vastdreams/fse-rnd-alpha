"""
Subscribe API Routes

Handles newsletter subscriptions and sends thank you emails.
Persists subscribers to JSON file for durability.

Publication: https://research.finsoeasy.com
"""

import os
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
SMTP_USER = "abhishek@finsoeasy.com"  # Lowercase for Hostinger compatibility
SMTP_PASSWORD = os.getenv("FINSOEASY_EMAIL_PASSWORD", "")

# Persistent storage path (mounted via Docker volume)
DATA_DIR = Path("/app/data")
SUBSCRIBERS_FILE = DATA_DIR / "subscribers.json"

def _ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load_subscribers() -> dict[str, dict]:
    """Load subscribers from JSON file."""
    try:
        if SUBSCRIBERS_FILE.exists():
            with open(SUBSCRIBERS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load subscribers: {e}")
    return {}

def _save_subscribers(subscribers: dict[str, dict]):
    """Save subscribers to JSON file."""
    try:
        _ensure_data_dir()
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump(subscribers, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save subscribers: {e}")

# Load subscribers on startup
subscribers: dict[str, dict] = _load_subscribers()


class SubscribeRequest(BaseModel):
    email: EmailStr
    source: Optional[str] = "website"


class SubscribeResponse(BaseModel):
    success: bool
    message: str


def send_thank_you_email(to_email: str) -> bool:
    """
    Send a thank you email to new subscriber.
    
    Args:
        to_email: Subscriber's email address
        
    Returns:
        True if email sent successfully, False otherwise
    """
    if not SMTP_PASSWORD:
        logger.warning("SMTP password not configured, skipping email")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Welcome to R&D Alpha Research"
        msg["From"] = f"R&D Alpha Research <{SMTP_USER}>"
        msg["To"] = to_email
        
        # Plain text version
        text_content = """
Thank you for subscribing to R&D Alpha Research!

You're now part of a community of researchers and investors exploring the relationship between R&D investment intensity and long-term stock returns.

What you'll receive:
- Research updates when we publish new findings
- Market insights on R&D factor performance
- Early access to new features and data

Visit our research platform: https://research.finsoeasy.com

Best regards,
Abhishek Sehgal
R&D Alpha Research
https://finsoeasy.com

---
You can unsubscribe at any time by replying to this email.
        """.strip()
        
        # HTML version
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #059669 0%, #0d9488 100%); padding: 32px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Welcome to R&D Alpha Research</h1>
    </div>
    
    <div style="background: #f8fafc; padding: 32px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
        <p style="font-size: 16px; margin-top: 0;">Thank you for subscribing!</p>
        
        <p>You're now part of a community of researchers and investors exploring the relationship between <strong>R&D investment intensity</strong> and <strong>long-term stock returns</strong>.</p>
        
        <h3 style="color: #059669; margin-top: 24px;">What you'll receive:</h3>
        <ul style="padding-left: 20px;">
            <li>Research updates when we publish new findings</li>
            <li>Market insights on R&D factor performance</li>
            <li>Early access to new features and data</li>
        </ul>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="https://research.finsoeasy.com" style="display: inline-block; background: #059669; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                Visit Research Platform
            </a>
        </div>
        
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        
        <p style="color: #64748b; font-size: 14px; margin-bottom: 0;">
            Best regards,<br>
            <strong>Abhishek Sehgal</strong><br>
            R&D Alpha Research<br>
            <a href="https://finsoeasy.com" style="color: #059669;">finsoeasy.com</a>
        </p>
    </div>
    
    <p style="color: #94a3b8; font-size: 12px; text-align: center; margin-top: 16px;">
        You can unsubscribe at any time by replying to this email.
    </p>
</body>
</html>
        """.strip()
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        # Send via SSL
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        
        logger.info(f"Thank you email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def add_subscriber_to_list(email: str, source: str = "donation") -> bool:
    """
    Add an email to the subscriber list (called from donations webhook).
    
    Args:
        email: Email address to add
        source: Where subscription came from
        
    Returns:
        True if newly added, False if already existed
    """
    global subscribers
    email = email.lower()
    
    if email in subscribers:
        logger.info(f"Subscriber {email} already exists, skipping")
        return False
    
    subscribers[email] = {
        "email": email,
        "source": source,
        "subscribed_at": datetime.utcnow().isoformat(),
    }
    _save_subscribers(subscribers)  # Persist to file
    
    logger.info(f"Auto-subscribed donor: {email} (source: {source})")
    return True


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(request: SubscribeRequest):
    """
    Subscribe to R&D Alpha research updates.
    
    Stores the email and sends a thank you email.
    """
    global subscribers
    email = request.email.lower()
    
    # Check if already subscribed
    if email in subscribers:
        return SubscribeResponse(
            success=True,
            message="You're already subscribed! Check your inbox for our latest updates."
        )
    
    # Store subscriber
    subscribers[email] = {
        "email": email,
        "source": request.source,
        "subscribed_at": datetime.utcnow().isoformat(),
    }
    _save_subscribers(subscribers)  # Persist to file
    
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


@router.get("/subscribers/count")
async def get_subscriber_count():
    """Get total subscriber count (admin only in production)."""
    return {"count": len(subscribers)}


def get_all_subscribers() -> list[dict]:
    """Get all subscribers (used by admin routes)."""
    return list(subscribers.values())

