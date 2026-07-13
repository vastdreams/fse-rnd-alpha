"""
PATH: backend/app/api/routes/research/publication.py
PURPOSE: Publication snapshot get/build endpoints (frozen submission-grade data).
"""
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
from datetime import datetime
import numpy as np

from app.db.session import get_session
from app.api.routes.auth import require_operator
from app.db.models import (
    ResearchCohort, RollingWindowResult, AnovaResult, FactorPremium,
    FMPIncomeStatement, SP500Company, PublicationSnapshot
)
from app.services.cohort_classifier import CohortClassifier
from app.services.rolling_window import RollingWindowAnalyzer
from app.services.statistics import StatisticalAnalyzer
from app.services.publication_snapshot import (
    get_active_snapshot,
    build_snapshot_payload,
    create_publication_snapshot,
)
from app.services.sanity_checks import (
    MIN_REVENUE_THRESHOLD, MAX_RD_INTENSITY_ABSOLUTE
)
from app.api.routes.research.schemas import (
    CohortCompanyResponse, CohortSummaryResponse, QuintileResponse,
    WindowResultResponse, AnovaResultResponse, FactorPremiumResponse,
    ComputeJobResponse, PublicationSnapshotMetaResponse,
    PublicationSnapshotResponse, BuildPublicationSnapshotRequest,
    DataQualityResponse,
)

router = APIRouter()


@router.get("/publication-snapshot", response_model=PublicationSnapshotResponse)
async def get_publication_snapshot(
    snapshot_id: Optional[str] = Query(None, description="If provided, fetch this specific snapshot id; otherwise return the active snapshot."),
    session: AsyncSession = Depends(get_session),
):
    snap: Optional[PublicationSnapshot]
    if snapshot_id:
        snap = await session.get(PublicationSnapshot, snapshot_id)
    else:
        snap = await get_active_snapshot(session)

    if not snap:
        raise HTTPException(
            status_code=404,
            detail="No publication snapshot found. Build one via POST /api/research/publication-snapshot/build",
        )

    return PublicationSnapshotResponse(
        meta=PublicationSnapshotMetaResponse(
            id=snap.id,
            label=snap.label,
            is_active=bool(snap.is_active),
            return_convention=snap.return_convention,
            data_tier=snap.data_tier,
            built_at=snap.built_at,
            git_commit=snap.git_commit,
            git_branch=snap.git_branch,
            notes=snap.notes,
        ),
        payload=snap.payload,
    )


@router.post("/publication-snapshot/build", response_model=PublicationSnapshotResponse)
async def build_publication_snapshot(
    req: BuildPublicationSnapshotRequest,
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(require_operator),
):
    payload = await build_snapshot_payload(
        session,
        return_convention=req.return_convention,
        data_tier=req.data_tier,
    )

    snap = await create_publication_snapshot(
        session,
        label=req.label,
        payload=payload,
        return_convention=req.return_convention,
        data_tier=req.data_tier,
        notes=req.notes,
        git_commit=req.git_commit,
        git_branch=req.git_branch,
        set_active=req.set_active,
    )

    return PublicationSnapshotResponse(
        meta=PublicationSnapshotMetaResponse(
            id=snap.id,
            label=snap.label,
            is_active=bool(snap.is_active),
            return_convention=snap.return_convention,
            data_tier=snap.data_tier,
            built_at=snap.built_at,
            git_commit=snap.git_commit,
            git_branch=snap.git_branch,
            notes=snap.notes,
        ),
        payload=snap.payload,
    )

