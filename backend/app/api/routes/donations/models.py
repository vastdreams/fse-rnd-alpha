"""
PATH: backend/app/api/routes/donations/models.py
PURPOSE: Pydantic models and Stripe client accessor for donations
"""

from typing import Optional
from pydantic import BaseModel, EmailStr

from app.core.config import settings

# Lazy import stripe
_stripe = None


def get_stripe():
    global _stripe
    if _stripe is None:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        _stripe = stripe
    return _stripe


class CreateCheckoutRequest(BaseModel):
    amount: int
    is_recurring: bool = False
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    email: Optional[EmailStr] = None


class CreateCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
