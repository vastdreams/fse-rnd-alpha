#!/usr/bin/env python
"""
Migration script: Add R&D tracking columns to financials_core.

New columns:
- rd_is_estimated: Boolean flag for imputed values
- rd_source: Source of R&D data ("10k_line_item", "notes", "estimated")
"""
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.connection import get_engine

COLUMNS_TO_ADD = [
    ("rd_is_estimated", "BOOLEAN DEFAULT FALSE"),
    ("rd_source", "VARCHAR(50)"),
]


def migrate():
    """Add new R&D tracking columns."""
    engine = get_engine()
    
    with engine.connect() as conn:
        for column_name, column_def in COLUMNS_TO_ADD:
            try:
                conn.execute(f"ALTER TABLE financials_core ADD COLUMN {column_name} {column_def}")
                conn.commit()
                print(f"✓ Added column: {column_name}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"✓ Column already exists: {column_name}")
                else:
                    print(f"✗ Error adding {column_name}: {e}")
    
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()

