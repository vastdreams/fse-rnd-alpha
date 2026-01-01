#!/usr/bin/env python3
"""
PATH: scripts/ingest_benchmark_prices.py
PURPOSE:
  Ingest benchmark ticker daily prices (e.g., SPY) into the Tier-1 price table (`fmp_daily_prices`).

WHY:
  The research platform’s investable backtest reports benchmark-relative results. For practitioner
  submissions (e.g., JPM), we want a familiar investable benchmark series (SPY) without relying on
  an “S&P 500 constituents API”. This script ingests *one ticker’s* daily price history and stores it
  alongside the existing Tier-1 price universe.

FLOW:
  ┌────────────────────────────┐
  │ Fetch daily prices (FMP)   │
  └──────────────┬─────────────┘
                 ▼
  ┌────────────────────────────┐
  │ Upsert into fmp_daily_prices│
  └──────────────┬─────────────┘
                 ▼
  ┌────────────────────────────┐
  │ (Optional) compute July–June│  → run `scripts/compute_july_june_returns.py --symbols ...`
  │ returns for the benchmark  │
  └────────────────────────────┘

DEPENDENCIES:
  - `FMP_API_KEY` env var (see deploy/.env)
  - Postgres (via `DATABASE_URL` / settings)
  - backend modules:
      - app.services.fmp_client.FMPClient
      - app.db.models.FMPDailyPrice
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Make `backend/app` importable as `app.*`
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.models import FMPDailyPrice
from app.services.fmp_client import FMPClient


def _parse_iso_date(value: Any) -> Optional[date]:
    if not isinstance(value, str):
        return None
    try:
        y, m, d = value.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _coerce_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


async def ingest_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    from_date: str,
    to_date: Optional[str],
) -> int:
    """
    Fetch and upsert daily prices for a single ticker into `fmp_daily_prices`.

    NOTE:
      The FMP stable EOD endpoint used by our Tier-1 ingestion returns `close` but does not provide
      an `adjClose` field. We persist `close` and leave `adj_close` null for this benchmark unless a
      richer price endpoint is adopted in the future.
    """
    async with FMPClient() as client:
        prices = await client.get_historical_prices(symbol, from_date=from_date, to_date=to_date)

    if not prices:
        return 0

    rows: List[Dict[str, Any]] = []
    for p in prices:
        if not isinstance(p, dict):
            continue
        dt = _parse_iso_date(p.get("date"))
        if not dt:
            continue
        rows.append(
            {
                "symbol": str(symbol),
                "date": dt,
                "open": _coerce_float(p.get("open")),
                "high": _coerce_float(p.get("high")),
                "low": _coerce_float(p.get("low")),
                "close": _coerce_float(p.get("close")),
                # Not available from the stable endpoint:
                "adj_close": None,
                "volume": _coerce_int(p.get("volume")),
                "change_pct": _coerce_float(p.get("changePercent")),
                "vwap": _coerce_float(p.get("vwap")),
            }
        )

    if not rows:
        return 0

    stmt = pg_insert(FMPDailyPrice).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "adj_close": stmt.excluded.adj_close,
            "volume": stmt.excluded.volume,
            "change_pct": stmt.excluded.change_pct,
            "vwap": stmt.excluded.vwap,
        },
    )

    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def _run(symbols: List[str], from_date: str, to_date: Optional[str]) -> Dict[str, int]:
    engine = create_async_engine(settings.async_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        results: Dict[str, int] = {}
        async with async_session() as session:
            for symbol in symbols:
                n = await ingest_symbol(session, symbol=symbol, from_date=from_date, to_date=to_date)
                results[str(symbol)] = int(n)
        return results
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest benchmark daily prices into Tier-1 price table")
    parser.add_argument(
        "--symbols",
        type=str,
        default="SPY",
        help="Comma-separated tickers to ingest (default: SPY).",
    )
    parser.add_argument(
        "--from-date",
        type=str,
        default="1995-01-01",
        help="Start date (YYYY-MM-DD). Default: 1995-01-01.",
    )
    parser.add_argument(
        "--to-date",
        type=str,
        default=None,
        help="Optional end date (YYYY-MM-DD). Default: none (provider max).",
    )

    args = parser.parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        raise SystemExit("No symbols provided.")

    results = asyncio.run(_run(symbols, args.from_date, args.to_date))
    for sym, n in results.items():
        print(f"{sym}: upserted {n} daily price rows into fmp_daily_prices")


if __name__ == "__main__":
    main()


