"""
PATH: backend/app/api/routes/company_report_artifacts.py
PURPOSE: Rendered-artifact ledger for company briefs — register checksum-
verified PDFs/JSON from the pinned renderer and serve verified downloads.

Ship rules:
- Artifacts attach only to reviewed/published snapshots.
- Report PDFs must be exactly 2 pages (renderer asserts; server re-asserts).
- Every download is re-verified against the ledger sha256 before serving.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.routes.auth import get_current_user, require_operator
from app.services.company_report_builder import deterministic_artifact_id
from app.services.report_artifact_store import (
    ArtifactStoreError,
    load_artifact,
    store_artifact,
)

router = APIRouter()

_now = lambda: datetime.now(timezone.utc).replace(tzinfo=None)  # noqa: E731


class ArtifactRegister(BaseModel):
    kind: str = Field(pattern="^(pdf|json)$")
    content_base64: str
    renderer_version: str = Field(min_length=1, max_length=120)
    n_pages: Optional[int] = None


async def _snapshot_status(db: AsyncSession, snapshot_id: str) -> str:
    status = await db.scalar(
        text("SELECT status FROM company_report_snapshots WHERE snapshot_id=:sid"),
        {"sid": snapshot_id},
    )
    if status is None:
        raise HTTPException(404, f"Report snapshot {snapshot_id} not found")
    return str(status)


@router.post("/{snapshot_id}/artifact")
async def register_artifact(
    snapshot_id: str,
    payload: ArtifactRegister,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> dict:
    """Store a rendered artifact for a reviewed/published snapshot."""
    status = await _snapshot_status(db, snapshot_id)
    if status not in ("reviewed", "published"):
        raise HTTPException(409, "Artifacts attach only to reviewed or published snapshots")
    if payload.kind == "pdf" and payload.n_pages != 2:
        raise HTTPException(422, f"Report PDFs must be exactly 2 pages, got {payload.n_pages}")
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except Exception:
        raise HTTPException(422, "content_base64 is not valid base64")
    if not content:
        raise HTTPException(422, "Artifact is empty")
    storage_key, sha = store_artifact(snapshot_id, payload.kind, content)
    artifact_id = deterministic_artifact_id(snapshot_id, payload.kind, sha)
    existing = (
        await db.execute(
            text("SELECT artifact_id FROM company_report_artifacts WHERE artifact_id=:aid"),
            {"aid": artifact_id},
        )
    ).first()
    if not existing:
        await db.execute(
            text(
                """INSERT INTO company_report_artifacts
                       (artifact_id, snapshot_id, kind, storage_key, sha256,
                        renderer_version, n_pages, created_at)
                   VALUES (:aid, :sid, :kind, :key, :sha, :rv, :np, :now)"""
            ),
            {
                "aid": artifact_id,
                "sid": snapshot_id,
                "kind": payload.kind,
                "key": storage_key,
                "sha": sha,
                "rv": payload.renderer_version,
                "np": payload.n_pages,
                "now": _now(),
            },
        )
        await db.commit()
    return {"artifact_id": artifact_id, "sha256": sha, "storage_key": storage_key}


@router.get("/{snapshot_id}/export.pdf")
async def export_pdf(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> Response:
    """Serve the latest checksum-verified PDF artifact."""
    row = (
        await db.execute(
            text(
                """SELECT storage_key, sha256 FROM company_report_artifacts
                    WHERE snapshot_id=:sid AND kind='pdf'
                    ORDER BY created_at DESC LIMIT 1"""
            ),
            {"sid": snapshot_id},
        )
    ).first()
    if row is None:
        raise HTTPException(404, "No rendered PDF for this snapshot yet")
    try:
        content = load_artifact(row[0], row[1])
    except ArtifactStoreError as exc:
        raise HTTPException(500, str(exc))
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{snapshot_id}.pdf"'},
    )
