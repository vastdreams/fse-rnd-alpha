"""
PATH: backend/app/services/rank_row_invariants.py
PURPOSE: First-principles checks for ranked Universe rows.

Machine-checkable contracts — not ad-hoc logs. Use `audit_rank_row` on
fixtures or live API payloads; any returned violation is a break.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional

EPS = 1e-6


def compute_live_vs_target_pct(
    price: Optional[float], fair_med: Optional[float]
) -> Optional[float]:
    """Live quote gap: (target − price) / price."""
    if price is None or fair_med is None:
        return None
    if not isinstance(price, (int, float)) or not isinstance(fair_med, (int, float)):
        return None
    if price <= 0:
        return None
    return (fair_med - price) / price


def compute_live_vs_target_usd(
    price: Optional[float], fair_med: Optional[float]
) -> Optional[float]:
    if price is None or fair_med is None:
        return None
    if not isinstance(price, (int, float)) or not isinstance(fair_med, (int, float)):
        return None
    return fair_med - price


def fair_band_zone(
    price: Optional[float], lo: Optional[float], hi: Optional[float]
) -> str:
    if price is None or lo is None or hi is None:
        return "unknown"
    # lo == hi is a legal degenerate band (all lenses agree); only inverted
    # bands are unknown. Keeps parity with the build-time ordering check.
    if lo > hi:
        return "unknown"
    if price < lo:
        return "below"
    if price > hi:
        return "above"
    return "inside"

def audit_rank_row(row: Mapping[str, Any], eps: float = EPS) -> list[dict[str, str]]:
    """Return [] when first-principles contracts hold."""
    violations: list[dict[str, str]] = []
    ticker = str(row.get("ticker") or "?")

    price = row.get("price_live")
    fair_lo = row.get("fair_px_lo")
    fair_med = row.get("fair_px_med")
    fair_hi = row.get("fair_px_hi")
    mos = row.get("mos_live")
    vs = row.get("vs_median_pct")
    score = row.get("score")
    contributions = row.get("contributions") or {}

    for name, value in (
        ("price_live", price),
        ("fair_px_lo", fair_lo),
        ("fair_px_med", fair_med),
        ("fair_px_hi", fair_hi),
        ("mos_live", mos),
        ("vs_median_pct", vs),
        ("revenue_usd", row.get("revenue_usd")),
        ("score", score),
    ):
        if value is not None and isinstance(value, (int, float)) and not math.isfinite(value):
            violations.append(
                {
                    "code": "NON_FINITE_METRIC",
                    "ticker": ticker,
                    "detail": f"{name} is non-finite ({value!r})",
                }
            )

    expected = compute_live_vs_target_pct(price, fair_med)
    if expected is not None and isinstance(vs, (int, float)):
        if abs(expected - vs) > eps:
            violations.append(
                {
                    "code": "VS_MEDIAN_MISMATCH",
                    "ticker": ticker,
                    "detail": f"vs_median_pct={vs} but (target−price)/price={expected}",
                }
            )

    if all(isinstance(x, (int, float)) for x in (fair_lo, fair_med, fair_hi)):
        if not (fair_lo <= fair_med <= fair_hi):
            violations.append(
                {
                    "code": "FAIR_BAND_ORDER",
                    "ticker": ticker,
                    "detail": f"fair band not ordered lo≤med≤hi ({fair_lo}, {fair_med}, {fair_hi})",
                }
            )

    zone = fair_band_zone(price, fair_lo, fair_hi)
    if zone == "below" and isinstance(vs, (int, float)) and vs <= 0:
        violations.append(
            {
                "code": "FAIR_BAND_ZONE_CONTRADICTION",
                "ticker": ticker,
                "detail": f"price below fair band but vs_median_pct={vs} is not positive",
            }
        )
    if zone == "above" and isinstance(vs, (int, float)) and vs >= 0:
        violations.append(
            {
                "code": "FAIR_BAND_ZONE_CONTRADICTION",
                "ticker": ticker,
                "detail": f"price above fair band but vs_median_pct={vs} is not negative",
            }
        )

    if (
        isinstance(mos, (int, float))
        and isinstance(price, (int, float))
        and isinstance(fair_med, (int, float))
    ):
        if price > fair_med and mos > eps:
            violations.append(
                {
                    "code": "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET",
                    "ticker": ticker,
                    "detail": f"mos_live={mos} > 0 while price {price} > target {fair_med}",
                }
            )
        if price < fair_med and mos < -eps:
            violations.append(
                {
                    "code": "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET",
                    "ticker": ticker,
                    "detail": f"mos_live={mos} < 0 while price {price} < target {fair_med}",
                }
            )

    if isinstance(score, (int, float)) and score != 0:
        has_driver = any(
            isinstance(v, (int, float)) and v != 0 for v in contributions.values()
        )
        if not has_driver:
            violations.append(
                {
                    "code": "SCORE_WITHOUT_DRIVERS",
                    "ticker": ticker,
                    "detail": f"score={score} but contributions are empty/zero",
                }
            )

    return violations


def audit_rank_rows(rows: list[Mapping[str, Any]], eps: float = EPS) -> list[dict[str, str]]:
    """Audit a batch of ranked rows."""
    out: list[dict[str, str]] = []
    for row in rows:
        out.extend(audit_rank_row(row, eps=eps))
    return out


def assert_rank_rows_invariants(rows: list[Mapping[str, Any]], eps: float = EPS) -> None:
    """Fail closed if any first-principles violation is present."""
    violations = audit_rank_rows(rows, eps=eps)
    if not violations:
        return
    lines = [f"[{v['code']}] {v.get('ticker', '?')} — {v['detail']}" for v in violations]
    raise AssertionError("rank row invariant violations:\n" + "\n".join(lines))
