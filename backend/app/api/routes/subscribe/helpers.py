"""
PATH: backend/app/api/routes/subscribe/helpers.py
PURPOSE: Shared helper functions (add_subscriber_to_db, get_all_subscribers)
WHY: Called by donations webhook and admin routes respectively
"""

import logging
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


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
