"""
PATH: backend/app/api/routes/donations/helpers.py
PURPOSE: Shared helper to retrieve all donations (used by admin routes)
"""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


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
