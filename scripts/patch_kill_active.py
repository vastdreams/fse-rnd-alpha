#!/usr/bin/env python3
"""
PATH: scripts/patch_kill_active.py
PURPOSE: Apply only explicitly reviewed kill_active True/False states to an
  immutable candidate universe clone. Unknown names remain NULL/fail-closed.

Rules (matches build_universe.py):
  - WDAY = True
  - FRSH, DOCU, PCTY = False
  - everyone else remains NULL (never manufacture a safe state)
"""

from __future__ import annotations

import asyncio
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone

KILL_ACTIVE = {"WDAY": True, "FRSH": False, "DOCU": False, "PCTY": False}
ENGINE_VERSION = "kill_state_review@w2c"


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _release_sha() -> str:
    value = os.environ.get("RELEASE_SHA", "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SystemExit(
            "RELEASE_SHA must be the full 40-character committed source SHA before patching a universe."
        )
    return value


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="Immutable sealed source universe version")
    ap.add_argument(
        "--output-version",
        required=True,
        help="New immutable universe version containing the reviewed kill states",
    )
    ap.add_argument("--reviewer", required=True, help="Named reviewer who approved the explicit states")
    ap.add_argument(
        "--review-reference",
        required=True,
        help="Immutable approval ticket, memo, or evidence reference.",
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
    build_source_sha = _release_sha()

    import asyncpg

    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        source_version = args.version
        if source_version == args.output_version:
            raise RuntimeError("output-version must differ from the immutable source version")

        rows = await conn.fetch(
            """SELECT ticker, vector, completeness_grade, route, kill_active, stale
               FROM metric_vectors WHERE universe_version=$1 ORDER BY ticker""",
            source_version,
        )
        if not rows:
            raise RuntimeError(f"Universe {source_version} has no vectors")
        input_sha = _sha(
            {
                "parent_version": source_version,
                "reviewed_states": KILL_ACTIVE,
                "engine_version": ENGINE_VERSION,
                "reviewer": args.reviewer,
                "review_reference": args.review_reference,
                "source_sha": build_source_sha,
            }
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        updated = 0
        async with conn.transaction():
            builds_table = await conn.fetchval("SELECT to_regclass('public.universe_builds')")
            if builds_table is None:
                raise RuntimeError(
                    "universe_builds is missing; apply migration "
                    "011_release_integrity.sql first"
                )
            source_status = await conn.fetchval(
                "SELECT status FROM universe_builds WHERE universe_version=$1",
                source_version,
            )
            if source_status != "sealed":
                raise RuntimeError(
                    f"Kill-review source {source_version} must be sealed, got {source_status!r}"
                )
            if await conn.fetchval(
                "SELECT 1 FROM universe_builds WHERE universe_version=$1",
                args.output_version,
            ):
                raise RuntimeError(f"Universe {args.output_version} is already sealed")
            if await conn.fetchval(
                "SELECT 1 FROM universe_builds WHERE input_sha256=$1",
                input_sha,
            ):
                raise RuntimeError("This exact kill-state review is already sealed")
            parent_exists = await conn.fetchval(
                "SELECT 1 FROM universe_builds WHERE universe_version=$1",
                source_version,
            )
            manifest = {
                "parent_version": source_version,
                "reviewed_states": KILL_ACTIVE,
                "engine_version": ENGINE_VERSION,
                "reviewer": args.reviewer,
                "review_reference": args.review_reference,
            }
            await conn.execute(
                """INSERT INTO universe_builds
                   (universe_version, input_sha256, manifest, parent_version, engine_version, status, sealed_at, is_active, source_sha)
                   VALUES ($1,$2,$3::jsonb,$4,$5,'building',NULL,false,$6)""",
                args.output_version,
                input_sha,
                json.dumps(manifest),
                source_version if parent_exists else None,
                ENGINE_VERSION,
                build_source_sha,
            )
            for r in rows:
                t = r["ticker"]
                flag = KILL_ACTIVE.get(t, r["kill_active"])
                raw = r["vector"]
                vec = raw if isinstance(raw, dict) else json.loads(raw)
                vec["kill_active"] = flag
                vec["universe_version"] = args.output_version
                vec["computed_at"] = now.isoformat()
                await conn.execute(
                    """INSERT INTO metric_vectors
                       (ticker, universe_version, computed_at, vector, completeness_grade, route, kill_active, stale)
                       VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,$8)""",
                    t,
                    args.output_version,
                    now,
                    json.dumps(vec),
                    r["completeness_grade"],
                    r["route"],
                    flag,
                    r["stale"],
                )
                if t in KILL_ACTIVE:
                    updated += 1
            await conn.fetchval(
                "SELECT materialize_universe_evidence_refs($1)",
                args.output_version,
            )
            if args.activate:
                await conn.execute("SELECT pg_advisory_xact_lock(842183002)")
                await conn.execute("UPDATE universe_builds SET is_active=false WHERE is_active")
            await conn.execute(
                """UPDATE universe_builds
                   SET status='sealed', sealed_at=CURRENT_TIMESTAMP, is_active=$2
                   WHERE universe_version=$1 AND status='building'""",
                args.output_version,
                args.activate,
            )
        print(
            json.dumps(
                {
                    "source_version": source_version,
                    "universe_version": args.output_version,
                    "updated_explicit_states": updated,
                    "unknown_states_preserved": True,
                    "wday": True,
                    "activated": args.activate,
                }
            )
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
