"""
PATH: backend/app/services/formula_math.py
PURPOSE: Shared first-principles maths referenced by formula-registry.json.

Keep pure: f(inputs) → output. No I/O. Numbers here must match FE twins.
"""

from __future__ import annotations

import math
from typing import Optional

MAD_SIGMA = 1.4826
ROBUST_Z_WINSOR = 3.0
MOS_UI_EPS = 0.005

# R3 axis weights — must match rank_service.engine._PRESET_AXES["R3"]
R3_AXIS_WEIGHTS: dict[str, float] = {
    "rd_prod": 1.5,
    "fcfm_sbc": 1.0,
    "roic": 1.0,
    "mos_live": 1.5,
}


def mos_from_price_target(price: float, fair_med: float) -> float:
    """F_MOS_LIVE algebra: fair/price − 1."""
    if price <= 0:
        raise ValueError("price must be > 0")
    return fair_med / price - 1.0


def live_gap_pct(price: float, fair_med: float) -> float:
    """F_VS_MEDIAN_PCT: (fair − price) / price."""
    if price <= 0:
        raise ValueError("price must be > 0")
    return (fair_med - price) / price


def mos_equals_live_gap(price: float, fair_med: float, eps: float = 1e-12) -> bool:
    """F_MOS_VS_IDENTITY."""
    return abs(mos_from_price_target(price, fair_med) - live_gap_pct(price, fair_med)) <= eps


def annualized_from_prices(live: float, target: float, years: float) -> Optional[float]:
    """F_IMPLIED_ANN_RETURN via prices: (target/live)^(1/H) − 1."""
    if not (live > 0 and target > 0 and years > 0):
        return None
    return (target / live) ** (1.0 / years) - 1.0


def annualized_from_gap(gap: float, years: float) -> Optional[float]:
    """F_IMPLIED_ANN_RETURN via gap: (1+gap)^(1/H) − 1."""
    if not (years > 0 and math.isfinite(gap)):
        return None
    return (1.0 + gap) ** (1.0 / years) - 1.0


def hold_horizon_years(gap: Optional[float]) -> Optional[int]:
    """F_HOLD_HORIZON buckets shared with sell ceiling / stance."""
    if gap is None or not math.isfinite(gap) or gap <= 0:
        return None
    if gap >= 0.6:
        return 3
    if gap >= 0.25:
        return 2
    return 1
