"""
PATH: backend/app/api/routes/universe_rank.py
PURPOSE: Recipe catalog + full-universe ranking endpoints (W2a).

Auth: JWT required (fail closed) — this serves the research dataset.
Ship rules surfaced here:
- Recipe formula (human + exact) is returned with every rank response so the
  UI can always show the formula above the table.
- Output is variable-length (survivors), never a fixed N.
- reviewer_passed comes back as stored (null until a FinalReview exists).
"""

from __future__ import annotations

import json
import math
import time
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.routes.auth import get_current_user
from app.contracts.recipes import PRESET_RECIPES
from app.contracts.research import MetricVector, RankRecipe
from app.services.company_meta_service import (
    description_map,
    identity_map,
    live_price_from_mos,
    panel_valuation,
)
from app.services.rank_service import RankEngine, RankRequest


def _valid_fair_value_band(panel: dict) -> bool:
    """A sell target is safe to show only for a finite ordered value band."""

    values = (panel.get("fair_px_lo"), panel.get("fair_px_med"), panel.get("fair_px_hi"))
    return all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0 for value in values) and (
        values[0] <= values[1] <= values[2]
    )


async def _enrich_rows(rows: list[dict], vectors: list[MetricVector]) -> list[dict]:
    """Attach identity, business blurb, live price, and fair-value gap so the
    universe table reads like a research terminal — not ticker soup."""
    tickers = [v.ticker for v in vectors]
    idmap = await identity_map(tickers)
    blurbs = description_map(tickers, idmap)
    panel = panel_valuation()
    by_ticker = {v.ticker: v for v in vectors}

    # Cached FMP profiles (price_change) — disk only, never blocks rank.
    # A quote carries source/as-of metadata so the UI never calls a 30-day
    # cache entry "live" without qualification.
    from app.services.company_meta_service import CACHE_DIR
    import json as _json
    price_moves: dict[str, dict] = {}
    if CACHE_DIR.exists():
        for p in CACHE_DIR.glob("profile_*.json"):
            try:
                payload = _json.loads(p.read_text())
                prof = payload.get("profile") or {}
                t = p.stem.replace("profile_", "").upper()
                price_moves[t] = {
                    "price_live": prof.get("price_live"),
                    "price_change": prof.get("price_change"),
                    "price_change_pct": prof.get("price_change_pct"),
                    "price_as_of": prof.get("price_as_of") or payload.get("fetched_at"),
                    "price_source": prof.get("price_source") or prof.get("source") or "FMP stable/profile",
                    "price_stale": prof.get("price_stale"),
                }
            except Exception:
                continue

    for r in rows:
        t = r["ticker"]
        ident = idmap.get(t) or {}
        pan = panel.get(t) or {}
        v = by_ticker.get(t)
        mos = v.mos_live.value if v is not None else None
        frozen_band = (
            {
                "fair_px_lo": v.fair_px_lo.value,
                "fair_px_med": v.fair_px_med.value,
                "fair_px_hi": v.fair_px_hi.value,
            }
            if v is not None
            else {}
        )
        # A historical rank must never silently substitute today's panel lenses
        # for an invalid or missing frozen vector. Current panel values remain
        # optional overlays below, but never become historical fair value.
        band = frozen_band if _valid_fair_value_band(frozen_band) else {}
        fair_band_valid = _valid_fair_value_band(band)
        fair_med = band.get("fair_px_med") if fair_band_valid else None
        move = price_moves.get(t) or {}

        # Prefer the FMP quote when cached; otherwise expose the stored
        # research price basis. The latter is an exact MoS inversion, not a
        # market quote, and is labelled as such to users.
        price_live = move.get("price_live")
        price_source = move.get("price_source")
        price_as_of = move.get("price_as_of")
        price_is_derived = False
        if price_live is None:
            price_live = live_price_from_mos(fair_med, mos)
            price_source = "Research vector price basis (derived from stored MoS)"
            price_as_of = (
                v.mos_live.as_of_date.isoformat()
                if v is not None and v.mos_live.as_of_date is not None
                else None
            )
            price_is_derived = price_live is not None

        r["name"] = ident.get("name")
        r["industry"] = ident.get("industry")
        r["size"] = ident.get("size")
        r["description"] = blurbs.get(t)
        r["fair_px_lo"] = band.get("fair_px_lo") if fair_band_valid else None
        r["fair_px_med"] = fair_med
        r["fair_px_hi"] = band.get("fair_px_hi") if fair_band_valid else None
        r["fair_value_band_valid"] = fair_band_valid
        r["fair_value_source"] = (
            "Frozen universe vector"
            if fair_band_valid
            else "Unavailable in frozen universe vector"
        )
        r["fair_value_band_note"] = (
            None
            if fair_band_valid
            else "Fair-value band unavailable: expected finite low ≤ median ≤ high lenses."
        )
        r["price_snapshot"] = pan.get("price_snapshot")
        r["price_live"] = price_live
        r["price_as_of"] = price_as_of
        r["price_source"] = price_source
        r["price_stale"] = move.get("price_stale")
        r["price_is_derived"] = price_is_derived
        r["price_change"] = move.get("price_change")
        r["price_change_pct"] = move.get("price_change_pct")
        r["quadrant"] = pan.get("quadrant")
        r["mos_live"] = mos
        # Dollar gap: median fair value − live price (positive = trading below FV / "cheap")
        if price_live is not None and fair_med is not None:
            r["vs_median_usd"] = fair_med - price_live
            # Frozen MoS may use a different captured price basis than a newer
            # FMP quote. Calculate the displayed quote gap independently.
            r["vs_median_pct"] = (
                (fair_med - price_live) / price_live
                if isinstance(price_live, (int, float)) and price_live > 0
                else None
            )
        else:
            r["vs_median_usd"] = None
            r["vs_median_pct"] = None
        if v is not None:
            r["retention"] = v.retention.value
            r["rev_cagr"] = v.rev_cagr.value if v.rev_cagr.value is not None else pan.get("rev_cagr")
            r["gm"] = v.gm.value if v.gm.value is not None else pan.get("gm")
            r["fcfm_sbc"] = v.fcfm_sbc.value if v.fcfm_sbc.value is not None else pan.get("fcfm_sbc")
            r["roic"] = v.roic.value
            r["rd_int"] = v.rd_int.value
            r["rd_prod"] = v.rd_prod.value
            r["rule40"] = v.rule40.value
        else:
            r["retention"] = None
            r["rev_cagr"] = pan.get("rev_cagr")
            r["gm"] = pan.get("gm")
            r["fcfm_sbc"] = pan.get("fcfm_sbc")
            r["roic"] = None
            r["rd_int"] = None
            r["rd_prod"] = None
            r["rule40"] = None

        r["fundamentals_baseline_as_of"] = pan.get("fundamentals_baseline_as_of")
        r["fundamentals_as_of"] = pan.get("fundamentals_as_of")
        rev = pan.get("revenue_usd")
        npm = pan.get("npm")
        r["revenue_usd"] = rev
        r["npm"] = npm
        r["opm"] = pan.get("opm")
        r["fcf_usd"] = pan.get("fcf_usd")
        if rev is not None and npm is not None:
            r["net_profit_usd"] = rev * npm
        else:
            r["net_profit_usd"] = None
    return rows

router = APIRouter()
_engine = RankEngine()

# In-process TTL cache: parsing 347 MetricVector JSON payloads through pydantic
# on EVERY rank call dominates latency. Vectors only change when a builder runs,
# so a short TTL is safe (staleness bounded at 5 min, and builds bump the
# universe_version key anyway).
_VECTOR_TTL_SECONDS = 300
_vector_cache: dict[str, tuple[float, list[MetricVector]]] = {}


async def _load_vectors(db: AsyncSession, universe_version: str) -> list[MetricVector]:
    hit = _vector_cache.get(universe_version)
    if hit and (time.monotonic() - hit[0]) < _VECTOR_TTL_SECONDS:
        return hit[1]
    res = await db.execute(
        text("SELECT vector FROM metric_vectors WHERE universe_version = :uv"),
        {"uv": universe_version},
    )
    vectors = [
        MetricVector.model_validate(p if isinstance(p, dict) else json.loads(p))
        for (p,) in res.fetchall()
    ]
    _vector_cache[universe_version] = (time.monotonic(), vectors)
    return vectors


async def _active_universe_version(db: AsyncSession) -> str:
    """Return the one explicitly activated sealed research build."""

    version = await db.scalar(
        text(
            """SELECT universe_version
                 FROM universe_builds
                WHERE status='sealed' AND is_active=true
                LIMIT 1"""
        )
    )
    if not version:
        raise HTTPException(
            404,
            "No active sealed universe build is available; activate a sealed build first.",
        )
    return str(version)


async def _require_sealed_universe(db: AsyncSession, universe_version: str) -> None:
    status = await db.scalar(
        text(
            "SELECT status FROM universe_builds WHERE universe_version=:uv"
        ),
        {"uv": universe_version},
    )
    if status != "sealed":
        raise HTTPException(404, f"Universe version {universe_version} is not a sealed build")


@router.get("/recipes")
async def list_recipes(user: dict = Depends(get_current_user)) -> dict:
    """All preset recipes with formulas and benchmarks (R9 customs come from DB)."""
    return {
        "recipes": [r.model_dump() for r in PRESET_RECIPES],
        "default_recipe": "R3",
        "note": "Research only — not investment advice.",
    }


class CustomRecipeBody(BaseModel):
    """R9 custom combination builder: axes over MetricVector fields, equal weights."""

    name: str = Field(default="Custom recipe", max_length=120)
    axes: list[str] = Field(min_length=1, max_length=10)
    universe_version: Optional[str] = None
    as_of: Optional[date] = None


@router.post("/rank/custom")
async def rank_custom(
    body: CustomRecipeBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """R9: rank the universe on a user-selected axis combination (formula shown)."""
    for axis in body.axes:
        if axis not in MetricVector.model_fields:
            raise HTTPException(400, f"'{axis}' is not a MetricVector field")
    recipe = RankRecipe(
        recipe_id="R9",
        name=body.name,
        formula_human=f"Equal-weight robust z of: {', '.join(body.axes)}",
        formula_exact=f"score = Σ z({axis})" if len(body.axes) == 1 else f"score = Σ z over {body.axes}",
        hard_filters=["kill_active == False"],
        axes=body.axes,
        benchmark_vs="any preset; formula always on screen",
        custom=True,
    )
    universe_version = body.universe_version
    if universe_version is None:
        universe_version = await _active_universe_version(db)
    else:
        await _require_sealed_universe(db, universe_version)
    vectors = await _load_vectors(db, universe_version)
    resolved_as_of = body.as_of or max(v.computed_at.date() for v in vectors)
    ranked = _engine.rank(
        vectors, RankRequest(recipe=recipe, universe_version=universe_version, as_of=resolved_as_of)
    )
    return {
        "recipe": recipe.model_dump(),
        "universe_version": universe_version,
        "as_of": resolved_as_of.isoformat(),
        "n_universe": len(vectors),
        "n_ranked": len(ranked),
        "rows": await _enrich_rows([r.model_dump() for r in ranked], vectors),
        "note": "Research only — not investment advice.",
    }


@router.get("/rank")
async def rank_universe(
    recipe_id: str = Query(default="R3", pattern="^R[1-8]$"),
    universe_version: Optional[str] = Query(default=None, description="Defaults to active sealed build"),
    as_of: Optional[date] = Query(default=None, description="PIT cutoff; defaults to build timestamp"),
    include_excluded: bool = Query(default=False, description="Also return excluded names with reasons"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Rank the ENTIRE universe under a recipe. Variable-length output."""
    recipe: RankRecipe = next(r for r in PRESET_RECIPES if r.recipe_id == recipe_id)

    if universe_version is None:
        universe_version = await _active_universe_version(db)
    else:
        await _require_sealed_universe(db, universe_version)

    vectors = await _load_vectors(db, universe_version)

    if not vectors:
        raise HTTPException(404, f"Universe version {universe_version} has no metric vectors")

    resolved_as_of = as_of or max(v.computed_at.date() for v in vectors)
    request = RankRequest(recipe=recipe, universe_version=universe_version, as_of=resolved_as_of)
    ranked = _engine.rank(vectors, request)

    out = {
        "recipe": recipe.model_dump(),  # formula ALWAYS travels with the rank
        "universe_version": universe_version,
        "as_of": resolved_as_of.isoformat(),
        "n_universe": len(vectors),
        "n_ranked": len(ranked),
        "rows": await _enrich_rows([r.model_dump() for r in ranked], vectors),
        "note": "Research only — not investment advice.",
    }
    if include_excluded:
        excluded = _engine.exclusions(vectors, request)
        out["excluded"] = await _enrich_rows(sorted(excluded, key=lambda e: e["ticker"]), vectors)
        out["n_excluded"] = len(excluded)
    return out
