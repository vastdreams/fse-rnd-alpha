"""
Donations API Routes

Handles Stripe donations with PostgreSQL persistence.
Sends thank you emails via Resend and auto-subscribes donors.

Publication: https://research.finsoeasy.com
"""

import os
import logging
import resend
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.api.deps import get_db
from app.api.routes.subscribe import add_subscriber_to_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Resend API configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
resend.api_key = RESEND_API_KEY

# Lazy import stripe
_stripe = None

def get_stripe():
    global _stripe
    if _stripe is None:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        _stripe = stripe
    return _stripe


def send_donation_thank_you_email(to_email: str, amount: float, is_recurring: bool = False) -> bool:
    """Send a beautiful thank you email to donor via Resend."""
    if not RESEND_API_KEY:
        logger.warning("Resend API key not configured, skipping donation email")
        return False
    
    donation_type = "monthly" if is_recurring else "one-time"
    amount_str = f"${amount:.2f}"
    
    try:
        html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 20px; background: #f1f5f9;">
    <div style="background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%); padding: 40px 32px; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 16px;">💖</div>
            <h1 style="color: white; margin: 0; font-size: 28px;">Thank You!</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 18px;">
                Your {amount_str} {donation_type} donation has been received
            </p>
        </div>
        <div style="padding: 32px;">
            <p style="font-size: 16px; margin-top: 0;">Your generosity directly supports free, open research for everyone.</p>
            <div style="background: #fdf2f8; border-left: 4px solid #ec4899; padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 24px 0;">
                <h3 style="color: #be185d; margin: 0 0 12px 0;">Your donation supports:</h3>
                <ul style="margin: 0; padding-left: 20px; color: #64748b;">
                    <li style="margin-bottom: 6px;">Premium financial data feeds</li>
                    <li style="margin-bottom: 6px;">Server infrastructure 24/7</li>
                    <li style="margin-bottom: 6px;">New factor strategies and markets</li>
                    <li>Open-source research tools</li>
                </ul>
            </div>
            <div style="text-align: center; margin: 32px 0;">
                <a href="https://research.finsoeasy.com" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%); color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">Explore the Research</a>
            </div>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
            <p style="color: #64748b; font-size: 14px; margin-bottom: 0;">With gratitude,<br><strong>Abhishek Sehgal</strong><br>Founder, R&D Alpha Research<br><a href="https://finsoeasy.com" style="color: #ec4899;">finsoeasy.com</a></p>
        </div>
    </div>
    <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 16px;">
        © 2025 R&D Alpha Research. All rights reserved.
    </p>
</body>
</html>
        """.strip()
        
        params = {
            "from": "Abhishek Sehgal <abhishek@finsoeasy.com>",
            "to": [to_email],
            "subject": f"Thank You for Your {amount_str} Donation 💖",
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Donation email sent to {to_email}, id: {response.get('id', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send donation email to {to_email}: {e}")
        return False


class CreateCheckoutRequest(BaseModel):
    amount: int
    is_recurring: bool = False
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    email: Optional[EmailStr] = None


class CreateCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


@router.post("/donations/create-checkout", response_model=CreateCheckoutResponse)
async def create_checkout_session(request: CreateCheckoutRequest):
    """Create a Stripe Checkout session for donations."""
    
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")
    
    stripe = get_stripe()
    
    try:
        amount_cents = request.amount * 100
        
        if request.is_recurring:
            product_name = "R&D Alpha Monthly Supporter"
            mode = "subscription"
        else:
            product_name = "R&D Alpha Research Donation"
            mode = "payment"
        
        line_items = [{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": product_name},
                "unit_amount": amount_cents,
                "recurring": {"interval": "month"} if request.is_recurring else None,
            },
            "quantity": 1,
        }]
        
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode=mode,
            success_url=request.success_url or settings.STRIPE_SUCCESS_URL,
            cancel_url=request.cancel_url or settings.STRIPE_CANCEL_URL,
            customer_email=request.email if request.email else None,
            metadata={
                "donation_amount": str(request.amount),
                "is_recurring": str(request.is_recurring),
            }
        )
        
        logger.info(f"Created Stripe checkout: {session.id} for ${request.amount}")
        
        return CreateCheckoutResponse(checkout_url=session.url, session_id=session.id)
        
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/donations/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """Handle Stripe webhooks for payment events."""
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Webhook secret not configured")
        raise HTTPException(status_code=503, detail="Webhook not configured")
    
    stripe = get_stripe()
    payload = await request.body()
    
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
    
    if event.type == "checkout.session.completed":
        session = event.data.object
        amount_cents = session.get("amount_total", 0)
        amount_dollars = amount_cents / 100 if amount_cents else 0
        customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        metadata = session.get("metadata", {})
        is_recurring = metadata.get("is_recurring", "False").lower() == "true"
        stripe_session_id = session.get("id")
        
        logger.info(f"Payment completed: {stripe_session_id}, ${amount_dollars}, {customer_email}")
        
        # Store donation in database
        await db.execute(
            text("""
                INSERT INTO donations (email, amount, is_recurring, stripe_session_id, created_at)
                VALUES (:email, :amount, :is_recurring, :stripe_session_id, :created_at)
            """),
            {
                "email": customer_email or "unknown",
                "amount": amount_dollars,
                "is_recurring": is_recurring,
                "stripe_session_id": stripe_session_id,
                "created_at": datetime.utcnow()
            }
        )
        
        if customer_email:
            # Send thank you email
            send_donation_thank_you_email(customer_email, amount_dollars, is_recurring)
            # Auto-subscribe donor
            source = "recurring_donation" if is_recurring else "one_time_donation"
            await add_subscriber_to_db(db, customer_email, source)
    
    elif event.type == "invoice.paid":
        invoice = event.data.object
        amount_cents = invoice.get("amount_paid", 0)
        amount_dollars = amount_cents / 100 if amount_cents else 0
        customer_email = invoice.get("customer_email")
        
        logger.info(f"Subscription payment: {invoice.id}, ${amount_dollars}")
        
        # Store recurring payment
        await db.execute(
            text("""
                INSERT INTO donations (email, amount, is_recurring, stripe_session_id, created_at)
                VALUES (:email, :amount, true, :stripe_session_id, :created_at)
            """),
            {
                "email": customer_email or "unknown",
                "amount": amount_dollars,
                "stripe_session_id": invoice.get("id"),
                "created_at": datetime.utcnow()
            }
        )
        
        if customer_email:
            send_donation_thank_you_email(customer_email, amount_dollars, is_recurring=True)
    
    return {"status": "success", "event": event.type}


@router.get("/donations/config")
async def get_stripe_config():
    """Return public Stripe configuration."""
    if not settings.STRIPE_PUBLISHABLE_KEY:
        return {"configured": False}
    return {"configured": True, "publishable_key": settings.STRIPE_PUBLISHABLE_KEY}


async def get_all_donations(db: AsyncSession) -> List[dict]:
    """Get all donations (used by admin routes)."""
    result = await db.execute(
        text("""
            SELECT id, email, amount, is_recurring, stripe_session_id, created_at
            FROM donations
            ORDER BY created_at DESC
        """)
    )
    rows = result.fetchall()
    return [
        {
            "id": row[0],
            "email": row[1],
            "amount": float(row[2]),
            "is_recurring": row[3],
            "stripe_session_id": row[4],
            "created_at": row[5].isoformat() if row[5] else None
        }
        for row in rows
    ]
