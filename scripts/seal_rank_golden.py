#!/usr/bin/env python3
"""Seal rank-golden.json from the live rank API inside the backend container."""
from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient

from app.api.routes.auth import get_current_user
from app.main import app


async def main() -> None:
    async def fake_user():
        return type(
            "U",
            (),
            {
                "id": "seal",
                "email": "seal@finsoeasy.com",
                "role": "admin",
                "is_active": True,
            },
        )()

    app.dependency_overrides[get_current_user] = fake_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/universe/rank", params={"mode": "buy", "limit": 138})
        print("status", r.status_code)
        r.raise_for_status()
        j = r.json()

    rows = j["rows"]
    fields = [
        "ticker",
        "recipe_id",
        "universe_version",
        "rank",
        "score",
        "contributions",
        "completeness_grade",
        "freshness_ok",
        "kill_active",
        "reviewer_passed",
        "name",
        "industry",
        "price_live",
        "fair_px_lo",
        "fair_px_med",
        "fair_px_hi",
        "mos_live",
        "vs_median_pct",
        "revenue_usd",
        "rev_cagr",
        "gm",
        "fcfm_sbc",
        "roic",
        "rd_prod",
        "retention",
    ]
    by = {x["ticker"]: x for x in rows}
    edge = {
        "KSPI": ["top_1", "below_band", "mos_eq_vs", "retention_null", "grade_c"],
        "APP": ["top_2", "above_band", "mos_eq_vs", "retention_null", "grade_c"],
        "SPSC": ["top_3", "below_band", "mos_eq_vs", "retention_null", "grade_a"],
        "GRND": ["top_4", "inside_band", "mos_eq_vs", "retention_null", "grade_b"],
        "DAVE": ["top_5", "above_band", "mos_eq_vs", "retention_null", "grade_c"],
        "YOU": ["top_6", "inside_band", "mos_eq_vs", "retention_null", "grade_c"],
        "GCT": ["top_7", "below_band", "mos_eq_vs", "retention_null", "grade_c"],
        "KARO": ["top_8", "above_band", "mos_eq_vs", "retention_null", "grade_c"],
        "DSP": ["top_9", "inside_band", "mos_eq_vs", "retention_null", "grade_b"],
        "ADBE": ["top_10", "inside_band", "mos_eq_vs", "retention_null", "grade_c"],
        "MAPS": ["mos_ne_vs", "retention_null", "grade_c"],
        "PCTY": ["retention_disclosed", "inside_band"],
    }
    curated = []
    for t, tags in edge.items():
        row = by[t]
        slim = {k: row.get(k) for k in fields}
        slim["edge_tags"] = tags
        curated.append(slim)

    meta = {
        "universe_version": j.get("universe_version") or curated[0]["universe_version"],
        "recipe_id": (j.get("recipe") or {}).get("recipe_id") or "R3",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "GET /api/universe/rank?mode=buy&limit=138 via ASGI admin override",
        "n_universe_ranked": j.get("n_ranked"),
        "kill_active_note": "N/A — no kill_active=true rows in this R3 survivor set",
    }
    pre = {"meta": meta, "rows": curated}
    # Canonical form so FE/BE CI can recompute the same digest.
    body = json.dumps(pre, indent=2, sort_keys=True) + "\n"
    sha = hashlib.sha256(body.encode()).hexdigest()
    pre["meta"]["sha256"] = sha
    final = json.dumps(pre, indent=2, sort_keys=True) + "\n"
    open("/tmp/rank-golden.json", "w").write(final)
    open("/tmp/rank-golden.json.sha256", "w").write(f"{sha}  rank-golden.json\n")
    print(json.dumps({"n": len(curated), "sha256": sha, "uv": meta["universe_version"]}))


if __name__ == "__main__":
    asyncio.run(main())
