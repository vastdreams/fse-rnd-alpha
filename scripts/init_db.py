"""Initialize database - create all tables."""
# Setup path - must be first
import _setup_path  # noqa: F401

from src.db.connection import init_engine, get_engine
from src.db.base import Base
from src.models.orm import *  # Import all models
from config.settings import get_settings
from src.logging.logger import get_logger

logger = get_logger(__name__)


def init_database():
    """Create all database tables."""
    settings = get_settings()
    logger.info(f"Initializing database: {settings.DATABASE_URL}")
    
    init_engine()
    engine = get_engine()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database tables created successfully")


if __name__ == "__main__":
    init_database()
