"""
PATH: backend/app/services/publication_snapshot/helpers.py
PURPOSE: Shared helpers for the publication_snapshot package — JSON safety, config loading, active snapshot lookup.
WHY: Extracted from the monolithic publication_snapshot.py to keep each module under ~300 lines.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PublicationSnapshot

# Path to the auto-detected window configuration
WINDOW_CONFIG_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "backtest_window_config.json"


def load_backtest_window_config() -> Optional[Dict[str, Any]]:
    """Load the auto-detected backtest window configuration."""
    if not WINDOW_CONFIG_PATH.exists():
        return None
    try:
        with open(WINDOW_CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _json_safe(obj: Any) -> Any:
    """
    Convert objects that commonly appear in analytics output into JSON-safe types.
    """
    if obj is None:
        return None

    # Datetimes
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Numpy scalars
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()

    # Plain python primitives
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # Containers
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, set):
        return [_json_safe(v) for v in sorted(obj)]

    # Fallback: try to coerce numpy arrays, decimals, etc.
    try:
        if hasattr(obj, "tolist"):
            return _json_safe(obj.tolist())
    except Exception:
        pass

    return str(obj)


async def get_active_snapshot(session: AsyncSession) -> Optional[PublicationSnapshot]:
    result = await session.execute(
        select(PublicationSnapshot)
        .where(PublicationSnapshot.is_active.is_(True))
        .order_by(PublicationSnapshot.built_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
