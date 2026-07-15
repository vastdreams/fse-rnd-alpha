"""
PATH: backend/tests/test_consensus_provider.py
PURPOSE: Normalization and failure tests for the licensed consensus adapter.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.services.consensus.base import ConsensusUnavailable, NormalizedConsensus
from app.services.consensus.fmp_provider import FmpConsensusProvider


RAW = {
    "estimates": [
        {
            "date": "2027-12-31",
            "estimatedRevenueAvg": 2.1e9,
            "estimatedRevenueLow": 1.9e9,
            "estimatedRevenueHigh": 2.3e9,
            "estimatedEpsAvg": 6.4,
            "estimatedEpsLow": 5.9,
            "estimatedEpsHigh": 7.0,
            "estimatedEbitdaAvg": 5.5e8,
            "numberAnalystEstimatedRevenue": 18,
            "numberAnalystsEstimatedEps": 20,
        },
        {
            "date": "2026-12-31",
            "estimatedRevenueAvg": 1.9e9,
            "estimatedEpsAvg": 5.6,
        },
        {"date": None, "estimatedRevenueAvg": 1.0},  # unusable row dropped
    ],
    "price_targets": [
        {
            "targetConsensus": 210.5,
            "targetMedian": 208.0,
            "targetHigh": 260.0,
            "targetLow": 150.0,
            "numberOfAnalysts": 24,
        }
    ],
}


def test_normalize_estimates_sorted_and_typed():
    estimates, targets = FmpConsensusProvider().normalize("WIX", RAW)
    assert [e.period_end for e in estimates] == [date(2026, 12, 31), date(2027, 12, 31)]
    assert estimates[1].revenue_avg == 2.1e9
    assert estimates[1].n_analysts_eps == 20
    # Missing fields stay None, never imputed.
    assert estimates[0].revenue_low is None
    assert targets is not None and targets.target_mean == 210.5 and targets.n_analysts == 24


def test_normalize_handles_missing_targets():
    estimates, targets = FmpConsensusProvider().normalize("WIX", {"estimates": RAW["estimates"], "price_targets": []})
    assert estimates and targets is None


def test_normalized_consensus_pit_guard():
    with pytest.raises(ValueError, match="available_date"):
        NormalizedConsensus(
            ticker="WIX",
            provider="fmp",
            consensus_id="cons_x",
            as_of_date=date(2026, 7, 15),
            available_date=date(2026, 7, 14),
            payload_sha256="0" * 64,
        )


@pytest.mark.asyncio
async def test_fetch_raw_raises_when_provider_empty(monkeypatch):
    provider = FmpConsensusProvider()

    class _StubClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def _get(self, endpoint, params=None):
            return None

    monkeypatch.setattr(
        "app.services.consensus.fmp_provider.FMPClientBase", lambda: _StubClient()
    )
    with pytest.raises(ConsensusUnavailable):
        await provider.fetch_raw("WIX")
