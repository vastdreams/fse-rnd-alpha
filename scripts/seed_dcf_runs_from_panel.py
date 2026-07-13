#!/usr/bin/env python3
"""
PATH: scripts/seed_dcf_runs_from_panel.py
PURPOSE: Seed reproducible base dcf_runs for every universe ticker from the
  paper panel CSV (fundamental_value_run.csv) using dcf_service.run_dcf.

Does NOT invent assumptions — only uses panel columns already computed in the
research run (revenue, FCF, WACC, growth, net cash, peer EV multiple).

Usage:
  python scripts/seed_dcf_runs_from_panel.py [--limit N] [--ticker EGAN] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.dcf_service import DcfInputs, ENGINE_VERSION, run_dcf  # noqa: E402

PANEL = ROOT / "data" / "saas_ai_repricing" / "fundamental_value_run.csv"


def _f(v) -> float | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def inputs_from_row(row: pd.Series) -> DcfInputs | None:
    t = str(row["ticker"]).upper()
    growth = _f(row.get("rev_cagr"))
    wacc = _f(row.get("wacc"))
    if growth is None or wacc is None:
        return None
    # Cap wild growth for engine stability (same spirit as dcf_service GCAP)
    growth = max(-0.10, min(0.30, growth))
    price = _f(row.get("price_l"))
    fcfm = _f(row.get("fcfm_sbc_l"))
    return DcfInputs(
        ticker=t,
        scenario="base",
        revenue_usd=_f(row.get("revenueusd_l")),
        fcf_sbc_usd=_f(row.get("fcf_sbc_usd_l")),
        fcfm_sbc=fcfm,
        net_cash_usd=_f(row.get("netcash_usd_l")) or 0.0,
        ev_mult_usd=_f(row.get("ev_mult")),
        shares_fut_implied=None,
        price=price,
        growth=growth,
        wacc=wacc,
        target_margin=fcfm if fcfm is not None and fcfm > 0 else None,
    )


async def main() -> None:
    import asyncpg

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ticker", type=str, default="")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Append a superseding immutable reference run for this sealed universe",
    )
    args = ap.parse_args()

    if not PANEL.exists():
        raise SystemExit(f"Missing panel CSV: {PANEL}")

    df = pd.read_csv(PANEL)
    if args.ticker:
        df = df[df["ticker"].str.upper() == args.ticker.upper()]
    elif args.limit > 0:
        df = df.head(args.limit)

    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    uv = await conn.fetchval(
        """SELECT build.universe_version
             FROM universe_builds AS build
             JOIN metric_vectors AS vector
               ON vector.universe_version = build.universe_version
            WHERE build.status = 'sealed'
              AND build.is_active
            GROUP BY build.universe_version, build.sealed_at
            ORDER BY build.sealed_at DESC NULLS LAST, build.universe_version DESC
            LIMIT 1"""
    )
    if not uv:
        raise SystemExit("No active sealed universe is available for reference DCF seeding")

    inserted = 0
    skipped = 0
    failed = 0
    try:
        for _, row in df.iterrows():
            t = str(row["ticker"]).upper()
            if not args.force:
                exists = await conn.fetchval(
                    """SELECT 1 FROM dcf_runs
                       WHERE ticker=$1
                         AND universe_version=$2
                         AND user_id IS NULL
                         AND visibility='reference'
                         AND scenario='base'
                       LIMIT 1""",
                    t,
                    uv,
                )
                if exists:
                    skipped += 1
                    continue
            inp = inputs_from_row(row)
            if inp is None:
                failed += 1
                continue
            out = run_dcf(inp)
            run_identity = f"pipeline|{t}|{uv}|{inp.model_dump_json()}|{ENGINE_VERSION}"
            if args.force:
                # DCF runs are append-only. A forced refresh creates a new,
                # explicitly superseding reference record; it never erases the
                # historical calculation it replaces.
                run_identity = f"{run_identity}|{now.isoformat()}"
            rid = "dcf_" + hashlib.sha256(run_identity.encode()).hexdigest()[:36]
            result = await conn.execute(
                """INSERT INTO dcf_runs
                   (run_id, ticker, user_id, scenario, inputs, outputs, engine_version,
                    universe_version, visibility, created_at)
                   VALUES ($1,$2,NULL,'base',$3::jsonb,$4::jsonb,$5,$6,'reference',$7)
                   ON CONFLICT (run_id) DO NOTHING""",
                rid,
                t,
                inp.model_dump_json(),
                out.model_dump_json(),
                out.engine_version,
                uv,
                now,
            )
            if result.endswith("1"):
                inserted += 1
            else:
                skipped += 1
        print(
            json.dumps(
                {
                    "universe_version": uv,
                    "n_panel": len(df),
                    "inserted": inserted,
                    "skipped": skipped,
                    "failed": failed,
                    "engine": ENGINE_VERSION,
                },
                indent=2,
            )
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
