#!/usr/bin/env python3
"""
PATH: scripts/backfill_price_history.py
PURPOSE: Warm Sharadar SEP day bars into data/price_history_cache for every
  universe ticker so L0 tape / stances never fan out live.

Usage:
  python scripts/backfill_price_history.py --universe-version univ_... [--missing-only]

The target universe is explicit and must already be sealed. A partial run
requires --allow-partial so a successful one-ticker probe is never mistaken for
full-universe release coverage.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.price_history_service import (  # noqa: E402
    CACHE_DIR,
    PriceHistoryUnavailable,
    get_cached_price_history,
    get_price_history,
)


async def _tickers(universe_version: str) -> list[str]:
    import asyncpg

    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        status = await conn.fetchval(
            "SELECT status FROM universe_builds WHERE universe_version=$1",
            universe_version,
        )
        if status != "sealed":
            raise RuntimeError(
                f"Universe {universe_version!r} must exist and be sealed; got {status!r}"
            )
        rows = await conn.fetch(
            "SELECT ticker FROM metric_vectors WHERE universe_version=$1 ORDER BY ticker",
            universe_version,
        )
        tickers = [r["ticker"].upper() for r in rows]
        if not tickers:
            raise RuntimeError(f"Sealed universe {universe_version!r} has no metric vectors")
        return tickers
    finally:
        await conn.close()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--universe-version",
        required=True,
        help="Sealed universe version whose tickers this backfill must cover",
    )
    ap.add_argument("--missing-only", action="store_true", help="Skip tickers with any cache file")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ticker", type=str, default="")
    ap.add_argument(
        "--allow-partial",
        action="store_true",
        help="Permit --ticker/--limit probes and incomplete coverage (never use for a release).",
    )
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--years", type=int, default=3)
    args = ap.parse_args()

    universe_tickers = await _tickers(args.universe_version)
    if args.ticker and not args.allow_partial:
        ap.error("--ticker requires --allow-partial")
    if args.limit > 0 and not args.allow_partial:
        ap.error("--limit requires --allow-partial")
    if args.ticker:
        ticker = args.ticker.upper()
        if ticker not in universe_tickers:
            ap.error(f"{ticker} is not part of sealed universe {args.universe_version}")
        tickers = [ticker]
    else:
        tickers = universe_tickers[: args.limit] if args.limit > 0 else universe_tickers

    if args.missing_only:
        keep = []
        for t in tickers:
            if get_cached_price_history(t, years=args.years, allow_stale=True) is None:
                keep.append(t)
        tickers = keep

    print(
        f"universe={args.universe_version} n={len(tickers)} "
        f"universe_n={len(universe_tickers)} cache_dir={CACHE_DIR}",
        flush=True,
    )
    ok = 0
    fail = 0
    failures: list[dict[str, str]] = []
    t0 = time.time()
    for i, t in enumerate(tickers, 1):
        try:
            hist = await get_price_history(t, years=args.years)
            ok += 1
            n = hist.get("n", 0)
        except PriceHistoryUnavailable as e:
            fail += 1
            n = 0
            failures.append({"ticker": t, "error": str(e)})
            print(f"  FAIL {t}: {e}", flush=True)
        except Exception as e:
            fail += 1
            n = 0
            failures.append({"ticker": t, "error": str(e)})
            print(f"  ERR {t}: {e}", flush=True)
        if i % 25 == 0 or i == len(tickers) or i <= 3:
            print(
                f"[{i}/{len(tickers)}] ok={ok} fail={fail} "
                f"elapsed={time.time()-t0:.0f}s last={t} bars={n}",
                flush=True,
            )
        await asyncio.sleep(args.sleep)

    missing_tickers = [
        ticker
        for ticker in universe_tickers
        if get_cached_price_history(ticker, years=args.years, allow_stale=True) is None
    ]
    report = {
        "kind": "price_history",
        "universe_version": args.universe_version,
        "universe_tickers": len(universe_tickers),
        "selected_tickers": len(tickers),
        "succeeded": ok,
        "failed": fail,
        "missing_tickers": missing_tickers,
        "coverage_pct": round(
            100.0 * (len(universe_tickers) - len(missing_tickers)) / len(universe_tickers),
            1,
        ),
        "allow_partial": args.allow_partial,
        "elapsed_s": round(time.time() - t0, 1),
        "cache_dir": str(CACHE_DIR),
        "failures": failures,
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_version = args.universe_version.replace("/", "_")
    (CACHE_DIR / f"_backfill_report_{safe_version}.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    if missing_tickers and not args.allow_partial:
        raise SystemExit(
            f"Price-history coverage is incomplete for sealed universe {args.universe_version}: "
            f"{len(missing_tickers)} ticker(s) missing"
        )


if __name__ == "__main__":
    asyncio.run(main())
