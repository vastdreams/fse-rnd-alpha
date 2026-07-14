#!/usr/bin/env python3
"""
PATH: scripts/derive_sealed_universe.py
PURPOSE: Clone a sealed universe to a new sealed version bound to RELEASE_SHA.

App-only releases still need a data artifact whose source_sha matches the app
image. This derives a vector copy, materializes evidence refs, binds PIT-valid
catalyst_anchor claims (same contract as build_universe), optionally repairs
completeness grades when a PIT-valid filing already sits in filings_cache, and
seals with is_active=false for later staging.

Usage:
  RELEASE_SHA=<40-char> DATABASE_URL=postgresql://... \
    python3 scripts/derive_sealed_universe.py \
      --parent-version univ_... \
      --output-version univ_... \
      [--repair-completeness-from-filings-cache]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path


def release_sha() -> str:
    value = os.environ.get("RELEASE_SHA", "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SystemExit("RELEASE_SHA must be the full 40-character committed source SHA")
    return value


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
    ).replace("postgresql+asyncpg://", "postgresql://")


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/opt/rd-alpha-data"))


def sha(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()


def _mv(node) -> object:
    if isinstance(node, dict):
        return node.get("value")
    return None


def pit_filing_present(ticker: str, computed_at: datetime, cache_root: Path) -> bool:
    """True when filings_cache has a non-error accession dated on/before computed_at."""
    meta_path = cache_root / "filings_cache" / f"{ticker.upper()}.meta.json"
    if not meta_path.is_file():
        return False
    try:
        meta = json.loads(meta_path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if meta.get("error") or not meta.get("accession"):
        return False
    filing_date = meta.get("filing_date")
    if not filing_date:
        return False
    try:
        fd = date.fromisoformat(str(filing_date)[:10])
    except ValueError:
        return False
    cutoff = computed_at.date() if hasattr(computed_at, "date") else date.fromisoformat(str(computed_at)[:10])
    return fd <= cutoff


def repair_completeness(raw: dict, computed_at: datetime, cache_root: Path) -> tuple[dict, str, bool]:
    """
    Recompute grade using the same rules as build_universe once a PIT filing exists.
    Returns (vector, grade, changed).
    """
    ticker = str(raw.get("ticker") or "").upper()
    comp = dict(raw.get("completeness") or {})
    grade = str(comp.get("grade") or raw.get("completeness_grade") or "Incomplete")
    if grade in ("A", "B"):
        return raw, grade, False
    if not pit_filing_present(ticker, computed_at, cache_root):
        return raw, grade, False

    core = [
        _mv(raw.get("mos_snapshot")),
        _mv(raw.get("gm")),
        _mv(raw.get("fcfm_sbc")),
        _mv(raw.get("roic")),
        _mv(raw.get("rule40")),
        _mv(raw.get("rd_prod")),
        _mv(raw.get("rd_int")),
    ]
    overlay = [
        _mv(raw.get("retention")),
        _mv(raw.get("concentration")),
        _mv(raw.get("ai_text_stance")),
    ]
    core_ok = sum(1 for x in core if x is not None)
    fill = sum(1 for x in overlay if x is not None) / max(len(overlay), 1)
    if core_ok == len(core) and fill >= 2 / 3:
        new_grade = "A"
    elif core_ok >= 5:
        new_grade = "B"
    else:
        new_grade = "Incomplete"

    if new_grade == grade and comp.get("filing_fetched") is True:
        return raw, grade, False

    comp["grade"] = new_grade
    comp["filing_fetched"] = True
    if "overlay_fill_rate" not in comp:
        comp["overlay_fill_rate"] = round(fill, 4)
    raw = dict(raw)
    raw["completeness"] = comp
    return raw, new_grade, True


async def derive(
    parent_version: str,
    output_version: str,
    build_source_sha: str,
    *,
    repair_completeness_from_filings_cache: bool = False,
) -> None:
    import asyncpg

    if parent_version == output_version:
        raise SystemExit("output-version must differ from parent-version")

    cache_root = data_dir()
    conn = await asyncpg.connect(database_url())
    try:
        parent = await conn.fetchrow(
            """SELECT status, source_sha FROM universe_builds WHERE universe_version=$1""",
            parent_version,
        )
        if parent is None:
            raise SystemExit(f"Unknown parent universe: {parent_version}")
        if parent["status"] != "sealed":
            raise SystemExit(f"Parent {parent_version} is {parent['status']}, not sealed")
        if await conn.fetchval(
            "SELECT 1 FROM universe_builds WHERE universe_version=$1", output_version
        ):
            raise SystemExit(f"Universe version already exists: {output_version}")

        source_rows = await conn.fetch(
            """SELECT ticker, vector, completeness_grade, route, kill_active, stale,
                      computed_at
               FROM metric_vectors WHERE universe_version=$1 ORDER BY ticker""",
            parent_version,
        )
        if not source_rows:
            raise SystemExit(f"Parent {parent_version} has no vectors")

        parent_digest = sha(
            json.dumps(
                [{"ticker": r["ticker"], "vector": r["vector"]} for r in source_rows],
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
        )
        input_sha = sha(
            json.dumps(
                {
                    "mode": "derive_sealed_universe",
                    "parent_version": parent_version,
                    "parent_digest": parent_digest,
                    "source_sha": build_source_sha,
                    # Distinct from pre-fix derives that copied parent refs only.
                    "bind_catalyst_anchors": True,
                    "repair_completeness_from_filings_cache": repair_completeness_from_filings_cache,
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
            raise SystemExit(f"Identical derive already sealed as {prior}")

        repaired = 0
        prepared: list[tuple] = []
        for row in source_rows:
            raw = row["vector"] if isinstance(row["vector"], dict) else json.loads(row["vector"])
            raw = dict(raw)
            raw["universe_version"] = output_version
            grade = row["completeness_grade"]
            if repair_completeness_from_filings_cache:
                raw, grade, changed = repair_completeness(raw, row["computed_at"], cache_root)
                if changed:
                    repaired += 1
            prepared.append((row, raw, grade))

        manifest = {
            "mode": "derive_sealed_universe",
            "parent_version": parent_version,
            "parent_vector_sha256": parent_digest,
            "source_sha": build_source_sha,
            "bind_catalyst_anchors": True,
            "repair_completeness_from_filings_cache": repair_completeness_from_filings_cache,
            "completeness_repaired": repaired,
            "note": (
                "Vector copy + PIT catalyst_anchor bind"
                + (" + filings_cache completeness repair" if repair_completeness_from_filings_cache else "")
                + " — no Layer-0 enrichment"
            ),
        }

        async with conn.transaction():
            await conn.execute(
                """INSERT INTO universe_builds
                   (universe_version, input_sha256, manifest, parent_version,
                    engine_version, status, sealed_at, is_active, source_sha)
                   VALUES ($1,$2,$3::jsonb,$4,$5,'building',NULL,false,$6)""",
                output_version,
                input_sha,
                json.dumps(manifest),
                parent_version,
                "derive_sealed_universe@v2",
                build_source_sha,
            )
            for row, raw, grade in prepared:
                # PIT: keep the parent's computed_at. Rewriting it to derive time
                # would let evidence/tape newer than the parent seal become
                # "known" to the clone and silently change stances.
                await conn.execute(
                    """INSERT INTO metric_vectors
                       (ticker, universe_version, computed_at, vector,
                        completeness_grade, route, kill_active, stale)
                       VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,$8)""",
                    row["ticker"],
                    output_version,
                    row["computed_at"],
                    json.dumps(raw),
                    grade,
                    row["route"],
                    row["kill_active"],
                    row["stale"],
                )
            await conn.fetchval("SELECT materialize_universe_evidence_refs($1)", output_version)
            await conn.execute(
                """INSERT INTO universe_evidence_refs (universe_version, claim_id)
                   SELECT $1, claim_id FROM universe_evidence_refs
                   WHERE universe_version=$2
                   ON CONFLICT DO NOTHING""",
                output_version,
                parent_version,
            )
            # Parents derived before catalyst backfill have zero catalyst refs.
            # Bind PIT-valid catalyst_anchor claims the same way build_universe
            # does, while the clone is still 'building'. Without this, F4 sees
            # zero anchors forever and the landing page stays empty.
            anchor_status = await conn.execute(
                """INSERT INTO universe_evidence_refs (universe_version, claim_id)
                   SELECT DISTINCT $1, claim.claim_id
                     FROM evidence_claims AS claim
                     JOIN source_snapshots AS snapshot
                       ON snapshot.snapshot_id = claim.snapshot_id
                     JOIN metric_vectors AS vector_row
                       ON vector_row.universe_version = $1
                      AND vector_row.ticker = claim.ticker
                    WHERE claim.field = 'catalyst_anchor'
                      AND claim.extracted_at <= vector_row.computed_at
                      AND snapshot.available_date <= vector_row.computed_at::date
                   ON CONFLICT DO NOTHING""",
                output_version,
            )
            await conn.execute(
                """UPDATE universe_builds
                   SET status='sealed', sealed_at=CURRENT_TIMESTAMP, is_active=false
                   WHERE universe_version=$1 AND status='building'""",
                output_version,
            )

        print(
            json.dumps(
                {
                    "ok": True,
                    "parent_version": parent_version,
                    "output_version": output_version,
                    "source_sha": build_source_sha,
                    "n_vectors": len(source_rows),
                    "input_sha256": input_sha,
                    "catalyst_anchor_bind": str(anchor_status),
                    "completeness_repaired": repaired,
                },
                sort_keys=True,
            )
        )
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-version", required=True)
    parser.add_argument("--output-version", required=True)
    parser.add_argument(
        "--repair-completeness-from-filings-cache",
        action="store_true",
        help="Upgrade C/Incomplete→A|B when a PIT-valid filing already exists in DATA_DIR/filings_cache",
    )
    args = parser.parse_args()
    asyncio.run(
        derive(
            args.parent_version,
            args.output_version,
            release_sha(),
            repair_completeness_from_filings_cache=args.repair_completeness_from_filings_cache,
        )
    )


if __name__ == "__main__":
    main()
