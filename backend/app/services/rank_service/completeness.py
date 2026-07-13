"""
PATH: backend/app/services/rank_service/completeness.py
PURPOSE: Single source of truth for research-completeness grading.

Used by scripts/build_universe.py AND scripts/fill_layer0.py so the grade
rules cannot drift between the initial build and the extractor fill pass.

Grade ladder (underwrite eligibility — never blended into attractiveness):
  A          filing fetched + all 7 core metrics + >=2/3 overlay fields
  B          filing fetched + >=5 core metrics
  C          >=5 core metrics (no filing)
  Incomplete everything else
"""

from __future__ import annotations

from app.contracts.research import MetricVector, ResearchCompleteness

CORE_FIELDS = ("mos_snapshot", "gm", "fcfm_sbc", "roic", "rule40", "rd_prod", "rd_int")
OVERLAY_FIELDS = ("retention", "concentration", "ai_text_stance")


def grade_completeness(
    vector: MetricVector,
    *,
    filing_fetched: bool,
    claims_n: int,
    competitor_map_filled: bool = False,
) -> ResearchCompleteness:
    core_ok = sum(1 for f in CORE_FIELDS if getattr(vector, f).value is not None)
    overlay_ok = sum(1 for f in OVERLAY_FIELDS if getattr(vector, f).value is not None)
    fill = overlay_ok / len(OVERLAY_FIELDS)

    if filing_fetched and core_ok == len(CORE_FIELDS) and fill >= 2 / 3:
        grade = "A"
    elif filing_fetched and core_ok >= 5:
        grade = "B"
    elif core_ok >= 5:
        grade = "C"
    else:
        grade = "Incomplete"

    prev = vector.completeness
    return ResearchCompleteness(
        grade=grade,
        filing_fetched=filing_fetched,
        claims_n=claims_n,
        dcf_reproducible=vector.mos_snapshot.value is not None,
        overlay_fill_rate=round(fill, 4),
        competitor_map_filled=competitor_map_filled,
        asof_freshness_days=prev.asof_freshness_days if prev else None,
        stale=prev.stale if prev else False,
    )
