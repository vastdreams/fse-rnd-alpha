"""Price/fair-value display guards for investor-facing research surfaces."""

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import app.api.routes.universe_rank as universe_rank
import app.services.company_meta_service as company_meta_service
from app.api.routes.universe_company import (
    _anchor_known_at_vector,
    _bound_memo_citations,
    _vector_claim_ids,
)
from app.api.routes.universe_rank import _enrich_rows, _valid_fair_value_band
from app.contracts.research import MetricValue, MetricVector, ResearchCompleteness
import app.services.price_history_service as price_history_service
from app.services.price_history_service import _annotate_cache


def test_fair_value_band_requires_ordered_positive_lenses():
    assert _valid_fair_value_band({"fair_px_lo": 80, "fair_px_med": 100, "fair_px_hi": 130})
    assert not _valid_fair_value_band({"fair_px_lo": 130, "fair_px_med": 100, "fair_px_hi": 80})
    assert not _valid_fair_value_band({"fair_px_lo": 0, "fair_px_med": 100, "fair_px_hi": 130})
    assert not _valid_fair_value_band({"fair_px_lo": 80, "fair_px_med": None, "fair_px_hi": 130})


def test_cached_daily_prices_are_labeled_as_of_not_live():
    annotated = _annotate_cache(
        {"ticker": "ACME", "end": "2026-07-12", "bars": []},
        stale=True,
    )
    assert annotated["price_as_of"] == "2026-07-12"
    assert annotated["price_source"] == "Sharadar SEP adjusted close"
    assert annotated["cache_stale"] is True


def test_frozen_stance_cache_cannot_reuse_runtime_price_memory(tmp_path, monkeypatch):
    """A current overlay read must not leak into a frozen-universe stance."""

    immutable = tmp_path / "release-price-cache"
    runtime = tmp_path / "runtime"
    immutable.mkdir()
    runtime_cache = runtime / "price_history_cache"
    runtime_cache.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat()
    filename = "ACME_365.json"
    (immutable / filename).write_text(
        json.dumps(
            {
                "ticker": "ACME",
                "fetched_at": now,
                "end": "2026-07-10",
                "bars": [{"date": "2026-07-10", "close": 10}],
            }
        )
    )
    (runtime_cache / filename).write_text(
        json.dumps(
            {
                "ticker": "ACME",
                "fetched_at": now,
                "end": "2026-07-13",
                "bars": [{"date": "2026-07-13", "close": 20}],
            }
        )
    )
    monkeypatch.setattr(price_history_service, "DEFAULT_CACHE_DIR", immutable)
    monkeypatch.setattr(price_history_service, "CACHE_DIR", immutable)
    monkeypatch.setenv("APP_RUNTIME_CACHE_DIR", str(runtime))
    price_history_service._memory.clear()

    current = price_history_service.get_cached_price_history("ACME", years=1)
    frozen = price_history_service.get_cached_price_history(
        "ACME", years=1, immutable_only=True
    )

    assert current is not None
    assert current["bars"][-1]["close"] == 20
    assert frozen is not None
    assert frozen["bars"][-1]["close"] == 10
    price_history_service._memory.clear()


def test_audit_export_uses_only_claims_bound_to_frozen_vector():
    vector = MetricVector(
        ticker="TEST",
        universe_version="univ_test",
        computed_at=datetime(2026, 7, 13),
        retention=MetricValue(claim_ids=["retention-claim"]),
        rd_prod=MetricValue(claim_ids=["productivity-claim", "retention-claim"]),
        completeness=ResearchCompleteness(
            grade="A",
            filing_fetched=True,
            claims_n=2,
            dcf_reproducible=True,
            overlay_fill_rate=1,
            competitor_map_filled=True,
        ),
    )

    assert _vector_claim_ids(vector) == ["productivity-claim", "retention-claim"]
    assert _bound_memo_citations(
        ["retention-claim", "retention-claim"], vector
    ) == ["retention-claim"]
    with pytest.raises(HTTPException, match="bound to the selected universe vector"):
        _bound_memo_citations(["later-unbound-claim"], vector)


def test_later_catalyst_claims_cannot_rewrite_frozen_universe_stance():
    cutoff = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)

    assert _anchor_known_at_vector(
        vector_computed_at=cutoff,
        claim_extracted_at=cutoff - timedelta(minutes=1),
        snapshot_available_date=date(2026, 7, 12),
    )
    assert not _anchor_known_at_vector(
        vector_computed_at=cutoff,
        claim_extracted_at=cutoff + timedelta(minutes=1),
        snapshot_available_date=date(2026, 7, 12),
    )
    assert not _anchor_known_at_vector(
        vector_computed_at=cutoff,
        claim_extracted_at=cutoff - timedelta(minutes=1),
        snapshot_available_date=date(2026, 7, 14),
    )


@pytest.mark.asyncio
async def test_rank_enrichment_reads_profile_cache_as_of_metadata(tmp_path, monkeypatch):
    async def identity_stub(_: list[str]) -> dict[str, dict]:
        return {"ACME": {"name": "Acme"}}

    monkeypatch.setattr(company_meta_service, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(universe_rank, "identity_map", identity_stub)
    monkeypatch.setattr(universe_rank, "description_map", lambda *_: {"ACME": "Acme software"})
    monkeypatch.setattr(
        universe_rank,
        "panel_valuation",
        lambda: {"ACME": {"fair_px_lo": 90, "fair_px_med": 100, "fair_px_hi": 110}},
    )
    (tmp_path / "profile_ACME.json").write_text(
        json.dumps(
            {
                "fetched_at": "2026-07-12T15:30:00+00:00",
                "profile": {"price_live": 95, "price_change": 1.5, "price_stale": True},
            }
        )
    )

    rows = await _enrich_rows([{"ticker": "ACME"}], [])

    assert rows[0]["price_live"] == 95
    assert rows[0]["price_as_of"] == "2026-07-12T15:30:00+00:00"
    assert rows[0]["price_stale"] is True
