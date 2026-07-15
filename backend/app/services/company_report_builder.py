"""
PATH: backend/app/services/company_report_builder.py
PURPOSE: Deterministic assembly of the two-page company brief snapshot.

Inputs are already-resolved artifacts: the company research payload (sealed
vector + thesis + stance + valuation), a stored PIT consensus snapshot, and
the analyst-authored narrative. This module never calls a data vendor and
never invents a number — every metric is copied from a cited artifact by
company_report_metrics.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.contracts.company_reports import (
    PAGE1_SECTIONS,
    PAGE2_SECTIONS,
    TEMPLATE_VERSION,
    CompanyReportSnapshot,
    ProvenanceClass,
    ReportCitation,
    ReportMetric,
    ReportScenario,
    ReportSection,
    report_content_sha256,
)
from app.services.company_report_metrics import (
    auto_citations,
    financial_metrics,
    fnum,
    gate_metrics,
    mv,
    sizing_metrics,
)

ENGINE_VERSION = "report_builder_v1"

SECTION_TITLES: dict[str, str] = {
    "variant_perception": "Variant perception",
    "business_model": "Business & revenue model",
    "industry_map": "Industry & competitive map",
    "moat": "Moat evidence",
    "financial_trends": "Financial & KPI trends",
    "thesis": "Investment thesis",
    "catalysts": "Dated catalysts",
    "consensus_vs_internal": "Consensus vs internal underwriting",
    "estimate_revisions": "Estimates & sell-side targets",
    "management_governance": "Management, governance & culture",
    "gates_factor_context": "Thesis gates & factor context",
    "risks_falsification": "Risks & falsification triggers",
    "sizing": "Sizing",
    "methodology": "Methodology & sources",
}


class AuthoredSection(BaseModel):
    """Analyst-authored narrative for one section, citing authored sources."""

    body: str = ""
    cite_ids: list[str] = Field(default_factory=list)


class AuthoredBrief(BaseModel):
    """The full analyst work product consumed by the assembler."""

    sections: dict[str, AuthoredSection] = Field(default_factory=dict)
    citations: list[ReportCitation] = Field(default_factory=list)
    scenarios: list[ReportScenario] = Field(default_factory=list)


def _consensus_scenarios(consensus: Any) -> list[ReportScenario]:
    if consensus is None or consensus.price_targets is None:
        return []
    pt = consensus.price_targets
    return [
        ReportScenario(
            name="consensus",
            provenance=ProvenanceClass.LICENSED_CONSENSUS,
            fair_px=pt.target_mean,
            cite_ids=["S4"],
            note=f"Sell-side mean target ({pt.n_analysts or '?'} analysts); external, not our band.",
        )
    ]


def _internal_scenarios(vr: dict, price: Optional[float]) -> list[ReportScenario]:
    """Sealed-band underwriting rows — the analyst cannot hand-type a fair value."""
    out: list[ReportScenario] = []
    for name, px, note in (
        ("bear", fnum(vr.get("fair_px_lo")), "Sealed conservative lens."),
        ("base", fnum(vr.get("fair_px_med")), "Sealed median lens."),
        ("bull", fnum(vr.get("fair_px_hi")), "Sealed high lens."),
    ):
        if px is None:
            continue
        out.append(
            ReportScenario(
                name=name,
                provenance=ProvenanceClass.MODEL,
                fair_px=px,
                implied_return=(px / price - 1) if price else None,
                cite_ids=["S1"],
                note=note,
            )
        )
    return out


def _sections(
    page_ids: tuple[str, ...],
    authored: AuthoredBrief,
    auto_metrics: dict[str, list[ReportMetric]],
    auto_scenarios: dict[str, list[ReportScenario]],
) -> list[ReportSection]:
    sections = []
    for sid in page_ids:
        a = authored.sections.get(sid) or AuthoredSection()
        sections.append(
            ReportSection(
                section_id=sid,
                title=SECTION_TITLES[sid],
                body=a.body,
                cite_ids=a.cite_ids,
                metrics=auto_metrics.get(sid, []),
                scenarios=auto_scenarios.get(sid, []),
            )
        )
    return sections


def build_report_snapshot(
    *,
    research: dict,
    authored: AuthoredBrief,
    consensus: Any = None,
    proxy_weight_pct: Optional[float] = None,
    created_at: Optional[datetime] = None,
) -> CompanyReportSnapshot:
    """Pure assembly of a validated draft snapshot. Raises on any contract breach."""
    vector = research["vector"]
    identity = research.get("identity") or {}
    profile = research.get("profile") or {}
    vr = research.get("valuation_range") or {}
    stance = (research.get("close_call_waterfall") or {}).get("aggregate") or {}
    thesis = research.get("thesis") or {}

    citations = auto_citations(research, consensus)
    known = {c.cite_id for c in citations}
    for cite in authored.citations:
        if cite.cite_id in known:
            raise ValueError(f"Authored citation reuses reserved cite_id {cite.cite_id}")
        citations.append(cite)

    price = fnum(vr.get("price_live") or profile.get("price_live"))
    auto_scenarios = {
        "consensus_vs_internal": (
            _consensus_scenarios(consensus) + _internal_scenarios(vr, price) + list(authored.scenarios)
        )
    }
    auto_metrics = {
        "financial_trends": financial_metrics(vector),
        "gates_factor_context": gate_metrics(research),
        "sizing": sizing_metrics(research, proxy_weight_pct),
    }

    now = created_at or datetime.now(timezone.utc).replace(tzinfo=None)
    snapshot = CompanyReportSnapshot(
        snapshot_id="pending",
        ticker=vector["ticker"],
        universe_version=research["universe_version"],
        engine_version=ENGINE_VERSION,
        created_at=now,
        as_of_date=now.date(),
        company_name=profile.get("name") or identity.get("name"),
        exchange=identity.get("exchange"),
        sector=identity.get("sector"),
        industry=identity.get("industry"),
        stance=stance.get("stance"),
        price=price,
        price_as_of=(
            date.fromisoformat(str(profile["price_as_of"])[:10]) if profile.get("price_as_of") else None
        ),
        fair_px_lo=fnum(vr.get("fair_px_lo")),
        fair_px_med=fnum(vr.get("fair_px_med")),
        fair_px_hi=fnum(vr.get("fair_px_hi")),
        mos_live=mv(vector, "mos_live"),
        implied_ann_return=fnum(stance.get("implied_ann_return")),
        horizon_years=stance.get("horizon_years"),
        market_cap=fnum(profile.get("market_cap")),
        page1=_sections(PAGE1_SECTIONS, authored, auto_metrics, auto_scenarios),
        page2=_sections(PAGE2_SECTIONS, authored, auto_metrics, auto_scenarios),
        citations=citations,
        disclosures=[
            "Research only — not investment advice.",
            "Sealed values come from an immutable universe build; overlays carry visible dates.",
            "Unknown means unknown: no value in this report is imputed.",
            f"Thesis engine: {thesis.get('engine_version') or 'close_call_v3'}; template {TEMPLATE_VERSION}.",
        ],
    )
    content_hash = report_content_sha256(snapshot)
    return snapshot.model_copy(update={"snapshot_id": f"rpt_{content_hash[:24]}"})


def deterministic_artifact_id(snapshot_id: str, kind: str, sha256: str) -> str:
    seed = f"{snapshot_id}|{kind}|{sha256}"
    return "art_" + hashlib.sha256(seed.encode()).hexdigest()[:24]
