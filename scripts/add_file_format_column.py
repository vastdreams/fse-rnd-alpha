"""Add file_format column to annual_reports table if it doesn't exist."""
# Setup path - must be first
import _setup_path  # noqa: F401

from src.db.connection import get_engine
from sqlalchemy import text
from src.logging.logger import get_logger

logger = get_logger(__name__)


def add_file_format_column():
    """Add file_format column to annual_reports table."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='annual_reports' AND column_name='file_format'
        """))
        exists = result.fetchone() is not None
        
        if not exists:
            logger.info("Adding file_format column to annual_reports table...")
            conn.execute(text("ALTER TABLE annual_reports ADD COLUMN file_format VARCHAR"))
            conn.commit()
            logger.info("✓ Column file_format added successfully")
        else:
            logger.info("✓ Column file_format already exists")


if __name__ == "__main__":
    add_file_format_column()

