"""
PATH: backend/app/api/routes/subscribe/models.py
PURPOSE: Pydantic request/response models for subscribe endpoints
"""

from typing import Optional
from pydantic import BaseModel, EmailStr


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
