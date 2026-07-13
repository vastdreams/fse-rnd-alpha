"""Coverage reports disclose gaps without mutating sealed research evidence."""

import json
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from research_coverage_report import (  # noqa: E402
    build_report,
    validate_report,
    verify_report,
    write_immutable_report,
)


def _vector(*, stance: float | None, band: tuple[float, float, float] | None) -> dict:
    def metric_value(item: float | None) -> dict:
        return {"value": item}

    if band is None:
        return {"ai_text_stance": metric_value(stance)}
    lo, med, hi = band
    return {
        "ai_text_stance": metric_value(stance),
        "fair_px_lo": metric_value(lo),
        "fair_px_med": metric_value(med),
        "fair_px_hi": metric_value(hi),
    }


def test_coverage_report_preserves_unknowns_and_lists_missing_evidence(tmp_path: Path) -> None:
    (tmp_path / "financials_cache").mkdir()
    (tmp_path / "filings_cache").mkdir()
    (tmp_path / "financials_cache" / "AAA.json").write_text("{}")
    (tmp_path / "filings_cache" / "AAA.txt").write_text("10-K fixture")

    report = build_report(
        build={
            "universe_version": "univ_fixture",
            "source_sha": "a" * 40,
            "input_sha256": "b" * 64,
            "sealed_at": "2026-07-13T00:00:00Z",
        },
        rows=[
            {
                "ticker": "AAA",
                "vector": _vector(stance=0.3, band=(80, 100, 120)),
                "completeness_grade": "A",
                "kill_active": False,
                "has_filing_evidence": True,
                "has_filing_map": True,
            },
            {
                "ticker": "BBB",
                "vector": _vector(stance=None, band=(120, 100, 80)),
                "completeness_grade": "Incomplete",
                "kill_active": None,
                "has_filing_evidence": False,
                "has_filing_map": False,
            },
            {
                "ticker": "CCC",
                "vector": _vector(stance=None, band=(90, 100, 110)),
                "completeness_grade": "B",
                "kill_active": True,
                "has_filing_evidence": True,
                "has_filing_map": False,
            },
        ],
        data_dir=tmp_path,
    )

    coverage = report["coverage"]
    assert coverage["financials_cache"]["missing_tickers"] == ["BBB", "CCC"]
    assert coverage["filing_text_cache"]["missing_tickers"] == ["BBB", "CCC"]
    assert coverage["filing_map"]["missing_tickers"] == ["BBB", "CCC"]
    assert coverage["measured_text_stance"]["missing_tickers"] == ["BBB", "CCC"]
    assert coverage["valid_fair_value_band"]["missing_tickers"] == ["BBB"]
    assert coverage["kill_state"]["explicit_inactive"] == 1
    assert coverage["kill_state"]["explicit_active"] == 1
    assert coverage["kill_state"]["unknown_tickers"] == ["BBB"]
    assert report["policy"]["unknowns_are_fail_closed"] is True
    assert len(report["report_sha256"]) == 64
    validate_report(report)

    invalid = json.loads(json.dumps(report))
    invalid["coverage"] = {}
    with pytest.raises(RuntimeError, match="financials_cache"):
        validate_report(invalid)

    build = {
        "universe_version": "univ_fixture",
        "source_sha": "a" * 40,
        "input_sha256": "b" * 64,
        "sealed_at": "2026-07-13T00:00:00Z",
    }
    rows = [
        {
            "ticker": "AAA",
            "vector": _vector(stance=0.3, band=(80, 100, 120)),
            "completeness_grade": "A",
            "kill_active": False,
            "has_filing_evidence": True,
            "has_filing_map": True,
        },
        {
            "ticker": "BBB",
            "vector": _vector(stance=None, band=(120, 100, 80)),
            "completeness_grade": "Incomplete",
            "kill_active": None,
            "has_filing_evidence": False,
            "has_filing_map": False,
        },
        {
            "ticker": "CCC",
            "vector": _vector(stance=None, band=(90, 100, 110)),
            "completeness_grade": "B",
            "kill_active": True,
            "has_filing_evidence": True,
            "has_filing_map": False,
        },
    ]
    verify_report(report, build=build, rows=rows, data_dir=tmp_path)
    (tmp_path / "financials_cache" / "BBB.json").write_text("{}")
    with pytest.raises(RuntimeError, match="does not match sealed research rows"):
        verify_report(report, build=build, rows=rows, data_dir=tmp_path)


def test_coverage_report_is_write_once_per_universe_version(tmp_path: Path) -> None:
    report = build_report(
        build={
            "universe_version": "univ_fixture",
            "source_sha": "a" * 40,
            "input_sha256": "b" * 64,
            "sealed_at": "2026-07-13T00:00:00Z",
        },
        rows=[
            {
                "ticker": "AAA",
                "vector": _vector(stance=None, band=None),
                "completeness_grade": "Incomplete",
                "kill_active": None,
                "has_filing_evidence": False,
                "has_filing_map": False,
            }
        ],
        data_dir=tmp_path,
    )
    output = tmp_path / "coverage_reports" / "univ_fixture.json"

    write_immutable_report(output, report)
    original = json.loads(output.read_text())
    write_immutable_report(output, report)
    assert json.loads(output.read_text()) == original

    changed = dict(report)
    changed["coverage"] = {"changed": True}
    changed["report_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="Backfill evidence"):
        write_immutable_report(output, changed)
