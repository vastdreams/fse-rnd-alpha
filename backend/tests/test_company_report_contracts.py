"""
PATH: backend/tests/test_company_report_contracts.py
PURPOSE: Contract tests for the two-page company brief — section structure,
word budgets, citation completeness, and content-hash stability.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.contracts.company_reports import (
    PAGE1_SECTIONS,
    PAGE2_SECTIONS,
    CompanyReportSnapshot,
    ProvenanceClass,
    ReportCitation,
    ReportMetric,
    ReportSection,
    canonical_report_json,
    report_content_sha256,
)


def _cite(cid: str = "1") -> ReportCitation:
    return ReportCitation(
        cite_id=cid,
        provenance=ProvenanceClass.SEALED,
        title="10-K FY2025",
        locator="sec:0001234567-25-000001",
        as_of_date=date(2025, 12, 31),
        available_date=date(2026, 2, 1),
    )


def _section(section_id: str, body: str = "Cited narrative.", cite_ids: list[str] | None = None) -> ReportSection:
    return ReportSection(
        section_id=section_id,
        title=section_id.replace("_", " ").title(),
        body=body,
        cite_ids=cite_ids if cite_ids is not None else ["1"],
    )


def _snapshot(**overrides) -> CompanyReportSnapshot:
    base = dict(
        snapshot_id="rpt_test01",
        ticker="WIX",
        universe_version="univ_2026-07-15_test",
        engine_version="report_builder_v1",
        created_at=datetime(2026, 7, 15, 8, 0, 0),
        as_of_date=date(2026, 7, 15),
        page1=[_section(s) for s in PAGE1_SECTIONS],
        page2=[_section(s) for s in PAGE2_SECTIONS],
        citations=[_cite()],
        disclosures=["Research only — not investment advice."],
    )
    base.update(overrides)
    return CompanyReportSnapshot(**base)


def test_happy_path_snapshot_validates():
    snap = _snapshot()
    assert [s.section_id for s in snap.page1] == list(PAGE1_SECTIONS)
    assert report_content_sha256(snap) == report_content_sha256(snap)


def test_hash_ignores_workflow_but_not_content():
    a = _snapshot()
    b = _snapshot(reviewed_by="agent", reviewed_at=datetime(2026, 7, 15, 9, 0, 0))
    assert report_content_sha256(a) == report_content_sha256(b)
    c = _snapshot(ticker="TTD")
    assert report_content_sha256(a) != report_content_sha256(c)


def test_canonical_json_is_deterministic():
    assert canonical_report_json(_snapshot()) == canonical_report_json(_snapshot())


def test_missing_section_rejected():
    with pytest.raises(ValueError, match="page1 sections"):
        _snapshot(page1=[_section(s) for s in PAGE1_SECTIONS[:-1]])


def test_wrong_section_order_rejected():
    shuffled = list(PAGE2_SECTIONS)
    shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
    with pytest.raises(ValueError, match="page2 sections"):
        _snapshot(page2=[_section(s) for s in shuffled])


def test_word_budget_overflow_rejected():
    long_body = " ".join(["word"] * 500)
    with pytest.raises(ValueError, match="budget"):
        _section("moat", body=long_body)


def test_narrative_without_citation_rejected():
    with pytest.raises(ValueError, match="no citations"):
        _section("thesis", cite_ids=[])


def test_dangling_cite_id_rejected():
    with pytest.raises(ValueError, match="unknown cite_ids"):
        _snapshot(page1=[
            _section(s, cite_ids=["99"]) if s == "thesis" else _section(s)
            for s in PAGE1_SECTIONS
        ])


def test_metric_with_value_requires_citation():
    with pytest.raises(ValueError, match="no citation"):
        ReportMetric(label="Revenue", value=1.0, provenance=ProvenanceClass.SEALED)


def test_unknown_metric_needs_no_citation():
    metric = ReportMetric(label="NRR", provenance=ProvenanceClass.SEALED)
    assert metric.value is None


def test_disclosures_required():
    with pytest.raises(ValueError, match="disclosures"):
        _snapshot(disclosures=[])


def test_pit_order_enforced_on_citation():
    with pytest.raises(ValueError, match="available_date"):
        ReportCitation(
            cite_id="1",
            provenance=ProvenanceClass.SEALED,
            title="x",
            locator="y",
            as_of_date=date(2026, 2, 1),
            available_date=date(2026, 1, 1),
        )
