#!/usr/bin/env python3
"""
PATH: scripts/backfill_thesis_fields.py
PURPOSE: One-shot backfill of the thesis fields (rd_composite, rd_elig,
  survivable, payoff_skew, weave_z) into an already-sealed universe's
  metric_vectors JSONB.

HONESTY: uses ONLY values already sealed inside that universe's own vectors —
no new data enters a sealed build. The implied sealed price for payoff_skew is
derived arithmetically as fair_px_med / (1 + mos_live), both sealed values.
Idempotent: rows that already carry rd_composite keys are skipped unless
--force is given. Every write is logged per ticker.

Usage:
  DATABASE_URL=... python3 scripts/backfill_thesis_fields.py \
    --universe-version univ_... [--apply] [--force]

Without --apply it is a dry run and prints what would change.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.thesis_fields import compute_thesis_fields, load_thesis_contract  # noqa: E402

ENGINE_NOTE = "backfill_thesis_fields.py — computed from this universe's own sealed values only"


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
    ).replace("postgresql+asyncpg://", "postgresql://")


def _val(vec: dict, field: str):
    node = vec.get(field)
    if isinstance(node, dict):
        return node.get("value")
    return node


def _dates(vec: dict, field: str) -> tuple:
    node = vec.get(field)
    if isinstance(node, dict):
        return node.get("as_of_date"), node.get("available_date")
    return None, None


def implied_sealed_price(vec: dict):
    """fair_px_med / (1 + mos_live): arithmetic on two sealed values."""
    med = _val(vec, "fair_px_med")
    mos = _val(vec, "mos_live")
    if med is None or mos is None or (1.0 + mos) <= 0:
        return None
    return med / (1.0 + mos)


async def main() -> None:
    import asyncpg

    ap = argparse.ArgumentParser()
    ap.add_argument("--universe-version", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true", help="Recompute rows that already have thesis keys")
    args = ap.parse_args()

    contract = load_thesis_contract()
    conn = await asyncpg.connect(database_url())
    try:
        status = await conn.fetchval(
            "SELECT status FROM universe_builds WHERE universe_version=$1",
            args.universe_version,
        )
        if status != "sealed":
            raise SystemExit(f"Universe {args.universe_version!r} must be sealed; got {status!r}")
        rows = await conn.fetch(
            "SELECT ticker, vector FROM metric_vectors WHERE universe_version=$1 ORDER BY ticker",
            args.universe_version,
        )
        if not rows:
            raise SystemExit(f"No metric vectors for {args.universe_version!r}")

        vecs = [json.loads(r["vector"]) if isinstance(r["vector"], str) else dict(r["vector"]) for r in rows]
        already = [i for i, v in enumerate(vecs) if isinstance(v.get("rd_composite"), dict) and v["rd_composite"].get("value") is not None]
        if already and not args.force:
            print(f"{len(already)} vectors already carry thesis fields; skipping them (use --force to recompute)")

        thesis_rows = []
        for v in vecs:
            thesis_rows.append(
                {
                    "rd_int": _val(v, "rd_int"),
                    "rd_capital": _val(v, "rd_capital"),
                    "rd_prod": _val(v, "rd_prod"),
                    "rd_mom": _val(v, "rd_mom"),
                    "roic": _val(v, "roic"),
                    "gm": _val(v, "gm"),
                    "fcfm_sbc": _val(v, "fcfm_sbc"),
                    "rule40": _val(v, "rule40"),
                    "runway_yrs": _val(v, "runway_yrs"),
                    "dilution_ann": _val(v, "dilution_ann"),
                    "retention": _val(v, "retention"),
                    "mos_live": _val(v, "mos_live"),
                    "ret_3m": _val(v, "ret_3m"),
                    "ret_12m": _val(v, "ret_12m"),
                    "drawdown_from_peak": _val(v, "drawdown_from_peak"),
                    "price": implied_sealed_price(v),
                    "fair_px_lo": _val(v, "fair_px_lo"),
                    "fair_px_hi": _val(v, "fair_px_hi"),
                }
            )
        results = compute_thesis_fields(thesis_rows, contract)

        n_written = 0
        n_elig = sum(1 for r in results if r["rd_elig"] is True)
        n_surv = sum(1 for r in results if r["survivable"] is True)
        async with conn.transaction():
            for r, v, tf in zip(rows, vecs, results):
                idx = vecs.index(v)
                if idx in already and not args.force:
                    continue
                engine = v.get("mos_live", {}).get("engine_version") if isinstance(v.get("mos_live"), dict) else None
                rd_asof, rd_avail = _dates(v, "rd_int")
                mos_asof, mos_avail = _dates(v, "mos_live")
                v["rd_composite"] = (
                    {
                        "value": tf["rd_composite"],
                        "as_of_date": rd_asof,
                        "available_date": rd_avail,
                        "claim_ids": [],
                        "formula": "mean robust-z(rd_int, rd_capital, rd_prod, rd_mom) — thesis-gates.json rd_composite ("
                        + ENGINE_NOTE
                        + ")",
                        "engine_version": engine,
                    }
                    if tf["rd_composite"] is not None and rd_asof and rd_avail
                    else {"value": None, "as_of_date": None, "available_date": None, "claim_ids": [], "formula": None, "engine_version": None}
                )
                v["rd_elig"] = tf["rd_elig"]
                v["survivable"] = tf["survivable"]
                v["payoff_skew"] = (
                    {
                        "value": tf["payoff_skew"],
                        "as_of_date": mos_asof,
                        "available_date": mos_avail,
                        "claim_ids": [],
                        "formula": "(fair_px_hi − price_implied)/(price_implied − fair_px_lo); price_implied = fair_px_med/(1+mos_live) ("
                        + ENGINE_NOTE
                        + ")",
                        "engine_version": engine,
                    }
                    if tf["payoff_skew"] is not None and mos_asof and mos_avail
                    else {"value": None, "as_of_date": None, "available_date": None, "claim_ids": [], "formula": None, "engine_version": None}
                )
                v["payoff_skew_label"] = tf["payoff_skew_label"]
                v["weave_z"] = tf["weave"]
                if args.apply:
                    await conn.execute(
                        "UPDATE metric_vectors SET vector=$1 WHERE universe_version=$2 AND ticker=$3",
                        json.dumps(v),
                        args.universe_version,
                        r["ticker"],
                    )
                n_written += 1

        print(
            json.dumps(
                {
                    "universe_version": args.universe_version,
                    "mode": "applied" if args.apply else "dry_run",
                    "vectors": len(rows),
                    "written": n_written if args.apply else 0,
                    "would_write": n_written,
                    "rd_eligible": n_elig,
                    "survivable": n_surv,
                }
            )
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
