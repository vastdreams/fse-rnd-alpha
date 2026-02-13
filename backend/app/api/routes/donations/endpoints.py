"""
PATH: backend/app/api/routes/donations/endpoints.py
PURPOSE: Stripe checkout, webhook, and config endpoints
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.api.deps import get_db
from app.api.routes.subscribe import add_subscriber_to_db
from app.api.routes.donations.models import (
    CreateCheckoutRequest, CreateCheckoutResponse, get_stripe
)
from app.api.routes.donations.email import send_donation_thank_you_email

router = APIRouter()
logger = logging.getLogger(__name__)


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
