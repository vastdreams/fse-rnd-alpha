"""Tests for derive_sealed_universe completeness repair + catalyst bind contract."""
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_derive():
    import importlib.util

    path = ROOT / "scripts" / "derive_sealed_universe.py"
    spec = importlib.util.spec_from_file_location("derive_sealed_universe", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_script_binds_catalyst_anchors_like_build_universe():
    src = (ROOT / "scripts" / "derive_sealed_universe.py").read_text()
    assert "claim.field = 'catalyst_anchor'" in src
    assert "claim.extracted_at <= vector_row.computed_at" in src
    assert "snapshot.available_date <= vector_row.computed_at::date" in src
    assert "bind_catalyst_anchors" in src


def test_repair_completeness_upgrades_c_when_pit_filing_exists(tmp_path: Path):
    mod = _load_derive()
    filings = tmp_path / "filings_cache"
    filings.mkdir()
    (filings / "KSPI.meta.json").write_text(
        '{"ticker":"KSPI","accession":"0001","filing_date":"2026-03-16","error":null}'
    )
    raw = {
        "ticker": "KSPI",
        "completeness": {"grade": "C", "filing_fetched": False, "claims_n": 21},
        "mos_snapshot": {"value": 1.0},
        "gm": {"value": 0.7},
        "fcfm_sbc": {"value": 0.1},
        "roic": {"value": 0.2},
        "rule40": {"value": 50},
        "rd_prod": {"value": 0.5},
        "rd_int": {"value": 0.1},
        "retention": {"value": None},
        "concentration": {"value": None},
        "ai_text_stance": {"value": None},
    }
    out, grade, changed = mod.repair_completeness(
        raw, datetime(2026, 7, 14), tmp_path
    )
    assert changed is True
    assert grade == "B"
    assert out["completeness"]["filing_fetched"] is True
    assert out["completeness"]["grade"] == "B"


def test_repair_completeness_skips_future_filings(tmp_path: Path):
    mod = _load_derive()
    filings = tmp_path / "filings_cache"
    filings.mkdir()
    (filings / "KSPI.meta.json").write_text(
        '{"ticker":"KSPI","accession":"0001","filing_date":"2026-08-01","error":null}'
    )
    raw = {
        "ticker": "KSPI",
        "completeness": {"grade": "C", "filing_fetched": False},
        "mos_snapshot": {"value": 1.0},
        "gm": {"value": 0.7},
        "fcfm_sbc": {"value": 0.1},
        "roic": {"value": 0.2},
        "rule40": {"value": 50},
        "rd_prod": {"value": 0.5},
        "rd_int": {"value": 0.1},
    }
    out, grade, changed = mod.repair_completeness(
        raw, datetime(2026, 7, 14), tmp_path
    )
    assert changed is False
    assert grade == "C"
    assert out["completeness"]["filing_fetched"] is False


def test_repair_completeness_leaves_a_b_alone(tmp_path: Path):
    mod = _load_derive()
    raw = {"ticker": "WIX", "completeness": {"grade": "B", "filing_fetched": True}}
    out, grade, changed = mod.repair_completeness(
        raw, datetime(2026, 7, 14), tmp_path
    )
    assert changed is False
    assert grade == "B"
