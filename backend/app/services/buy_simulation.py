"""
PATH: backend/app/services/buy_simulation.py
PURPOSE: SIMULATED historical BUY robustness study — pre-registered proxy gates
  (contracts/simulated-buy-gates.json, study_id sim_proxy_v1) + Newey-West
  inference on the monthly equal-weight book vs a benchmark.

This is NOT the sealed track record (buy_set_snapshots kind='sealed'). Every
result carries the contract's disclosures; fair bands / grades are look-ahead
by construction and the study says so.

Pure functions only: bars/vector rows in → gate decisions and statistics out.
DB and cache IO live in scripts/simulate_buy_history.py.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Optional

STUDY_ID = "sim_proxy_v1"
TAPE_WINDOW_DAYS = 548  # ~18 months, mirrors close_call_service._detect_tape_event
TAPE_MIN_BARS = 40
TAPE_DRAWDOWN = -0.25
WARMUP_MONTHS = 2
HORIZONS_SESSIONS = (21, 63, 126)


def parse_bars(bars: list[dict[str, Any]]) -> list[tuple[date, float]]:
    """Sorted (date, close) pairs; malformed or non-positive bars are dropped."""
    out: list[tuple[date, float]] = []
    for bar in bars or []:
        try:
            d = date.fromisoformat(str(bar.get("date") or "")[:10])
            px = float(bar["close"])
        except (TypeError, ValueError, KeyError):
            continue
        if px > 0:
            out.append((d, px))
    out.sort(key=lambda x: x[0])
    return out


def pit_bars(parsed: list[tuple[date, float]], as_of: date) -> list[tuple[date, float]]:
    """Only bars dated on or before as_of — the simulator's PIT guarantee."""
    return [b for b in parsed if b[0] <= as_of]


def close_at(parsed: list[tuple[date, float]], as_of: date) -> Optional[float]:
    """Last close on or before as_of (None when no PIT bar exists)."""
    window = pit_bars(parsed, as_of)
    return window[-1][1] if window else None


def tape_event_pit(parsed: list[tuple[date, float]], as_of: date) -> Optional[bool]:
    """G3: >=25% peak→trough drawdown in trailing ~18m of PIT bars.

    Returns None (exclude, fail closed) when fewer than TAPE_MIN_BARS PIT bars.
    """
    window = pit_bars(parsed, as_of)
    if len(window) < TAPE_MIN_BARS:
        return None
    start_cut = as_of - timedelta(days=TAPE_WINDOW_DAYS)
    recent = [b for b in window if b[0] >= start_cut]
    if len(recent) < 20:
        recent = window
    peak = 0.0
    for _, px in recent:
        if px > peak:
            peak = px
        elif peak > 0 and px / peak - 1.0 < TAPE_DRAWDOWN:
            return True
    return False


def evaluate_gates(
    *,
    parsed: list[tuple[date, float]],
    as_of: date,
    mos: Optional[float],
    fair_px_med: Optional[float],
    grade: Optional[str],
    kill_active: Optional[bool],
) -> dict[str, Any]:
    """Apply the pre-registered proxy gates. Missing inputs → excluded, never passed."""
    px = close_at(parsed, as_of)
    tape = tape_event_pit(parsed, as_of)

    missing: list[str] = []
    if mos is None:
        missing.append("mos")
    if fair_px_med is None or px is None:
        missing.append("gap_inputs")
    if tape is None:
        missing.append("tape_bars")
    if grade is None or kill_active is None:
        missing.append("vector_quality")
    if missing:
        return {"decision": "excluded", "missing": missing}

    g1 = mos > 0
    g2 = (fair_px_med - px) / px > 0
    g3 = bool(tape)
    g4 = str(grade).upper() in {"A", "B"} and kill_active is False
    passed = g1 and g2 and g3 and g4
    return {
        "decision": "buy" if passed else "no_buy",
        "gates": {"G1": g1, "G2": g2, "G3": g3, "G4": g4},
        "close_at_sim": round(px, 4),
        "gap_to_median": round((fair_px_med - px) / px, 6),
    }


def rebalance_dates(trading_days: list[date], *, warmup_months: int = WARMUP_MONTHS) -> list[date]:
    """First trading day of each month, skipping the initial warmup months."""
    firsts: list[date] = []
    seen: set[tuple[int, int]] = set()
    for d in sorted(trading_days):
        key = (d.year, d.month)
        if key not in seen:
            seen.add(key)
            firsts.append(d)
    return firsts[warmup_months:]


def newey_west_tstat(series: list[float], *, lags: Optional[int] = None) -> Optional[dict[str, Any]]:
    """NW t-stat of the mean (Bartlett kernel). None when n < 8 — too few obs to claim anything."""
    n = len(series)
    if n < 8:
        return None
    mean = sum(series) / n
    resid = [x - mean for x in series]
    if lags is None:
        lags = int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    lags = max(0, min(lags, n - 2))
    var = sum(r * r for r in resid) / n
    for lag in range(1, lags + 1):
        w = 1.0 - lag / (lags + 1.0)
        cov = sum(resid[i] * resid[i - lag] for i in range(lag, n)) / n
        var += 2.0 * w * cov
    if var <= 0:
        return None
    se = math.sqrt(var / n)
    # Degenerate (near-constant) series: a t-stat from float noise is meaningless.
    if not math.isfinite(se) or se < 1e-12 * max(1.0, abs(mean)):
        return None
    return {
        "mean": round(mean, 6),
        "t_stat": round(mean / se, 4),
        "se": round(se, 6),
        "n": n,
        "lags": lags,
        "kernel": "bartlett",
    }


def max_drawdown(period_returns: list[float]) -> Optional[float]:
    """Max peak-to-trough drawdown of the compounded series (negative fraction)."""
    if not period_returns:
        return None
    level = 1.0
    peak = 1.0
    worst = 0.0
    for r in period_returns:
        level *= 1.0 + r
        peak = max(peak, level)
        worst = min(worst, level / peak - 1.0)
    return round(worst, 6)


def forward_return_pit(
    parsed: list[tuple[date, float]], *, as_of: date, sessions: int
) -> Optional[float]:
    """Entry at first close strictly after as_of; exit `sessions` bars later."""
    start_i = next((i for i, (d, _) in enumerate(parsed) if d > as_of), None)
    if start_i is None or sessions < 1:
        return None
    end_i = start_i + sessions
    if end_i >= len(parsed):
        return None
    return round(parsed[end_i][1] / parsed[start_i][1] - 1.0, 6)


def summarise_study(
    *,
    per_date: list[dict[str, Any]],
    benchmark_parsed: list[tuple[date, float]],
) -> dict[str, Any]:
    """Aggregate per-rebalance results into the inference pack.

    per_date rows: {"as_of": date, "members": [ticker...], "returns": {sessions: {ticker: ret|None}}}
    """
    horizons: dict[str, Any] = {}
    for h in HORIZONS_SESSIONS:
        book: list[float] = []
        excess: list[float] = []
        hits = 0
        obs = 0
        for row in per_date:
            rets = [r for r in (row["returns"].get(h) or {}).values() if r is not None]
            if not rets:
                continue
            ew = sum(rets) / len(rets)
            book.append(ew)
            obs += len(rets)
            hits += sum(1 for r in rets if r > 0)
            bench = forward_return_pit(benchmark_parsed, as_of=row["as_of"], sessions=h)
            if bench is not None:
                excess.append(ew - bench)
        horizons[f"{h}s"] = {
            "n_rebalances": len(book),
            "mean_book_return": round(sum(book) / len(book), 6) if book else None,
            "mean_excess_vs_benchmark": (
                round(sum(excess) / len(excess), 6) if excess else None
            ),
            "hit_rate": round(hits / obs, 4) if obs else None,
            "n_member_observations": obs,
            "max_drawdown_book": max_drawdown(book),
            "newey_west_excess": newey_west_tstat(excess),
        }
    return {"horizon_unit": "trading_sessions", "horizons": horizons}
