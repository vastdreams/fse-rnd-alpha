"""
PATH: backend/app/api/deps.py
PURPOSE:
  - FastAPI dependencies for injection
  - Database session, auth, etc.

ROLE IN ARCHITECTURE:
  - Dependency injection layer
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

