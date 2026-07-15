"""
PATH: backend/app/services/consensus/base.py
PURPOSE: Provider-neutral normalized consensus shapes. The report contract
binds to these, never to a vendor payload.

Rules:
- Missing = None = Unknown. Never imputed.
- Every normalized snapshot keeps the raw payload sha256 so the stored PIT
  row can be re-verified against what the vendor returned.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol

from pydantic import BaseModel, Field, model_validator


class ConsensusUnavailable(Exception):
    """Provider returned nothing usable for this ticker."""


class ConsensusEstimate(BaseModel):
    """One fiscal-period consensus row (annual)."""

    period_end: date
    revenue_avg: Optional[float] = None
    revenue_low: Optional[float] = None
    revenue_high: Optional[float] = None
    eps_avg: Optional[float] = None
    eps_low: Optional[float] = None
    eps_high: Optional[float] = None
    ebitda_avg: Optional[float] = None
    n_analysts_revenue: Optional[int] = None
    n_analysts_eps: Optional[int] = None


class PriceTargetSummary(BaseModel):
    """Sell-side target aggregate — clearly external, never our fair band."""

    target_mean: Optional[float] = None
    target_median: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    n_analysts: Optional[int] = None


class NormalizedConsensus(BaseModel):
    """The only consensus shape the report builder may consume."""

    ticker: str
    provider: str
    consensus_id: str = Field(description="Stored consensus_snapshots primary key")
    as_of_date: date
    available_date: date
    payload_sha256: str
    estimates: list[ConsensusEstimate] = Field(default_factory=list)
    price_targets: Optional[PriceTargetSummary] = None

    @model_validator(mode="after")
    def _pit(self) -> "NormalizedConsensus":
        if self.available_date < self.as_of_date:
            raise ValueError("available_date before as_of_date")
        return self


class ConsensusProvider(Protocol):
    """Vendor adapter interface."""

    name: str

    async def fetch_raw(self, ticker: str) -> dict:
        """Return the raw vendor payload: {'estimates': [...], 'price_targets': {...}}."""
        ...

    def normalize(self, ticker: str, raw: dict) -> tuple[list[ConsensusEstimate], Optional[PriceTargetSummary]]:
        ...
