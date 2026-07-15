"""
PATH: backend/tests/test_company_report_builder.py
PURPOSE: Assembly tests — deterministic snapshot ids, provenance separation,
unknown propagation, and reserved-citation protection.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.contracts.company_reports import ProvenanceClass, ReportCitation
from app.services.company_report_builder import (
    AuthoredBrief,
    AuthoredSection,
    build_report_snapshot,
)
from app.services.consensus.base import (
    ConsensusEstimate,
    NormalizedConsensus,
    PriceTargetSummary,
)

FIXED_AT = datetime(2026, 7, 15, 8, 0, 0)


def _metric(value=None, asof="2026-06-30"):
    if value is None:
        return {"value": None, "as_of_date": None, "available_date": None, "claim_ids": []}
    return {"value": value, "as_of_date": asof, "available_date": asof, "claim_ids": ["clm_1"]}


def _research() -> dict:
    return {
        "ticker": "WIX",
        "universe_version": "univ_test",
        "identity": {"name": "Wix.com Ltd", "exchange": "NASDAQ", "sector": "Technology", "industry": "Software"},
        "profile": {
            "name": "Wix.com Ltd", "price_live": 150.0, "price_as_of": "2026-07-14",
            "price_source": "sharadar", "market_cap": 8.4e9,
        },
        "valuation_range": {"fair_px_lo": 160.0, "fair_px_med": 210.0, "fair_px_hi": 280.0, "price_live": 150.0},
        "close_call_waterfall": {"aggregate": {"stance": "BUY", "score": 78.0, "implied_ann_return": 0.12, "horizon_years": 3}},
        "thesis": {
            "engine_version": "close_call_v3",
            "repayment_engine": {"rd_elig": True, "rd_composite": 1.4},
            "survivability": {"survivable": True},
            "skew": {"payoff_skew": 4.3, "payoff_skew_label": None},
            "size": {"f_max_fraction": 0.0},
        },
        "vector": {
            "ticker": "WIX",
            "computed_at": "2026-07-15T02:00:00",
            "rev_cagr": _metric(0.13),
            "gm": _metric(0.68),
            "fcfm_sbc": _metric(0.11),
            "rd_int": _metric(0.24),
            "rule40": _metric(24.0),
            "roic": _metric(0.09),
            "retention": _metric(None),
            "dilution_ann": _metric(0.02),
            "mos_live": _metric(0.4),
            "mos_snapshot": _metric(0.35),
        },
    }


def _authored() -> AuthoredBrief:
    cite = ReportCitation(
        cite_id="A1",
        provenance=ProvenanceClass.ANALYST,
        title="Wix 20-F FY2025",
        locator="sec:0001576914-26-000010",
        as_of_date=date(2025, 12, 31),
        available_date=date(2026, 3, 20),
    )
    section_ids = [
        "variant_perception", "business_model", "industry_map", "moat",
        "financial_trends", "thesis", "catalysts", "consensus_vs_internal",
        "estimate_revisions", "management_governance", "gates_factor_context",
        "risks_falsification", "sizing", "methodology",
    ]
    return AuthoredBrief(
        sections={sid: AuthoredSection(body="Cited analyst text.", cite_ids=["A1"]) for sid in section_ids},
        citations=[cite],
    )


def _consensus() -> NormalizedConsensus:
    return NormalizedConsensus(
        ticker="WIX",
        provider="fmp",
        consensus_id="cons_fixture",
        as_of_date=date(2026, 7, 14),
        available_date=date(2026, 7, 14),
        payload_sha256="0" * 64,
        estimates=[ConsensusEstimate(period_end=date(2026, 12, 31), revenue_avg=2.0e9, eps_avg=6.1)],
        price_targets=PriceTargetSummary(target_mean=205.0, n_analysts=22),
    )


def test_build_is_deterministic():
    a = build_report_snapshot(research=_research(), authored=_authored(), consensus=_consensus(), created_at=FIXED_AT)
    b = build_report_snapshot(research=_research(), authored=_authored(), consensus=_consensus(), created_at=FIXED_AT)
    assert a.snapshot_id == b.snapshot_id and a.snapshot_id.startswith("rpt_")


def test_header_and_metrics_populated():
    snap = build_report_snapshot(
        research=_research(), authored=_authored(), consensus=_consensus(),
        proxy_weight_pct=15.0, created_at=FIXED_AT,
    )
    assert snap.stance == "BUY" and snap.fair_px_med == 210.0 and snap.price == 150.0
    fin = next(s for s in snap.page1 if s.section_id == "financial_trends")
    retention = next(m for m in fin.metrics if m.label == "Net revenue retention")
    assert retention.value is None and retention.cite_ids == []  # unknown stays unknown
    sizing = next(s for s in snap.page2 if s.section_id == "sizing")
    assert any(m.label == "Construction proxy weight" and m.value == 15.0 for m in sizing.metrics)
    f_max = next(m for m in sizing.metrics if m.label.startswith("Validated sizing"))
    assert f_max.value == 0.0  # honest zero, not hidden


def test_consensus_scenario_is_labeled_external():
    snap = build_report_snapshot(research=_research(), authored=_authored(), consensus=_consensus(), created_at=FIXED_AT)
    section = next(s for s in snap.page2 if s.section_id == "consensus_vs_internal")
    consensus_rows = [x for x in section.scenarios if x.name == "consensus"]
    assert consensus_rows and consensus_rows[0].provenance == ProvenanceClass.LICENSED_CONSENSUS
    assert consensus_rows[0].fair_px == 205.0


def test_no_consensus_means_no_consensus_row():
    snap = build_report_snapshot(research=_research(), authored=_authored(), consensus=None, created_at=FIXED_AT)
    section = next(s for s in snap.page2 if s.section_id == "consensus_vs_internal")
    assert not [x for x in section.scenarios if x.name == "consensus"]
    assert not any(c.cite_id == "S4" for c in snap.citations)


def test_reserved_cite_id_rejected():
    authored = _authored()
    authored.citations.append(
        ReportCitation(cite_id="S1", provenance=ProvenanceClass.ANALYST, title="x", locator="y")
    )
    with pytest.raises(ValueError, match="reserved"):
        build_report_snapshot(research=_research(), authored=authored, consensus=None, created_at=FIXED_AT)


def test_uncited_narrative_fails_contract():
    authored = _authored()
    authored.sections["thesis"] = AuthoredSection(body="Uncited claim.", cite_ids=[])
    with pytest.raises(ValueError, match="no citations"):
        build_report_snapshot(research=_research(), authored=authored, consensus=None, created_at=FIXED_AT)
