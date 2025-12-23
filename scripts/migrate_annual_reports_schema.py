"""Add all missing columns to annual_reports table to match the model."""
# Setup path - must be first
import _setup_path  # noqa: F401

from src.db.connection import get_engine
from sqlalchemy import text
from src.logging.logger import get_logger

logger = get_logger(__name__)


def migrate_annual_reports_schema():
    """Add all missing columns to annual_reports table."""
    engine = get_engine()
    
    # All columns that should exist in annual_reports table
    columns_to_add = [
        ("file_format", "VARCHAR"),
        ("document_count", "INTEGER"),
        ("has_xbrl", "BOOLEAN"),
        ("xbrl_url", "VARCHAR"),
        ("sections_found", "JSONB"),
        ("total_pages", "INTEGER"),
        ("word_count", "INTEGER"),
    ]
    
    with engine.connect() as conn:
        for column_name, column_type in columns_to_add:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='annual_reports' AND column_name=:col_name
            """), {"col_name": column_name})
            exists = result.fetchone() is not None
            
            if not exists:
                logger.info(f"Adding column {column_name} ({column_type}) to annual_reports table...")
                try:
                    conn.execute(text(f"ALTER TABLE annual_reports ADD COLUMN {column_name} {column_type}"))
                    conn.commit()
                    logger.info(f"✓ Column {column_name} added successfully")
                except Exception as e:
                    logger.error(f"✗ Error adding column {column_name}: {e}")
                    conn.rollback()
            else:
                logger.debug(f"✓ Column {column_name} already exists")
        
        logger.info("Migration complete!")


if __name__ == "__main__":
    migrate_annual_reports_schema()

