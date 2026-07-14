"""
PATH: backend/app/api/routes/books.py
PURPOSE: W3 server-persisted books (portfolios) with risk-constraint breach wall.

Ship rules:
- Books START EMPTY. There is no auto-seed path in this module by design
  (kill criterion: Model 10 auto-seed → stop ship).
- Constraint breaches BLOCK save unless every breaching holding carries an
  override_reason (server-rejects, not just UI).
- kill_active / Unknown kill state / Incomplete / stale names require
  override_reason to add.
- Every response watermarked research-only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.tradability import adv_usd_from_bars
from app.services.price_history_service import get_cached_price_history
from app.api.routes.auth import get_current_user
from app.contracts.research import BookConstraint, BookHolding, MetricVector, SavedBook
from app.services.factor_sizing import f_max as factor_f_max
from app.services.factor_sizing import sizing_payload
from app.services.sizing_proxy import proxy_weights
from app.services.thesis_fields import weave_composite

router = APIRouter()

_now = lambda: datetime.now(timezone.utc).replace(tzinfo=None)  # noqa: E731


def _db_timestamp(value: datetime) -> datetime:
    """Normalize public ISO timestamps for legacy timestamp columns."""

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value

DEFAULT_CONSTRAINTS = [
    BookConstraint(kind="max_name_pct", limit=15.0),
    BookConstraint(kind="max_incomplete_pct", limit=20.0),
    BookConstraint(kind="ban_kill_active"),
    # Validated-evidence sizing wall: only enforced when f_max > 0. When the
    # bound is zero, construction uses the declared sizing proxy (relative
    # weights among cleared BUYs) — not a fake Kelly unlock.
    BookConstraint(kind="max_factor_sizing"),
]
_MANDATORY_CONSTRAINTS = {constraint.kind: constraint for constraint in DEFAULT_CONSTRAINTS}


class BookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    recipe_id: Optional[str] = None
    universe_version: Optional[str] = None
    constraints: list[BookConstraint] = Field(default_factory=lambda: list(DEFAULT_CONSTRAINTS))
    make_primary: bool = True


class BookSave(BaseModel):
    holdings: list[BookHolding]
    constraints: Optional[list[BookConstraint]] = None
    revision: Optional[int] = Field(default=None, ge=1)


class BookLock(BaseModel):
    acknowledgements: list[str] = Field(
        default_factory=list,
        description="Tickers whose current research/kill state the owner acknowledged",
    )
    revision: Optional[int] = Field(default=None, ge=1)


def _user_id(user: dict) -> str:
    user_id = str(user.get("id") or "")
    if not user_id:
        raise HTTPException(401, "Authenticated user has no durable account id")
    return user_id


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
        raise HTTPException(404, "No universe build available")
    return str(version)


def _policy_constraints(requested: list[BookConstraint]) -> list[BookConstraint]:
    """Add/validate non-disableable safety controls for every persisted Book."""

    by_kind: dict[str, BookConstraint] = {}
    for constraint in requested:
        if constraint.kind in by_kind:
            raise HTTPException(422, f"Duplicate constraint kind: {constraint.kind}")
        by_kind[constraint.kind] = constraint

    for kind, baseline in _MANDATORY_CONSTRAINTS.items():
        supplied = by_kind.get(kind)
        if supplied is None:
            by_kind[kind] = baseline.model_copy(deep=True)
            continue
        if not supplied.enabled:
            raise HTTPException(422, f"{kind} is a mandatory safety constraint")
        if baseline.limit is not None:
            if supplied.limit is None or supplied.limit > baseline.limit:
                raise HTTPException(
                    422,
                    f"{kind} may not be relaxed above {baseline.limit:g}",
                )
        supplied.enabled = True

    return list(by_kind.values())


async def _vector_flags(
    db: AsyncSession, tickers: list[str], universe_version: str
) -> dict[str, dict]:
    if not tickers:
        return {}
    rows = (
        await db.execute(
            text(
                """SELECT ticker, vector, completeness_grade, kill_active, stale
                   FROM metric_vectors
                   WHERE universe_version=:uv AND ticker = ANY(:tickers)"""
            ),
            {"uv": universe_version, "tickers": [ticker.upper() for ticker in tickers]},
        )
    ).mappings().all()
    flags: dict[str, dict] = {}
    for row in rows:
        raw = row["vector"] if isinstance(row["vector"], dict) else json.loads(row["vector"])
        float_fcf = ((raw.get("float_fcf_share") or {}).get("value"))
        liq = raw.get("liquidity_usd")
        if liq is None:
            hist = get_cached_price_history(str(row["ticker"]).upper(), years=1, immutable_only=True)
            liq = adv_usd_from_bars((hist or {}).get("bars") or [])
        flags[row["ticker"]] = {
            "completeness_grade": row["completeness_grade"],
            "kill_active": row["kill_active"],
            "stale": row["stale"],
            "float_fcf_share": float_fcf,
            # Stance still requires an explicitly persisted research field.
            # Liquidity falls back to 20d ADV from SEP cache; still Unknown if volume missing.
            "stance": raw.get("research_stance"),
            "liquidity_usd": liq,
            "sector": raw.get("sector"),
        }
    return flags


def evaluate_breaches(
    holdings: list[BookHolding],
    constraints: list[BookConstraint],
    flags: dict[str, dict],
) -> list[dict]:
    """Constraint engine. Returns breach list; empty = save allowed."""
    breaches: list[dict] = []

    def fl(h: BookHolding) -> dict:
        # Vector flag keys are DB-uppercase; never miss on client casing.
        return flags.get(h.ticker.upper()) or flags.get(h.ticker) or {}

    total = sum(h.weight_pct for h in holdings)
    if holdings and abs(total - 100.0) > 0.01 and total > 100.0001:
        breaches.append({"kind": "weights_sum", "detail": f"weights sum to {total:.2f}% > 100%"})

    for c in constraints:
        if not c.enabled:
            continue
        if c.kind == "max_name_pct" and c.limit is not None:
            for h in holdings:
                if h.weight_pct > c.limit and not h.override_reason:
                    breaches.append({"kind": c.kind, "ticker": h.ticker,
                                     "detail": f"{h.ticker} {h.weight_pct:.1f}% > max {c.limit:.0f}%"})
        elif c.kind == "ban_kill_active":
            for h in holdings:
                kill_state = fl(h).get("kill_active")
                # An ACTIVE kill is never overridable; only UNKNOWN may be
                # waived with a reviewed reason.
                if kill_state is True or (kill_state is not False and not h.override_reason):
                    breaches.append({"kind": c.kind, "ticker": h.ticker,
                                     "detail": (
                                         f"{h.ticker} has an ACTIVE kill criterion"
                                         if kill_state is True
                                         else f"{h.ticker} kill state is UNKNOWN"
                                     )})
        elif c.kind == "max_incomplete_pct" and c.limit is not None:
            incomplete = [
                h
                for h in holdings
                if fl(h).get("completeness_grade") in ("Incomplete", None)
            ]
            # Overrides are individual, reviewed exceptions. An override on an
            # unrelated name must not suppress incomplete exposure elsewhere.
            unresolved_incomplete = [h for h in incomplete if not h.override_reason]
            inc = sum(h.weight_pct for h in unresolved_incomplete)
            if inc > c.limit:
                for h in unresolved_incomplete:
                    breaches.append(
                        {
                            "kind": c.kind,
                            "ticker": h.ticker,
                            "detail": (
                                f"Incomplete-grade unresolved weight {inc:.1f}% > max "
                                f"{c.limit:.0f}% (override this holding to proceed)"
                            ),
                        }
                    )
        elif c.kind == "max_sector_pct" and c.limit is not None:
            sectors: dict[str, list[BookHolding]] = {}
            for h in holdings:
                sector = fl(h).get("sector")
                if not sector and not h.override_reason:
                    breaches.append(
                        {
                            "kind": c.kind,
                            "ticker": h.ticker,
                            "detail": f"{h.ticker} sector is Unknown for the pinned universe",
                        }
                    )
                    continue
                sectors.setdefault(str(sector or "Unknown"), []).append(h)
            for sector, grouped in sectors.items():
                weight = sum(h.weight_pct for h in grouped)
                if weight > c.limit:
                    for h in grouped:
                        if not h.override_reason:
                            breaches.append(
                                {
                                    "kind": c.kind,
                                    "ticker": h.ticker,
                                    "detail": f"{sector} weight {weight:.1f}% > max {c.limit:.0f}%",
                                }
                            )
        elif c.kind == "max_float_fcf_share" and c.limit is not None:
            for h in holdings:
                observed = fl(h).get("float_fcf_share")
                if (observed is None or observed > c.limit) and not h.override_reason:
                    detail = (
                        f"{h.ticker} float-FCF share is Unknown"
                        if observed is None
                        else f"{h.ticker} float-FCF share {observed:.1f}% > max {c.limit:.1f}%"
                    )
                    breaches.append({"kind": c.kind, "ticker": h.ticker, "detail": detail})
        elif c.kind == "ban_on_hold":
            for h in holdings:
                stance = fl(h).get("stance")
                if stance in (None, "HOLD", "UNKNOWN") and not h.override_reason:
                    label = "Unknown" if stance in (None, "UNKNOWN") else "HOLD"
                    breaches.append(
                        {
                            "kind": c.kind,
                            "ticker": h.ticker,
                            "detail": f"{h.ticker} research stance is {label}",
                        }
                    )
        elif c.kind == "max_factor_sizing":
            # Enforce only when a positive validated bound exists. A zero bound
            # means "no Kelly claim" — not "ban all BUY weights." Relative
            # construction then uses sizing_proxy (contracts/sizing-proxy.json).
            bound_pct = c.limit if c.limit is not None else factor_f_max(None, 0) * 100.0
            if bound_pct <= 0:
                continue
            buy_holdings = [h for h in holdings if fl(h).get("stance") == "BUY"]
            buy_weight = sum(h.weight_pct for h in buy_holdings)
            if buy_weight > bound_pct + 1e-9:
                for h in buy_holdings:
                    if not h.override_reason:
                        breaches.append(
                            {
                                "kind": c.kind,
                                "ticker": h.ticker,
                                "detail": (
                                    f"BUY-clearance weight {buy_weight:.1f}% > validated bound "
                                    f"{bound_pct:.1f}% — override to acknowledge sizing above "
                                    "the evidence-backed cap"
                                ),
                            }
                        )
        elif c.kind == "liquidity_floor" and c.limit is not None:
            for h in holdings:
                liquidity = fl(h).get("liquidity_usd")
                if (liquidity is None or liquidity < c.limit) and not h.override_reason:
                    detail = (
                        f"{h.ticker} liquidity is Unknown"
                        if liquidity is None
                        else f"{h.ticker} liquidity ${liquidity:,.0f} < floor ${c.limit:,.0f}"
                    )
                    breaches.append({"kind": c.kind, "ticker": h.ticker, "detail": detail})

    # Kill state is non-negotiable research hygiene. It remains fail-closed
    # even when a client removes/disables the display constraint.
    existing_kill_breaches = {
        breach.get("ticker") for breach in breaches if breach.get("kind") == "ban_kill_active"
    }
    for h in holdings:
        kill_state = fl(h).get("kill_active")
        if (
            kill_state is True or (kill_state is not False and not h.override_reason)
        ) and h.ticker not in existing_kill_breaches:
            breaches.append(
                {
                    "kind": "ban_kill_active",
                    "ticker": h.ticker,
                    "detail": (
                        f"{h.ticker} has an ACTIVE kill criterion"
                        if kill_state is True
                        else f"{h.ticker} kill state is UNKNOWN"
                    ),
                }
            )

    # Stale or Unknown freshness always needs an override (freshness SLA).
    for h in holdings:
        stale = fl(h).get("stale")
        if stale is not False and not h.override_reason:
            breaches.append(
                {
                    "kind": "stale",
                    "ticker": h.ticker,
                    "detail": (
                        f"{h.ticker} fundamentals are past the freshness SLA"
                        if stale is True
                        else f"{h.ticker} freshness state is UNKNOWN"
                    ),
                }
            )
    return breaches


@router.get("/sizing-bound")
async def get_sizing_bound(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
) -> dict:
    """The validated-evidence sizing wall: bound, both frozen premium series, and why.

    σ²_book requires ≥ 12 sealed monthly BUY snapshots; we report the sealed
    count honestly and the bound stays 0 until both the edge and the variance
    are validated.
    """
    n_months = 0
    try:
        n_months = int(
            await db.scalar(
                text(
                    "SELECT count(DISTINCT date_trunc('month', as_of_date)) "
                    "FROM buy_set_snapshots WHERE kind='sealed'"
                )
            )
            or 0
        )
    except Exception:
        n_months = 0
    payload = sizing_payload(sigma_book_sq=None, n_sealed_months=n_months)
    payload["note"] = (
        "Research only — not investment advice. Validated f_max only caps BUY weight when "
        "positive; when zero, use the construction proxy (/api/books/sizing-proxy) for "
        "relative weights among cleared theses."
    )
    payload["construction_proxy"] = {
        "endpoint": "/api/books/sizing-proxy",
        "contract": "SIZING_PROXY_V1",
        "role": "Relative split among cleared BUY names — not a validated edge claim.",
    }
    return payload


class SizingProxyRequest(BaseModel):
    tickers: list[str] = Field(min_length=1)
    universe_version: Optional[str] = None


@router.post("/sizing-proxy")
async def post_sizing_proxy(
    body: SizingProxyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Weave-weighted construction proxy for cleared BUY tickers.

    Returns suggested weight_pct that sum to ≤100% with a 15% per-name cap.
    Non-BUY names are dropped. Validated f_max is untouched.
    """
    tickers = sorted({t.strip().upper() for t in body.tickers if t and t.strip()})
    if not tickers:
        raise HTTPException(400, "tickers required")

    uv = body.universe_version
    if not uv:
        uv = await db.scalar(
            text(
                "SELECT universe_version FROM universe_builds "
                "WHERE is_active AND status='sealed' LIMIT 1"
            )
        )
    if not uv:
        raise HTTPException(404, "No active sealed universe")

    # Reuse the same stance waterfall path the list endpoint uses — but we only
    # need BUY confirmation + scores. Pull vectors + run close-call cheaply.
    from app.api.routes.universe_company import (
        _anchor_known_at_vector,
        _utc_naive,
    )
    from app.services.catalyst_event_service import load_catalyst_anchors_from_db_rows
    from app.services.close_call_service import build_close_call_waterfall
    from app.services.price_history_service import get_cached_price_history as _gph

    res = await db.execute(
        text(
            "SELECT ticker, vector FROM metric_vectors "
            "WHERE universe_version=:uv AND ticker = ANY(:tickers)"
        ),
        {"uv": uv, "tickers": tickers},
    )
    vectors = {
        str(t).upper(): MetricVector.model_validate(v if isinstance(v, dict) else json.loads(v))
        for t, v in res.fetchall()
    }
    if not vectors:
        raise HTTPException(404, "No vectors for the requested tickers in this universe")

    claim_res = await db.execute(
        text(
            """SELECT claim.ticker, claim.value_text, claim.excerpt_locator,
                      claim.extracted_at, snapshot.available_date
               FROM evidence_claims AS claim
               JOIN universe_evidence_refs AS ref ON ref.claim_id = claim.claim_id
               JOIN source_snapshots AS snapshot ON snapshot.snapshot_id = claim.snapshot_id
               WHERE ref.universe_version=:universe_version
                 AND claim.field='catalyst_anchor'
                 AND claim.ticker = ANY(:tickers)"""
        ),
        {"tickers": list(vectors), "universe_version": uv},
    )
    known_anchor_rows = [
        row
        for row in claim_res.fetchall()
        if (
            (vector := vectors.get(str(row.ticker).upper())) is not None
            and _anchor_known_at_vector(
                vector_computed_at=vector.computed_at,
                claim_extracted_at=row.extracted_at,
                snapshot_available_date=row.available_date,
            )
        )
    ]
    anchors_by_ticker = load_catalyst_anchors_from_db_rows(known_anchor_rows)

    rows_for_proxy: list[dict] = []
    for ticker, vec in vectors.items():
        hist = _gph(ticker, years=3, immutable_only=True)
        cutoff = _utc_naive(vec.computed_at).date().isoformat()
        bars = [
            bar
            for bar in ((hist or {}).get("bars") or [])
            if str(bar.get("date") or "")[:10] <= cutoff
        ]
        price = bars[-1]["close"] if bars else None
        fair = vec.fair_px_med.value if vec.fair_px_med else None
        gap = (fair / price - 1.0) if price and fair and fair > 0 and price > 0 else None
        wf = build_close_call_waterfall(
            ticker=ticker,
            universe_version=uv,
            vector=vec,
            valuation_range={"gap_to_median": gap, "price_stale": False},
            price_bars=bars,
            extra_anchors=anchors_by_ticker.get(ticker, []),
        )
        weave = None
        if isinstance(vec.weave_z, dict):
            try:
                weave, _partial = weave_composite(vec.weave_z)
            except Exception:
                weave = None
        rows_for_proxy.append(
            {
                "ticker": ticker,
                "stance": wf.aggregate.stance,
                "score": wf.aggregate.score,
                "weave_score": weave,
                "mos_live": vec.mos_live.value if vec.mos_live else None,
                "payoff_skew": vec.payoff_skew.value if vec.payoff_skew else None,
                "payoff_skew_label": vec.payoff_skew_label,
            }
        )

    payload = proxy_weights(rows_for_proxy)
    payload["universe_version"] = uv
    payload["requested"] = tickers
    payload["dropped_non_buy"] = sorted(
        t for t in tickers if t not in {h["ticker"] for h in payload["holdings"]}
    )
    return payload


@router.get("")
async def list_books(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)) -> dict:
    uid = _user_id(user)
    books = (await db.execute(
        text(
            "SELECT * FROM saved_books WHERE user_id=:u AND owner_state='owned' "
            "ORDER BY is_primary DESC, updated_at DESC"
        ),
        {"u": uid},
    )).mappings().all()
    out = []
    for b in books:
        public_book = dict(b)
        public_book.pop("user_id", None)
        holdings = (await db.execute(
            text("SELECT ticker, weight_pct, added_at, override_reason FROM saved_book_holdings WHERE book_id=:b ORDER BY weight_pct DESC"),
            {"b": b["book_id"]},
        )).mappings().all()
        lock_acknowledgements = b["lock_acknowledgements"]
        out.append({
            **public_book,
            "constraints": b["constraints"] if isinstance(b["constraints"], list) else json.loads(b["constraints"]),
            "lock_acknowledgements": (
                lock_acknowledgements
                if isinstance(lock_acknowledgements, list)
                else json.loads(lock_acknowledgements or "[]")
            ),
            "holdings": [dict(h) for h in holdings],
        })
    return {"books": out, "note": "Research only — not investment advice."}


@router.post("")
async def create_book(
    body: BookCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
) -> dict:
    uid = _user_id(user)
    universe_version = body.universe_version or await _latest_version(db)
    constraints = _policy_constraints(body.constraints)
    has_vectors = await db.scalar(
        text(
            """SELECT EXISTS(
                   SELECT 1
                     FROM metric_vectors AS vector
                     JOIN universe_builds AS build
                       ON build.universe_version = vector.universe_version
                    WHERE vector.universe_version=:uv
                      AND build.status='sealed'
               )"""
        ),
        {"uv": universe_version},
    )
    if not has_vectors:
        raise HTTPException(422, f"Unknown or empty universe version {universe_version}")
    book_id = hashlib.sha256(f"{uid}|{body.name}|{_now().isoformat()}".encode()).hexdigest()[:40]
    is_primary = body.make_primary
    if is_primary:
        await db.execute(
            text("UPDATE saved_books SET is_primary=false WHERE user_id=:u AND owner_state='owned'"),
            {"u": uid},
        )
    await db.execute(
        text(
            """INSERT INTO saved_books
               (book_id, user_id, name, recipe_id, universe_version, constraints, is_primary)
               VALUES (:id, :u, :n, :r, :uv, :c, :primary)"""
        ),
        {"id": book_id, "u": uid, "n": body.name, "r": body.recipe_id,
         "uv": universe_version,
         "c": json.dumps([c.model_dump() for c in constraints]),
         "primary": is_primary},
    )
    await db.commit()
    # Book starts EMPTY by contract — no seeding.
    return {
        "book_id": book_id,
        "holdings": [],
        "universe_version": universe_version,
        "is_primary": is_primary,
        "revision": 1,
        "note": "Book starts empty — add names explicitly.",
    }


@router.put("/{book_id}")
async def save_book(
    book_id: str,
    body: BookSave,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    uid = _user_id(user)
    book = (await db.execute(
        text("SELECT * FROM saved_books WHERE book_id=:b AND user_id=:u AND owner_state='owned' FOR UPDATE"), {"b": book_id, "u": uid}
    )).mappings().first()
    if book is None:
        raise HTTPException(404, "Book not found")
    if book["locked_at"] is not None:
        raise HTTPException(409, "Book is locked; unlock it before changing holdings")
    if body.revision is not None and body.revision != int(book["revision"]):
        raise HTTPException(
            409,
            detail={
                "message": "Book changed in another session; reload before saving.",
                "current_revision": book["revision"],
            },
        )

    constraints = body.constraints
    if constraints is None:
        raw = book["constraints"] if isinstance(book["constraints"], list) else json.loads(book["constraints"])
        constraints = [BookConstraint.model_validate(c) for c in raw]
    constraints = _policy_constraints(constraints)

    universe_version = book["universe_version"] or await _latest_version(db)
    if book["universe_version"] is None:
        await db.execute(
            text(
                """UPDATE saved_books SET universe_version=:uv
                   WHERE book_id=:b AND user_id=:u AND owner_state='owned'"""
            ),
            {"uv": universe_version, "b": book_id, "u": uid},
        )
    normalized_tickers = [holding.ticker.upper() for holding in body.holdings]
    if len(set(normalized_tickers)) != len(normalized_tickers):
        raise HTTPException(422, "A Book cannot contain the same ticker more than once")
    flags = await _vector_flags(db, normalized_tickers, universe_version)
    breaches = evaluate_breaches(body.holdings, constraints, flags)
    if breaches:
        # BREACH WALL: server rejects. UI shows the wall; typed override reasons
        # on the breaching holdings are the only way through.
        raise HTTPException(422, detail={"breaches": breaches,
                                         "message": "Constraint breaches block save. Fix or add override_reason per holding."})

    # Validate through the contract (weights sum etc.)
    SavedBook(
        book_id=book_id, user_id=uid, name=book["name"], holdings=body.holdings,
        constraints=constraints, universe_version=universe_version,
        created_at=book["created_at"], updated_at=_now(),
    )

    await db.execute(text("DELETE FROM saved_book_holdings WHERE book_id=:b"), {"b": book_id})
    for h in body.holdings:
        await db.execute(
            text("""INSERT INTO saved_book_holdings (book_id, ticker, weight_pct, added_at, override_reason)
                    VALUES (:b, :t, :w, :a, :o)"""),
            {
                "b": book_id,
                "t": h.ticker.upper(),
                "w": h.weight_pct,
                "a": _db_timestamp(h.added_at),
                "o": h.override_reason,
            },
        )
    revision = await db.scalar(
        text(
            """UPDATE saved_books
               SET constraints=:c, revision=revision + 1, updated_at=:ts
               WHERE book_id=:b AND user_id=:u AND owner_state='owned'
               RETURNING revision"""
        ),
        {
            "c": json.dumps([c.model_dump() for c in constraints]),
            "ts": _now(),
            "b": book_id,
            "u": uid,
        },
    )
    await db.commit()
    return {"book_id": book_id, "saved": True, "n_holdings": len(body.holdings), "revision": revision,
            "note": "Research only — not investment advice."}


@router.post("/{book_id}/check")
async def check_constraints(
    book_id: str,
    body: BookSave,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Dry-run constraint evaluation for the breach wall UI (no writes)."""
    uid = _user_id(user)
    book = (await db.execute(
        text("SELECT * FROM saved_books WHERE book_id=:b AND user_id=:u AND owner_state='owned' FOR SHARE"), {"b": book_id, "u": uid}
    )).mappings().first()
    if book is None:
        raise HTTPException(404, "Book not found")
    constraints = body.constraints
    if constraints is None:
        raw = book["constraints"] if isinstance(book["constraints"], list) else json.loads(book["constraints"])
        constraints = [BookConstraint.model_validate(c) for c in raw]
    constraints = _policy_constraints(constraints)
    universe_version = book["universe_version"] or await _latest_version(db)
    flags = await _vector_flags(db, [h.ticker for h in body.holdings], universe_version)
    return {"breaches": evaluate_breaches(body.holdings, constraints, flags)}


@router.post("/{book_id}/primary")
async def set_primary_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    uid = _user_id(user)
    owned = await db.scalar(
        text("SELECT EXISTS(SELECT 1 FROM saved_books WHERE book_id=:b AND user_id=:u AND owner_state='owned')"),
        {"b": book_id, "u": uid},
    )
    if not owned:
        raise HTTPException(404, "Book not found")
    await db.execute(
        text("UPDATE saved_books SET is_primary=false WHERE user_id=:u AND owner_state='owned'"),
        {"u": uid},
    )
    await db.execute(
        text("UPDATE saved_books SET is_primary=true, updated_at=:ts WHERE book_id=:b AND user_id=:u AND owner_state='owned'"),
        {"ts": _now(), "b": book_id, "u": uid},
    )
    return {"book_id": book_id, "is_primary": True}


@router.post("/{book_id}/lock")
async def lock_book(
    book_id: str,
    body: BookLock,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Persist a reviewed immutable book state before exporting its audit pack."""

    uid = _user_id(user)
    book = (
        await db.execute(
            text("SELECT * FROM saved_books WHERE book_id=:b AND user_id=:u AND owner_state='owned' FOR UPDATE"),
            {"b": book_id, "u": uid},
        )
    ).mappings().first()
    if book is None:
        raise HTTPException(404, "Book not found")
    if book["locked_at"] is not None:
        stored_acknowledgements = book["lock_acknowledgements"]
        return {
            "book_id": book_id,
            "locked": True,
            "universe_version": book["lock_version"] or book["universe_version"],
            "revision": book["revision"],
            "acknowledgements": (
                stored_acknowledgements
                if isinstance(stored_acknowledgements, list)
                else json.loads(stored_acknowledgements or "[]")
            ),
        }
    if body.revision is not None and body.revision != int(book["revision"]):
        raise HTTPException(
            409,
            detail={
                "message": "Book changed in another session; reload before locking.",
                "current_revision": book["revision"],
            },
        )
    universe_version = book["universe_version"] or await _latest_version(db)
    holdings_rows = (
        await db.execute(
            text(
                """SELECT ticker, weight_pct, added_at, override_reason
                   FROM saved_book_holdings WHERE book_id=:b ORDER BY ticker"""
            ),
            {"b": book_id},
        )
    ).mappings().all()
    holdings = [BookHolding.model_validate(dict(row)) for row in holdings_rows]
    if not holdings:
        raise HTTPException(422, "A Book must contain at least one holding before it can be locked")
    acknowledgements = {ticker.strip().upper() for ticker in body.acknowledgements if ticker.strip()}
    missing_acknowledgements = sorted(
        holding.ticker for holding in holdings if holding.ticker.upper() not in acknowledgements
    )
    if missing_acknowledgements:
        raise HTTPException(
            422,
            detail={
                "message": "Acknowledge every holding before locking/exporting.",
                "missing_acknowledgements": missing_acknowledgements,
            },
        )
    raw = book["constraints"] if isinstance(book["constraints"], list) else json.loads(book["constraints"])
    constraints = _policy_constraints([BookConstraint.model_validate(value) for value in raw])
    flags = await _vector_flags(db, [holding.ticker for holding in holdings], universe_version)
    breaches = evaluate_breaches(holdings, constraints, flags)
    if breaches:
        raise HTTPException(422, detail={"breaches": breaches, "message": "Constraint breaches block lock."})
    lock_revision = int(book["revision"]) + 1
    lock_payload = {
        "book_id": book_id,
        "user_id": uid,
        "revision": lock_revision,
        "universe_version": universe_version,
        "constraints": [constraint.model_dump() for constraint in constraints],
        "holdings": [
            {
                "ticker": holding.ticker,
                "weight_pct": holding.weight_pct,
                "added_at": holding.added_at.isoformat(),
                "override_reason": holding.override_reason,
                "flags": flags.get(holding.ticker, {}),
            }
            for holding in holdings
        ],
        "acknowledgements": sorted(acknowledgements),
    }
    await db.execute(
        text(
            """UPDATE saved_books
               SET universe_version=:uv, locked_at=:locked_at,
                   lock_acknowledgements=:acks, lock_version=:uv,
                   lock_payload=CAST(:lock_payload AS jsonb),
                   revision=:revision, updated_at=:updated_at
               WHERE book_id=:b AND user_id=:u AND owner_state='owned'"""
        ),
        {
            "uv": universe_version,
            "locked_at": _now(),
            "acks": json.dumps(sorted(acknowledgements)),
            "lock_payload": json.dumps(lock_payload, default=str),
            "revision": lock_revision,
            "updated_at": _now(),
            "b": book_id,
            "u": uid,
        },
    )
    return {
        "book_id": book_id,
        "locked": True,
        "universe_version": universe_version,
        "revision": lock_revision,
        "acknowledgements": sorted(acknowledgements),
    }


@router.post("/{book_id}/unlock")
async def unlock_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    uid = _user_id(user)
    result = await db.execute(
        text(
            """UPDATE saved_books
               SET locked_at=NULL, lock_acknowledgements='[]', lock_version=NULL,
                   lock_payload=NULL, revision=revision + 1, updated_at=:ts
               WHERE book_id=:b AND user_id=:u AND owner_state='owned' RETURNING book_id, revision"""
        ),
        {"ts": _now(), "b": book_id, "u": uid},
    )
    updated = result.mappings().first()
    if updated is None:
        raise HTTPException(404, "Book not found")
    return {"book_id": book_id, "locked": False, "revision": updated["revision"]}


@router.delete("/{book_id}")
async def delete_book(
    book_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
) -> dict:
    uid = _user_id(user)
    protected = await db.scalar(
        text(
            """SELECT EXISTS(
                   SELECT 1
                     FROM saved_books AS book
                    WHERE book.book_id=:b
                      AND book.user_id=:u
                      AND book.owner_state='owned'
                      AND (
                          book.locked_at IS NOT NULL
                          OR EXISTS (
                              SELECT 1 FROM audit_exports AS export
                               WHERE export.book_id = book.book_id
                          )
                      )
               )"""
        ),
        {"b": book_id, "u": uid},
    )
    if protected:
        raise HTTPException(
            409,
            "A locked Book or a Book with an audit export is retained as immutable history",
        )
    res = await db.execute(
        text("DELETE FROM saved_books WHERE book_id=:b AND user_id=:u AND owner_state='owned' RETURNING book_id, is_primary"),
        {"b": book_id, "u": uid},
    )
    deleted = res.mappings().first()
    if deleted is None:
        raise HTTPException(404, "Book not found")
    if deleted["is_primary"]:
        await db.execute(
            text(
                """UPDATE saved_books SET is_primary=true
                   WHERE book_id=(
                     SELECT book_id FROM saved_books
                     WHERE user_id=:u AND owner_state='owned' ORDER BY updated_at DESC LIMIT 1
                   )"""
            ),
            {"u": uid},
        )
    await db.commit()
    return {"deleted": book_id}


@router.get("/{book_id}/audit-pack")
async def book_audit_pack(
    book_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
) -> dict:
    """Watermarked export: holdings + per-name evidence summary."""
    uid = _user_id(user)
    book = (await db.execute(
        text("SELECT * FROM saved_books WHERE book_id=:b AND user_id=:u AND owner_state='owned'"), {"b": book_id, "u": uid}
    )).mappings().first()
    if book is None:
        raise HTTPException(404, "Book not found")
    if book["locked_at"] is None:
        raise HTTPException(409, "Lock and acknowledge the book before exporting its audit pack")
    raw_lock_payload = book["lock_payload"]
    lock_payload = (
        raw_lock_payload
        if isinstance(raw_lock_payload, dict)
        else json.loads(raw_lock_payload or "{}")
    )
    holdings = lock_payload.get("holdings")
    if not isinstance(holdings, list):
        # Legacy locked Books predate lock_payload. They remain exportable, but
        # use the locked row state only as a compatibility fallback.
        holdings = [
            dict(row)
            for row in (
                await db.execute(
                    text(
                        """SELECT ticker, weight_pct, added_at, override_reason
                           FROM saved_book_holdings WHERE book_id=:b ORDER BY ticker"""
                    ),
                    {"b": book_id},
                )
            ).mappings().all()
        ]
    tickers = [str(holding["ticker"]).upper() for holding in holdings]
    universe_version = book["lock_version"] or book["universe_version"] or await _latest_version(db)
    flags = await _vector_flags(db, tickers, universe_version)
    generated = _now().isoformat()
    vector_rows = (
        await db.execute(
            text(
                """SELECT ticker, vector FROM metric_vectors
                   WHERE universe_version=:uv AND ticker = ANY(:tickers)"""
            ),
            {"uv": universe_version, "tickers": tickers},
        )
    ).mappings().all()
    vectors = {
        row["ticker"]: MetricVector.model_validate(
            row["vector"] if isinstance(row["vector"], dict) else json.loads(row["vector"])
        )
        for row in vector_rows
    }
    claim_ids = sorted(
        {
            claim_id
            for vector in vectors.values()
            for field_name in MetricVector.model_fields
            for claim_id in (
                getattr(getattr(vector, field_name), "claim_ids", None) or []
            )
        }
    )
    claims = []
    snapshots = []
    if claim_ids:
        claims = [
            dict(row)
            for row in (
                await db.execute(
                    text(
                        """SELECT claim.*
                           FROM evidence_claims AS claim
                           JOIN universe_evidence_refs AS ref
                             ON ref.claim_id = claim.claim_id
                           WHERE ref.universe_version=:uv
                             AND claim.claim_id = ANY(:claim_ids)
                           ORDER BY claim.ticker, claim.field, claim.claim_id"""
                    ),
                    {"claim_ids": claim_ids, "uv": universe_version},
                )
            ).mappings().all()
        ]
        snapshot_ids = sorted(
            {str(claim["snapshot_id"]) for claim in claims if claim.get("snapshot_id")}
        )
        if snapshot_ids:
            snapshots = [
                dict(row)
                for row in (
                    await db.execute(
                        text(
                            """SELECT * FROM source_snapshots
                               WHERE snapshot_id = ANY(:snapshot_ids)
                               ORDER BY ticker, available_date, snapshot_id"""
                        ),
                        {"snapshot_ids": snapshot_ids},
                    )
                ).mappings().all()
            ]
    public_book = dict(book)
    public_book.pop("user_id", None)
    pack_content = {
        "watermark": {
            "notice": "RESEARCH ONLY — NOT INVESTMENT ADVICE",
            "generated_at": generated,
            "generated_for": uid,
            "universe_version": universe_version,
        },
        "book": {
            **public_book,
            "constraints": (
                book["constraints"]
                if isinstance(book["constraints"], list)
                else json.loads(book["constraints"])
            ),
            "locked_revision": lock_payload.get("revision", book["revision"]),
        },
        "holdings": [
            {
                **dict(holding),
                **{
                    key: flags.get(str(holding["ticker"]).upper(), {}).get(key)
                    for key in ("completeness_grade", "kill_active", "stale")
                },
                "vector": vectors.get(str(holding["ticker"]).upper()).model_dump(mode="json")
                if vectors.get(str(holding["ticker"]).upper())
                else None,
            }
            for holding in holdings
        ],
        "bound_claim_ids": claim_ids,
        "evidence_claims": claims,
        "source_snapshots": snapshots,
    }
    payload_sha256 = hashlib.sha256(
        json.dumps(pack_content, sort_keys=True, default=str).encode()
    ).hexdigest()
    export_id = hashlib.sha256(f"{book_id}|{generated}|{payload_sha256}".encode()).hexdigest()[:40]
    pack = {
        **pack_content,
        "export_id": export_id,
        "payload_sha256": payload_sha256,
    }
    await db.execute(
        text(
            """INSERT INTO audit_exports
               (export_id, book_id, user_id, universe_version, payload_sha256, payload, book_revision)
               VALUES (:id, :book_id, :user_id, :uv, :hash, CAST(:payload AS jsonb), :revision)"""
        ),
        {
            "id": export_id,
            "book_id": book_id,
            "user_id": uid,
            "uv": universe_version,
            "hash": payload_sha256,
            "payload": json.dumps(pack, default=str),
            "revision": lock_payload.get("revision", book["revision"]),
        },
    )
    return pack
