"""
PATH: backend/app/services/stance_scores.py
PURPOSE: Pure stance sub-score curves (F_STANCE_BUY_GATES) — sealed for tests.
Mirrors close_call_service scoring without I/O.
"""

from __future__ import annotations

from typing import Optional


def clip10(x: float) -> float:
    return round(max(0.0, min(10.0, x)), 2)


def score_valuation_from_gap(gap: Optional[float]) -> float:
    """MoS/gap → 0–10: 0→5, +50%→8.5, +100%→10."""
    return clip10(5.0 + (gap or 0.0) * 7.0)


def score_fcfm(fcfm: Optional[float]) -> Optional[float]:
    if fcfm is None:
        return None
    return clip10(3.0 + fcfm * 40.0)


def score_rule40(rule40: Optional[float]) -> Optional[float]:
    if rule40 is None:
        return None
    return clip10(rule40 * 15.0)


def score_roic(roic: Optional[float]) -> Optional[float]:
    if roic is None:
        return None
    return clip10(min(roic, 1.0) * 12.0 + 2.0)


def aggregate_stance_score(
    run_scores: list[tuple[float, Optional[float]]],
) -> Optional[float]:
    """
    run_scores: list of (weight, score_0_10|None).
    Returns 0–100 aggregate with coverage penalty, or None if nothing scored.
    """
    scored = [(w, s) for w, s in run_scores if s is not None]
    total_w = sum(w for w, _ in run_scores)
    scored_w = sum(w for w, _ in scored)
    if not scored or total_w <= 0:
        return None
    agg_0_10 = sum(w * s for w, s in scored) / scored_w
    coverage = scored_w / total_w
    return round(agg_0_10 * 10.0 * coverage, 1)
