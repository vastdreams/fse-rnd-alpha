#!/usr/bin/env python3
"""
PATH: scripts/backfill_catalyst_anchors.py
PURPOSE: Universe-wide catalyst event backfill (FMP + SEC EDGAR) into
  data/catalyst_event_cache + source_snapshots/evidence_claims.

Usage:
  cd backend && python3 ../scripts/backfill_catalyst_anchors.py \
    --universe-version univ_...

The backfill targets a named sealed universe. Partial probes and empty-anchor
results require explicit opt-in so release automation cannot silently treat
unknown catalyst coverage as complete.
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
    fetch_and_cache_ticker,
    lookback_since,
    merge_anchor_lists,
    write_cache,
)
from saas_ai.analysis import sec_edgar  # noqa: E402


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _kind_for_db(kind: str) -> str:
    if kind == "earnings_release":
        return "earnings_release"
    if kind == "8-K":
        return "8-K"
    # press / news → allowed enum slot with notes
    return "fmp_quote"


async def _tickers_from_db(universe_version: str) -> list[str]:
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


async def _upsert_claims(anchors_by_ticker: dict[str, list[dict]]) -> int:
    import asyncpg

    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    snaps = []
    claims = []
    for ticker, anchors in anchors_by_ticker.items():
        for a in anchors:
            d = a["date"]
            locator = a.get("locator") or f"{a.get('source')}:{ticker}:{d}"
            content = f"{ticker}|{a.get('kind')}|{d}|{a.get('title')}|{locator}"
            snap_id = "snap_" + _sha(content)[:24]
            claim_id = "cl_" + _sha(content + "|catalyst_anchor")[:24]
            as_of = date.fromisoformat(d)
            snaps.append(
                (
                    snap_id,
                    _kind_for_db(a.get("kind", "press_coverage")),
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
                    "catalyst_backfill_v1",
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


async def backfill_one(
    ticker: str,
    cik_map: dict,
    since: str,
    *,
    skip_fmp: bool = False,
    include_news: bool = False,
    fmp_retries: int = 1,
) -> list[dict]:
    fmp_anchors: list[dict] = []
    raw: dict = {}
    if not skip_fmp:
        payload = await fetch_and_cache_ticker(
            ticker, include_news=include_news, fmp_retries=fmp_retries
        )
        fmp_anchors = list(payload.get("anchors") or [])
        raw = dict(payload.get("raw") or {})
    else:
        # Preserve any existing FMP anchors already on disk
        from app.services.catalyst_event_service import load_cached_anchors

        fmp_anchors = [
            a
            for a in load_cached_anchors(ticker, allow_stale=True)
            if a.get("source", "").startswith("fmp")
        ]

    # SEC 8-K / 6-K
    sec_anchors: list[dict] = []
    try:
        sec_anchors = sec_edgar.recent_forms(
            ticker, forms={"8-K", "6-K"}, since=since, cik_map=cik_map, limit=40
        )
    except Exception as e:
        print(f"  SEC miss {ticker}: {e}", flush=True)

    merged = merge_anchor_lists(fmp_anchors, sec_anchors)
    write_cache(
        ticker,
        merged,
        raw={
            **raw,
            "sec_n": len(sec_anchors),
            "merged_n": len(merged),
            "skip_fmp": skip_fmp,
        },
    )
    return merged


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--universe-version",
        required=True,
        help="Sealed universe version whose tickers this backfill must cover",
    )
    ap.add_argument("--limit", type=int, default=0, help="Cap tickers (0 = all)")
    ap.add_argument("--ticker", type=str, default="", help="Single ticker")
    ap.add_argument("--skip-db", action="store_true", help="Cache only, no snapshots/claims")
    ap.add_argument("--skip-fmp", action="store_true", help="SEC-only pass (reuse cached FMP)")
    ap.add_argument("--include-news", action="store_true", help="Also pull FMP stock news")
    ap.add_argument("--sleep", type=float, default=0.25, help="Pause between tickers")
    ap.add_argument("--fmp-retries", type=int, default=1, help="FMP 429 retries per call")
    ap.add_argument(
        "--allow-partial",
        action="store_true",
        help="Permit --ticker/--limit probes and incomplete coverage (never use for a release).",
    )
    ap.add_argument(
        "--allow-empty-anchors",
        action="store_true",
        help="Allow successfully fetched tickers with no dated anchors; defaults to fail closed.",
    )
    args = ap.parse_args()

    universe_tickers = await _tickers_from_db(args.universe_version)
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
        f"fmp_key={'yes' if settings.FMP_API_KEY else 'NO'} skip_fmp={args.skip_fmp}",
        flush=True,
    )
    since = lookback_since(2.0)
    print(f"since={since}", flush=True)

    print("loading SEC ticker→CIK map…", flush=True)
    cik_map = sec_edgar.ticker_cik_map()
    print(f"cik_map={len(cik_map)}", flush=True)

    by_ticker: dict[str, list[dict]] = {}
    with_any = 0
    completed: set[str] = set()
    failures: list[dict[str, str]] = []
    empty_anchor_tickers: list[str] = []
    t0 = time.time()
    for i, t in enumerate(tickers, 1):
        try:
            anchors = await backfill_one(
                t,
                cik_map,
                since,
                skip_fmp=args.skip_fmp,
                include_news=args.include_news,
                fmp_retries=args.fmp_retries,
            )
        except Exception as e:
            print(f"[{i}/{len(tickers)}] {t} FAIL {e}", flush=True)
            failures.append({"ticker": t, "error": str(e)})
            anchors = []
        else:
            completed.add(t)
        by_ticker[t] = anchors
        if anchors:
            with_any += 1
        elif t in completed:
            empty_anchor_tickers.append(t)
        if i % 10 == 0 or i == len(tickers) or i <= 3:
            print(
                f"[{i}/{len(tickers)}] with_anchors={with_any} "
                f"elapsed={time.time()-t0:.0f}s last={t} n={len(anchors)}",
                flush=True,
            )
        await asyncio.sleep(args.sleep)

    claim_n = 0
    if not args.skip_db:
        claim_n = await _upsert_claims(by_ticker)

    report = {
        "kind": "catalyst_anchors",
        "universe_version": args.universe_version,
        "universe_tickers": len(universe_tickers),
        "selected_tickers": len(tickers),
        "succeeded": len(completed),
        "failed": len(failures),
        "missing_tickers": sorted(set(universe_tickers) - completed),
        "empty_anchor_tickers": empty_anchor_tickers,
        "n_with_anchors": with_any,
        "n_claims_attempted": claim_n,
        "coverage_pct": round(100.0 * len(completed) / len(universe_tickers), 1),
        "anchor_coverage_pct": round(100.0 * with_any / len(universe_tickers), 1),
        "allow_partial": args.allow_partial,
        "allow_empty_anchors": args.allow_empty_anchors,
        "elapsed_s": round(time.time() - t0, 1),
        "skip_fmp": args.skip_fmp,
        "failures": failures,
    }
    out = ROOT / "data" / "catalyst_event_cache" / "_backfill_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out = out.with_name(f"_backfill_report_{args.universe_version.replace('/', '_')}.json")
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    incomplete = report["missing_tickers"] or (
        empty_anchor_tickers and not args.allow_empty_anchors
    )
    if incomplete and not args.allow_partial:
        raise SystemExit(
            f"Catalyst coverage is incomplete for sealed universe {args.universe_version}: "
            f"{len(report['missing_tickers'])} fetch failure(s), "
            f"{len(empty_anchor_tickers)} ticker(s) without dated anchors"
        )


if __name__ == "__main__":
    asyncio.run(main())
