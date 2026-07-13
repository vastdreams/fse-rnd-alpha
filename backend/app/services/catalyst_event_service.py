"""
PATH: backend/app/services/catalyst_event_service.py
PURPOSE: Fetch + cache dated catalyst events (FMP press/earnings/news) per ticker.

L1 anchors for close-call load from this cache (and optional DB claims).
Never invents headlines — empty API = empty anchors = UNKNOWN catalyst.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings

_DATA = Path("/app/data") if Path("/app/data").exists() else Path(__file__).resolve().parents[3] / "data"
DEFAULT_CACHE_DIR = _DATA / "catalyst_event_cache"
CACHE_DIR = DEFAULT_CACHE_DIR
CACHE_TTL_SECONDS = 7 * 24 * 3600
ENGINE_VERSION = "catalyst_events_v1"

_memory: dict[str, tuple[float, dict]] = {}


def _runtime_cache_dir() -> Path:
    # Mounted release data is immutable in production. Tests can monkeypatch
    # CACHE_DIR and still exercise a single local cache directory.
    if CACHE_DIR != DEFAULT_CACHE_DIR:
        return CACHE_DIR
    return Path(os.environ.get("APP_RUNTIME_CACHE_DIR", "/tmp/rd-alpha-runtime-cache")) / (
        "catalyst_event_cache"
    )


def _cache_files(ticker: str) -> list[Path]:
    filename = f"{ticker}.json"
    paths = [_runtime_cache_dir() / filename, CACHE_DIR / filename]
    return list(dict.fromkeys(paths))


def _iso_date(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # FMP may return "2025-11-12 16:00:00" or ISO with Z. A quarter label
    # (or any other approximation) is not a dated catalyst anchor.
    candidate = s[:10]
    try:
        date.fromisoformat(candidate)
    except ValueError:
        return None
    return candidate


def normalize_fmp_events(
    ticker: str,
    *,
    press: list[dict] | None = None,
    earnings: list[dict] | None = None,
    news: list[dict] | None = None,
) -> list[dict[str, Any]]:
    """Normalize FMP payloads into close-call anchor rows."""
    t = ticker.upper()
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(kind: str, date_s: Optional[str], title: str, locator: str, source: str, role: str = "event") -> None:
        if not date_s or not title:
            return
        key = (kind, date_s, title[:80])
        if key in seen:
            return
        seen.add(key)
        out.append(
            {
                "ticker": t,
                "date": date_s,
                "kind": kind,
                "title": title.strip()[:300],
                "locator": locator or f"fmp:{kind}:{t}:{date_s}",
                "source": source,
                "role": role,
            }
        )

    for row in press or []:
        title = str(row.get("title") or row.get("text") or "").strip()
        if not title:
            continue
        add(
            "press_coverage",
            _iso_date(row.get("publishedDate") or row.get("date")),
            title,
            str(row.get("url") or row.get("link") or ""),
            "fmp_press_releases",
            role="press",
        )

    for row in earnings or []:
        date_s = _iso_date(row.get("date") or row.get("filingDate") or row.get("acceptedDate"))
        eps = row.get("epsActual")
        est = row.get("epsEstimated")
        parts = ["Earnings announcement"]
        if eps is not None:
            parts.append(f"EPS actual={eps}")
        if est is not None:
            parts.append(f"est={est}")
        add(
            "earnings_release",
            date_s,
            "; ".join(parts),
            f"https://financialmodelingprep.com/stable/earnings?symbol={t}",
            "fmp_earnings",
            role="earnings",
        )

    for row in news or []:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        add(
            "press_coverage",
            _iso_date(row.get("publishedDate") or row.get("date")),
            title,
            str(row.get("url") or row.get("link") or ""),
            "fmp_stock_news",
            role="news_secondary",
        )

    out.sort(key=lambda a: a["date"], reverse=True)
    return out


def anchors_from_claim_locator(value_text: str, excerpt_locator: Any) -> Optional[dict[str, Any]]:
    """Rebuild an L1 anchor row from an evidence_claims catalyst_anchor row."""
    meta: dict[str, Any] = {}
    if isinstance(excerpt_locator, dict):
        meta = excerpt_locator
    elif isinstance(excerpt_locator, str) and excerpt_locator.strip():
        try:
            meta = json.loads(excerpt_locator)
        except json.JSONDecodeError:
            meta = {}
    date_s = str(meta.get("date") or "")[:10]
    if not date_s:
        return None
    try:
        date.fromisoformat(date_s)
    except ValueError:
        return None
    return {
        "ticker": str(meta.get("ticker") or "").upper() or None,
        "date": date_s,
        "kind": meta.get("kind") or "press_coverage",
        "title": value_text or meta.get("title") or "Catalyst event",
        "locator": meta.get("locator") or "",
        "source": meta.get("source") or "evidence_claims",
        "role": meta.get("role") or "event",
    }


def load_catalyst_anchors_from_db_rows(rows: list[Any]) -> dict[str, list[dict[str, Any]]]:
    """Group DB claim rows into ticker → anchor list."""
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        # support Row / tuple / mapping
        if hasattr(r, "_mapping"):
            m = dict(r._mapping)
        elif isinstance(r, dict):
            m = r
        else:
            m = {"ticker": r[0], "value_text": r[1], "excerpt_locator": r[2]}
        t = str(m.get("ticker") or "").upper()
        if not t:
            continue
        anchor = anchors_from_claim_locator(m.get("value_text") or "", m.get("excerpt_locator"))
        if not anchor:
            continue
        anchor["ticker"] = t
        out.setdefault(t, []).append(anchor)
    return out


def load_cached_anchors(ticker: str, *, allow_stale: bool = True) -> list[dict[str, Any]]:
    """Return cached anchors for a ticker (no network).

    L1 prefers any on-disk anchors over UNKNOWN; refresh uses TTL via fetch path.
    """
    payload = _read_cache(ticker.upper(), allow_stale=allow_stale)
    if not payload:
        return []
    return list(payload.get("anchors") or [])


def _read_cache(ticker: str, *, allow_stale: bool = False) -> Optional[dict]:
    hit = _memory.get(ticker)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    for cache_file in _cache_files(ticker):
        if not cache_file.exists():
            continue
        try:
            cached = json.loads(cache_file.read_text())
            fetched = datetime.fromisoformat(cached["fetched_at"])
            stale = (datetime.now(timezone.utc) - fetched).total_seconds() >= CACHE_TTL_SECONDS
            if stale and not allow_stale:
                continue
            if not stale:
                _memory[ticker] = (time.monotonic(), cached)
            return cached
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return None


def write_cache(ticker: str, anchors: list[dict[str, Any]], *, raw: Optional[dict] = None) -> dict:
    runtime_cache = _runtime_cache_dir()
    payload = {
        "ticker": ticker.upper(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": ENGINE_VERSION,
        "n": len(anchors),
        "anchors": anchors,
        "raw": raw or {},
    }
    try:
        runtime_cache.mkdir(parents=True, exist_ok=True)
        (runtime_cache / f"{ticker.upper()}.json").write_text(json.dumps(payload))
    except OSError:
        # A current overlay is best-effort; immutable release data must never
        # be rewritten just because a refresh could not be persisted.
        pass
    _memory[ticker.upper()] = (time.monotonic(), payload)
    return payload


async def fetch_and_cache_ticker(
    ticker: str,
    *,
    include_news: bool = True,
    fmp_retries: int = 3,
) -> dict:
    """Pull FMP event endpoints and write the catalyst cache for one ticker.

    Merges with any existing on-disk anchors (e.g. SEC) so a rate-limited
    FMP miss never wipes prior coverage.
    """
    from app.services.fmp_client import FMPClient

    t = ticker.upper()
    existing = load_cached_anchors(t, allow_stale=True)
    if not settings.FMP_API_KEY:
        return write_cache(t, existing, raw={"error": "FMP_API_KEY not configured"})

    press: list = []
    earnings: list = []
    news: list = []
    errors: list[str] = []
    async with FMPClient(api_key=settings.FMP_API_KEY) as client:
        try:
            press = await client.get_press_releases(t, retries=fmp_retries)
        except Exception as e:
            errors.append(f"press:{e}")
        try:
            earnings = await client.get_earnings(t, retries=fmp_retries)
        except Exception as e:
            errors.append(f"earnings:{e}")
        if include_news:
            try:
                news = await client.get_stock_news(t, retries=fmp_retries)
            except Exception as e:
                errors.append(f"news:{e}")

    # Prefer press + earnings for L1; keep news but mark secondary
    fmp_anchors = normalize_fmp_events(
        t, press=press, earnings=earnings, news=news if include_news else []
    )
    # Keep prior SEC/etc; do not drop on empty FMP
    merged = merge_anchor_lists(fmp_anchors, existing)
    return write_cache(
        t,
        merged,
        raw={
            "press_n": len(press or []),
            "earnings_n": len(earnings or []),
            "news_n": len(news or []),
            "errors": errors,
            "fmp_n": len(fmp_anchors),
            "kept_existing_n": len(existing),
        },
    )


def merge_anchor_lists(*lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate anchors by (kind, date, title prefix)."""
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for lst in lists:
        for a in lst:
            key = (a.get("kind", ""), a.get("date", ""), str(a.get("title", ""))[:80])
            if key in seen or not a.get("date"):
                continue
            seen.add(key)
            out.append(a)
    out.sort(key=lambda a: a["date"], reverse=True)
    return out


def lookback_since(years: float = 2.0) -> str:
    d = datetime.now(timezone.utc).date() - timedelta(days=int(365 * years))
    return d.isoformat()
