"""
PATH: backend/app/services/decision_provenance.py
PURPOSE: Attach first-principles provenance payloads to rank / stance outputs.
"""

from __future__ import annotations

from typing import Any, Optional

from app.contracts.decision_chains import chain_by_id
from app.contracts.formula_registry import formula_by_id
from app.contracts.recipes import LITERATURE_BINDS


def literature_for_axis(axis: str) -> Optional[dict[str, str]]:
    for bind in LITERATURE_BINDS:
        if bind.axis == axis:
            return {
                "axis": bind.axis,
                "bib_key": bind.bib_key,
                "citation": bind.citation,
                "paper_section": bind.paper_section or "",
            }
    return None


def rank_row_provenance(row: dict[str, Any]) -> dict[str, Any]:
    """Compact, assumption-free provenance for one ranked Universe row."""
    axes = ["rd_prod", "fcfm_sbc", "roic", "mos_live"]
    lit = [literature_for_axis(a) for a in axes]
    return {
        "decision_chain_id": "D_RANK_R3",
        "formula_ids": [
            "F_VS_MEDIAN_PCT",
            "F_MOS_LIVE",
            "F_SCORE_ROBUST_Z",
            "F_FAIR_BAND_ZONE",
            "F_SELL_CEILING",
        ],
        "data_mode": {
            "price_live": "live_quote_or_mos_implied",
            "fair_px_*": "sealed_vector_or_panel",
            "mos_live": "sealed_vector",
            "vs_median_pct": "derived_F_VS_MEDIAN_PCT",
            "fundamentals": "sealed_vector_or_panel_pass_through",
        },
        "assumption_policy": "no_imputation",
        "literature_binds": [x for x in lit if x],
        "above_band_advisory": bool(
            row.get("price_live") is not None
            and row.get("fair_px_hi") is not None
            and row["price_live"] > row["fair_px_hi"]
        ),
        "first_principles": chain_by_id("D_RANK_R3")["first_principles"],
    }


def enrich_flowchart_node(
    node: dict[str, Any],
    *,
    formula_ids: Optional[list[str]] = None,
    data_fields: Optional[list[str]] = None,
    gate_kind: str = "hard",
) -> dict[str, Any]:
    """Add provenance keys to a stance flowchart node (additive)."""
    out = dict(node)
    out["gate_kind"] = gate_kind
    out["opinion"] = False
    out["data_fields"] = list(data_fields or [])
    out["formula_ids"] = list(formula_ids or [])
    cites = []
    for fid in out["formula_ids"]:
        try:
            cites.append(formula_by_id(fid)["reference"]["cite"])
        except KeyError:
            continue
    out["references"] = cites
    return out


def stance_decision_provenance() -> dict[str, Any]:
    chain = chain_by_id("D_STANCE_BUY")
    return {
        "decision_chain_id": chain["id"],
        "first_principles": chain["first_principles"],
        "hard_gate_ids": [s["id"] for s in chain["steps"] if s.get("gate_kind") == "hard"],
        "advisory_not_gates": chain.get("advisory_not_gates") or [],
        "assumption_policy": "missing_critical_input → UNKNOWN; never invent catalyst or MoS",
    }
