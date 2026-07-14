"""
PATH: backend/app/services/tradability.py
PURPOSE: Capacity / ADV proxies for universe cards and book constraints.

Never invents volume. Missing close or volume → that session skipped; if fewer
than ``min_sessions`` known sessions remain, return None (UNKNOWN).
"""

from __future__ import annotations

from typing import Any, Optional


def adv_usd_from_bars(
    bars: list[dict[str, Any]] | None,
    *,
    window: int = 20,
    min_sessions: int = 10,
) -> Optional[float]:
    """Mean dollar volume over the last ``window`` sessions with both close+volume."""

    if not bars or window < 1:
        return None
    dollar: list[float] = []
    for bar in bars[-window:]:
        try:
            close = bar.get("close")
            volume = bar.get("volume")
            if close is None or volume is None:
                continue
            c = float(close)
            v = float(volume)
            if c <= 0 or v < 0:
                continue
            dollar.append(c * v)
        except (TypeError, ValueError):
            continue
    if len(dollar) < min_sessions:
        return None
    return round(sum(dollar) / len(dollar), 2)


def capacity_note(adv_usd: Optional[float], *, aum_usd: float = 50_000_000.0) -> str:
    """Honest one-liner for cards — not a sizing recommendation."""

    if adv_usd is None:
        return "ADV unknown — capacity not underwritten"
    soft = adv_usd * 0.01
    return (
        f"≈${adv_usd:,.0f} ADV (20d). Soft 1% ADV capacity ≈ ${soft:,.0f}/day "
        f"(illustration only — not a size order; not sized to ${aum_usd:,.0f} AUM)."
    )
