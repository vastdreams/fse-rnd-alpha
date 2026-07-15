"""
PATH: backend/app/api/routes/company_reports.py
PURPOSE: Two-page company brief workflow — draft, validate, review, publish,
retrieve. Rendered-artifact endpoints live in company_report_artifacts.py.

Ship rules:
- Snapshot content is assembled once and stored write-once; workflow columns
  only advance (enforced again by DB trigger).
- Publish requires an independent final review AND a cleared BUY stance for
  the snapshot's universe version. Fail closed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.routes.auth import get_current_user, require_operator
from app.api.routes.company_report_artifacts import router as artifacts_router
from app.api.routes.universe_company import company_research, research_stances
from app.contracts.company_reports import (
    CompanyReportSnapshot,
    report_content_sha256,
)
from app.services.company_report_builder import (
    ENGINE_VERSION,
    AuthoredBrief,
    build_report_snapshot,
)
from app.services.consensus import (
    ConsensusUnavailable,
    fetch_and_store_consensus,
    latest_stored_consensus,
)
from app.services.sizing_proxy import proxy_weights

router = APIRouter()
router.include_router(artifacts_router)

_now = lambda: datetime.now(timezone.utc).replace(tzinfo=None)  # noqa: E731


class DraftRequest(BaseModel):
    authored: AuthoredBrief
    universe_version: Optional[str] = None
    refresh_consensus: bool = False


class ReviewRequest(BaseModel):
    notes: str = Field(min_length=1, max_length=4000)
    acknowledge_independent: bool = Field(
        description="Reviewer confirms they checked every citation independently of authoring"
    )


async def _snapshot_row(db: AsyncSession, snapshot_id: str) -> dict:
    row = (
        await db.execute(
            text(
                """SELECT snapshot_id, ticker, universe_version, status, content,
                          content_sha256, created_by, created_at, reviewed_by,
                          reviewed_at, published_at
                     FROM company_report_snapshots WHERE snapshot_id=:sid"""
            ),
            {"sid": snapshot_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, f"Report snapshot {snapshot_id} not found")
    return dict(row)


def _content(row: dict) -> dict:
    return row["content"] if isinstance(row["content"], dict) else json.loads(row["content"])


async def _cleared_buy_tickers(db: AsyncSession, user: dict, universe_version: str) -> set[str]:
    listed = await research_stances(
        stance="BUY", universe_version=universe_version, limit=None, db=db, user=user
    )
    return {str(r["ticker"]).upper() for r in listed.get("rows", [])}


async def _proxy_weight_for(db: AsyncSession, user: dict, uv: str, ticker: str) -> Optional[float]:
    listed = await research_stances(stance="BUY", universe_version=uv, limit=None, db=db, user=user)
    rows = listed.get("rows") or []
    if not any(str(r.get("ticker")).upper() == ticker for r in rows):
        return None
    result = proxy_weights(rows)
    for holding in result.get("holdings", []):
        if holding["ticker"] == ticker:
            return holding["weight_pct"]
    return None


@router.post("/company/{ticker}/draft")
async def draft_report(
    ticker: str,
    payload: DraftRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> dict:
    """Assemble and store a validated draft snapshot for one company."""
    t = ticker.upper()
    research = await company_research(t, payload.universe_version, db, user)
    uv = research["universe_version"]

    if payload.refresh_consensus:
        try:
            consensus = await fetch_and_store_consensus(db, t)
        except ConsensusUnavailable as exc:
            raise HTTPException(502, f"Licensed consensus refresh failed: {exc}")
    else:
        consensus = await latest_stored_consensus(db, t)

    proxy_pct = await _proxy_weight_for(db, user, uv, t)
    try:
        snapshot = build_report_snapshot(
            research=research,
            authored=payload.authored,
            consensus=consensus,
            proxy_weight_pct=proxy_pct,
        )
    except ValueError as exc:
        raise HTTPException(422, f"Report failed contract validation: {exc}")

    sha = report_content_sha256(snapshot)
    existing = (
        await db.execute(
            text("SELECT snapshot_id, status FROM company_report_snapshots WHERE snapshot_id=:sid"),
            {"sid": snapshot.snapshot_id},
        )
    ).first()
    if existing:
        return {"snapshot_id": snapshot.snapshot_id, "status": existing[1], "deduplicated": True}
    await db.execute(
        text(
            """INSERT INTO company_report_snapshots
                   (snapshot_id, ticker, universe_version, template_version,
                    engine_version, status, content, content_sha256, created_by, created_at)
               VALUES (:sid, :t, :uv, :tpl, :engine, 'draft', CAST(:content AS jsonb), :sha, :uid, :now)"""
        ),
        {
            "sid": snapshot.snapshot_id,
            "t": t,
            "uv": uv,
            "tpl": snapshot.template_version,
            "engine": ENGINE_VERSION,
            "content": snapshot.model_dump_json(),
            "sha": sha,
            "uid": str(user["id"]),
            "now": _now(),
        },
    )
    await db.commit()
    return {
        "snapshot_id": snapshot.snapshot_id,
        "status": "draft",
        "content_sha256": sha,
        "consensus_used": consensus.consensus_id if consensus else None,
        "note": "Research only — not investment advice.",
    }


@router.post("/{snapshot_id}/validate")
async def validate_report(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> dict:
    """Re-run full contract validation + hash check, then advance to validated."""
    row = await _snapshot_row(db, snapshot_id)
    try:
        snapshot = CompanyReportSnapshot.model_validate(_content(row))
    except ValueError as exc:
        raise HTTPException(422, f"Stored snapshot no longer validates: {exc}")
    if report_content_sha256(snapshot) != row["content_sha256"]:
        raise HTTPException(409, "Stored content hash mismatch — snapshot is corrupt")
    status = row["status"]
    if status == "draft":
        await db.execute(
            text("UPDATE company_report_snapshots SET status='validated' WHERE snapshot_id=:sid"),
            {"sid": snapshot_id},
        )
        await db.commit()
        status = "validated"
    return {"snapshot_id": snapshot_id, "status": status}


@router.post("/{snapshot_id}/review")
async def review_report(
    snapshot_id: str,
    payload: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> dict:
    """Record the independent final review; advances validated → reviewed."""
    if not payload.acknowledge_independent:
        raise HTTPException(422, "Reviewer must acknowledge independent citation check")
    row = await _snapshot_row(db, snapshot_id)
    if row["status"] not in ("validated", "reviewed"):
        raise HTTPException(409, f"Cannot review a snapshot in status {row['status']}")
    await db.execute(
        text(
            """UPDATE company_report_snapshots
                  SET status='reviewed', reviewed_by=:rid, reviewed_at=:now
                WHERE snapshot_id=:sid"""
        ),
        {"sid": snapshot_id, "rid": str(user["id"]), "now": _now()},
    )
    await db.commit()
    return {"snapshot_id": snapshot_id, "status": "reviewed", "reviewed_by": str(user["id"])}


@router.post("/{snapshot_id}/publish")
async def publish_report(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> dict:
    """Publish a reviewed snapshot. Only cleared BUY names may publish."""
    row = await _snapshot_row(db, snapshot_id)
    if row["status"] != "reviewed":
        raise HTTPException(409, f"Only reviewed snapshots can publish (status={row['status']})")
    buys = await _cleared_buy_tickers(db, user, row["universe_version"])
    if row["ticker"].upper() not in buys:
        raise HTTPException(
            409,
            f"{row['ticker']} is not a cleared BUY in {row['universe_version']}; publication blocked",
        )
    await db.execute(
        text(
            """UPDATE company_report_snapshots
                  SET status='published', published_at=:now
                WHERE snapshot_id=:sid"""
        ),
        {"sid": snapshot_id, "now": _now()},
    )
    await db.commit()
    return {"snapshot_id": snapshot_id, "status": "published"}


@router.get("/company/{ticker}")
async def list_reports(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    rows = (
        await db.execute(
            text(
                """SELECT snapshot_id, universe_version, template_version, status,
                          content_sha256, created_at, reviewed_by, published_at
                     FROM company_report_snapshots
                    WHERE ticker=:t ORDER BY created_at DESC LIMIT 50"""
            ),
            {"t": ticker.upper()},
        )
    ).mappings().all()
    return {"ticker": ticker.upper(), "snapshots": [dict(r) for r in rows]}


@router.get("/{snapshot_id}")
async def get_report(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    row = await _snapshot_row(db, snapshot_id)
    return {
        "snapshot_id": row["snapshot_id"],
        "status": row["status"],
        "content_sha256": row["content_sha256"],
        "reviewed_by": row["reviewed_by"],
        "published_at": row["published_at"],
        "report": _content(row),
        "note": "Research only — not investment advice.",
    }
