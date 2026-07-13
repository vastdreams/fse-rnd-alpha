"""
PATH: backend/app/contracts/__init__.py
PURPOSE: Shared research-platform contracts (W1 / Sprint 0).

These Pydantic models are the single source of truth for the investor
platform redesign. Frontend domain types mirror them at
frontend/src/domain/research/contracts.ts — keep both in sync.
"""

from app.contracts.research import (  # noqa: F401
    AuditTrailEntry,
    DeepSeekAuditRun,
    DeepSeekOutputKind,
    EvidenceClaim,
    FinalReview,
    GateEvaluation,
    LiteratureBind,
    MetricValue,
    MetricVector,
    RankedRow,
    RankRecipe,
    RecipeId,
    ResearchCompleteness,
    SavedBook,
    SourceKind,
    SourceSnapshot,
)
