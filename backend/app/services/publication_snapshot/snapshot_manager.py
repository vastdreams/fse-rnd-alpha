"""
PATH: backend/app/services/publication_snapshot/snapshot_manager.py
PURPOSE: Create and persist publication snapshots in the database.
WHY: Separated from payload_builder to isolate the write concern from the read-only build concern.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PublicationSnapshot
from app.services.publication_snapshot.helpers import _json_safe


async def create_publication_snapshot(
    session: AsyncSession,
    *,
    label: str,
    payload: Dict[str, Any],
    return_convention: str,
    data_tier: str,
    notes: Optional[str] = None,
    git_commit: Optional[str] = None,
    git_branch: Optional[str] = None,
    set_active: bool = True,
) -> PublicationSnapshot:
    snapshot_id = str(uuid.uuid4())

    if set_active:
        await session.execute(
            update(PublicationSnapshot)
            .where(PublicationSnapshot.is_active.is_(True))
            .values(is_active=False)
        )

    snap = PublicationSnapshot(
        id=snapshot_id,
        label=label,
        is_active=set_active,
        return_convention=return_convention,
        data_tier=data_tier,
        built_at=datetime.utcnow(),
        git_commit=git_commit,
        git_branch=git_branch,
        notes=notes,
        payload=_json_safe(payload),
    )
    session.add(snap)
    await session.commit()
    return snap
