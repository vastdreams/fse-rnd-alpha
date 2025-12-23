"""Create initial Alembic migration from current database schema."""
# Setup path - must be first
import _setup_path  # noqa: F401

import subprocess
import sys
from pathlib import Path
from src.logging.logger import get_logger

logger = get_logger(__name__)


def create_initial_migration():
    """Create initial Alembic migration."""
    logger.info("Creating initial Alembic migration...")
    
    try:
        # Run alembic revision --autogenerate
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "Initial migration from existing schema"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Initial migration created successfully")
            logger.info(result.stdout)
        else:
            logger.error(f"Failed to create migration: {result.stderr}")
            sys.exit(1)
            
    except FileNotFoundError:
        logger.error("Alembic not found. Install with: pip install alembic")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error creating migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_initial_migration()

