"""
PATH: backend/app/services/sell_ceiling.py
PURPOSE: BE twin of frontend/src/lib/sellCeiling.ts (F_SELL_CEILING).

Must stay bit-compatible with the FE implementation for the same inputs.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from app.services.formula_math import annualized_from_prices, hold_horizon_years

SellZone = Literal["to_target", "in_upper_band", "past_ceiling", "unknown"]


def compute_sell_ceiling(
    *,
    fair_px_lo: Optional[float] = None,
    fair_px_med: Optional[float] = None,
    fair_px_hi: Optional[float] = None,
    price_live: Optional[float] = None,
    stance_horizon: Optional[int] = None,
) -> dict[str, Any]:
    lo, med, hi, live = fair_px_lo, fair_px_med, fair_px_hi, price_live
    base: dict[str, Any] = {
        "sell_ceil": None,
        "lens": None,
        "fair_lo": lo,
        "fair_med": med,
        "fair_hi": hi,
        "live": live,
        "upside_to_ceil": None,
        "horizon_years": None,
        "remaining_ann": None,
        "zone": "unknown",
        "formula_id": "F_SELL_CEILING",
    }
    if med is None or not (med > 0) or live is None or not (live > 0):
        return base

    if live < med:
        sell_ceil, lens, zone = med, "median", "to_target"
    elif hi is not None and hi > 0 and live < hi:
        sell_ceil, lens, zone = hi, "high", "in_upper_band"
    elif hi is not None and hi > 0 and live >= hi:
        sell_ceil, lens, zone = hi, "high", "past_ceiling"
    else:
        sell_ceil, lens = med, "median"
        zone = "past_ceiling" if live >= med else "to_target"

    upside = sell_ceil / live - 1.0
    if zone == "past_ceiling":
        horizon = None
    elif stance_horizon in (1, 2, 3):
        horizon = stance_horizon
    else:
        horizon = hold_horizon_years(upside if upside > 0 else None)

    remaining = None
    if zone != "past_ceiling" and horizon is not None and upside > 0:
        remaining = annualized_from_prices(live, sell_ceil, float(horizon))

    return {
        **base,
        "sell_ceil": sell_ceil,
        "lens": lens,
        "upside_to_ceil": upside,
        "horizon_years": horizon,
        "remaining_ann": remaining,
        "zone": zone,
    }
