"""
PATH: backend/app/api/routes/donations.py
PURPOSE: Handle Stripe donation payments, send thank you emails, auto-subscribe donors

ROLE IN ARCHITECTURE: Payment processing layer
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
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

from app.core.config import settings
from app.api.routes.subscribe import add_subscriber_to_list

router = APIRouter()
logger = logging.getLogger(__name__)

# Email configuration (same as subscribe.py)
SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
SMTP_USER = "abhishek@finsoeasy.com"  # Lowercase
SMTP_PASSWORD = os.getenv("FINSOEASY_EMAIL_PASSWORD", "")

# Persistent storage path (mounted via Docker volume)
DATA_DIR = Path("/app/data")
DONATIONS_FILE = DATA_DIR / "donations.json"

def _ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load_donations() -> list[dict]:
    """Load donations from JSON file."""
    try:
        if DONATIONS_FILE.exists():
            with open(DONATIONS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load donations: {e}")
    return []

def _save_donations(donations: list[dict]):
    """Save donations to JSON file."""
    try:
        _ensure_data_dir()
        with open(DONATIONS_FILE, "w") as f:
            json.dump(donations, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save donations: {e}")

# Load donations on startup
donations_list: list[dict] = _load_donations()

def record_donation(email: str, amount: float, is_recurring: bool, session_id: str):
    """Record a donation to persistent storage."""
    global donations_list
    donations_list.append({
        "email": email,
        "amount": amount,
        "is_recurring": is_recurring,
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
    })
    _save_donations(donations_list)
    logger.info(f"Recorded donation: {email}, ${amount}, recurring={is_recurring}")

def get_all_donations() -> list[dict]:
    """Get all donations (used by admin routes)."""
    return donations_list

# Lazy import stripe to avoid errors if not configured
_stripe = None

def get_stripe():
    global _stripe
    if _stripe is None:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        _stripe = stripe
    return _stripe


def send_donation_thank_you_email(to_email: str, amount: float, is_recurring: bool = False) -> bool:
    """
    Send a beautiful thank you email to donor.
    
    Args:
        to_email: Donor's email address
        amount: Donation amount in dollars
        is_recurring: Whether this is a recurring donation
        
    Returns:
        True if email sent successfully, False otherwise
    """
    if not SMTP_PASSWORD:
        logger.warning("SMTP password not configured, skipping donation thank you email")
        return False
    
    donation_type = "monthly" if is_recurring else "one-time"
    amount_str = f"${amount:.2f}"
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Thank You for Your {amount_str} Donation to R&D Alpha Research"
        msg["From"] = f"Abhishek Sehgal <{SMTP_USER}>"
        msg["To"] = to_email
        
        # Plain text version
        text_content = f"""
Thank you for your generous {amount_str} {donation_type} donation!

Your support means the world to us and directly helps keep R&D Alpha Research free and accessible to everyone.

What your donation supports:
- Premium financial data feeds for accurate research
- Server infrastructure to keep the platform running
- Expansion into new factor strategies and markets
- Open-source tools for the research community

Your contribution helps us continue exploring the relationship between R&D investment intensity and long-term stock returns, making this research available to investors, academics, and curious minds everywhere.

Visit our research: https://research.finsoeasy.com

With gratitude,
Abhishek Sehgal
Founder, R&D Alpha Research
https://finsoeasy.com

---
Questions? Reply to this email anytime.
        """.strip()
        
        # HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 20px; background: #f1f5f9;">
    <div style="background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <!-- Header with gradient -->
        <div style="background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%); padding: 40px 32px; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 16px;">💖</div>
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">Thank You!</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 18px;">
                Your {amount_str} {donation_type} donation has been received
            </p>
        </div>
        
        <!-- Main content -->
        <div style="padding: 32px;">
            <p style="font-size: 16px; margin-top: 0; color: #334155;">
                Your generosity directly supports free, open research for everyone.
            </p>
            
            <div style="background: #fdf2f8; border-left: 4px solid #ec4899; padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 24px 0;">
                <h3 style="color: #be185d; margin: 0 0 12px 0; font-size: 16px;">Your donation supports:</h3>
                <ul style="margin: 0; padding-left: 20px; color: #64748b;">
                    <li style="margin-bottom: 8px;">Premium financial data feeds for accurate research</li>
                    <li style="margin-bottom: 8px;">Server infrastructure to keep the platform running 24/7</li>
                    <li style="margin-bottom: 8px;">Expansion into new factor strategies and markets</li>
                    <li style="margin-bottom: 0;">Open-source tools for the research community</li>
                </ul>
            </div>
            
            <p style="color: #475569;">
                Your contribution helps us continue exploring the relationship between 
                <strong>R&D investment intensity</strong> and <strong>long-term stock returns</strong>, 
                making this research available to investors, academics, and curious minds everywhere.
            </p>
            
            <!-- CTA Button -->
            <div style="text-align: center; margin: 32px 0;">
                <a href="https://research.finsoeasy.com" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%); color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">
                    View Your Impact
                </a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
            
            <!-- Signature -->
            <table style="width: 100%;">
                <tr>
                    <td style="vertical-align: top;">
                        <p style="color: #64748b; font-size: 14px; margin: 0;">
                            With gratitude,<br><br>
                            <strong style="color: #1e293b; font-size: 16px;">Abhishek Sehgal</strong><br>
                            <span style="color: #94a3b8;">Founder, R&D Alpha Research</span><br>
                            <a href="https://finsoeasy.com" style="color: #ec4899; text-decoration: none;">finsoeasy.com</a>
                        </p>
                    </td>
                </tr>
            </table>
        </div>
    </div>
    
    <!-- Footer -->
    <p style="color: #94a3b8; font-size: 12px; text-align: center; margin-top: 24px;">
        Questions? Simply reply to this email.<br>
        © 2025 FSE Research & Investments Pty Ltd
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
        
        logger.info(f"Donation thank you email sent to {to_email} for {amount_str}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send donation email to {to_email}: {e}")
        return False


class CreateCheckoutRequest(BaseModel):
    amount: int  # Amount in dollars
    is_recurring: bool = False
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    email: Optional[str] = None  # Optional email for receipt


class CreateCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


@router.post("/donations/create-checkout", response_model=CreateCheckoutResponse)
async def create_checkout_session(request: CreateCheckoutRequest):
    """Create a Stripe Checkout session for donations."""
    
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured. Please contact support."
        )
    
    stripe = get_stripe()
    
    try:
        # Convert dollars to cents
        amount_cents = request.amount * 100
        
        # Build line items with better branding
        product_images = ["https://research.finsoeasy.com/logo.png"]
        
        if request.is_recurring:
            line_items = [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "R&D Alpha Monthly Supporter",
                        "description": "Monthly contribution to keep R&D research free for everyone. Cancel anytime.",
                        "images": product_images,
                    },
                    "unit_amount": amount_cents,
                    "recurring": {
                        "interval": "month"
                    }
                },
                "quantity": 1,
            }]
            mode = "subscription"
        else:
            line_items = [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Support R&D Alpha Research",
                        "description": "Your donation keeps our research free and accessible to everyone.",
                        "images": product_images,
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }]
            mode = "payment"
        
        # Create checkout session with better UX
        session_params = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": mode,
            "success_url": request.success_url or settings.STRIPE_SUCCESS_URL,
            "cancel_url": request.cancel_url or settings.STRIPE_CANCEL_URL,
            "metadata": {
                "donation_amount": str(request.amount),
                "is_recurring": str(request.is_recurring),
            },
            # Better checkout appearance
            "billing_address_collection": "auto",
            "allow_promotion_codes": False,
        }
        
        # Add customer email if provided
        if request.email:
            session_params["customer_email"] = request.email
        
        # One-time payments: use donate submit type for better UX
        if mode == "payment":
            session_params["submit_type"] = "donate"
            session_params["customer_creation"] = "always"
        
        session = stripe.checkout.Session.create(**session_params)
        
        logger.info(f"Created Stripe checkout session: {session.id} for ${request.amount}")
        
        return CreateCheckoutResponse(
            checkout_url=session.url,
            session_id=session.id
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/donations/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="stripe-signature")):
    """Handle Stripe webhooks for payment events."""
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Webhook secret not configured")
        raise HTTPException(status_code=503, detail="Webhook not configured")
    
    stripe = get_stripe()
    payload = await request.body()
    
    logger.info(f"Received webhook with signature: {stripe_signature[:20] if stripe_signature else 'None'}...")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Webhook event verified: {event.type}")
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event.type == "checkout.session.completed":
        session = event.data.object
        amount_cents = session.get("amount_total", 0)
        amount_dollars = amount_cents / 100 if amount_cents else 0
        customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        metadata = session.get("metadata", {})
        is_recurring = metadata.get("is_recurring", "False").lower() == "true"
        
        logger.info(f"Payment completed: {session.id}, amount: ${amount_dollars}, email: {customer_email}")
        
        # Record donation to persistent storage
        record_donation(
            email=customer_email or "unknown",
            amount=amount_dollars,
            is_recurring=is_recurring,
            session_id=session.id
        )
        
        if customer_email:
            # Send thank you email
            send_donation_thank_you_email(customer_email, amount_dollars, is_recurring)
            
            # Auto-subscribe donor to newsletter
            donation_type = "recurring_donation" if is_recurring else "one_time_donation"
            add_subscriber_to_list(customer_email, source=donation_type)
            logger.info(f"Auto-subscribed donor {customer_email} to newsletter")
        else:
            logger.warning(f"No email found for session {session.id}, skipping thank you email and subscription")
        
    elif event.type == "invoice.paid":
        invoice = event.data.object
        amount_cents = invoice.get("amount_paid", 0)
        amount_dollars = amount_cents / 100 if amount_cents else 0
        customer_email = invoice.get("customer_email")
        
        logger.info(f"Subscription payment: {invoice.id}, amount: ${amount_dollars}")
        
        # Record recurring donation
        record_donation(
            email=customer_email or "unknown",
            amount=amount_dollars,
            is_recurring=True,
            session_id=invoice.id
        )
        
        # Send thank you email for recurring payment
        if customer_email:
            send_donation_thank_you_email(customer_email, amount_dollars, is_recurring=True)
        
    elif event.type == "customer.subscription.deleted":
        subscription = event.data.object
        logger.info(f"Subscription cancelled: {subscription.id}")
    
    return {"status": "success", "event": event.type}


@router.get("/donations/config")
async def get_stripe_config():
    """Return public Stripe configuration."""
    if not settings.STRIPE_PUBLISHABLE_KEY:
        return {"configured": False}
    
    return {
        "configured": True,
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY
    }
