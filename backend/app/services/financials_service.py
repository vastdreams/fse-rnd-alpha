"""
PATH: backend/app/services/financials_service.py
PURPOSE: Year-on-year financial statements + key ratios per company
(Yahoo-Finance / SimplyWallSt-style depth), sourced from Sharadar SF1.

Provenance rules:
- Values are AS REPORTED by Sharadar (dimension MRY = most-recent annual,
  MRQ = most-recent quarterly). We never compute or impute a statement line.
- Every payload carries calendardate (period end) and datekey (filing/PIT
  availability date) per row, plus fetched_at for the cache.
- Derived fields we DO compute are labelled `derived_` (YoY growth only) and
  are pure arithmetic on adjacent as-reported rows.

Caching: SF1 history changes at most quarterly, so responses are cached on
disk for 7 days (data/financials_cache/) and in-process for the server's
lifetime. This keeps the company page fast and the API quota untouched.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

from app.core.config import settings

SF1_URL = "https://data.nasdaq.com/api/v3/datatables/SHARADAR/SF1"

# Statement lines and ratios pulled as-reported from SF1
SF1_COLUMNS = [
    "calendardate", "datekey",
    # income statement
    "revenue", "gp", "opex", "rnd", "sgna", "opinc", "ebitda", "netinc", "epsdil",
    # cash flow
    "ncfo", "capex", "fcf", "sbcomp",
    # balance sheet
    "assets", "equity", "debt", "cashnequsd", "liabilities",
    # margins & returns
    "grossmargin", "netmargin", "ebitdamargin", "roa", "roe", "roic", "ros",
    # health & valuation
    "de", "currentratio", "pe", "ps", "pb", "divyield", "payoutratio",
    "shareswadil", "marketcap", "ev",
]

CACHE_TTL_SECONDS = 7 * 24 * 3600

# Docker mounts host data at /app/data. parents[3] from /app/app/services/*.py
# resolves to filesystem root (/data) and PermissionError → HTTP 500.
_DATA = Path("/app/data") if Path("/app/data").exists() else Path(__file__).resolve().parents[3] / "data"
DEFAULT_CACHE_DIR = _DATA / "financials_cache"
CACHE_DIR = DEFAULT_CACHE_DIR

_memory_cache: dict[str, tuple[float, dict]] = {}


class FinancialsUnavailable(Exception):
    pass


def _runtime_cache_dir() -> Path:
    if CACHE_DIR != DEFAULT_CACHE_DIR:
        return CACHE_DIR
    return Path(os.environ.get("APP_RUNTIME_CACHE_DIR", "/tmp/rd-alpha-runtime-cache")) / (
        "financials_cache"
    )


def _cache_files(ticker: str) -> list[Path]:
    filename = f"{ticker}.json"
    return list(dict.fromkeys([_runtime_cache_dir() / filename, CACHE_DIR / filename]))


def _growth(rows: list[dict], field: str) -> None:
    """Attach derived_<field>_yoy to each row (pure arithmetic, labelled derived)."""
    for prev, cur in zip(rows, rows[1:]):
        p, c = prev.get(field), cur.get(field)
        if p and c is not None and p != 0:
            cur[f"derived_{field}_yoy"] = round((c - p) / abs(p), 4)


async def _fetch_sf1(session: aiohttp.ClientSession, ticker: str, dimension: str) -> list[dict]:
    params = {
        "ticker": ticker,
        "dimension": dimension,
        "qopts.columns": ",".join(SF1_COLUMNS),
        "api_key": settings.NASDAQ_DATA_LINK_API_KEY,
    }
    async with session.get(SF1_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        if resp.status != 200:
            raise FinancialsUnavailable(f"SF1 {dimension} HTTP {resp.status}")
        payload = await resp.json()
    table = payload.get("datatable") or {}
    cols = [c["name"] for c in table.get("columns", [])]
    rows = [dict(zip(cols, r)) for r in table.get("data", [])]
    rows.sort(key=lambda r: r.get("calendardate") or "")
    return rows


async def get_financials(ticker: str) -> dict[str, Any]:
    """Annual (full history) + quarterly (last 8) statements with derived YoY."""
    ticker = ticker.upper()

    hit = _memory_cache.get(ticker)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    for cache_file in _cache_files(ticker):
        if not cache_file.exists():
            continue
        try:
            cached = json.loads(cache_file.read_text())
            fetched = datetime.fromisoformat(cached["fetched_at"])
            if (datetime.now(timezone.utc) - fetched).total_seconds() < CACHE_TTL_SECONDS:
                _memory_cache[ticker] = (time.monotonic(), cached)
                return cached
        except Exception:
            continue  # corrupt cache → try the next layer or refetch

    if not settings.NASDAQ_DATA_LINK_API_KEY:
        raise FinancialsUnavailable("NASDAQ_DATA_LINK_API_KEY not configured")

    async with aiohttp.ClientSession() as session:
        annual = await _fetch_sf1(session, ticker, "MRY")
        quarterly = (await _fetch_sf1(session, ticker, "MRQ"))[-8:]

    if not annual:
        raise FinancialsUnavailable(f"No Sharadar SF1 coverage for {ticker}")

    for field in ("revenue", "gp", "opinc", "netinc", "fcf", "rnd", "epsdil"):
        _growth(annual, field)

    result = {
        "ticker": ticker,
        "source": "Sharadar SF1 (as reported; dimension MRY annual / MRQ quarterly)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "n_years": len(annual),
        "annual": annual,
        "quarterly": quarterly,
        "note": "Statement values are as reported — never computed or imputed. "
                "derived_*_yoy fields are pure arithmetic on adjacent reported rows.",
    }
    try:
        runtime_cache = _runtime_cache_dir()
        runtime_cache.mkdir(parents=True, exist_ok=True)
        (runtime_cache / f"{ticker}.json").write_text(json.dumps(result))
    except OSError:
        pass
    _memory_cache[ticker] = (time.monotonic(), result)
    return result
