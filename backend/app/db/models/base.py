"""
PATH: backend/app/db/models/base.py
PURPOSE: Common imports and SQLAlchemy Base re-export for all model modules.
WHY: Single source of truth for shared imports used across every model file.
"""

from __future__ import annotations

from datetime import datetime, date as date_type
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    Text, JSON, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.session import Base

__all__ = [
    "Base",
    "datetime",
    "date_type",
    "Optional",
    "List",
    "Column",
    "Integer",
    "String",
    "Float",
    "Boolean",
    "Date",
    "DateTime",
    "Text",
    "JSON",
    "ForeignKey",
    "Index",
    "UniqueConstraint",
    "relationship",
    "Mapped",
    "mapped_column",
]
