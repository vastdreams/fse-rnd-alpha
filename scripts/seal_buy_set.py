#!/usr/bin/env python3
"""
PATH: scripts/seal_buy_set.py
PURPOSE: Append a PIT research-BUY membership snapshot for the active universe.

Does not invent stances — calls the same close-call path as the API (operator
must provide a JSON list of already-cleared BUY rows, or rely on DB insert from
the /buy-performance-book/seal endpoint).

Usage:
  DATABASE_URL=... python3 scripts/seal_buy_set.py --universe-version univ_... \
    --as-of 2026-07-14 --members-json /path/to/buys.json
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
    ).replace("postgresql+asyncpg://", "postgresql://")


async def seal(universe_version: str, as_of: date, members: list[dict], engine: str) -> str:
    import asyncpg

    if not members:
        raise SystemExit("Refusing to seal an empty BUY set — that would fake coverage")
    for m in members:
        if (m.get("stance") or "").upper() != "BUY":
            raise SystemExit(f"Non-BUY member refused: {m.get('ticker')}")
    snapshot_id = f"buysnap_{as_of.isoformat()}_{uuid.uuid4().hex[:12]}"
    conn = await asyncpg.connect(database_url())
    try:
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO buy_set_snapshots
                   (snapshot_id, universe_version, as_of_date, sealed_at, engine_version,
                    source_sha, n_buy, note)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
                snapshot_id,
                universe_version,
                as_of,
                datetime.now(timezone.utc),
                engine,
                os.environ.get("RELEASE_SHA"),
                len(members),
                "PIT research BUY clearance set — not paper HML_RD",
            )
            for m in members:
                await conn.execute(
                    """INSERT INTO buy_set_members
                       (snapshot_id, ticker, stance, confidence, score, mos_live,
                        gap_to_median, horizon_years, implied_ann_return)
                       VALUES ($1,$2,'BUY',$3,$4,$5,$6,$7,$8)""",
                    snapshot_id,
                    str(m["ticker"]).upper(),
                    m.get("confidence"),
                    m.get("score"),
                    m.get("mos_live"),
                    m.get("gap_to_median"),
                    m.get("horizon_years"),
                    m.get("implied_ann_return"),
                )
    finally:
        await conn.close()
    return snapshot_id


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe-version", required=True)
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--members-json", required=True)
    ap.add_argument("--engine", default="close_call_v2")
    args = ap.parse_args()
    members = json.loads(open(args.members_json).read())
    if isinstance(members, dict):
        members = members.get("members") or members.get("rows") or []
    snap = asyncio.run(seal(args.universe_version, date.fromisoformat(args.as_of), members, args.engine))
    print(json.dumps({"snapshot_id": snap, "n_buy": len(members)}))


if __name__ == "__main__":
    main()
