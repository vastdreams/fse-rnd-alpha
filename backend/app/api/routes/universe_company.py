"""
PATH: backend/app/api/routes/universe_company.py
PURPOSE: W3/W4 company research endpoints — eight-tab deep dive, Audit drawer,
audit pack export, DCF workbench, admin KPIs.

Ship rules:
- Every number returned carries its MetricValue provenance (PIT dates, claim
  ids, formula, engine version) so the UI can open an Audit drawer anywhere.
- Missing = null, labeled Unknown by the UI. Never imputed here.
- Audit pack exports are watermarked research-only with user identity.
- reviewer_passed comes only from final_reviews rows.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.routes.auth import get_current_user, require_operator
from app.contracts.recipes import LITERATURE_BINDS
from app.contracts.research import MetricVector
from app.services.close_call_service import build_close_call_waterfall
from app.services.buy_performance_book import (
    empty_book_payload,
    summarise_snapshot,
    utc_now_naive,
)
from app.services.catalyst_event_service import load_catalyst_anchors_from_db_rows
from app.services.dcf_service import DcfInputs, run_dcf
from app.services.financials_service import FinancialsUnavailable, get_financials
from app.services.company_meta_service import (
    company_profile,
    identity_map,
    live_price_from_mos,
    panel_valuation,
)
from app.services.price_history_service import (
    PriceHistoryUnavailable,
    get_cached_price_history,
    get_price_history,
)

router = APIRouter()


@router.get("/price-history/{ticker}")
async def company_price_history(
    ticker: str,
    years: int = 3,
    user: dict = Depends(get_current_user),
) -> dict:
    """Day-by-day adjusted closes for the company price chart."""
    try:
        return {
            **(await get_price_history(ticker, years=years)),
            "overlay_kind": "current_price_history",
            "historical_snapshot": False,
        }
    except PriceHistoryUnavailable as e:
        raise HTTPException(404, str(e))


@router.get("/financials/{ticker}")
async def company_financials(
    ticker: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """As-reported annual + quarterly statements and ratios (Sharadar SF1).

    Available for ANY Sharadar-covered ticker, not just universe names —
    financial-statement depth shouldn't be gated on panel membership.
    """
    try:
        return {
            **(await get_financials(ticker)),
            "overlay_kind": "current_financials",
            "historical_snapshot": False,
        }
    except FinancialsUnavailable as e:
        raise HTTPException(404, str(e))

_now = lambda: datetime.now(timezone.utc).replace(tzinfo=None)  # noqa: E731


def _valid_fair_value_band(panel: dict) -> bool:
    values = (panel.get("fair_px_lo"), panel.get("fair_px_med"), panel.get("fair_px_hi"))
    return all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0 for value in values) and (
        values[0] <= values[1] <= values[2]
    )


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _frozen_dcf_seed(ticker: str, panel: dict) -> dict | None:
    """Expose only existing panel assumptions; never synthesize a valuation input."""

    ticker = ticker.upper()
    growth = _finite_number(panel.get("rev_cagr"))
    wacc = _finite_number(panel.get("wacc"))
    if growth is None or wacc is None:
        return None
    fcf_margin = _finite_number(panel.get("fcfm_sbc"))
    inputs = DcfInputs(
        ticker=ticker,
        scenario="base",
        revenue_usd=_finite_number(panel.get("revenue_usd")),
        fcf_sbc_usd=_finite_number(panel.get("fcf_usd")),
        fcfm_sbc=fcf_margin,
        net_cash_usd=_finite_number(panel.get("net_cash_usd")) or 0.0,
        ev_mult_usd=_finite_number(panel.get("ev_mult_usd")),
        shares_fut_implied=None,
        price=_finite_number(panel.get("price_snapshot")),
        # Mirror the release seeding script's bounded engine input, while
        # retaining the reported panel value in its provenance note.
        growth=max(-0.10, min(0.30, growth)),
        wacc=wacc,
        target_margin=fcf_margin if fcf_margin is not None and fcf_margin > 0 else None,
    )
    missing = [
        name
        for name, value in inputs.model_dump().items()
        if name
        in {
            "revenue_usd",
            "fcf_sbc_usd",
            "fcfm_sbc",
            "ev_mult_usd",
            "shares_fut_implied",
            "price",
            "target_margin",
        }
        and value is None
    ]
    return {
        "inputs": inputs.model_dump(mode="json"),
        "source": "Frozen fundamental-value panel",
        "as_of": panel.get("fundamentals_as_of"),
        "missing_inputs": missing,
        "note": (
            "Inputs come from the versioned release panel. Empty fields are "
            "unknown and must be supplied explicitly before a lens can use them."
        ),
    }


async def _latest_version(db: AsyncSession) -> str:
    version = await db.scalar(
        text(
            """SELECT universe_version
                 FROM universe_builds
                WHERE status='sealed' AND is_active=true
                LIMIT 1"""
        )
    )
    if not version:
        raise HTTPException(404, "No active sealed universe build available")
    return str(version)


async def _require_sealed_version(db: AsyncSession, universe_version: str) -> None:
    status = await db.scalar(
        text(
            "SELECT status FROM universe_builds WHERE universe_version=:uv"
        ),
        {"uv": universe_version},
    )
    if status != "sealed":
        raise HTTPException(404, f"Universe version {universe_version} is not a sealed build")


async def _vector(db: AsyncSession, ticker: str, uv: str) -> MetricVector:
    res = await db.execute(
        text(
            """SELECT vector
                 FROM metric_vectors AS vector
                 JOIN universe_builds AS build
                   ON build.universe_version = vector.universe_version
                WHERE vector.ticker=:t
                  AND vector.universe_version=:uv
                  AND build.status='sealed'"""
        ),
        {"t": ticker.upper(), "uv": uv},
    )
    row = res.first()
    if row is None:
        raise HTTPException(404, f"{ticker} not in universe {uv}")
    raw = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    return MetricVector.model_validate(raw)


def _vector_claim_ids(vec: MetricVector) -> list[str]:
    """Return only evidence explicitly bound into this immutable vector."""

    return sorted(
        {
            claim_id
            for field_name in MetricVector.model_fields
            for claim_id in (getattr(getattr(vec, field_name), "claim_ids", None) or [])
        }
    )


def _utc_naive(value: datetime) -> datetime:
    """Normalize contract datetimes for legacy PostgreSQL timestamp columns."""

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _anchor_known_at_vector(
    *,
    vector_computed_at: datetime,
    claim_extracted_at: datetime | None,
    snapshot_available_date: date | None,
) -> bool:
    """Do not let later catalyst evidence rewrite a frozen universe's stance."""

    if claim_extracted_at is None or snapshot_available_date is None:
        return False
    cutoff = _utc_naive(vector_computed_at)
    return _utc_naive(claim_extracted_at) <= cutoff and snapshot_available_date <= cutoff.date()


async def _catalyst_anchors_for_vector(
    db: AsyncSession, vec: MetricVector, universe_version: str
) -> list[dict]:
    """Resolve only catalysts bound to this immutable build and known at build time."""

    cutoff = _utc_naive(vec.computed_at)
    rows = (
        await db.execute(
            text(
                """SELECT claim.ticker, claim.value_text, claim.excerpt_locator
                   FROM evidence_claims AS claim
                   JOIN universe_evidence_refs AS ref
                     ON ref.claim_id = claim.claim_id
                   JOIN source_snapshots AS snapshot
                     ON snapshot.snapshot_id = claim.snapshot_id
                   WHERE ref.universe_version=:universe_version
                     AND claim.field='catalyst_anchor'
                     AND claim.ticker=:ticker
                     AND claim.extracted_at <= :cutoff
                     AND snapshot.available_date <= :available_on"""
            ),
            {
                "ticker": vec.ticker,
                "universe_version": universe_version,
                "cutoff": cutoff,
                "available_on": cutoff.date(),
            },
        )
    ).fetchall()
    return load_catalyst_anchors_from_db_rows(list(rows)).get(vec.ticker, [])


# =============================================================================
# Company deep dive (eight tabs read from this one payload)
# =============================================================================

@router.get("/company/{ticker}")
async def company_research(
    ticker: str,
    universe_version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    uv = universe_version or await _latest_version(db)
    await _require_sealed_version(db, uv)
    active_universe = await _latest_version(db)
    vec = await _vector(db, ticker, uv)
    t = ticker.upper()

    gates = (await db.execute(
        text("""SELECT gate_id, passed, threshold, observed FROM gate_evaluations
                WHERE ticker=:t AND universe_version=:uv
                ORDER BY evaluated_at DESC, gate_id"""),
        {"t": t, "uv": uv},
    )).mappings().all()
    seen: dict[str, dict] = {}
    for g in gates:
        seen.setdefault(g["gate_id"], dict(g))

    ds_runs = (await db.execute(
        text("""SELECT run_id, job, output_kind, status, severity, finished_at
                FROM deepseek_audit_runs
                WHERE ticker=:t AND universe_version=:uv
                ORDER BY finished_at DESC LIMIT 10"""),
        {"t": t, "uv": uv},
    )).mappings().all()

    review = (await db.execute(
        text("""SELECT review_id, passed, trigger, reviewed_at, notes FROM final_reviews
                WHERE ticker=:t AND universe_version=:uv
                ORDER BY reviewed_at DESC LIMIT 1"""), {"t": t, "uv": uv}
    )).mappings().first()

    dcf_runs = (await db.execute(
        text(
            """SELECT run_id, scenario, inputs, outputs, engine_version, created_at, universe_version, visibility
               FROM dcf_runs
               WHERE ticker=:t AND universe_version=:uv
                 AND owner_state='owned'
                 AND (user_id=:user_id OR visibility='reference')
               ORDER BY created_at DESC LIMIT 20"""
        ),
        {"t": t, "uv": uv, "user_id": user["id"]},
    )).mappings().all()

    profile = await company_profile(t)
    idmap = await identity_map([t])
    dcf_seed = None
    if uv == active_universe:
        try:
            dcf_seed = _frozen_dcf_seed(t, panel_valuation().get(t, {}))
        except OSError:
            dcf_seed = None
    frozen_band = {
        "fair_px_lo": vec.fair_px_lo.value,
        "fair_px_med": vec.fair_px_med.value,
        "fair_px_hi": vec.fair_px_hi.value,
    }
    valuation_source = frozen_band if _valid_fair_value_band(frozen_band) else {}
    valuation_source_label = (
        "Frozen universe vector"
        if valuation_source
        else "Unavailable in frozen universe vector"
    )

    # Valuation range: the paper run's own triangulated lenses + live price.
    valuation_range = None
    if _valid_fair_value_band(valuation_source):
        live_px = (profile or {}).get("price_live")
        lo, med, hi = (
            valuation_source["fair_px_lo"],
            valuation_source["fair_px_med"],
            valuation_source["fair_px_hi"],
        )
        zone = None
        if live_px is not None and lo is not None and hi is not None:
            zone = (
                "below conservative lens" if live_px < lo
                else "between conservative and median lens" if live_px < med
                else "between median and high lens" if live_px < hi
                else "above high lens"
            )
        valuation_range = {
            **valuation_source,
            "price_live": live_px,
            "price_as_of": (profile or {}).get("price_as_of"),
            "price_source": (profile or {}).get("price_source"),
            "price_stale": (profile or {}).get("price_stale"),
            "fair_value_source": valuation_source_label,
            "zone": zone,
            "gap_to_median": (med / live_px - 1) if (live_px and med) else None,
            "note": "Triangulated fair-value lenses from the paper research run "
                    "(2-stage DCF + normalized-margin DCF + peer multiple). "
                    "Research BUY/HOLD stance is computed separately in close_call_waterfall.",
        }
    elif any(value is not None for value in frozen_band.values()):
        valuation_range = {
            "fair_px_lo": None,
            "fair_px_med": None,
            "fair_px_hi": None,
            "price_live": (profile or {}).get("price_live"),
            "price_as_of": (profile or {}).get("price_as_of"),
            "price_source": (profile or {}).get("price_source"),
            "invalid_band": True,
            "note": "Fair-value band unavailable: expected finite low ≤ median ≤ high lenses.",
        }

    # Close-call waterfall (MedTwin-style) — never invents catalysts
    price_bars: list = []
    try:
        hist = await get_price_history(t, years=3)
        price_bars = hist.get("bars") or []
    except PriceHistoryUnavailable:
        price_bars = []

    extra = await _catalyst_anchors_for_vector(db, vec, uv)

    close_call = build_close_call_waterfall(
        ticker=t,
        universe_version=uv,
        vector=vec,
        valuation_range=valuation_range,
        price_bars=price_bars,
        extra_anchors=extra,
    )

    return {
        "ticker": t,
        "universe_version": uv,
        "identity": idmap.get(t),
        "profile": profile,
        "valuation_range": valuation_range,
        "close_call_waterfall": close_call.model_dump(mode="json"),
        "close_call_data_mode": "current_overlay",
        "vector": vec.model_dump(mode="json"),
        "gates": list(seen.values()),
        "deepseek_runs": [dict(r) for r in ds_runs],
        "final_review": dict(review) if review else None,
        "reviewer_passed": review["passed"] if review else None,
        "dcf_seed": dcf_seed,
        "dcf_runs": [
            {**dict(r),
             "inputs": r["inputs"] if isinstance(r["inputs"], dict) else json.loads(r["inputs"]),
             "outputs": r["outputs"] if isinstance(r["outputs"], dict) else json.loads(r["outputs"])}
            for r in dcf_runs
        ],
        "note": "Research only — not investment advice. BUY stance is waterfall-gated.",
    }


@router.get("/stances")
async def research_stances(
    stance: Optional[str] = None,
    universe_version: Optional[str] = None,
    limit: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Research BUY/HOLD/… list from the close-call waterfall (fail-closed).

    Uses cached price history only (no live SEP storm). Tickers without a
    cached tape keep an explicit UNKNOWN tape/catalyst stage; they are still
    returned when no stance filter is requested so the table has coverage.
    """
    uv = universe_version or await _latest_version(db)
    await _require_sealed_version(db, uv)
    res = await db.execute(
        text("SELECT ticker, vector FROM metric_vectors WHERE universe_version=:uv"),
        {"uv": uv},
    )
    rows = res.fetchall()
    vectors = [
        (
            ticker.upper(),
            MetricVector.model_validate(raw if isinstance(raw, dict) else json.loads(raw)),
        )
        for ticker, raw in rows
    ]
    vectors_by_ticker = {ticker: vec for ticker, vec in vectors}
    claim_res = await db.execute(
        text(
            """SELECT claim.ticker, claim.value_text, claim.excerpt_locator,
                      claim.extracted_at, snapshot.available_date
               FROM evidence_claims AS claim
               JOIN universe_evidence_refs AS ref
                 ON ref.claim_id = claim.claim_id
               JOIN source_snapshots AS snapshot
                 ON snapshot.snapshot_id = claim.snapshot_id
               WHERE ref.universe_version=:universe_version
                 AND claim.field='catalyst_anchor'
                 AND claim.ticker = ANY(:tickers)"""
        ),
        {"tickers": list(vectors_by_ticker), "universe_version": uv},
    )
    known_anchor_rows = [
        row
        for row in claim_res.fetchall()
        if (
            (vector := vectors_by_ticker.get(str(row.ticker).upper())) is not None
            and _anchor_known_at_vector(
                vector_computed_at=vector.computed_at,
                claim_extracted_at=row.extracted_at,
                snapshot_available_date=row.available_date,
            )
        )
    ]
    anchors_by_ticker = load_catalyst_anchors_from_db_rows(known_anchor_rows)
    out: list[dict] = []
    analyzed = 0
    want = (stance or "").upper() or None

    for ticker, vec in vectors:
        # Cheap prefilter for a BUY-only query. Do not apply this to the
        # unfiltered analysis feed: OUT/UNKNOWN rows are research output too.
        mos = vec.mos_live.value if vec.mos_live else None
        if want == "BUY" and (
            vec.kill_active
            or mos is None
            or mos <= 0
            or vec.completeness.grade not in ("A", "B")
        ):
            continue

        t = ticker.upper()
        # Never fetch SEP once per ticker from a universe screen. A missing
        # fresh cache is evidence of missing tape coverage, not permission to
        # invent a move or make the request hang.
        hist = get_cached_price_history(t, years=3, immutable_only=True)
        cutoff = _utc_naive(vec.computed_at).date().isoformat()
        bars = [
            bar
            for bar in ((hist or {}).get("bars") or [])
            if str(bar.get("date") or "")[:10] <= cutoff
        ]

        frozen_band = {
            "fair_px_lo": vec.fair_px_lo.value,
            "fair_px_med": vec.fair_px_med.value,
            "fair_px_hi": vec.fair_px_hi.value,
        }
        valuation_source = frozen_band if _valid_fair_value_band(frozen_band) else {}
        vr = None
        if _valid_fair_value_band(valuation_source):
            # Prefer the cached tape; otherwise derive the same live quote
            # already encoded by the vector's PIT MoS and fixed median lens.
            live = bars[-1]["close"] if bars else live_price_from_mos(
                valuation_source["fair_px_med"], mos
            )
            med = valuation_source["fair_px_med"]
            vr = {
                **valuation_source,
                "price_live": live,
                "gap_to_median": (med / live - 1) if (live and med) else mos,
            }

        wf = build_close_call_waterfall(
            ticker=t,
            universe_version=uv,
            vector=vec,
            valuation_range=vr,
            price_bars=bars,
            extra_anchors=anchors_by_ticker.get(t),
        )
        analyzed += 1
        agg = wf.aggregate
        if want and agg.stance != want:
            continue
        out.append(
            {
                "ticker": t,
                "stance": agg.stance,
                "confidence": agg.confidence,
                "score": agg.score,
                "horizon_years": agg.horizon_years,
                "implied_ann_return": agg.implied_ann_return,
                "horizon_note": agg.horizon_note,
                "blockers": agg.blockers,
                "watermark": agg.watermark,
                # PIT ledger inputs — entry-time sealed MoS and live gap.
                "mos_live": mos,
                "gap_to_median": (vr or {}).get("gap_to_median"),
            }
        )

    out.sort(key=lambda r: (-(r["score"] or 0), r["ticker"]))
    effective_limit = (
        max(1, min(limit, len(out))) if limit is not None else len(out)
    )
    return {
        "universe_version": uv,
        "stance_filter": want,
        "n_universe": len(rows),
        "n_analyzed": analyzed,
        "n": effective_limit,
        "rows": out[:effective_limit],
        "data_mode": "frozen_universe",
        "note": (
            "Frozen research stance list — only evidence bound to this universe "
            "and release-cache prices available at vector build time are used; "
            "not a broker recommendation."
        ),
    }


# =============================================================================
# Audit drawer: metric → claims → snapshots → literature
# =============================================================================

@router.get("/audit/{ticker}/{axis}")
async def audit_trail(
    ticker: str,
    axis: str,
    universe_version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    uv = universe_version or await _latest_version(db)
    await _require_sealed_version(db, uv)
    vec = await _vector(db, ticker, uv)
    t = ticker.upper()

    if axis not in MetricVector.model_fields:
        raise HTTPException(400, f"Unknown axis {axis}")
    field = getattr(vec, axis)
    metric = field.model_dump(mode="json") if hasattr(field, "model_dump") else {"value": field}

    claim_ids = metric.get("claim_ids", []) if isinstance(metric, dict) else []
    claims = []
    snapshots = []
    if claim_ids:
        claims = [dict(r) for r in (await db.execute(
            text(
                """SELECT claim.*
                   FROM evidence_claims AS claim
                   JOIN universe_evidence_refs AS ref
                     ON ref.claim_id = claim.claim_id
                  WHERE ref.universe_version=:uv
                    AND claim.claim_id = ANY(:ids)"""
            ),
            {"ids": claim_ids, "uv": uv},
        )).mappings().all()]
        snap_ids = list({c["snapshot_id"] for c in claims})
        if snap_ids:
            snapshots = [dict(r) for r in (await db.execute(
                text(
                    """SELECT snapshot.*
                       FROM source_snapshots AS snapshot
                       JOIN evidence_claims AS claim
                         ON claim.snapshot_id = snapshot.snapshot_id
                       JOIN universe_evidence_refs AS ref
                         ON ref.claim_id = claim.claim_id
                      WHERE ref.universe_version=:uv
                        AND snapshot.snapshot_id = ANY(:ids)"""
                ),
                {"ids": snap_ids, "uv": uv},
            )).mappings().all()]
    # Do not fall back to current ticker/field claims here. A vector without
    # bound claim IDs is explicitly Unknown for its frozen universe, and
    # showing a later claim would falsify the historical evidence trail.

    literature = [b.model_dump() for b in LITERATURE_BINDS if b.axis == axis]
    ds = (await db.execute(
        text("""SELECT run_id, job, status, severity FROM deepseek_audit_runs
                WHERE ticker=:t AND universe_version=:uv
                ORDER BY finished_at DESC LIMIT 1"""), {"t": t, "uv": uv}
    )).mappings().first()
    review = (await db.execute(
        text(
            """SELECT review_id, passed FROM final_reviews
               WHERE ticker=:t AND universe_version=:uv
               ORDER BY reviewed_at DESC LIMIT 1"""
        ),
        {"t": t, "uv": uv},
    )).mappings().first()

    return {
        "ticker": t,
        "universe_version": uv,
        "axis": axis,
        "metric": metric,
        "claims": claims,
        "snapshots": snapshots,
        "literature": literature,
        "deepseek_run": dict(ds) if ds else None,
        "final_review": dict(review) if review else None,
        "note": "Research only — not investment advice.",
    }


# =============================================================================
# Audit pack export (watermarked JSON)
# =============================================================================

@router.get("/audit-pack/{ticker}")
async def audit_pack(
    ticker: str,
    universe_version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    uv = universe_version or await _latest_version(db)
    await _require_sealed_version(db, uv)
    vec = await _vector(db, ticker, uv)
    t = ticker.upper()
    claim_ids = _vector_claim_ids(vec)
    claims = []
    snapshots = []
    if claim_ids:
        claims = [dict(r) for r in (await db.execute(
            text("SELECT * FROM evidence_claims WHERE ticker=:t AND claim_id = ANY(:ids) ORDER BY field"),
            {"t": t, "ids": claim_ids},
        )).mappings().all()]
        snapshot_ids = sorted({claim["snapshot_id"] for claim in claims if claim.get("snapshot_id")})
        if snapshot_ids:
            snapshots = [dict(r) for r in (await db.execute(
                text("SELECT * FROM source_snapshots WHERE snapshot_id = ANY(:ids)"),
                {"ids": snapshot_ids},
            )).mappings().all()]
    ds = [dict(r) for r in (await db.execute(
        text(
            """SELECT run_id, job, output_kind, output, status, severity, finished_at
               FROM deepseek_audit_runs
               WHERE ticker=:t AND universe_version=:uv"""
        ),
        {"t": t, "uv": uv},
    )).mappings().all()]
    reviews = [dict(r) for r in (await db.execute(
        text(
            """SELECT * FROM final_reviews
               WHERE ticker=:t AND universe_version=:uv"""
        ),
        {"t": t, "uv": uv},
    )).mappings().all()]

    generated = _now().isoformat()
    return {
        "watermark": {
            "notice": "RESEARCH ONLY — NOT INVESTMENT ADVICE",
            "generated_at": generated,
            "generated_for": user["id"],
            "universe_version": uv,
            "pack_sha256": hashlib.sha256(f"{t}|{uv}|{generated}".encode()).hexdigest(),
        },
        "ticker": t,
        "bound_claim_ids": claim_ids,
        "vector": vec.model_dump(mode="json"),
        "evidence_claims": claims,
        "source_snapshots": snapshots,
        "literature_binds": [b.model_dump() for b in LITERATURE_BINDS],
        "deepseek_runs": ds,
        "final_reviews": reviews,
        "note": (
            "Evidence claims and source snapshots are limited to IDs bound in "
            "the exported immutable universe vector. Research only — not investment advice."
        ),
    }


# =============================================================================
# DCF workbench (W4)
# =============================================================================

@router.post("/dcf/{ticker}")
async def run_and_save_dcf(
    ticker: str,
    inputs: DcfInputs,
    save: bool = True,
    universe_version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    t = ticker.upper()
    uv = universe_version or await _latest_version(db)
    await _require_sealed_version(db, uv)
    # A saved DCF always pins an actual research record, never a floating
    # latest ticker lookup.
    await _vector(db, t, uv)
    inputs.ticker = t
    outputs = run_dcf(inputs)
    if outputs.fair_ev_med is None:
        raise HTTPException(
            422,
            "DCF needs a positive SBC-adjusted FCF, revenue plus target margin, or a peer EV input",
        )
    run_id = hashlib.sha256(
        f"{t}|{user['id']}|{uv}|{_now().isoformat()}|{inputs.model_dump_json()}".encode()
    ).hexdigest()[:40]
    if save:
        await db.execute(
            text("""INSERT INTO dcf_runs
                    (run_id, ticker, user_id, scenario, inputs, outputs, engine_version, universe_version, visibility)
                    VALUES (:rid, :t, :u, :sc, :inp, :out, :ev, :uv, 'private')"""),
            {
                "rid": run_id, "t": t, "u": user["id"],
                "sc": inputs.scenario if inputs.scenario in ("base", "bear", "bull", "custom") else "custom",
                "inp": inputs.model_dump_json(), "out": outputs.model_dump_json(),
                "ev": outputs.engine_version,
                "uv": uv,
            },
        )
        await db.commit()
    return {
        "run_id": run_id if save else None,
        "inputs": inputs.model_dump(),
        "outputs": outputs.model_dump(),
        "universe_version": uv,
        "note": "Research only — not investment advice. Fair value recomputed from the shown assumptions.",
    }


class MemoBody(BaseModel):
    thesis: str = Field(min_length=1)
    risks: Optional[str] = None
    citations: list[str] = Field(default_factory=list, description="Claim ids cited by the memo")
    universe_version: Optional[str] = None
    analyst_judgment_ack: bool = Field(
        default=False,
        description="Must be true when the memo contains uncited analyst-judgment sentences",
    )


def _bound_memo_citations(citations: list[str], vec: MetricVector) -> list[str]:
    """Normalize citations and keep a memo attached to its frozen evidence."""

    normalized = sorted({citation.strip() for citation in citations if citation.strip()})
    unbound = sorted(set(normalized) - set(_vector_claim_ids(vec)))
    if unbound:
        raise HTTPException(
            422,
            "Memo citations must be evidence claims bound to the selected "
            f"universe vector: {', '.join(unbound)}",
        )
    return normalized


@router.get("/memo/{ticker}")
async def get_memos(
    ticker: str,
    universe_version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    uid = user["id"]
    uv = universe_version or await _latest_version(db)
    await _require_sealed_version(db, uv)
    rows = (await db.execute(
        text(
            """SELECT * FROM company_memos
               WHERE ticker=:t AND user_id=:u AND universe_version=:uv
                 AND owner_state='owned'
               ORDER BY version DESC"""
        ),
        {"t": ticker.upper(), "u": uid, "uv": uv},
    )).mappings().all()
    all_ids = sorted(
        {
            citation
            for row in rows
            for citation in (
                row["citations"]
                if isinstance(row["citations"], list)
                else json.loads(row["citations"])
            )
        }
    )
    claim_rows = []
    if all_ids:
        claim_rows = (
            await db.execute(
                text(
                    """SELECT claim.claim_id, claim.value_text, claim.excerpt_locator,
                              claim.snapshot_id, claim.extractor
                       FROM evidence_claims AS claim
                       JOIN universe_evidence_refs AS ref
                         ON ref.claim_id = claim.claim_id
                      WHERE ref.universe_version=:uv
                        AND claim.ticker=:t
                        AND claim.claim_id = ANY(:ids)"""
                ),
                {"t": ticker.upper(), "ids": all_ids, "uv": uv},
            )
        ).mappings().all()
    claims_by_id = {row["claim_id"]: dict(row) for row in claim_rows}
    return {
        "universe_version": uv,
        "memos": [
            {
                **dict(row),
                "citations": (
                    row["citations"]
                    if isinstance(row["citations"], list)
                    else json.loads(row["citations"])
                ),
                "citation_records": [
                    claims_by_id[citation]
                    for citation in (
                        row["citations"]
                        if isinstance(row["citations"], list)
                        else json.loads(row["citations"])
                    )
                    if citation in claims_by_id
                ],
            }
            for row in rows
        ],
    }


@router.post("/memo/{ticker}")
async def save_memo(
    ticker: str, body: MemoBody,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
) -> dict:
    t = ticker.upper()
    uid = user["id"]
    uv = body.universe_version or await _latest_version(db)
    await _require_sealed_version(db, uv)
    vec = await _vector(db, t, uv)
    citations = _bound_memo_citations(body.citations, vec)
    if not citations and not body.analyst_judgment_ack:
        raise HTTPException(
            422,
            "Memo must cite at least one evidence claim, or explicitly acknowledge it is analyst judgment.",
        )
    if citations:
        found = (
            await db.execute(
                text(
                    """SELECT claim.claim_id
                       FROM evidence_claims AS claim
                       JOIN universe_evidence_refs AS ref
                         ON ref.claim_id = claim.claim_id
                      WHERE ref.universe_version=:uv
                        AND claim.ticker=:t
                        AND claim.claim_id = ANY(:ids)"""
                ),
                {"t": t, "ids": citations, "uv": uv},
            )
        ).scalars().all()
        missing = sorted(set(citations) - set(found))
        if missing:
            raise HTTPException(422, f"Missing bound citation ids: {', '.join(missing)}")
    last = (await db.execute(
        text(
            """SELECT COALESCE(MAX(version),0) FROM company_memos
               WHERE ticker=:t AND user_id=:u AND owner_state='owned'"""
        ),
        {"t": t, "u": uid},
    )).scalar()
    version = int(last or 0) + 1
    memo_id = hashlib.sha256(f"{t}|{uid}|{version}".encode()).hexdigest()[:40]
    await db.execute(
        text("""INSERT INTO company_memos (memo_id, ticker, user_id, version, thesis, risks, citations, analyst_judgment_ack, universe_version)
                VALUES (:id, :t, :u, :v, :th, :ri, :ci, :ack, :uv)"""),
        {"id": memo_id, "t": t, "u": uid, "v": version, "th": body.thesis, "ri": body.risks,
         "ci": json.dumps(citations), "ack": body.analyst_judgment_ack, "uv": uv},
    )
    await db.commit()
    return {"memo_id": memo_id, "version": version, "universe_version": uv}


# =============================================================================
# Admin KPIs (freshness / fill rate / queues)
# =============================================================================

@router.get("/admin/kpis")
async def admin_kpis(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> dict:
    uv = await _latest_version(db)
    rows = (await db.execute(
        text("""SELECT completeness_grade, count(*) AS n,
                       sum(CASE WHEN stale THEN 1 ELSE 0 END) AS stale_n
                FROM metric_vectors WHERE universe_version=:uv GROUP BY 1"""), {"uv": uv}
    )).mappings().all()
    overlay = (await db.execute(
        text("""SELECT
                  count(*) FILTER (WHERE (vector->'retention'->>'value') IS NOT NULL) AS retention_n,
                  count(*) FILTER (WHERE (vector->'concentration'->>'value') IS NOT NULL) AS concentration_n,
                  count(*) AS total
                FROM metric_vectors WHERE universe_version=:uv"""), {"uv": uv}
    )).mappings().first()
    ds = (await db.execute(
        text("SELECT job, status, count(*) AS n FROM deepseek_audit_runs GROUP BY 1,2")
    )).mappings().all()
    reviews = (await db.execute(
        text("SELECT passed, count(*) AS n FROM final_reviews GROUP BY 1")
    )).mappings().all()
    claims_n = (await db.execute(text("SELECT count(*) FROM evidence_claims"))).scalar()
    return {
        "universe_version": uv,
        "grades": [dict(r) for r in rows],
        "overlay_fill": dict(overlay) if overlay else {},
        "deepseek_queue": [dict(r) for r in ds],
        "final_reviews": [dict(r) for r in reviews],
        "evidence_claims_total": claims_n,
    }


# =============================================================================
# PIT research-BUY performance book (≠ paper HML_RD)
# =============================================================================

@router.get("/buy-performance-book")
async def buy_performance_book(
    universe_version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Sealed BUY-set track record. Empty until seal_buy_set / seal endpoint runs."""

    uv = universe_version or await _latest_version(db)
    try:
        snaps = (
            await db.execute(
                text(
                    """SELECT snapshot_id, universe_version, as_of_date, sealed_at,
                              engine_version, n_buy, note
                         FROM buy_set_snapshots
                        WHERE universe_version=:uv
                        ORDER BY as_of_date DESC
                        LIMIT 24"""
                ),
                {"uv": uv},
            )
        ).mappings().all()
    except Exception:
        # Table may not exist until migration 021 — fail closed with honest empty.
        return empty_book_payload(universe_version=uv)

    if not snaps:
        return empty_book_payload(universe_version=uv)

    out_snaps = []
    for snap in snaps:
        members = (
            await db.execute(
                text(
                    """SELECT ticker, stance, confidence, score, mos_live, gap_to_median,
                              horizon_years, implied_ann_return
                         FROM buy_set_members WHERE snapshot_id=:id ORDER BY ticker"""
                ),
                {"id": snap["snapshot_id"]},
            )
        ).mappings().all()
        member_dicts = [dict(m) for m in members]
        bars_by = {
            m["ticker"].upper(): (get_cached_price_history(m["ticker"].upper(), years=3, immutable_only=True) or {}).get("bars") or []
            for m in member_dicts
        }
        summary = summarise_snapshot(
            as_of=snap["as_of_date"],
            universe_version=snap["universe_version"],
            members=member_dicts,
            bars_by_ticker=bars_by,
        )
        out_snaps.append(
            {
                **dict(snap),
                "as_of_date": snap["as_of_date"].isoformat() if snap["as_of_date"] else None,
                "sealed_at": snap["sealed_at"].isoformat() if snap["sealed_at"] else None,
                "members": member_dicts,
                "forward": summary,
            }
        )

    latest = out_snaps[0]["forward"] if out_snaps else None
    return {
        "status": "ready" if out_snaps else "empty",
        "universe_version": uv,
        "note": (
            "PIT research BUY clearance sets only. Paper HML_RD / RD20 is a different engine "
            "and must not be equated to this book. Forward returns require post-as_of tape."
        ),
        "snapshots": out_snaps,
        "summary": latest,
        "engine": "buy_performance_book_v1",
        "distinct_from": ["HML_RD", "RD20", "paper_publication_track"],
    }


@router.post("/buy-performance-book/seal")
async def seal_buy_performance_book(
    universe_version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> dict:
    """Seal today's cleared BUY shortlist for the active/sealed universe version."""

    import uuid
    from datetime import date as date_cls

    uv = universe_version or await _latest_version(db)
    await _require_sealed_version(db, uv)
    # Reuse stances endpoint logic by calling the same waterfall path inline would
    # be heavy; operator seal expects current BUY list from /stances?stance=BUY.
    # Here we compute BUY rows the same way as list_stances (cached tape only).
    listed = await research_stances(stance="BUY", universe_version=uv, limit=None, db=db, user=user)
    members = listed.get("rows") or []
    if not members:
        raise HTTPException(status_code=400, detail="No cleared BUY rows to seal — refusing empty ledger")

    as_of = date_cls.today()
    try:
        dup = await db.execute(
            text(
                """SELECT snapshot_id FROM buy_set_snapshots
                   WHERE universe_version=:uv AND as_of_date=:as_of LIMIT 1"""
            ),
            {"uv": uv, "as_of": as_of},
        )
        existing = dup.scalar()
    except Exception:
        existing = None
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"BUY set already sealed for {uv} on {as_of.isoformat()} ({existing})",
        )
    snapshot_id = f"buysnap_{as_of.isoformat()}_{uuid.uuid4().hex[:12]}"
    try:
        await db.execute(
            text(
                """INSERT INTO buy_set_snapshots
                   (snapshot_id, universe_version, as_of_date, sealed_at, engine_version,
                    source_sha, n_buy, note)
                   VALUES (:id, :uv, :as_of, :sealed, :engine, :sha, :n, :note)"""
            ),
            {
                "id": snapshot_id,
                "uv": uv,
                "as_of": as_of,
                "sealed": utc_now_naive(),
                "engine": "close_call_v2",
                "sha": None,
                "n": len(members),
                "note": "PIT research BUY clearance set — not paper HML_RD",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"buy_set_snapshots unavailable — run migration 021 ({exc})",
        ) from exc

    for m in members:
        await db.execute(
            text(
                """INSERT INTO buy_set_members
                   (snapshot_id, ticker, stance, confidence, score, mos_live,
                    gap_to_median, horizon_years, implied_ann_return)
                   VALUES (:id, :t, 'BUY', :c, :s, :mos, :gap, :h, :imp)"""
            ),
            {
                "id": snapshot_id,
                "t": m["ticker"],
                "c": m.get("confidence"),
                "s": m.get("score"),
                "mos": m.get("mos_live"),
                "gap": m.get("gap_to_median"),
                "h": m.get("horizon_years"),
                "imp": m.get("implied_ann_return"),
            },
        )
    await db.commit()
    return {"snapshot_id": snapshot_id, "n_buy": len(members), "universe_version": uv, "as_of": as_of.isoformat()}
