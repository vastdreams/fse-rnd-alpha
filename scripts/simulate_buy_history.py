#!/usr/bin/env python3
"""
PATH: scripts/simulate_buy_history.py
PURPOSE: Run the SIMULATED historical BUY robustness study (sim_proxy_v1).

Pre-registered gates: contracts/simulated-buy-gates.json — frozen before
results. Pure math lives in backend/app/services/buy_simulation.py.

The output artifact is a frozen JSON an allocator can audit. It is NOT the
sealed track record; every disclosure from the contract is copied in verbatim.

Usage:
  DATABASE_URL=... python3 scripts/simulate_buy_history.py \
    [--universe-version univ_...] [--benchmark SPY] [--persist] \
    [--output data/exports/buy_sim_study_v1.json]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.buy_simulation import (  # noqa: E402
    HORIZONS_SESSIONS,
    STUDY_ID,
    evaluate_gates,
    forward_return_pit,
    parse_bars,
    rebalance_dates,
    summarise_study,
)
from app.services.price_history_service import get_cached_price_history  # noqa: E402

GATES_CONTRACT = ROOT / "contracts" / "simulated-buy-gates.json"


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
    ).replace("postgresql+asyncpg://", "postgresql://")


async def _vector_rows(universe_version: str | None) -> tuple[str, list[dict]]:
    import asyncpg

    conn = await asyncpg.connect(database_url())
    try:
        uv = universe_version or await conn.fetchval(
            "SELECT universe_version FROM universe_builds WHERE is_active LIMIT 1"
        )
        if not uv:
            raise SystemExit("No active universe and no --universe-version given")
        status = await conn.fetchval(
            "SELECT status FROM universe_builds WHERE universe_version=$1", uv
        )
        if status != "sealed":
            raise SystemExit(f"Universe {uv!r} must be sealed; got {status!r}")
        rows = await conn.fetch(
            """SELECT ticker, completeness_grade, kill_active,
                      (vector->'mos_live'->>'value')::float8   AS mos,
                      (vector->'fair_px_med'->>'value')::float8 AS fair_px_med
                 FROM metric_vectors WHERE universe_version=$1 ORDER BY ticker""",
            uv,
        )
        if not rows:
            raise SystemExit(f"Sealed universe {uv!r} has no metric vectors")
        return uv, [dict(r) for r in rows]
    finally:
        await conn.close()


async def _persist_simulated(uv: str, per_date: list[dict]) -> int:
    import asyncpg

    conn = await asyncpg.connect(database_url())
    written = 0
    try:
        async with conn.transaction():
            for row in per_date:
                if not row["members"]:
                    continue
                snap_id = f"simsnap_{row['as_of'].isoformat()}_{uuid.uuid4().hex[:12]}"
                await conn.execute(
                    """INSERT INTO buy_set_snapshots
                       (snapshot_id, universe_version, as_of_date, sealed_at,
                        engine_version, source_sha, n_buy, note, kind)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'simulated')
                       ON CONFLICT (universe_version, as_of_date, kind) DO NOTHING""",
                    snap_id,
                    uv,
                    row["as_of"],
                    datetime.now(timezone.utc),
                    STUDY_ID,
                    os.environ.get("RELEASE_SHA"),
                    len(row["members"]),
                    "SIMULATED robustness study (contracts/simulated-buy-gates.json) — not a sealed track record",
                )
                for t in row["members"]:
                    await conn.execute(
                        """INSERT INTO buy_set_members (snapshot_id, ticker, stance)
                           VALUES ($1,$2,'BUY') ON CONFLICT DO NOTHING""",
                        snap_id,
                        t,
                    )
                written += 1
    finally:
        await conn.close()
    return written


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe-version", default=None)
    ap.add_argument("--benchmark", default="SPY")
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--persist", action="store_true", help="Write kind='simulated' snapshots to DB")
    ap.add_argument("--output", default=str(ROOT / "data" / "exports" / "buy_sim_study_v1.json"))
    args = ap.parse_args()

    contract = json.loads(GATES_CONTRACT.read_text())
    contract_sha = hashlib.sha256(GATES_CONTRACT.read_bytes()).hexdigest()

    uv, vectors = await _vector_rows(args.universe_version)

    bench_hist = get_cached_price_history(args.benchmark, years=args.years, immutable_only=True)
    if not bench_hist or not bench_hist.get("bars"):
        raise SystemExit(
            f"Benchmark {args.benchmark} not in immutable price cache — run scripts/cache_benchmark_bars.py first"
        )
    bench_parsed = parse_bars(bench_hist["bars"])

    parsed_by_ticker: dict[str, list] = {}
    missing_cache: list[str] = []
    for v in vectors:
        t = v["ticker"].upper()
        hist = get_cached_price_history(t, years=args.years, immutable_only=True)
        bars = (hist or {}).get("bars") or []
        parsed = parse_bars(bars)
        if parsed:
            parsed_by_ticker[t] = parsed
        else:
            missing_cache.append(t)

    trading_days = [d for d, _ in bench_parsed]
    dates = rebalance_dates(trading_days)
    if not dates:
        raise SystemExit("No rebalance dates — benchmark cache too short")

    per_date: list[dict] = []
    excluded_missing_data: dict[str, int] = {}
    for as_of in dates:
        members: list[str] = []
        for v in vectors:
            t = v["ticker"].upper()
            parsed = parsed_by_ticker.get(t)
            if parsed is None:
                excluded_missing_data[t] = excluded_missing_data.get(t, 0) + 1
                continue
            res = evaluate_gates(
                parsed=parsed,
                as_of=as_of,
                mos=v["mos"],
                fair_px_med=v["fair_px_med"],
                grade=v["completeness_grade"],
                kill_active=v["kill_active"],
            )
            if res["decision"] == "excluded":
                excluded_missing_data[t] = excluded_missing_data.get(t, 0) + 1
            elif res["decision"] == "buy":
                members.append(t)
        returns = {
            h: {t: forward_return_pit(parsed_by_ticker[t], as_of=as_of, sessions=h) for t in members}
            for h in HORIZONS_SESSIONS
        }
        per_date.append({"as_of": as_of, "members": members, "returns": returns})

    inference = summarise_study(per_date=per_date, benchmark_parsed=bench_parsed)

    persisted = 0
    if args.persist:
        persisted = await _persist_simulated(uv, per_date)

    artifact = {
        "kind": "simulated_buy_study",
        "study_id": STUDY_ID,
        "label": "SIMULATED — robustness study, not a track record",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe_version": uv,
        "gates_contract": "contracts/simulated-buy-gates.json",
        "gates_contract_sha256": contract_sha,
        "benchmark": {
            "ticker": args.benchmark,
            "source": bench_hist.get("price_source"),
            "start": bench_hist.get("start"),
            "end": bench_hist.get("end"),
        },
        "cache_span": {
            "start": bench_parsed[0][0].isoformat(),
            "end": bench_parsed[-1][0].isoformat(),
            "n_tickers_with_bars": len(parsed_by_ticker),
            "n_tickers_missing_cache": len(missing_cache),
            "missing_cache": sorted(missing_cache),
        },
        "rebalances": [
            {
                "as_of": row["as_of"].isoformat(),
                "n_buy": len(row["members"]),
                "members": row["members"],
            }
            for row in per_date
        ],
        "excluded_missing_data": excluded_missing_data,
        "inference": inference,
        "disclosures": contract["disclosures"],
        "persisted_simulated_snapshots": persisted,
        "clean_ledger_note": "The clean sealed BUY ledger (kind='sealed') starts 2026-07 and is the only allocator-facing track record.",
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True))
    print(
        json.dumps(
            {
                "written": str(out),
                "rebalances": len(per_date),
                "mean_n_buy": round(
                    sum(len(r["members"]) for r in per_date) / len(per_date), 1
                ),
                "persisted": persisted,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
