# =============================================================================
# File: src/db/connection.py
# =============================================================================
# Purpose:
#   Central module to configure and access the SQLAlchemy engine and session
#   factory used across the project.
# =============================================================================

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from config.settings import get_settings

settings = get_settings()

engine = None
SessionLocal = None


def init_engine(database_url: str | None = None) -> None:
    """Initialize the SQLAlchemy engine and session factory."""
    global engine, SessionLocal
    url = database_url or settings.DATABASE_URL
    engine = create_engine(url, pool_pre_ping=True, echo=settings.DEBUG)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_engine():
    """Get the SQLAlchemy engine, initializing if needed."""
    global engine
    if engine is None:
        init_engine()
    return engine


def get_session() -> Session:
    """Get a new database session."""
    if SessionLocal is None:
        init_engine()
    return SessionLocal()


@contextmanager
def db_session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic rollback on error.
    
    Enhanced with better error handling and transaction safety.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        from src.logging.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Database transaction error, rolled back: {e}", exc_info=True)
        raise
    finally:
        session.close()


def check_database_health() -> dict:
    """Check database connectivity and basic health."""
    from datetime import datetime
    
    try:
        with db_session_scope() as session:
            # Check basic connectivity
            result = session.execute(text("SELECT 1"))
            result.fetchone()
            
            # Check database version
            version_result = session.execute(text("SELECT version()"))
            db_version = version_result.fetchone()[0] if version_result else "unknown"
            
            # Check connection pool status
            pool = get_engine().pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
            
        return {
            "status": "healthy",
            "database": "connected",
            "version": db_version.split(",")[0] if db_version else "unknown",
            "pool": pool_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
