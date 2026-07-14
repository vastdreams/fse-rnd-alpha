#!/usr/bin/env python3
"""
PATH: scripts/cache_benchmark_bars.py
PURPOSE: Write benchmark (SPY) daily bars into data/price_history_cache in the
  exact {date, close, volume} bar format the BUY study reads offline.

WHY:
  Sharadar SEP does not cover ETFs, so the normal price backfill never caches
  SPY. The simulated BUY robustness study needs a benchmark series in the same
  immutable cache so the study runs offline and deterministically.

SOURCES (in order):
  1. fmp_daily_prices table (already ingested via scripts/ingest_benchmark_prices.py)
  2. FMP EOD API (requires FMP_API_KEY) — then rows are still raw close, no adjClose

Provenance is stamped in the payload; close is unadjusted FMP close, which is
disclosed in the study artifact.

Usage:
  DATABASE_URL=... python3 scripts/cache_benchmark_bars.py --symbol SPY --years 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.price_history_service import CACHE_DIR  # noqa: E402


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
    ).replace("postgresql+asyncpg://", "postgresql://")


async def _bars_from_db(symbol: str, start_iso: str) -> list[dict]:
    import asyncpg

    conn = await asyncpg.connect(database_url())
    try:
        rows = await conn.fetch(
            """SELECT date, COALESCE(adj_close, close) AS close, volume
                 FROM fmp_daily_prices
                WHERE symbol=$1 AND date >= $2 AND COALESCE(adj_close, close) > 0
                ORDER BY date""",
            symbol,
            datetime.fromisoformat(start_iso).date(),
        )
    finally:
        await conn.close()
    return [
        {"date": r["date"].isoformat(), "close": float(r["close"]), "volume": r["volume"]}
        for r in rows
    ]


async def _bars_from_fmp(symbol: str, start_iso: str) -> list[dict]:
    from app.services.fmp_client import FMPClient

    async with FMPClient() as client:
        prices = await client.get_historical_prices(symbol, from_date=start_iso, to_date=None)
    bars = []
    for p in prices or []:
        if not isinstance(p, dict) or not p.get("date") or p.get("close") is None:
            continue
        try:
            close = float(p["close"])
        except (TypeError, ValueError):
            continue
        if close <= 0:
            continue
        bars.append({"date": str(p["date"])[:10], "close": close, "volume": p.get("volume")})
    bars.sort(key=lambda b: b["date"])
    return bars


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="SPY")
    ap.add_argument("--years", type=int, default=3)
    args = ap.parse_args()

    symbol = args.symbol.upper()
    lookback = max(1, min(args.years, 10)) * 365
    start_iso = (datetime.now(timezone.utc).date() - timedelta(days=lookback)).isoformat()

    bars = await _bars_from_db(symbol, start_iso)
    source = "fmp_daily_prices table (FMP EOD close)"
    if not bars:
        bars = await _bars_from_fmp(symbol, start_iso)
        source = "FMP EOD API (close, unadjusted)"
    if len(bars) < 40:
        raise SystemExit(
            f"Refusing to cache {symbol}: only {len(bars)} bars from {source} — "
            "ingest via scripts/ingest_benchmark_prices.py first"
        )

    payload = {
        "ticker": symbol,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "n": len(bars),
        "start": bars[0]["date"],
        "end": bars[-1]["date"],
        "last": bars[-1]["close"],
        "bars": bars,
        "price_as_of": bars[-1]["date"],
        "price_source": source,
        "cache_stale": False,
        "note": (
            "Benchmark daily closes for the simulated BUY robustness study. "
            "FMP close (no adjClose from the stable endpoint) — disclosed in the study artifact."
        ),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / f"{symbol}_{lookback}.json"
    out.write_text(json.dumps(payload))
    print(json.dumps({"written": str(out), "n": len(bars), "start": payload["start"], "end": payload["end"], "source": source}))


if __name__ == "__main__":
    asyncio.run(main())
