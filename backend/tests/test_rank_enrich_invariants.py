"""
PATH: backend/tests/test_rank_enrich_invariants.py
PURPOSE: S3 — enriched rank rows fail closed on first-principles breaks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.rank_row_invariants import (
    assert_rank_rows_invariants,
    audit_rank_rows,
    compute_live_vs_target_pct,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rank-golden.json"


def test_golden_enrich_shape_passes_assert():
    rows = json.loads(FIXTURE.read_text())["rows"]
    assert_rank_rows_invariants(rows)


def test_injected_bad_vs_median_fails_closed():
    rows = json.loads(FIXTURE.read_text())["rows"]
    bad = dict(rows[0])
    bad["vs_median_pct"] = 0.0  # wrong on purpose for KSPI
    with pytest.raises(AssertionError) as exc:
        assert_rank_rows_invariants([bad])
    assert "VS_MEDIAN_MISMATCH" in str(exc.value)


def test_compute_live_vs_matches_golden_kspi():
    rows = json.loads(FIXTURE.read_text())["rows"]
    kspi = next(r for r in rows if r["ticker"] == "KSPI")
    expected = compute_live_vs_target_pct(kspi["price_live"], kspi["fair_px_med"])
    assert expected == pytest.approx(kspi["vs_median_pct"])
    assert audit_rank_rows([kspi]) == []
