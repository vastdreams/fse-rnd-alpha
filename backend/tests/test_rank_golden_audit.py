"""
PATH: backend/tests/test_rank_golden_audit.py
PURPOSE: S2/S3 — sealed golden rows must pass first-principles audit in CI.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.services.rank_row_invariants import audit_rank_row, fair_band_zone

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rank-golden.json"
# Prefer frontend fixture path in monorepo CI when present.
FE_FIXTURE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "fixtures" / "rank-golden.json"
SIDECAR = FE_FIXTURE.with_suffix(FE_FIXTURE.suffix + ".sha256") if FE_FIXTURE.exists() else FIXTURE.with_suffix(FIXTURE.suffix + ".sha256")


def _fixture_path() -> Path:
    return FE_FIXTURE if FE_FIXTURE.exists() else FIXTURE


def _load():
    return json.loads(_fixture_path().read_text())


def test_golden_meta_and_sidecar_sha():
    path = _fixture_path()
    data = json.loads(path.read_text())
    assert data["meta"]["universe_version"] == "univ_2026-07-13_f0c9acf6f41f"
    assert data["meta"]["recipe_id"] == "R3"
    sidecar = SIDECAR.read_text().strip().split()[0]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == sidecar


def test_every_golden_row_passes_audit():
    data = _load()
    for row in data["rows"]:
        violations = audit_rank_row(row)
        assert violations == [], (row["ticker"], violations)


def test_edge_tags_match_zones():
    data = _load()
    for row in data["rows"]:
        tags = set(row.get("edge_tags") or [])
        zone = fair_band_zone(row.get("price_live"), row.get("fair_px_lo"), row.get("fair_px_hi"))
        if "below_band" in tags:
            assert zone == "below"
        if "inside_band" in tags:
            assert zone == "inside"
        if "above_band" in tags:
            assert zone == "above"
