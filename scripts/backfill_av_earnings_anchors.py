#!/usr/bin/env python3
"""
PATH: scripts/backfill_av_earnings_anchors.py
PURPOSE: Enrich catalyst store with verified Alpha Vantage EARNINGS reported
  dates. Transcript quarter labels are observed for coverage only: they never
  become catalyst anchors because they do not establish an event date.

Writes:
  - data/catalyst_event_cache/{TICKER}.json (merged with existing SEC/etc)
  - source_snapshots + evidence_claims (field=catalyst_anchor)

Usage:
  python scripts/backfill_av_earnings_anchors.py --universe-version univ_...
    [--skip-api]   # validate/clean cached anchors without AV HTTP
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.core.config import settings  # noqa: E402
from app.services.catalyst_event_service import (  # noqa: E402
    load_cached_anchors,
    merge_anchor_lists,
    write_cache,
)


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def normalize_av_earnings(ticker: str, payload: dict) -> list[dict]:
    """Alpha Vantage EARNINGS → anchor rows (reported dates only)."""
    t = ticker.upper()
    out: list[dict] = []
    for row in payload.get("quarterlyEarnings") or []:
        d = str(row.get("reportedDate") or "")[:10]
        if not d:
            continue
        try:
            date.fromisoformat(d)
        except ValueError:
            continue
        eps = row.get("reportedEPS")
        title = "Earnings announcement"
        if eps is not None and str(eps) not in ("", "None"):
            title = f"Earnings announcement; EPS actual={eps}"
        out.append(
            {
                "ticker": t,
                "date": d,
                "kind": "earnings_release",
                "title": title[:300],
                "locator": f"alphavantage:EARNINGS:{t}:{d}",
                "source": "alphavantage_earnings",
                "role": "earnings",
            }
        )
    return out


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


async def _transcript_quarters(conn, ticker: str) -> list[str]:
    rows = await conn.fetch(
        "SELECT quarter FROM av_transcripts_raw WHERE symbol=$1 AND n_segments>0 "
        "ORDER BY quarter DESC LIMIT 12",
        ticker,
    )
    return [r["quarter"] for r in rows]


async def _upsert_claims(anchors_by_ticker: dict[str, list[dict]]) -> int:
    import asyncpg

    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    snaps = []
    claims = []
    for ticker, anchors in anchors_by_ticker.items():
        for a in anchors:
            if a.get("source") != "alphavantage_earnings":
                continue
            d = a["date"]
            locator = a.get("locator") or f"{a.get('source')}:{ticker}:{d}"
            content = f"{ticker}|{a.get('kind')}|{d}|{a.get('title')}|{locator}"
            snap_id = "snap_" + _sha(content)[:24]
            claim_id = "cl_" + _sha(content + "|catalyst_anchor")[:24]
            as_of = date.fromisoformat(d)
            snaps.append(
                (
                    snap_id,
                    "earnings_release",
                    ticker,
                    as_of,
                    as_of,
                    now,
                    locator,
                    _sha(content),
                    f"catalyst_anchor source={a.get('source')} role={a.get('role')}",
                )
            )
            claims.append(
                (
                    claim_id,
                    snap_id,
                    ticker,
                    "catalyst_anchor",
                    a.get("title") or "",
                    None,
                    None,
                    None,
                    json.dumps(
                        {
                            "date": d,
                            "kind": a.get("kind"),
                            "locator": locator,
                            "source": a.get("source"),
                            "role": a.get("role"),
                        }
                    ),
                    "av_earnings_backfill_v1",
                    now,
                )
            )
    if not snaps:
        return 0
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            await conn.executemany(
                """INSERT INTO source_snapshots
                   (snapshot_id, kind, ticker, as_of_date, available_date, fetched_at, locator, content_sha256, notes)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                   ON CONFLICT (snapshot_id) DO NOTHING""",
                snaps,
            )
            await conn.executemany(
                """INSERT INTO evidence_claims
                   (claim_id, snapshot_id, ticker, field, value_text, value_numeric, operator, unit,
                    excerpt_locator, extractor, extracted_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                   ON CONFLICT (claim_id) DO NOTHING""",
                claims,
            )
    finally:
        await conn.close()
    return len(claims)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--universe-version",
        required=True,
        help="Sealed universe version whose tickers this backfill must cover",
    )
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ticker", type=str, default="")
    ap.add_argument("--skip-api", action="store_true", help="DB transcripts only")
    ap.add_argument("--sleep", type=float, default=0.85)
    ap.add_argument(
        "--allow-partial",
        action="store_true",
        help="Permit --ticker/--limit probes and incomplete coverage (never use for a release).",
    )
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

    print(
        f"universe={args.universe_version} n={len(tickers)} universe_n={len(universe_tickers)} "
        f"av_key={'yes' if settings.ALPHAVANTAGE_API_KEY else 'NO'} skip_api={args.skip_api}",
        flush=True,
    )

    import asyncpg
    from saas_ai.clients import AlphaVantageClient

    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)

    by_ticker: dict[str, list[dict]] = {}
    with_any = 0
    covered: set[str] = set()
    transcript_quarters_observed = 0
    t0 = time.time()
    av = None
    try:
        if not args.skip_api and settings.ALPHAVANTAGE_API_KEY:
            av = AlphaVantageClient(settings.ALPHAVANTAGE_API_KEY, calls_per_min=70)
            await av.__aenter__()

        for i, t in enumerate(tickers, 1):
            existing = load_cached_anchors(t, allow_stale=True)
            av_anchors: list[dict] = []
            qs: list[str] = []
            try:
                qs = await _transcript_quarters(conn, t)
                transcript_quarters_observed += len(qs)
            except Exception as e:
                print(f"  transcript miss {t}: {e}", flush=True)
            if av is not None:
                try:
                    payload = await av.fundamental(t, "EARNINGS")
                    if isinstance(payload, dict) and "quarterlyEarnings" in payload:
                        av_anchors = normalize_av_earnings(t, payload)
                except Exception as e:
                    print(f"  AV miss {t}: {e}", flush=True)
            # Approximate transcript quarter dates never qualify as catalysts.
            # Remove any legacy synthetic transcript anchors while preserving
            # verified SEC/IR/FMP/AV anchors already in the cache.
            verified_existing = [
                anchor for anchor in existing if anchor.get("source") != "av_transcripts_raw"
            ]
            merged = merge_anchor_lists(verified_existing, av_anchors)
            write_cache(
                t,
                merged,
                raw={
                    "av_earnings_n": len(av_anchors),
                    "transcript_quarters_observed": len(qs),
                    "merged_n": len(merged),
                },
            )
            by_ticker[t] = merged
            if merged:
                with_any += 1
                covered.add(t)
            if i % 25 == 0 or i == len(tickers) or i <= 3:
                print(
                    f"[{i}/{len(tickers)}] enriched={with_any} "
                    f"elapsed={time.time()-t0:.0f}s last={t} "
                    f"av={len(av_anchors)} transcript_quarters={len(qs)} n={len(merged)}",
                    flush=True,
                )
            if av is not None:
                await asyncio.sleep(args.sleep)
    finally:
        if av is not None:
            await av.__aexit__(None, None, None)
        await conn.close()

    claim_n = await _upsert_claims(by_ticker)
    report = {
        "kind": "av_earnings_anchors",
        "universe_version": args.universe_version,
        "universe_tickers": len(universe_tickers),
        "selected_tickers": len(tickers),
        "n_with_anchors": with_any,
        "missing_tickers": sorted(set(universe_tickers) - covered),
        "coverage_pct": round(100.0 * len(covered) / len(universe_tickers), 1),
        "allow_partial": args.allow_partial,
        "n_claims_attempted": claim_n,
        "transcript_quarters_observed": transcript_quarters_observed,
        "elapsed_s": round(time.time() - t0, 1),
        "skip_api": args.skip_api,
    }
    out = (
        ROOT
        / "data"
        / "catalyst_event_cache"
        / f"_av_earnings_report_{args.universe_version.replace('/', '_')}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    if report["missing_tickers"] and not args.allow_partial:
        raise SystemExit(
            f"Alpha Vantage catalyst coverage is incomplete for sealed universe "
            f"{args.universe_version}: {len(report['missing_tickers'])} ticker(s) missing"
        )


if __name__ == "__main__":
    asyncio.run(main())
