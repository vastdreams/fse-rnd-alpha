#!/usr/bin/env python3
"""
PATH: scripts/fill_layer0.py
PURPOSE: W2b Layer-0 extractor fill — fetch the latest 10-K/20-F for every
universe name and run the DETERMINISTIC extractors (NRR, customer
concentration, AI risk language). Creates an immutable derived universe,
never mutating the source snapshot.

Rules:
  * Verbatim-only extraction (nrr_extractor / customer_concentration /
    edgar_risk_ai). Nothing inferred; not found stays Unknown.
  * Every value written is backed by an EvidenceClaim pointing at the filing
    accession (SourceSnapshot kind 10-K/20-F).
  * Filing text is cached under data/filings_cache/ so the DeepSeek filing_map
    job can reuse it without hitting EDGAR again.
  * SEC rate limit respected (max ~5 req/s; we do 2 concurrent with pauses).

Usage:
  backend/.venv/bin/python scripts/fill_layer0.py --version SOURCE --output-version NEW [--activate]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

os.environ.setdefault("DEBUG", "true")

from saas_ai.analysis import sec_edgar  # noqa: E402
from saas_ai.analysis.customer_concentration import extract_customer_concentration  # noqa: E402
from saas_ai.analysis.edgar_risk_ai import extract_ai_risk_flags  # noqa: E402
from saas_ai.analysis.nrr_extractor import extract_nrr  # noqa: E402

from app.contracts.research import MetricValue, MetricVector  # noqa: E402
from app.services.rank_service.completeness import grade_completeness  # noqa: E402

CACHE_DIR = REPO / "data/filings_cache"
EXTRACTOR_VERSION = "fill_layer0@w2b"
DSN = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
).replace("postgresql+asyncpg://", "postgresql://")


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def release_sha() -> str:
    value = os.environ.get("RELEASE_SHA", "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SystemExit(
            "RELEASE_SHA must be the full 40-character committed source SHA before deriving a universe."
        )
    return value


def cache_manifest_sha() -> str:
    """Stable digest of cached filing inputs present before this run."""

    digest = hashlib.sha256()
    if not CACHE_DIR.exists():
        return digest.hexdigest()
    for path in sorted(p for p in CACHE_DIR.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(CACHE_DIR)).encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


async def clone_universe(
    conn,
    *,
    source_version: str,
    output_version: str,
    reextract: bool,
    filing_cache_sha256: str,
    build_source_sha: str,
) -> None:
    """Copy a sealed source universe before any Layer-0 enrichment.

    The derived version records a stable digest of the parent vectors and
    extractor mode. New filing snapshots/claims then attach to this new
    version, leaving the source build replayable.
    """

    if source_version == output_version:
        raise RuntimeError("output-version must differ from the immutable source version")
    if await conn.fetchval("SELECT to_regclass('public.universe_builds')") is None:
        raise RuntimeError(
            "universe_builds is missing; apply migration "
            "011_release_integrity.sql before Layer-0 enrichment."
        )
    source_status = await conn.fetchval(
        "SELECT status FROM universe_builds WHERE universe_version=$1",
        source_version,
    )
    if source_status != "sealed":
        raise RuntimeError(
            f"Layer-0 source {source_version} must be a sealed build, got {source_status!r}"
        )
    source_rows = await conn.fetch(
        """SELECT ticker, vector, completeness_grade, route, kill_active, stale
           FROM metric_vectors WHERE universe_version=$1 ORDER BY ticker""",
        source_version,
    )
    if not source_rows:
        raise RuntimeError(f"Universe {source_version} has no vectors")
    if await conn.fetchval(
        "SELECT 1 FROM universe_builds WHERE universe_version=$1", output_version
    ):
        raise RuntimeError(f"Universe version {output_version} already exists")
    parent_digest = sha(
        json.dumps(
            [
                {
                    "ticker": r["ticker"],
                    "vector": r["vector"],
                }
                for r in source_rows
            ],
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
    )
    input_sha = sha(
        json.dumps(
            {
                "parent_version": source_version,
                "parent_digest": parent_digest,
                "extractor_version": EXTRACTOR_VERSION,
                "reextract": reextract,
                "filing_cache_sha256": filing_cache_sha256,
                "source_sha": build_source_sha,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    prior = await conn.fetchval(
        "SELECT universe_version FROM universe_builds WHERE input_sha256=$1",
        input_sha,
    )
    if prior:
        raise RuntimeError(
            f"An identical Layer-0 source set is already sealed as {prior}; "
            "do not duplicate immutable work."
        )
    parent_exists = await conn.fetchval(
        "SELECT 1 FROM universe_builds WHERE universe_version=$1", source_version
    )
    manifest = {
        "parent_version": source_version,
        "parent_vector_sha256": parent_digest,
        "extractor_version": EXTRACTOR_VERSION,
        "reextract": reextract,
        "filing_cache_sha256": filing_cache_sha256,
        "source_sha": build_source_sha,
    }
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await conn.execute(
        """INSERT INTO universe_builds
           (universe_version, input_sha256, manifest, parent_version, engine_version, status, sealed_at, is_active, source_sha)
           VALUES ($1,$2,$3::jsonb,$4,$5,'building',NULL,false,$6)""",
        output_version,
        input_sha,
        json.dumps(manifest),
        source_version if parent_exists else None,
        EXTRACTOR_VERSION,
        build_source_sha,
    )
    for row in source_rows:
        raw = row["vector"] if isinstance(row["vector"], dict) else json.loads(row["vector"])
        raw["universe_version"] = output_version
        raw["computed_at"] = now.isoformat()
        await conn.execute(
            """INSERT INTO metric_vectors
               (ticker, universe_version, computed_at, vector, completeness_grade, route, kill_active, stale)
               VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,$8)""",
            row["ticker"],
            output_version,
            now,
            json.dumps(raw),
            row["completeness_grade"],
            row["route"],
            row["kill_active"],
            row["stale"],
        )


def fetch_filing(ticker: str, cik_map: dict) -> dict:
    """Fetch (or load cached) latest annual filing text + metadata."""
    meta_path = CACHE_DIR / f"{ticker}.meta.json"
    text_path = CACHE_DIR / f"{ticker}.txt"
    if meta_path.exists() and text_path.exists():
        return {**json.loads(meta_path.read_text()), "filing_text": text_path.read_text(), "error": None}
    result = sec_edgar.fetch_latest_10k_text(ticker, cik_map)
    if result.get("filing_text"):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        text_path.write_text(result["filing_text"])
        meta = {k: v for k, v in result.items() if k not in ("filing_text",)}
        meta_path.write_text(json.dumps(meta))
    return result


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="Immutable sealed source universe version")
    ap.add_argument(
        "--output-version",
        required=True,
        help="New immutable universe version to receive Layer-0 enrichment",
    )
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--reextract",
        action="store_true",
        help="Process all names (use cache when present); only fill empty NRR/concentration fields",
    )
    ap.add_argument(
        "--activate",
        action="store_true",
        help="Deprecated: stage the data artifact and promote separately.",
    )
    args = ap.parse_args()
    if args.activate:
        raise SystemExit(
            "--activate is unsafe during a build. Stage the immutable data artifact "
            "first, then use scripts/activate_universe.py with its manifest hash."
        )
    build_source_sha = release_sha()

    import asyncpg

    conn = await asyncpg.connect(DSN)
    source_uv = args.version
    existing_cache_sha = cache_manifest_sha()
    async with conn.transaction():
        await clone_universe(
            conn,
            source_version=source_uv,
            output_version=args.output_version,
            reextract=args.reextract,
            filing_cache_sha256=existing_cache_sha,
            build_source_sha=build_source_sha,
        )
    uv = args.output_version
    rows = await conn.fetch(
        "SELECT ticker, vector FROM metric_vectors WHERE universe_version=$1 ORDER BY ticker", uv
    )
    print(
        f"Universe {uv} (derived from {source_uv}): {len(rows)} names "
        f"cache={CACHE_DIR} exists={CACHE_DIR.exists()}"
    )

    cik_map = sec_edgar.ticker_cik_map()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    done = 0
    filled_nrr = filled_conc = filled_ai = fetched = errors = 0

    targets = []
    for r in rows:
        vec = MetricVector.model_validate(
            r["vector"] if isinstance(r["vector"], dict) else json.loads(r["vector"])
        )
        if not args.reextract:
            # Skip names that already have a filing-backed overlay (from the 32-name overlay CSV)
            if vec.completeness.filing_fetched and vec.retention.value is not None:
                continue
        targets.append(vec)
    if args.limit:
        targets = targets[: args.limit]
    print(f"To fill: {len(targets)} reextract={args.reextract}")

    for vec in targets:
        t = vec.ticker
        try:
            result = await asyncio.to_thread(fetch_filing, t, cik_map)
        except Exception as exc:
            print(f"  {t}: fetch error {exc}")
            errors += 1
            continue
        if not result.get("filing_text"):
            print(f"  {t}: no filing ({result.get('error')})")
            errors += 1
            continue
        fetched += 1
        text = result["filing_text"]
        accession = result["accession"]
        filing_date = date.fromisoformat(result["filing_date"])
        report_date = date.fromisoformat(result["report_date"]) if result.get("report_date") else filing_date
        if report_date > filing_date:
            report_date = filing_date
        form = result.get("form", "10-K")
        kind = "20-F" if form in ("20-F", "40-F") else "10-K"

        snap_id = sha(f"10k|{t}|{accession}")[:40]
        await conn.execute(
            """INSERT INTO source_snapshots
               (snapshot_id, kind, ticker, as_of_date, available_date, fetched_at, locator, content_sha256, notes)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (snapshot_id) DO NOTHING""",
            snap_id, kind, t, report_date, filing_date, now, accession,
            sha(text[:100000]), result.get("filing_url"),
        )

        async def put_claim(field: str, value, text_val: str, locator: str, operator="=", unit=None) -> str:
            cid = sha(f"c|{t}|{field}|{uv}|{accession}")[:40]
            await conn.execute(
                """INSERT INTO evidence_claims
                   (claim_id, snapshot_id, ticker, field, value_text, value_numeric, operator, unit, excerpt_locator, extractor, extracted_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) ON CONFLICT (claim_id) DO NOTHING""",
                cid, snap_id, t, field, text_val[:2000],
                float(value) if value is not None else None,
                operator, unit, locator, EXTRACTOR_VERSION, now,
            )
            return cid

        # --- NRR (verbatim) ---
        nrr = extract_nrr(text)
        if nrr["nrr"] is not None and vec.retention.value is None:
            cid = await put_claim(
                "retention", nrr["nrr"], nrr["raw_match"] or nrr["raw_value"],
                "10-K MD&A NRR disclosure", nrr.get("operator") or "=", "%",
            )
            vec.retention = MetricValue(
                value=nrr["nrr"], as_of_date=report_date, available_date=filing_date,
                claim_ids=[cid], formula="disclosed NRR (verbatim)", engine_version=EXTRACTOR_VERSION,
            )
            filled_nrr += 1

        # --- Customer concentration (verbatim) ---
        conc = extract_customer_concentration(text)
        if conc["top10_pct"] is not None and vec.concentration.value is None:
            cid = await put_claim(
                "concentration", conc["top10_pct"], conc["raw_match"] or conc["raw_value"],
                "10-K Risk Factors / MD&A concentration disclosure", "=", "%",
            )
            vec.concentration = MetricValue(
                value=conc["top10_pct"], as_of_date=report_date, available_date=filing_date,
                claim_ids=[cid], formula="disclosed customer concentration (verbatim)",
                engine_version=EXTRACTOR_VERSION,
            )
            filled_conc += 1

        # --- AI risk language (verbatim sentences; flag only, no scores) ---
        ai = extract_ai_risk_flags(t, report_date.year, filing_text=text)
        if ai.get("has_ai_risk"):
            sample = " | ".join(ai["ai_risk_sentences"][:3])
            await put_claim("ai_risk_language", None, sample, "10-K Item 1A AI risk sentences")
            filled_ai += 1

        vec.completeness = grade_completeness(
            vec,
            filing_fetched=True,
            claims_n=await conn.fetchval(
                "SELECT count(*) FROM evidence_claims WHERE ticker=$1", t
            ),
        )
        # This derived vector is not complete until its freshly extracted
        # evidence is present. Keep the persisted vector timestamp aligned
        # with those claims so seal-time PIT validation has one UTC basis.
        vec.computed_at = now
        await conn.execute(
            """UPDATE metric_vectors
               SET vector=$3, completeness_grade=$4, computed_at=$5
               WHERE ticker=$1 AND universe_version=$2""",
            t,
            uv,
            json.dumps(vec.model_dump(mode="json")),
            vec.completeness.grade,
            now,
        )
        done += 1
        if done % 20 == 0:
            print(f"  progress {done}/{len(targets)} (nrr={filled_nrr} conc={filled_conc} ai={filled_ai} err={errors})")
        time.sleep(0.35)  # SEC politeness

    complete = errors == 0 and args.limit is None
    async with conn.transaction():
        if complete:
            await conn.fetchval(
                "SELECT materialize_universe_evidence_refs($1)",
                uv,
            )
            if args.activate:
                await conn.execute("SELECT pg_advisory_xact_lock(842183002)")
                await conn.execute(
                    "UPDATE universe_builds SET is_active=false WHERE is_active"
                )
            await conn.execute(
                """UPDATE universe_builds
                   SET status='sealed', sealed_at=CURRENT_TIMESTAMP, is_active=$2
                   WHERE universe_version=$1 AND status='building'""",
                uv,
                args.activate,
            )
        else:
            await conn.execute(
                """UPDATE universe_builds
                   SET status='failed', is_active=false
                   WHERE universe_version=$1 AND status='building'""",
                uv,
            )

    print(f"\nFill done: {done} updated, filings fetched {fetched}, errors {errors}")
    print(f"  NRR filled: {filled_nrr}  concentration: {filled_conc}  AI-risk flags: {filled_ai}")
    grades = await conn.fetch(
        "SELECT completeness_grade, count(*) FROM metric_vectors WHERE universe_version=$1 GROUP BY 1", uv
    )
    print("  grades now:", {g["completeness_grade"]: g["count"] for g in grades})
    await conn.close()
    if not complete:
        reason = "limited run" if args.limit is not None else f"{errors} extraction errors"
        raise RuntimeError(
            f"Universe {uv} was marked failed ({reason}) and was not activated."
        )


if __name__ == "__main__":
    asyncio.run(main())
