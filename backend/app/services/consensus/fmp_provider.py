"""
PATH: backend/app/services/consensus/fmp_provider.py
PURPOSE: FMP (licensed commercial subscription) adapter for company-level
consensus estimates and sell-side price targets.

FMP is the initially selected licensed provider because the platform already
holds a commercial FMP subscription with estimate/price-target entitlements.
The interface is provider-neutral; swapping in I/B/E/S-class data later only
adds a new adapter.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Optional

from app.services.consensus.base import (
    ConsensusEstimate,
    ConsensusUnavailable,
    PriceTargetSummary,
)
from app.services.fmp_client.base import FMPClientBase

logger = logging.getLogger(__name__)

PROVIDER_NAME = "fmp"


def _f(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _i(value: Any) -> Optional[int]:
    parsed = _f(value)
    return int(parsed) if parsed is not None else None


def _d(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


class FmpConsensusProvider:
    """Adapter for FMP analyst-estimates + price-target-consensus endpoints."""

    name = PROVIDER_NAME

    async def fetch_raw(self, ticker: str) -> dict:
        symbol = ticker.upper()
        async with FMPClientBase() as client:
            estimates = await client._get(
                f"/api/v3/analyst-estimates/{symbol}", {"period": "annual", "limit": 8}
            )
            targets = await client._get(
                "/api/v4/price-target-consensus", {"symbol": symbol}
            )
        if not estimates and not targets:
            raise ConsensusUnavailable(f"FMP returned no consensus data for {symbol}")
        return {
            "estimates": estimates if isinstance(estimates, list) else [],
            "price_targets": targets if isinstance(targets, (list, dict)) else [],
        }

    def normalize(
        self, ticker: str, raw: dict
    ) -> tuple[list[ConsensusEstimate], Optional[PriceTargetSummary]]:
        estimates: list[ConsensusEstimate] = []
        for row in raw.get("estimates") or []:
            period_end = _d(row.get("date"))
            if period_end is None:
                continue
            estimates.append(
                ConsensusEstimate(
                    period_end=period_end,
                    revenue_avg=_f(row.get("estimatedRevenueAvg")),
                    revenue_low=_f(row.get("estimatedRevenueLow")),
                    revenue_high=_f(row.get("estimatedRevenueHigh")),
                    eps_avg=_f(row.get("estimatedEpsAvg")),
                    eps_low=_f(row.get("estimatedEpsLow")),
                    eps_high=_f(row.get("estimatedEpsHigh")),
                    ebitda_avg=_f(row.get("estimatedEbitdaAvg")),
                    n_analysts_revenue=_i(row.get("numberAnalystEstimatedRevenue")),
                    n_analysts_eps=_i(row.get("numberAnalystsEstimatedEps")),
                )
            )
        estimates.sort(key=lambda e: e.period_end)

        targets_raw = raw.get("price_targets")
        if isinstance(targets_raw, list):
            targets_raw = targets_raw[0] if targets_raw else None
        price_targets: Optional[PriceTargetSummary] = None
        if isinstance(targets_raw, dict):
            price_targets = PriceTargetSummary(
                target_mean=_f(targets_raw.get("targetConsensus")),
                target_median=_f(targets_raw.get("targetMedian")),
                target_high=_f(targets_raw.get("targetHigh")),
                target_low=_f(targets_raw.get("targetLow")),
                n_analysts=_i(targets_raw.get("numberOfAnalysts")),
            )
        return estimates, price_targets
