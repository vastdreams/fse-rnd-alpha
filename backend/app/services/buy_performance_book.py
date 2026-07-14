"""
PATH: backend/app/services/buy_performance_book.py
PURPOSE: PIT research-BUY set ledger + forward returns.

Distinct from paper HML_RD / RD20. Never invents membership or prices.
Empty ledger → honest ``status=empty`` payload (not a fabricated track record).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional


HORIZONS_SESSIONS = (21, 63, 126, 252)


def forward_return(
    bars: list[dict[str, Any]],
    *,
    as_of: date,
    sessions: int,
) -> Optional[float]:
    """PIT: first close on/after as_of → close ``sessions`` trading bars later."""

    if not bars or sessions < 1:
        return None
    ordered: list[tuple[date, float]] = []
    for bar in bars:
        try:
            d = date.fromisoformat(str(bar.get("date") or "")[:10])
            px = float(bar["close"])
            if px <= 0:
                continue
            ordered.append((d, px))
        except (TypeError, ValueError, KeyError):
            continue
    ordered.sort(key=lambda x: x[0])
    start_i = next((i for i, (d, _) in enumerate(ordered) if d >= as_of), None)
    if start_i is None:
        return None
    end_i = start_i + sessions
    if end_i >= len(ordered):
        return None
    p0 = ordered[start_i][1]
    p1 = ordered[end_i][1]
    return round(p1 / p0 - 1.0, 6)


def equal_weight_book_return(member_returns: list[Optional[float]]) -> Optional[float]:
    known = [r for r in member_returns if r is not None]
    if not known:
        return None
    return round(sum(known) / len(known), 6)


def hit_rate(member_returns: list[Optional[float]]) -> Optional[float]:
    known = [r for r in member_returns if r is not None]
    if not known:
        return None
    return round(sum(1 for r in known if r > 0) / len(known), 4)


def empty_book_payload(*, universe_version: str | None = None) -> dict[str, Any]:
    return {
        "status": "empty",
        "universe_version": universe_version,
        "note": (
            "No sealed research-BUY sets yet. Paper HML_RD / RD20 is a different engine "
            "and must not be read as this BUY track record. Seal membership via "
            "scripts/seal_buy_set.py after promote."
        ),
        "snapshots": [],
        "summary": None,
        "engine": "buy_performance_book_v1",
        "distinct_from": ["HML_RD", "RD20", "paper_publication_track"],
    }


def summarise_snapshot(
    *,
    as_of: date,
    universe_version: str,
    members: list[dict[str, Any]],
    bars_by_ticker: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Compute forward metrics for one sealed BUY set. Missing bars → null horizons."""

    summary: dict[str, Any] = {
        "as_of": as_of.isoformat(),
        "universe_version": universe_version,
        "n_buy": len(members),
        "horizons": {},
    }
    for h in HORIZONS_SESSIONS:
        rets = [
            forward_return(bars_by_ticker.get(m["ticker"].upper(), []), as_of=as_of, sessions=h)
            for m in members
        ]
        summary["horizons"][f"{h}d"] = {
            "mean_equal_weight": equal_weight_book_return(rets),
            "hit_rate": hit_rate(rets),
            "n_observed": sum(1 for r in rets if r is not None),
            "n_missing": sum(1 for r in rets if r is None),
        }
    return summary


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
