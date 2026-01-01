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

# Resend API configuration - set dynamically in function to ensure env is loaded

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
    """Send a thank you email to donor via Resend. Includes R&D Alpha research highlights."""
    # Set API key dynamically to ensure env is loaded
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("Resend API key not configured, skipping donation email")
        return False
    
    resend.api_key = api_key
    donation_type = "monthly supporter" if is_recurring else "one-time"
    amount_str = f"${amount:.2f}"
    
    # Generate unsubscribe URL (import from subscribe module)
    from app.api.routes.subscribe import get_unsubscribe_url
    unsubscribe_url = get_unsubscribe_url(to_email)
    
    try:
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
                        <td style="padding: 48px 40px 32px 40px; text-align: center; background: linear-gradient(135deg, rgba(236,72,153,0.2) 0%, rgba(244,63,94,0.2) 100%); border-bottom: 1px solid #334155;">
                            <div style="font-size: 48px; margin-bottom: 16px;">💖</div>
                            <div style="font-size: 28px; font-weight: 800; color: #f8fafc; letter-spacing: -0.5px; margin-bottom: 4px;">
                                R&D Alpha
                            </div>
                            <div style="font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 16px;">
                                FSE Research & Investments
                            </div>
                            <div style="font-size: 16px; color: #f472b6;">
                                Your {amount_str} {donation_type} donation received
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h1 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 700; color: #f8fafc;">
                                Thank You for Your Support
                            </h1>
                            
                            <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.7; color: #cbd5e1;">
                                Your generosity directly supports our mission to provide <strong style="color: #f8fafc;">free, open investment research</strong> to everyone.
                            </p>
                            
                            <!-- Research Highlight -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(99,102,241,0.15) 100%); border-radius: 12px; padding: 20px; border-left: 4px solid #3b82f6;">
                                        <div style="font-size: 13px; font-weight: 600; color: #60a5fa; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">
                                            📊 Research Highlight
                                        </div>
                                        <p style="margin: 0; color: #e2e8f0; font-size: 15px; line-height: 1.6;">
                                            Our R&D Alpha research documents a <strong style="color: #60a5fa;">+7.55% annual high-minus-low premium</strong> (71% win rate across 24 annual periods) and an implementable long-only variant retains ~99% of the premium after estimated trading costs.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- What Your Donation Supports -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(236,72,153,0.1) 0%, rgba(244,63,94,0.1) 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #ec4899;">
                                        <div style="font-size: 14px; font-weight: 600; color: #f472b6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;">
                                            Your Support Enables
                                        </div>
                                        <table role="presentation" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #f472b6; margin-right: 10px;">→</span> Premium SEC & financial data feeds
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #f472b6; margin-right: 10px;">→</span> 24/7 research infrastructure
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #f472b6; margin-right: 10px;">→</span> New factor research & strategies
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #f472b6; margin-right: 10px;">→</span> Open-source tools for all investors
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
                                        <a href="https://research.finsoeasy.com" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%); color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 36px; border-radius: 8px;">
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
                                With gratitude,
                            </p>
                            <p style="margin: 0 0 8px 0; font-size: 15px; font-weight: 600; color: #f8fafc;">
                                Abhishek Sehgal
                            </p>
                            <p style="margin: 0 0 16px 0; font-size: 13px; color: #64748b;">
                                FSE Research and Investments
                            </p>
                            <div style="margin-bottom: 16px;">
                                <a href="https://research.finsoeasy.com" style="color: #f472b6; font-size: 13px; text-decoration: none; margin: 0 8px;">Research</a>
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
            "from": "FSE Research <abhishek@finsoeasy.com>",
            "to": [to_email],
            "subject": f"Thank You for Your Support – {amount_str} Donation Received",
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
        await db.commit()
        logger.info(f"Donation stored in database: {stripe_session_id}")
        
        if customer_email:
            # Send thank you email
            email_sent = send_donation_thank_you_email(customer_email, amount_dollars, is_recurring)
            logger.info(f"Thank you email sent: {email_sent}")
            # Auto-subscribe donor
            source = "recurring_donation" if is_recurring else "one_time_donation"
            await add_subscriber_to_db(db, customer_email, source)
            logger.info(f"Donor auto-subscribed: {customer_email}")
    
    elif event.type == "invoice.paid":
        invoice = event.data.object
        amount_cents = invoice.get("amount_paid", 0)
        amount_dollars = amount_cents / 100 if amount_cents else 0
        customer_email = invoice.get("customer_email")
        invoice_id = invoice.get("id")
        
        logger.info(f"Subscription invoice paid: {invoice_id}, ${amount_dollars}, {customer_email}")
        
        # Store recurring payment
        await db.execute(
            text("""
                INSERT INTO donations (email, amount, is_recurring, stripe_session_id, created_at)
                VALUES (:email, :amount, true, :stripe_session_id, :created_at)
            """),
            {
                "email": customer_email or "unknown",
                "amount": amount_dollars,
                "stripe_session_id": invoice_id,
                "created_at": datetime.utcnow()
            }
        )
        await db.commit()
        logger.info(f"Recurring payment stored: {invoice_id}")
        
        if customer_email:
            email_sent = send_donation_thank_you_email(customer_email, amount_dollars, is_recurring=True)
            logger.info(f"Monthly thank you email sent: {email_sent}")
    
    elif event.type == "customer.subscription.deleted":
        subscription = event.data.object
        customer_email = subscription.get("customer_email")
        logger.info(f"Subscription cancelled: {subscription.get('id')}, {customer_email}")
    
    elif event.type == "invoice.payment_failed":
        invoice = event.data.object
        customer_email = invoice.get("customer_email")
        logger.warning(f"Payment failed for subscription: {invoice.get('id')}, {customer_email}")
    
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
