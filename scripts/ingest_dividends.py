#!/usr/bin/env python3
"""
PATH: scripts/ingest_dividends.py
PURPOSE:
  Ingest dividend events (ex-dividend dates) from Financial Modeling Prep (FMP) into `fmp_dividends`.

WHY:
  Our Tier-1 daily price ingestion uses the FMP *stable* EOD endpoint which provides split-adjusted
  close prices but does NOT provide vendor `adjClose` (dividend-adjusted close). For publication-grade
  return construction, we therefore ingest dividends separately and combine them with split-adjusted
  closes to compute a total-return proxy in `july_june_returns`.

FLOW:
  ┌───────────────────────────────┐
  │ Discover symbols (Tier-1)     │
  └───────────────┬───────────────┘
                  ▼
  ┌───────────────────────────────┐
  │ Fetch dividends (FMP stable)  │
  └───────────────┬───────────────┘
                  ▼
  ┌───────────────────────────────┐
  │ Upsert rows into fmp_dividends│
  └───────────────────────────────┘

DEPENDENCIES:
  - `FMP_API_KEY` env var (passed into backend container)
  - Postgres (via `DATABASE_URL` / settings)
  - backend modules:
      - app.services.fmp_client.FMPClient
      - app.db.models.FMPDailyPrice
      - app.db.models.FMPDividend
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Make `backend/app` importable as `app.*`
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.models import FMPDailyPrice, FMPDividend
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


async def _get_symbols(session: AsyncSession) -> List[str]:
    result = await session.execute(select(func.distinct(FMPDailyPrice.symbol)))
    symbols = [str(r[0]).upper() for r in result.fetchall() if r and r[0]]
    symbols = sorted(set(symbols))
    return symbols


async def ingest_symbol_dividends(
    session: AsyncSession,
    *,
    client: FMPClient,
    symbol: str,
) -> int:
    dividends = await client.get_dividends(symbol)
    if not dividends:
        return 0

    rows: List[Dict[str, Any]] = []
    for rec in dividends:
        if not isinstance(rec, dict):
            continue
        dt = _parse_iso_date(rec.get("date"))
        if not dt:
            continue

        rows.append(
            {
                "symbol": str(symbol).upper(),
                "date": dt,
                "dividend": _coerce_float(rec.get("dividend")),
                "adj_dividend": _coerce_float(rec.get("adjDividend")),
                "declaration_date": _parse_iso_date(rec.get("declarationDate")),
                "record_date": _parse_iso_date(rec.get("recordDate")),
                "payment_date": _parse_iso_date(rec.get("paymentDate")),
                "frequency": rec.get("frequency") if isinstance(rec.get("frequency"), str) else None,
                "yield_pct": _coerce_float(rec.get("yield")),
            }
        )

    if not rows:
        return 0

    stmt = pg_insert(FMPDividend).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "date"],
        set_={
            "dividend": stmt.excluded.dividend,
            "adj_dividend": stmt.excluded.adj_dividend,
            "declaration_date": stmt.excluded.declaration_date,
            "record_date": stmt.excluded.record_date,
            "payment_date": stmt.excluded.payment_date,
            "frequency": stmt.excluded.frequency,
            "yield_pct": stmt.excluded.yield_pct,
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def _run(symbols: Optional[List[str]]) -> Dict[str, int]:
    engine = create_async_engine(settings.async_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            if not symbols:
                symbols = await _get_symbols(session)
            if not symbols:
                raise SystemExit("No symbols found (is `fmp_daily_prices` populated?).")

            results: Dict[str, int] = {}
            async with FMPClient() as client:
                for sym in symbols:
                    n = await ingest_symbol_dividends(session, client=client, symbol=sym)
                    results[sym] = int(n)
            return results
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest dividend events into fmp_dividends (Tier-1)")
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Optional comma-separated tickers (e.g., SPY,AAPL). Default: all symbols in fmp_daily_prices.",
    )
    args = parser.parse_args()

    symbols = None
    if isinstance(args.symbols, str) and args.symbols.strip():
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    results = asyncio.run(_run(symbols))
    total = sum(results.values())
    print(f"Upserted {total} dividend rows into fmp_dividends across {len(results)} symbols.")


if __name__ == "__main__":
    main()


