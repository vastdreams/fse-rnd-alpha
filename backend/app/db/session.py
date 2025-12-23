"""
PATH: backend/app/db/session.py
PURPOSE:
  - Async SQLAlchemy session management
  - Database connection pooling

ROLE IN ARCHITECTURE:
  - Database layer
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Create async engine (use async_database_url to ensure asyncpg driver)
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DATABASE_ECHO,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def create_tables():
    """Create all database tables."""
    # IMPORTANT:
    # SQLAlchemy only creates tables for models that have been imported and registered on Base.metadata.
    # We import app.db.models here to ensure all ORM models are loaded before create_all.
    from app.db import models as _models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Backwards-compatible alias used by older scripts (and some reproducibility helpers).
# Prefer importing async_session_maker directly for new code.
async_session_factory = async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
