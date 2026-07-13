"""
PATH: backend/app/services/price_history_service.py
PURPOSE: Day-by-day adjusted close history for company charts (Sharadar SEP).

Cached on disk for 1 day — price history only needs a daily refresh. Never
invents prices; returns as-reported SEP closeadj (falls back to close).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import aiohttp

from app.core.config import settings

SEP_URL = "https://data.nasdaq.com/api/v3/datatables/SHARADAR/SEP"
_DATA = Path("/app/data") if Path("/app/data").exists() else Path(__file__).resolve().parents[3] / "data"
DEFAULT_CACHE_DIR = _DATA / "price_history_cache"
CACHE_DIR = DEFAULT_CACHE_DIR
CACHE_TTL_SECONDS = 24 * 3600
DEFAULT_LOOKBACK_DAYS = 365 * 3  # 3 years of daily bars

_memory: dict[str, tuple[float, dict]] = {}


class PriceHistoryUnavailable(Exception):
    pass


def _runtime_cache_dir() -> Path:
    if CACHE_DIR != DEFAULT_CACHE_DIR:
        return CACHE_DIR
    return Path(os.environ.get("APP_RUNTIME_CACHE_DIR", "/tmp/rd-alpha-runtime-cache")) / (
        "price_history_cache"
    )


def _cache_files(cache_key: str) -> list[Path]:
    filename = f"{cache_key}.json"
    return list(dict.fromkeys([_runtime_cache_dir() / filename, CACHE_DIR / filename]))


def _annotate_cache(payload: dict[str, Any], *, stale: bool) -> dict[str, Any]:
    """Expose price provenance without relabeling a daily bar as streaming."""

    return {
        **payload,
        "price_as_of": payload.get("end"),
        "price_source": "Sharadar SEP adjusted close",
        "cache_stale": stale,
    }


def get_cached_price_history(
    ticker: str,
    years: int = 3,
    *,
    allow_stale: bool = True,
    immutable_only: bool = False,
) -> Optional[dict[str, Any]]:
    """Return a local SEP snapshot without making a network request.

    Universe-wide stance screens may touch hundreds of tickers. They must not
    fan out into one remote request per company: a missing cache is an
    explicit UNKNOWN tape stage, not a reason to block the whole table.

    Stale files are preferred over UNKNOWN for L0 (refresh job owns freshness).
    """

    ticker = ticker.upper()
    lookback = max(1, min(years, 10)) * 365
    cache_key = f"{ticker}_{lookback}"
    memory_key = f"{cache_key}|immutable" if immutable_only else cache_key

    hit = _memory.get(memory_key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    cache_files = (
        [CACHE_DIR / f"{cache_key}.json"] if immutable_only else _cache_files(cache_key)
    )
    for cache_file in cache_files:
        if not cache_file.exists():
            continue
        try:
            cached = json.loads(cache_file.read_text())
            fetched = datetime.fromisoformat(cached["fetched_at"])
            stale = (datetime.now(timezone.utc) - fetched).total_seconds() >= CACHE_TTL_SECONDS
            if stale and not allow_stale:
                continue
            annotated = _annotate_cache(cached, stale=stale)
            if not stale:
                _memory[memory_key] = (time.monotonic(), annotated)
            return annotated
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return None


async def get_price_history(ticker: str, years: int = 3) -> dict[str, Any]:
    ticker = ticker.upper()
    lookback = max(1, min(years, 10)) * 365
    cache_key = f"{ticker}_{lookback}"

    hit = _memory.get(cache_key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    cached = get_cached_price_history(ticker, years=years, allow_stale=False)
    if cached is not None:
        return cached

    if not settings.NASDAQ_DATA_LINK_API_KEY:
        stale_cached = get_cached_price_history(ticker, years=years, allow_stale=True)
        if stale_cached is not None:
            return stale_cached
        raise PriceHistoryUnavailable("NASDAQ_DATA_LINK_API_KEY not configured")

    start = (datetime.now(timezone.utc).date() - timedelta(days=lookback)).isoformat()
    rows: list[dict] = []
    cursor: Optional[str] = None
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                params: dict[str, Any] = {
                    "ticker": ticker,
                    "date.gte": start,
                    "qopts.columns": "ticker,date,closeadj,close,volume",
                    "api_key": settings.NASDAQ_DATA_LINK_API_KEY,
                }
                if cursor:
                    params["qopts.cursor_id"] = cursor
                async with session.get(
                    SEP_URL, params=params, timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        raise PriceHistoryUnavailable(f"SEP HTTP {resp.status}")
                    payload = await resp.json()
                table = payload.get("datatable") or {}
                cols = [c["name"] for c in table.get("columns", [])]
                for r in table.get("data", []):
                    d = dict(zip(cols, r))
                    px = d.get("closeadj") if d.get("closeadj") is not None else d.get("close")
                    if px is None or not d.get("date"):
                        continue
                    try:
                        close = float(px)
                    except (TypeError, ValueError):
                        continue
                    rows.append({"date": d["date"], "close": close, "volume": d.get("volume")})
                cursor = (payload.get("meta") or {}).get("next_cursor_id")
                if not cursor:
                    break
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
        stale_cached = get_cached_price_history(ticker, years=years, allow_stale=True)
        if stale_cached is not None:
            return stale_cached
        raise PriceHistoryUnavailable("Sharadar SEP is temporarily unavailable") from exc

    rows.sort(key=lambda r: r["date"])
    if not rows:
        raise PriceHistoryUnavailable(f"No SEP price history for {ticker}")

    result = {
        "ticker": ticker,
        "source": "Sharadar SEP (adjusted close)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "n": len(rows),
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "last": rows[-1]["close"],
        "bars": rows,
        "price_as_of": rows[-1]["date"],
        "price_source": "Sharadar SEP adjusted close",
        "cache_stale": False,
        "note": "Daily adjusted closes as of price_as_of; not a streaming/live quote. "
                "Fair-value guide overlays come from the paper run.",
    }
    try:
        runtime_cache = _runtime_cache_dir()
        runtime_cache.mkdir(parents=True, exist_ok=True)
        (runtime_cache / f"{cache_key}.json").write_text(json.dumps(result))
    except OSError:
        # Dynamic quote overlays must not mutate the sealed release tree.
        pass
    _memory[cache_key] = (time.monotonic(), result)
    return result
