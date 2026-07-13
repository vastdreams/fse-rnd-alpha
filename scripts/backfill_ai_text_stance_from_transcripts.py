#!/usr/bin/env python3
"""
PATH: scripts/backfill_ai_text_stance_from_transcripts.py
PURPOSE: Fill ai_text_stance from av_transcripts_raw via text_exposure (no invention).

Writes/updates first_principles_overlay.csv `stance` only when a transcript
yields measurable AI-salient language. Blank stays Unknown — never invented.

Re-run build_universe.py after to refresh metric vectors.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from saas_ai.analysis.text_exposure import _as_segments, _measure_one  # noqa: E402

OVERLAY = REPO / "data/saas_ai_repricing/first_principles_overlay.csv"
DSN = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
).replace("postgresql+asyncpg://", "postgresql://")


async def _latest_stance(conn, ticker: str) -> dict | None:
    rows = await conn.fetch(
        "SELECT quarter, transcript FROM av_transcripts_raw "
        "WHERE symbol=$1 AND n_segments>0 ORDER BY quarter DESC LIMIT 8",
        ticker.upper(),
    )
    for r in rows:
        segs = _as_segments(r["transcript"])
        if not segs:
            continue
        m = _measure_one(segs)
        if m["n_sentences"] < 20:
            continue
        if m["n_ai_sentences"] < 1:
            continue
        return {
            "ticker": ticker.upper(),
            "quarter": r["quarter"],
            "stance": float(m["stance"]),
            "aiexp": float(m["aiexp"]),
            "n_ai": int(m["n_ai_sentences"]),
            "n_aug": int(m["n_aug"]),
            "n_auto": int(m["n_auto"]),
        }
    return None


async def run(args: argparse.Namespace) -> dict:
    import asyncpg

    if not args.overlay.exists():
        raise SystemExit(f"overlay missing: {args.overlay}")

    ov = pd.read_csv(args.overlay)
    if "ticker" not in ov.columns:
        raise SystemExit("overlay needs ticker column")
    if "stance" not in ov.columns:
        ov["stance"] = pd.NA

    tickers = ov["ticker"].astype(str).str.upper().tolist()
    if args.limit:
        tickers = tickers[: args.limit]

    filled = skipped = 0
    conn = await asyncpg.connect(DSN)
    try:
        for t in tickers:
            idx = ov.index[ov["ticker"].astype(str).str.upper() == t]
            if len(idx) == 0:
                continue
            i = int(idx[0])
            if pd.notna(ov.at[i, "stance"]):
                skipped += 1
                continue
            m = await _latest_stance(conn, t)
            if not m:
                skipped += 1
                continue
            print(
                f"  fill {t} stance={m['stance']:.3f} from {m['quarter']} "
                f"(ai={m['n_ai']} aug={m['n_aug']} auto={m['n_auto']})",
                flush=True,
            )
            if not args.dry_run:
                ov.at[i, "stance"] = m["stance"]
            filled += 1
    finally:
        await conn.close()

    if not args.dry_run and filled:
        ov.to_csv(args.overlay, index=False)
        print(f"wrote {args.overlay}", flush=True)
    return {"filled": filled, "skipped": skipped, "dry_run": args.dry_run}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overlay", type=Path, default=OVERLAY)
    args = ap.parse_args()
    out = asyncio.run(run(args))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
