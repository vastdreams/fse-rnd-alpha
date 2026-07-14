#!/usr/bin/env python3
"""
PATH: scripts/derive_sealed_universe.py
PURPOSE: Clone a sealed universe to a new sealed version bound to RELEASE_SHA.

App-only releases still need a data artifact whose source_sha matches the app
image. This derives a byte-stable vector copy (no SEC / Layer-0 enrichment),
materializes evidence refs, and seals with is_active=false for later staging.

Usage:
  RELEASE_SHA=<40-char> DATABASE_URL=postgresql://... \
    python3 scripts/derive_sealed_universe.py \
      --parent-version univ_... \
      --output-version univ_...
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone


def release_sha() -> str:
    value = os.environ.get("RELEASE_SHA", "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SystemExit("RELEASE_SHA must be the full 40-character committed source SHA")
    return value


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
    ).replace("postgresql+asyncpg://", "postgresql://")


def sha(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()


async def derive(parent_version: str, output_version: str, build_source_sha: str) -> None:
    import asyncpg

    if parent_version == output_version:
        raise SystemExit("output-version must differ from parent-version")

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

        manifest = {
            "mode": "derive_sealed_universe",
            "parent_version": parent_version,
            "parent_vector_sha256": parent_digest,
            "source_sha": build_source_sha,
            "note": "Vector copy for app/data source_sha bind — no Layer-0 enrichment",
        }
        now = datetime.now(timezone.utc).replace(tzinfo=None)

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
                "derive_sealed_universe@v1",
                build_source_sha,
            )
            for row in source_rows:
                raw = row["vector"] if isinstance(row["vector"], dict) else json.loads(row["vector"])
                raw["universe_version"] = output_version
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
                    row["completeness_grade"],
                    row["route"],
                    row["kill_active"],
                    row["stale"],
                )
            await conn.fetchval("SELECT materialize_universe_evidence_refs($1)", output_version)
            # Copy every parent evidence ref (including catalyst_anchor claims
            # not referenced inside vectors) so the clone sees the exact same
            # evidence set as its parent. Refs are immutable after seal.
            await conn.execute(
                """INSERT INTO universe_evidence_refs (universe_version, claim_id)
                   SELECT $1, claim_id FROM universe_evidence_refs
                   WHERE universe_version=$2
                   ON CONFLICT DO NOTHING""",
                output_version,
                parent_version,
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
    args = parser.parse_args()
    asyncio.run(derive(args.parent_version, args.output_version, release_sha()))


if __name__ == "__main__":
    main()
