"""
PATH: backend/app/services/company_meta_service.py
PURPOSE: Company identity + valuation-range metadata for the universe UI.

Three sources, each with clear provenance:
1. Sharadar TICKERS — official name, industry, sector, size bucket, HQ
   (bulk-fetched once for the whole universe, cached 30 days on disk).
2. Paper panel CSV — triangulated fair-value lenses (fair_px_lo/med/hi),
   snapshot price and MoS, quadrant, cohort. These are the research run's
   own numbers — never recomputed here.
3. FMP profile — business description, website, quote-as-of price, 52w range,
   beta (per-ticker on demand, cached 30 days).

Nothing here invents a metric; this is identity + already-computed
valuation context that the UI was failing to surface.
"""

from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiohttp

from app.core.config import settings

# Docker mounts research data at /app/data; local checkout uses repo-root/data.
_DATA = Path("/app/data") if Path("/app/data").exists() else Path(__file__).resolve().parents[3] / "data"
PANEL_CSV = _DATA / "saas_ai_repricing" / "fundamental_value_run.csv"
DEFAULT_CACHE_DIR = _DATA / "company_meta_cache"
CACHE_DIR = DEFAULT_CACHE_DIR
CACHE_TTL_SECONDS = 30 * 24 * 3600

TICKERS_URL = "https://data.nasdaq.com/api/v3/datatables/SHARADAR/TICKERS"
FMP_PROFILE_URL = "https://financialmodelingprep.com/stable/profile"

_identity_cache: Optional[dict[str, dict]] = None
_identity_loaded_at: float = 0.0
_panel_cache: Optional[dict[str, dict]] = None
_profile_memory: dict[str, tuple[float, dict]] = {}


# ---------------------------------------------------------------------------
# Panel valuation lenses (paper research run — as computed, never recomputed)
# ---------------------------------------------------------------------------


def _runtime_cache_dir() -> Path:
    if CACHE_DIR != DEFAULT_CACHE_DIR:
        return CACHE_DIR
    return Path(os.environ.get("APP_RUNTIME_CACHE_DIR", "/tmp/rd-alpha-runtime-cache")) / (
        "company_meta_cache"
    )


def _cache_files(filename: str) -> list[Path]:
    return list(dict.fromkeys([_runtime_cache_dir() / filename, CACHE_DIR / filename]))


def _write_runtime_cache(filename: str, payload: dict[str, Any]) -> None:
    try:
        runtime_cache = _runtime_cache_dir()
        runtime_cache.mkdir(parents=True, exist_ok=True)
        (runtime_cache / filename).write_text(json.dumps(payload))
    except OSError:
        # Release data is deliberately read-only in production. Live metadata
        # is an overlay, never a mutation of the staged artifact.
        pass


def panel_valuation() -> dict[str, dict]:
    global _panel_cache
    if _panel_cache is not None:
        return _panel_cache
    out: dict[str, dict] = {}
    with PANEL_CSV.open() as f:
        for row in csv.DictReader(f):
            def num(k: str) -> Optional[float]:
                v = row.get(k)
                try:
                    return float(v) if v not in (None, "", "nan") else None
                except ValueError:
                    return None
            out[row["ticker"]] = {
                "fair_px_lo": num("fair_px_lo"),
                "fair_px_med": num("fair_px_med"),
                "fair_px_hi": num("fair_px_hi"),
                "price_snapshot": num("price_l"),
                "mos_snapshot": num("mos"),
                "quadrant": row.get("quadrant") or None,
                "cohort": row.get("cohort") or None,
                "wave": row.get("wave") or None,
                # Baseline and latest dates for period-based productivity labels.
                "fundamentals_baseline_as_of": row.get("date_b") or None,
                # The financial snapshot date for every fundamental below.
                "fundamentals_as_of": row.get("date_l") or None,
                "rev_cagr": num("rev_cagr"),
                "wacc": num("wacc"),
                # Fundamentals that drive the fair-value guide (panel as-of, never invented)
                "revenue_usd": num("revenueusd_l") or num("revenue_l"),
                "npm": num("npm_l"),
                "gm": num("gm_l"),
                "opm": num("opm_l"),
                "fcfm_sbc": num("fcfm_sbc_l"),
                "fcf_usd": num("fcf_sbc_usd_l"),
                "net_cash_usd": num("netcash_usd_l"),
                "ev_mult_usd": num("ev_mult"),
            }
    _panel_cache = out
    return out


# ---------------------------------------------------------------------------
# Sharadar TICKERS identity (bulk, cached)
# ---------------------------------------------------------------------------

async def identity_map(tickers: list[str]) -> dict[str, dict]:
    """ticker -> {name, industry, sector, size, location}.

    The cache is a MERGED map: only tickers not yet cached are fetched, so a
    single-ticker call can never shadow the full-universe map (and vice versa).
    """
    global _identity_cache, _identity_loaded_at

    if _identity_cache is None or time.monotonic() - _identity_loaded_at >= CACHE_TTL_SECONDS:
        _identity_cache = {}
        for cache_file in _cache_files("identity.json"):
            if not cache_file.exists():
                continue
            try:
                cached = json.loads(cache_file.read_text())
                fetched = datetime.fromisoformat(cached["fetched_at"])
                if (datetime.now(timezone.utc) - fetched).total_seconds() < CACHE_TTL_SECONDS:
                    _identity_cache = cached["map"]
                    break
            except Exception:
                continue
        _identity_loaded_at = time.monotonic()

    missing = [t.upper() for t in tickers if t.upper() not in _identity_cache]
    if not missing:
        return _identity_cache

    result: dict[str, dict] = dict(_identity_cache)
    if settings.NASDAQ_DATA_LINK_API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                # TICKERS accepts comma-separated tickers; batch to stay under URL limits
                for i in range(0, len(missing), 80):
                    batch = missing[i : i + 80]
                    params = {
                        "table": "SF1",
                        "ticker": ",".join(batch),
                        "qopts.columns": "ticker,name,exchange,sicsector,industry,scalemarketcap,location",
                        "api_key": settings.NASDAQ_DATA_LINK_API_KEY,
                    }
                    async with session.get(
                        TICKERS_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status != 200:
                            continue
                        payload = await resp.json()
                    table = payload.get("datatable") or {}
                    cols = [c["name"] for c in table.get("columns", [])]
                    for r in table.get("data", []):
                        d = dict(zip(cols, r))
                        result[d["ticker"]] = {
                            "name": (d.get("name") or "").title(),
                            "exchange": d.get("exchange"),
                            "sector": d.get("sicsector"),
                            "industry": d.get("industry"),
                            "size": d.get("scalemarketcap"),
                            "location": d.get("location"),
                        }
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError):
            # Identity is a current overlay. Missing it must not erase or block
            # a sealed-universe row when the provider is degraded.
            pass

    for t in missing:
        result.setdefault(t, {})  # negative-cache unresolved tickers

    _write_runtime_cache(
        "identity.json",
        {"fetched_at": datetime.now(timezone.utc).isoformat(), "map": result},
    )
    _identity_cache = result
    return result


# ---------------------------------------------------------------------------
# FMP profile (description etc.), per ticker on demand
# ---------------------------------------------------------------------------

async def company_profile(ticker: str) -> Optional[dict[str, Any]]:
    ticker = ticker.upper()
    hit = _profile_memory.get(ticker)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    for cache_file in _cache_files(f"profile_{ticker}.json"):
        if not cache_file.exists():
            continue
        try:
            cached = json.loads(cache_file.read_text())
            fetched = datetime.fromisoformat(cached["fetched_at"])
            if fetched.tzinfo is None:
                fetched = fetched.replace(tzinfo=timezone.utc)
            profile = {
                **(cached.get("profile") or {}),
                "price_as_of": fetched.isoformat(),
                "price_source": "FMP stable/profile",
                "price_stale": (
                    datetime.now(timezone.utc) - fetched
                ).total_seconds() >= CACHE_TTL_SECONDS,
            }
            # Require price_change so the universe table can show the daily move;
            # older caches without it are treated as stale.
            fresh = (datetime.now(timezone.utc) - fetched).total_seconds() < CACHE_TTL_SECONDS
            if fresh and profile.get("description") and "price_change" in profile:
                _profile_memory[ticker] = (time.monotonic(), profile)
                return profile
        except Exception:
            continue

    if not settings.FMP_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                FMP_PROFILE_URL,
                params={"symbol": ticker, "apikey": settings.FMP_API_KEY},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    return None
                rows = await resp.json()
    except Exception:
        return None
    if not rows:
        return None
    p = rows[0]
    profile = {
        "name": p.get("companyName"),
        "description": p.get("description"),
        "website": p.get("website"),
        "industry": p.get("industry"),
        "sector": p.get("sector"),
        "ceo": p.get("ceo"),
        "employees": p.get("fullTimeEmployees"),
        "ipo_date": p.get("ipoDate"),
        # This is a vendor quote at fetch time, never a promise of a
        # streaming/live exchange price.
        "price_live": p.get("price"),
        "price_change": p.get("change"),
        "price_change_pct": p.get("changePercentage"),
        "range_52w": p.get("range"),
        "beta": p.get("beta"),
        "market_cap": p.get("marketCap"),
        "source": "FMP stable/profile",
        "price_as_of": datetime.now(timezone.utc).isoformat(),
        "price_source": "FMP stable/profile",
        "price_stale": False,
    }
    _write_runtime_cache(
        f"profile_{ticker}.json",
        {"fetched_at": datetime.now(timezone.utc).isoformat(), "profile": profile},
    )
    _profile_memory[ticker] = (time.monotonic(), profile)
    return profile


# Curated one-liners for names the paper underwrites closely. Fallback is the
# first sentence of the FMP business description (cached), then industry.
_PRODUCT_BLURB: dict[str, str] = {
    "FRSH": "Sells customer-support SaaS seats; AI automation is the main narrative threat to seat demand.",
    "DOCU": "E-signature and agreement workflow SaaS; exposed to cheaper AI-assisted document flows.",
    "PCTY": "Payroll / HCM SaaS for mid-market employers.",
    "WDAY": "Enterprise HCM / finance SaaS.",
    "CRM": "Enterprise CRM cloud seats — large exposed incumbent in the AI-threat cohort.",
    "ADBE": "Creative-suite subscription software — exposed incumbent in the AI-threat cohort.",
    "NOW": "Workflow / ITSM cloud seats — exposed incumbent in the AI-threat cohort.",
    "SPSC": "Cloud supply-chain / EDI network connecting retailers and suppliers.",
    "PRGS": "Application software and infrastructure tools for enterprises (Progress Software).",
    "PATH": "Enterprise automation / RPA and AI agents platform (UiPath).",
    "DDOG": "Observability / monitoring cloud platform.",
    "SNOW": "Cloud data platform.",
    "MDB": "Developer data platform (MongoDB).",
    "CRWD": "Endpoint / cloud security platform.",
    "PANW": "Network and cloud security platform.",
    "ZS": "Cloud security (Zscaler).",
    "OKTA": "Identity and access management.",
    "TEAM": "Developer collaboration (Atlassian).",
    "INTU": "SMB / consumer tax and finance software.",
    "SHOP": "E-commerce platform for merchants.",
    "HUBS": "Inbound marketing / CRM SaaS.",
    "ZM": "Video meetings and collaboration.",
    "BILL": "AP/AR automation with payments adjacency.",
    "PAYC": "Payroll / HCM SaaS.",
    "MNDY": "Work-management SaaS.",
    "NICE": "Contact-center / customer-experience software.",
}


def _first_sentence(text: str, limit: int = 160) -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    for sep in (". ", "! ", "? "):
        i = text.find(sep)
        if 40 <= i <= limit:
            return text[: i + 1]
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def description_map(tickers: list[str], idmap: dict[str, dict]) -> dict[str, str]:
    """ticker -> one-line 'what they do'. Prefers curated blurbs, then cached
    FMP profile first sentence, then industry fallback. Disk-only — never blocks
    a rank call on an outbound FMP request."""
    out: dict[str, str] = {}
    # Load any already-cached FMP profiles in one pass
    cached: dict[str, dict] = {}
    cache_dirs = list(dict.fromkeys([_runtime_cache_dir(), CACHE_DIR]))
    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue
        for p in cache_dir.glob("profile_*.json"):
            try:
                payload = json.loads(p.read_text())
                prof = payload.get("profile") or {}
                t = p.stem.replace("profile_", "").upper()
                cached[t] = prof
            except Exception:
                continue

    for t in tickers:
        t = t.upper()
        if t in _PRODUCT_BLURB:
            out[t] = _PRODUCT_BLURB[t]
            continue
        prof = cached.get(t) or {}
        blurb = _first_sentence(prof.get("description") or "")
        if blurb:
            out[t] = blurb
            continue
        industry = (idmap.get(t) or {}).get("industry") or (prof.get("industry") or "Software")
        industry = industry.replace("Software - ", "")
        size = (idmap.get(t) or {}).get("size") or ""
        size_bit = f", {size.split(' - ')[-1].lower()} cap" if size else ""
        out[t] = f"{industry} company{size_bit}."
    return out


def live_price_from_mos(fair_med: Optional[float], mos_live: Optional[float]) -> Optional[float]:
    """Invert mos_live = fair_med / price − 1 → price = fair_med / (1 + mos)."""
    if fair_med is None or mos_live is None:
        return None
    denom = 1.0 + mos_live
    if denom <= 0:
        return None
    return fair_med / denom
