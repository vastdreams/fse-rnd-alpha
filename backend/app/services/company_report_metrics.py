"""
PATH: backend/app/services/company_report_metrics.py
PURPOSE: Metric/citation extraction for the two-page brief — pure functions
copying values from already-resolved research artifacts. Nothing is computed
or imputed here; every emitted metric points at a system citation.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.contracts.company_reports import (
    ProvenanceClass,
    ReportCitation,
    ReportMetric,
)


def fnum(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def mv(vector: dict, name: str) -> Optional[float]:
    metric = vector.get(name)
    return fnum(metric.get("value")) if isinstance(metric, dict) else None


def mv_date(vector: dict, name: str) -> Optional[date]:
    metric = vector.get(name)
    raw = metric.get("as_of_date") if isinstance(metric, dict) else None
    return date.fromisoformat(raw) if raw else None


def auto_citations(research: dict, consensus: Any) -> list[ReportCitation]:
    """System citations for sealed vector, live overlay, and consensus rows."""
    uv = research["universe_version"]
    vector = research["vector"]
    cites = [
        ReportCitation(
            cite_id="S1",
            provenance=ProvenanceClass.SEALED,
            title=f"Sealed universe vector {uv} — {vector['ticker']}",
            locator=f"metric_vectors:{uv}:{vector['ticker']}",
            source_id=uv,
            as_of_date=mv_date(vector, "mos_snapshot") or date.fromisoformat(vector["computed_at"][:10]),
            available_date=date.fromisoformat(vector["computed_at"][:10]),
        ),
        ReportCitation(
            cite_id="S2",
            provenance=ProvenanceClass.MODEL,
            title="Thesis engine output (close_call_v3 / thesis gates)",
            locator=f"api:/api/universe/company/{vector['ticker']}?universe_version={uv}",
            source_id=research.get("thesis", {}).get("engine_version"),
        ),
    ]
    profile = research.get("profile") or {}
    if profile.get("price_as_of"):
        cites.append(
            ReportCitation(
                cite_id="S3",
                provenance=ProvenanceClass.CURRENT_OVERLAY,
                title=f"Live price overlay ({profile.get('price_source') or 'provider'})",
                locator=f"price:{vector['ticker']}:{profile['price_as_of']}",
                as_of_date=date.fromisoformat(str(profile["price_as_of"])[:10]),
                available_date=date.fromisoformat(str(profile["price_as_of"])[:10]),
            )
        )
    if consensus is not None:
        cites.append(
            ReportCitation(
                cite_id="S4",
                provenance=ProvenanceClass.LICENSED_CONSENSUS,
                title=f"Licensed consensus snapshot ({consensus.provider})",
                locator=f"consensus_snapshots:{consensus.consensus_id}",
                source_id=consensus.consensus_id,
                as_of_date=consensus.as_of_date,
                available_date=consensus.available_date,
            )
        )
    return cites


def _sealed_pct(label: str, value: Optional[float], cite: str) -> ReportMetric:
    return ReportMetric(
        label=label,
        value=value,
        unit="%" if value is not None else None,
        provenance=ProvenanceClass.SEALED,
        cite_ids=[cite] if value is not None else [],
    )


def financial_metrics(vector: dict) -> list[ReportMetric]:
    rows = [
        ("Revenue CAGR", mv(vector, "rev_cagr")),
        ("Gross margin", mv(vector, "gm")),
        ("FCF margin (SBC-adj)", mv(vector, "fcfm_sbc")),
        ("R&D intensity", mv(vector, "rd_int")),
        ("Rule of 40", mv(vector, "rule40")),
        ("ROIC", mv(vector, "roic")),
        ("Net revenue retention", mv(vector, "retention")),
        ("Annualised dilution", mv(vector, "dilution_ann")),
    ]
    return [_sealed_pct(label, value, "S1") for label, value in rows]


def gate_metrics(research: dict) -> list[ReportMetric]:
    vector = research["vector"]
    thesis = research.get("thesis") or {}
    spine = thesis.get("repayment_engine") or {}
    skew = thesis.get("skew") or {}
    stance = (research.get("close_call_waterfall") or {}).get("aggregate") or {}

    def m(label: str, value: Optional[float], display: Optional[str] = None) -> ReportMetric:
        return ReportMetric(
            label=label,
            value=value,
            display=display,
            provenance=ProvenanceClass.MODEL,
            cite_ids=["S2"] if (value is not None or display is not None) else [],
        )

    survivable = (thesis.get("survivability") or {}).get("survivable")
    return [
        m("R&D composite (σ)", fnum(spine.get("rd_composite"))),
        m("RD-cohort eligible", None, {True: "Yes", False: "No"}.get(spine.get("rd_elig"))),
        m("Survivability floors", None, {True: "All clear", False: "Failed"}.get(survivable)),
        m(
            "Payoff skew",
            fnum(skew.get("payoff_skew")),
            "Below band" if skew.get("payoff_skew_label") == "below_band" else None,
        ),
        m("Stance score", fnum(stance.get("score"))),
        m("Margin of safety (live)", mv(vector, "mos_live")),
    ]


def sizing_metrics(research: dict, proxy_weight_pct: Optional[float]) -> list[ReportMetric]:
    size = (research.get("thesis") or {}).get("size") or {}
    out = [
        ReportMetric(
            label="Validated sizing bound (f_max)",
            value=fnum(size.get("f_max_fraction")),
            provenance=ProvenanceClass.MODEL,
            cite_ids=["S2"] if size.get("f_max_fraction") is not None else [],
            methodology="Conservative Kelly bound from frozen HML_RD evidence; zero until CI excludes zero.",
        )
    ]
    if proxy_weight_pct is not None:
        out.append(
            ReportMetric(
                label="Construction proxy weight",
                value=proxy_weight_pct,
                unit="%",
                provenance=ProvenanceClass.MODEL,
                cite_ids=["S2"],
                methodology="SIZING_PROXY_V1 relative split among cleared BUYs; 15% per-name cap. Not validated edge.",
            )
        )
    return out
