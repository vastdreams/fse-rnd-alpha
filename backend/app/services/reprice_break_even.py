"""
PATH: backend/app/services/reprice_break_even.py
PURPOSE: Market-implied repricing probability p* — inverted scenario maths.

p* = (price − V_base) / (V_rep − V_base)

where V_base is the sealed base-case median fair value and V_rep the repriced
(bull-scenario) median. We never assign a probability to the AI-SaaS repricing
thesis; p* displays what the market is charging for it. p* < 0 means the
repricing leg is a free option (price below base case). Display only — p*
never gates and never sizes.
"""

from __future__ import annotations

import math
from typing import Any, Optional


def _f(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def p_star(
    price: Optional[float],
    v_base_med: Optional[float],
    v_rep_med: Optional[float],
) -> Optional[float]:
    """Break-even probability of the repriced scenario. None = not computable."""
    p, base, rep = _f(price), _f(v_base_med), _f(v_rep_med)
    if p is None or base is None or rep is None:
        return None
    if p <= 0 or base <= 0 or rep <= base:
        return None
    return round((p - base) / (rep - base), 4)


def p_star_payload(
    price: Optional[float],
    v_base_med: Optional[float],
    v_rep_med: Optional[float],
    *,
    scenario_source: Optional[str] = None,
) -> dict[str, Any]:
    """Display payload with the honest reading spelled out."""
    value = p_star(price, v_base_med, v_rep_med)
    if value is None:
        reading = (
            "No repricing leg run — p* needs a sealed base median and a bull-scenario median."
            if _f(v_rep_med) is None or _f(v_base_med) is None
            else "p* not computable (price/base/repriced values degenerate)."
        )
    elif value < 0:
        reading = (
            f"p* = {value:.0%}: price sits below the base case — the repricing thesis is a "
            "free option at this price."
        )
    elif value > 1:
        reading = (
            f"p* = {value:.0%}: price already exceeds the repriced value — the market has "
            "over-paid the thesis; no repricing edge remains."
        )
    else:
        reading = (
            f"The market charges a {value:.0%} implied probability for the repricing scenario. "
            "We do not claim the true probability — you are the one underwriting the difference."
        )
    return {
        "p_star": value,
        "price": _f(price),
        "v_base_med": _f(v_base_med),
        "v_rep_med": _f(v_rep_med),
        "scenario_source": scenario_source,
        "formula": "p* = (price − V_base_med) / (V_rep_med − V_base_med)",
        "reading": reading,
        "never_gates": True,
    }
