"""
PATH: backend/app/services/close_call_service.py
PURPOSE: MedTwin/FRE-style close-call waterfall for one ticker.

Pipeline (fail-closed):
  L0 Tape event (deterministic from SEP bars)
  L1 Anchors (curated SEC/PR catalog only — never invent headlines)
  L2 Fundamentals delta (MetricVector)
  L3 Gates & kill
  L4 Catalyst clarity (L0∩L1; else UNKNOWN)
  ROI runs (weighted) → aggregate score
  Stance BUY|HOLD|WATCH|OUT|UNKNOWN + horizon

BUY requires: kill off, completeness A|B, sealed mos_live > 0,
live vs-target (gap_to_median) > 0, catalyst known, aggregate ≥ 65,
confidence ≥ med. Unknown never imputed. Sealed MoS ≠ live intrinsic value;
implied return is gap-close maths, not a forecast; paper HML_RD ≠ this engine.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from app.contracts.research import (
    CloseCallWaterfall,
    PrecedenceExample,
    RoiRun,
    StanceAggregate,
    WaterfallClaim,
    WaterfallStage,
)
from app.services.decision_provenance import (
    enrich_flowchart_node,
    stance_decision_provenance,
)
from app.services.stance_scores import (
    clip10 as _clip10,
    score_fcfm,
    score_roic,
    score_rule40,
    score_valuation_from_gap,
)

ENGINE_VERSION = "close_call_v2"

# Bootstrap curated anchors (kept as seed; live store is catalyst_event_cache / claims).
_ANCHOR_CATALOG: dict[str, list[dict[str, Any]]] = {
    "EGAN": [
        {
            "date": "2025-10-18",
            "kind": "press_coverage",
            "title": "Shares +52% in a month on AI/Solve25 narrative (growth not matching)",
            "locator": "https://simplywall.st/stocks/us/software/nasdaq-egan/egain",
            "role": "near_peak",
        },
        {
            "date": "2025-11-12",
            "kind": "earnings_release",
            "title": "Q1 FY26 results: AI Knowledge ARR +23% YoY; messaging sunset + gov delays cited on call",
            "locator": "https://www.sec.gov/Archives/edgar/data/1066194/000106619425000027/egan-20251112xex99d1.htm",
            "role": "post_peak",
        },
    ],
}

# Paper / desk precedence: stance must be judged against these rules.
_PRECEDENCE: list[dict[str, str]] = [
    {
        "id": "P1_MOS",
        "label": "Sealed MoS+",
        "rule": "Sealed mos_live must be > 0 (frozen research MoS — not live intrinsic value)",
    },
    {
        "id": "P1b_LIVE_GAP",
        "label": "Live vs-target still open",
        "rule": "gap_to_median (live tape vs sealed median target) must be > 0 to underwrite BUY",
    },
    {
        "id": "P2_FCF",
        "label": "FCF+ check (advisory — not a BUY gate)",
        "rule": (
            "SBC-adjusted FCF margin known and > 0 (paper G2 spirit). "
            "ADVISORY ONLY — not evaluated in buy_ok. Do not treat match/fail as underwriting."
        ),
    },
    {
        "id": "P3_KILL",
        "label": "No kill criterion",
        "rule": "kill_active must be false — else HOLD / OUT, never BUY",
    },
    {
        "id": "P4_CATALYST",
        "label": "Named catalyst for the tape move",
        "rule": "L4 catalyst stage status=known with dated anchors; else UNKNOWN confidence",
    },
    {
        "id": "P5_COMPLETE",
        "label": "Completeness A or B",
        "rule": "Underwrite only when research completeness grade is A or B",
    },
]


def _mv(vec: Any, name: str) -> Optional[float]:
    m = getattr(vec, name, None)
    if m is None:
        return None
    return getattr(m, "value", None) if hasattr(m, "value") else None


def _detect_tape_event(bars: list[dict]) -> Optional[dict[str, Any]]:
    """Largest peak→trough drawdown in the last ~18 months (≥25%)."""
    if not bars or len(bars) < 40:
        return None
    # Prefer last ~18m of bars
    cutoff = bars[-1]["date"]
    try:
        end = date.fromisoformat(str(cutoff)[:10])
        start_cut = date(end.year - 1, end.month, end.day) if end.month != 2 or end.day != 29 else date(end.year - 1, 2, 28)
        window = [b for b in bars if date.fromisoformat(str(b["date"])[:10]) >= start_cut]
    except Exception:
        window = bars[-400:]
    if len(window) < 20:
        window = bars

    best: Optional[dict[str, Any]] = None
    peak_i = 0
    for i, b in enumerate(window):
        if b["close"] >= window[peak_i]["close"]:
            peak_i = i
        peak = window[peak_i]["close"]
        if peak <= 0:
            continue
        dd = b["close"] / peak - 1.0
        if dd >= -0.25:
            continue
        cand = {
            "peak_date": window[peak_i]["date"][:10],
            "peak_px": round(peak, 4),
            "trough_date": str(b["date"])[:10],
            "trough_px": round(b["close"], 4),
            "drawdown": round(dd, 4),
            "last_px": round(window[-1]["close"], 4),
            "last_date": str(window[-1]["date"])[:10],
        }
        if best is None or cand["drawdown"] < best["drawdown"]:
            best = cand
    return best


def _load_anchor_catalog(
    ticker: str,
    *,
    extra_anchors: Optional[list[dict[str, Any]]] = None,
    include_cached: bool = False,
) -> list[dict[str, Any]]:
    """Load immutable anchors, optionally adding a clearly requested live overlay.

    Historical waterfall output must never silently depend on a mutable disk
    cache. Callers rendering an explicitly current view can opt in.
    """
    from app.services.catalyst_event_service import load_cached_anchors, merge_anchor_lists

    t = ticker.upper()
    seed = list(_ANCHOR_CATALOG.get(t, []))
    cached: list[dict[str, Any]] = []
    if include_cached:
        try:
            cached = load_cached_anchors(t)
        except Exception:
            cached = []
    return merge_anchor_lists(seed, cached, list(extra_anchors or []))


def _anchors_for(
    ticker: str,
    event: Optional[dict],
    *,
    extra_anchors: Optional[list[dict[str, Any]]] = None,
    include_cached: bool = False,
) -> tuple[list[dict], str]:
    catalog = _load_anchor_catalog(
        ticker,
        extra_anchors=extra_anchors,
        include_cached=include_cached,
    )
    if not catalog:
        return [], "No verified SEC/PR/earnings anchors in store for this ticker"
    if not event:
        return [], "No tape event detected — anchors not applied"
    peak = date.fromisoformat(event["peak_date"])
    trough = date.fromisoformat(event["trough_date"])
    kept = []
    for a in catalog:
        try:
            d = date.fromisoformat(str(a["date"])[:10])
        except Exception:
            continue
        # Peak−30d … trough+45d
        if (d - peak).days >= -30 and (d - trough).days <= 45:
            kept.append(a)
    if not kept:
        return [], "Anchors exist but none fall inside the peak→trough window"
    return kept, ""


def _score_valuation(mos: Optional[float], gap: Optional[float]) -> tuple[Optional[float], dict, list[str]]:
    unk: list[str] = []
    contrib: dict[str, float] = {}
    if mos is None and gap is None:
        return None, {}, ["mos_live", "gap_to_median"]
    g = mos if mos is not None else gap
    s = score_valuation_from_gap(g)
    contrib["mos_or_gap"] = s
    if mos is None:
        unk.append("mos_live")
    return s, contrib, unk


def _score_quality(fcfm: Optional[float], rule40: Optional[float], roic: Optional[float]) -> tuple[Optional[float], dict, list[str]]:
    parts: list[float] = []
    contrib: dict[str, float] = {}
    unk: list[str] = []
    v_fcfm = score_fcfm(fcfm)
    if v_fcfm is None:
        unk.append("fcfm_sbc")
    else:
        contrib["fcfm_sbc"] = v_fcfm
        parts.append(v_fcfm)
    v_r40 = score_rule40(rule40)
    if v_r40 is None:
        unk.append("rule40")
    else:
        contrib["rule40"] = v_r40
        parts.append(v_r40)
    v_roic = score_roic(roic)
    if v_roic is None:
        unk.append("roic")
    else:
        contrib["roic"] = v_roic
        parts.append(v_roic)
    if not parts:
        return None, contrib, unk
    return round(sum(parts) / len(parts), 2), contrib, unk


def _score_completeness(grade: Optional[str], claims_n: int, filing: bool) -> tuple[Optional[float], dict, list[str]]:
    if not grade:
        return None, {}, ["completeness.grade"]
    base = {"A": 9.0, "B": 7.0, "C": 4.0, "Incomplete": 1.5}.get(grade, None)
    if base is None:
        return None, {}, ["completeness.grade"]
    bonus = 0.5 if filing else 0.0
    bonus += 0.5 if claims_n >= 3 else 0.0
    s = _clip10(base + bonus)
    return s, {"grade": base, "filing_claims_bonus": bonus}, []


def _annualized(gap: float, years: int) -> float:
    return round(pow(1.0 + gap, 1.0 / years) - 1.0, 4)


def build_close_call_waterfall(
    *,
    ticker: str,
    universe_version: str,
    vector: Any,
    valuation_range: Optional[dict] = None,
    price_bars: Optional[list[dict]] = None,
    extra_anchors: Optional[list[dict[str, Any]]] = None,
    include_cached_anchors: bool = False,
) -> CloseCallWaterfall:
    t = ticker.upper()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    vr = valuation_range or {}
    bars = price_bars or []

    mos = _mv(vector, "mos_live")
    # Explicit live gap only — do not silently substitute sealed MoS here.
    # Horizon maths may fall back to mos when live gap is absent.
    live_gap = vr.get("gap_to_median") if isinstance(vr, dict) else None
    gap = live_gap if live_gap is not None else mos
    fcfm = _mv(vector, "fcfm_sbc")
    rule40 = _mv(vector, "rule40")
    roic = _mv(vector, "roic")
    rev_cagr = _mv(vector, "rev_cagr")
    # Unknown kill state is not the same thing as no kill. It must block BUY.
    kill_state = getattr(vector, "kill_active", None)
    kill = kill_state is True
    kill_unknown = kill_state is None
    comp = getattr(vector, "completeness", None)
    grade = getattr(comp, "grade", None) if comp else None
    claims_n = int(getattr(comp, "claims_n", 0) or 0) if comp else 0
    filing = bool(getattr(comp, "filing_fetched", False)) if comp else False
    table20 = getattr(vector, "table20_pass_count", None)

    # ----- L0 Tape -----
    event = _detect_tape_event(bars)
    if event:
        l0 = WaterfallStage(
            id="L0",
            title="Tape event (peak → trough)",
            status="known",
            score=_clip10(min(10.0, abs(event["drawdown"]) * 12)),
            summary=(
                f"Peak ${event['peak_px']:.2f} on {event['peak_date']} → "
                f"${event['trough_px']:.2f} on {event['trough_date']} "
                f"({event['drawdown']*100:.0f}% drawdown). Last ${event['last_px']:.2f}."
            ),
            claims=[
                WaterfallClaim(
                    claim_id=f"{t}-L0-peak",
                    field="peak",
                    value_text=f"{event['peak_date']} ${event['peak_px']:.2f}",
                    value_numeric=event["peak_px"],
                    locator="Sharadar SEP",
                    as_of_date=date.fromisoformat(event["peak_date"]),
                ),
                WaterfallClaim(
                    claim_id=f"{t}-L0-dd",
                    field="drawdown",
                    value_text=f"{event['drawdown']*100:.1f}%",
                    value_numeric=event["drawdown"],
                    locator="Sharadar SEP",
                    as_of_date=date.fromisoformat(event["trough_date"]),
                ),
            ],
        )
    else:
        l0 = WaterfallStage(
            id="L0",
            title="Tape event (peak → trough)",
            status="unknown",
            score=None,
            summary="No ≥25% peak→trough drawdown detected in the lookback window.",
            unknown_reason="Insufficient bars or no material drawdown event",
        )

    # ----- L1 Anchors -----
    anchors, anchor_miss = _anchors_for(
        t,
        event,
        extra_anchors=extra_anchors,
        include_cached=include_cached_anchors,
    )
    if anchors:
        l1 = WaterfallStage(
            id="L1",
            title="Dated anchors (SEC / PR catalog)",
            status="known",
            score=_clip10(4.0 + 2.0 * len(anchors)),
            summary=f"{len(anchors)} verified anchor(s) inside the event window.",
            claims=[
                WaterfallClaim(
                    claim_id=f"{t}-L1-{i}",
                    field=a["kind"],
                    value_text=f"{a['date']}: {a['title']}",
                    locator=a["locator"],
                    as_of_date=date.fromisoformat(a["date"]),
                )
                for i, a in enumerate(anchors)
            ],
        )
    else:
        l1 = WaterfallStage(
            id="L1",
            title="Dated anchors (SEC / PR catalog)",
            status="unknown",
            score=None,
            summary="No verified dated anchors applied.",
            unknown_reason=anchor_miss or "Not in anchor catalog — will not invent headlines",
        )

    # ----- L2 Fundamentals -----
    fund_claims: list[WaterfallClaim] = []
    fund_unk: list[str] = []
    for field, val, label in [
        ("mos_live", mos, "MoS live / gap vs target"),
        ("fcfm_sbc", fcfm, "FCF margin SBC-adj"),
        ("rule40", rule40, "Rule of 40"),
        ("rev_cagr", rev_cagr, "Revenue CAGR"),
        ("roic", roic, "ROIC"),
    ]:
        if val is None:
            fund_unk.append(field)
        else:
            fund_claims.append(
                WaterfallClaim(
                    claim_id=f"{t}-L2-{field}",
                    field=field,
                    value_text=f"{label}={val:.4g}",
                    value_numeric=val,
                    locator="MetricVector",
                )
            )
    if len(fund_claims) >= 3:
        l2_status: str = "known"
        l2_score = _clip10(3.0 + len(fund_claims))
        l2_unk = None
    elif fund_claims:
        l2_status = "partial"
        l2_score = _clip10(2.0 + len(fund_claims))
        l2_unk = f"Missing: {', '.join(fund_unk)}" if fund_unk else None
    else:
        l2_status = "unknown"
        l2_score = None
        l2_unk = "No fundamental metrics available"
    l2 = WaterfallStage(
        id="L2",
        title="Fundamentals delta",
        status=l2_status,  # type: ignore[arg-type]
        score=l2_score,
        summary=(
            f"{len(fund_claims)} known metric(s)"
            + (f"; unknown: {', '.join(fund_unk)}" if fund_unk else "")
        ),
        claims=fund_claims,
        unknown_reason=l2_unk,
    )

    # ----- L3 Gates -----
    l3_claims = [
        WaterfallClaim(
            claim_id=f"{t}-L3-kill",
            field="kill_active",
            value_text=str(kill_state if not kill_unknown else "unknown"),
            value_numeric=1.0 if kill else 0.0 if not kill_unknown else None,
            locator="MetricVector.kill_active",
        ),
        WaterfallClaim(
            claim_id=f"{t}-L3-grade",
            field="completeness.grade",
            value_text=str(grade or "unknown"),
            locator="ResearchCompleteness",
        ),
    ]
    if table20 is not None:
        l3_claims.append(
            WaterfallClaim(
                claim_id=f"{t}-L3-t20",
                field="table20_pass_count",
                value_text=f"{table20}/12",
                value_numeric=float(table20),
                locator="MetricVector",
            )
        )
    l3 = WaterfallStage(
        id="L3",
        title="Gates & kill criterion",
        status="partial" if kill_unknown else "known",
        score=None if kill_unknown else (0.0 if kill else _clip10(4.0 + (table20 or 0) * 0.4)),
        summary=(
            f"kill_active={kill_state if not kill_unknown else 'unknown'}; completeness={grade or 'unknown'}; "
            f"table20={table20 if table20 is not None else 'unknown'}/12"
        ),
        claims=l3_claims,
        unknown_reason="kill_active is unknown — BUY is blocked" if kill_unknown else None,
    )

    # ----- L4 Catalyst -----
    if l0.status == "known" and l1.status == "known":
        l4 = WaterfallStage(
            id="L4",
            title="Catalyst clarity",
            status="known",
            score=_clip10((l0.score or 0) * 0.4 + (l1.score or 0) * 0.6),
            summary="Tape event bounded by verified dated anchors — catalyst named, not invented.",
            claims=l0.claims[:1] + l1.claims,
        )
    elif l0.status == "known" and l1.status == "unknown":
        l4 = WaterfallStage(
            id="L4",
            title="Catalyst clarity",
            status="unknown",
            score=None,
            summary="Drawdown is known; why it happened is not verified in our anchor catalog.",
            unknown_reason=l1.unknown_reason,
        )
    else:
        l4 = WaterfallStage(
            id="L4",
            title="Catalyst clarity",
            status="unknown",
            score=None,
            summary="No material tape event and/or no anchors — catalyst UNKNOWN.",
            unknown_reason="Need L0 event + L1 anchors",
        )

    stages = [l0, l1, l2, l3, l4]

    # ----- ROI runs -----
    v_score, v_c, v_u = _score_valuation(mos, gap)
    q_score, q_c, q_u = _score_quality(fcfm, rule40, roic)
    c_score = l4.score  # catalyst run mirrors L4 — null if unknown
    k_score, k_c, k_u = _score_completeness(grade, claims_n, filing)
    risk_score: Optional[float]
    risk_c: dict[str, float] = {}
    risk_u: list[str] = []
    if kill:
        risk_score = 0.0
        risk_c["kill_veto"] = 0.0
    elif kill_unknown:
        risk_score = None
        risk_u.append("kill_active")
    else:
        risk_score = 8.0
        risk_c["no_kill"] = 8.0
        if _mv(vector, "retention") is None:
            risk_u.append("retention")
            risk_score = 6.5

    roi_runs = [
        RoiRun(
            id="valuation_gap",
            label="Valuation gap vs price target",
            weight=0.30,
            score=v_score,
            contributions=v_c,
            unknown_axes=v_u,
            note="MoS / gap to median lens. Null if price or FV missing.",
        ),
        RoiRun(
            id="quality_cash",
            label="Quality / cash generation",
            weight=0.25,
            score=q_score,
            contributions=q_c,
            unknown_axes=q_u,
            note="FCF (SBC-adj), Rule of 40, ROIC — only known axes averaged.",
        ),
        RoiRun(
            id="catalyst_timing",
            label="Catalyst / timing clarity",
            weight=0.20,
            score=c_score,
            contributions={"L4": c_score} if c_score is not None else {},
            unknown_axes=[] if c_score is not None else ["L4_catalyst"],
            note="Blocks BUY when unknown — no invented news.",
        ),
        RoiRun(
            id="completeness",
            label="Evidence completeness",
            weight=0.15,
            score=k_score,
            contributions=k_c,
            unknown_axes=k_u,
            note="Completeness grade is underwrite eligibility, not attractiveness.",
        ),
        RoiRun(
            id="risk_kill",
            label="Risk / kill criterion",
            weight=0.10,
            score=risk_score,
            contributions=risk_c,
            unknown_axes=risk_u,
            note="kill_active is a hard veto on BUY.",
        ),
    ]

    # Aggregate: weighted mean over scored runs only; track coverage
    scored = [(r.weight, r.score) for r in roi_runs if r.score is not None]
    total_w = sum(r.weight for r in roi_runs)
    scored_w = sum(w for w, _ in scored)
    if scored:
        agg_0_10 = sum(w * s for w, s in scored) / scored_w
        # Penalize missing weight mass
        coverage = scored_w / total_w
        agg_score = round(agg_0_10 * 10.0 * coverage, 1)
    else:
        agg_score = None

    # Precedence
    precedence: list[PrecedenceExample] = []
    for p in _PRECEDENCE:
        matched: Optional[bool]
        evidence: str
        if p["id"] == "P1_MOS":
            matched = None if mos is None else mos > 0
            evidence = "unknown" if mos is None else f"mos_live={mos:.3f}"
        elif p["id"] == "P1b_LIVE_GAP":
            matched = None if live_gap is None else live_gap > 0
            evidence = "unknown" if live_gap is None else f"gap_to_median={live_gap:.3f}"
        elif p["id"] == "P2_FCF":
            matched = None if fcfm is None else fcfm > 0
            evidence = "unknown" if fcfm is None else f"fcfm_sbc={fcfm:.3f}"
        elif p["id"] == "P3_KILL":
            matched = None if kill_unknown else not kill
            evidence = f"kill_active={kill_state if not kill_unknown else 'unknown'}"
        elif p["id"] == "P4_CATALYST":
            matched = l4.status == "known"
            evidence = f"L4.status={l4.status}"
        else:  # P5_COMPLETE
            matched = None if grade is None else grade in ("A", "B")
            evidence = f"grade={grade or 'unknown'}"
        precedence.append(
            PrecedenceExample(
                id=p["id"],
                label=p["label"],
                rule=p["rule"],
                matched=matched,
                evidence=evidence,
                gate_kind="advisory" if p["id"] == "P2_FCF" else "hard",
                opinion=False,
            )
        )

    # Decision flowchart + stance (fail-closed)
    blockers: list[str] = []
    flowchart: list[dict] = []

    def node(
        nid: str,
        label: str,
        result: str,
        detail: str,
        *,
        formula_ids: Optional[list[str]] = None,
        data_fields: Optional[list[str]] = None,
        gate_kind: str = "hard",
    ) -> None:
        flowchart.append(
            enrich_flowchart_node(
                {"id": nid, "label": label, "result": result, "detail": detail},
                formula_ids=formula_ids,
                data_fields=data_fields,
                gate_kind=gate_kind,
            )
        )

    # Step 1 kill
    if kill:
        node(
            "F1",
            "Kill criterion",
            "FAIL",
            "kill_active=true → cannot BUY",
            data_fields=["kill_active"],
        )
        blockers.append("Kill criterion active")
    elif kill_unknown:
        node(
            "F1",
            "Kill criterion",
            "UNKNOWN",
            "kill_active is missing → cannot BUY",
            data_fields=["kill_active"],
        )
        blockers.append("Kill criterion state unknown")
    else:
        node(
            "F1",
            "Kill criterion",
            "PASS",
            "kill_active=false",
            data_fields=["kill_active"],
        )

    # Step 2 completeness
    if grade in ("A", "B"):
        node(
            "F2",
            "Completeness A|B",
            "PASS",
            f"grade={grade}",
            data_fields=["completeness_grade"],
        )
    else:
        node(
            "F2",
            "Completeness A|B",
            "FAIL",
            f"grade={grade or 'unknown'}",
            data_fields=["completeness_grade"],
        )
        blockers.append(f"Completeness {grade or 'unknown'} — need A or B to BUY")

    # Step 3 sealed MoS
    if mos is None:
        node(
            "F3",
            "Sealed MoS > 0",
            "UNKNOWN",
            "mos_live missing — sealed MoS is not live intrinsic value",
            data_fields=["mos_live"],
            formula_ids=["F_MOS_LIVE"],
        )
        blockers.append("Sealed MoS unknown")
    elif mos > 0:
        node(
            "F3",
            "Sealed MoS > 0",
            "PASS",
            f"mos_live={mos:.1%} (frozen research MoS — not live IV)",
            data_fields=["mos_live"],
            formula_ids=["F_MOS_LIVE"],
        )
    else:
        node(
            "F3",
            "Sealed MoS > 0",
            "FAIL",
            f"mos_live={mos:.1%} — no sealed margin of safety",
            data_fields=["mos_live"],
            formula_ids=["F_MOS_LIVE"],
        )
        blockers.append("Sealed MoS ≤ 0")

    # Step 3b live vs sealed target
    if live_gap is None:
        node(
            "F3b",
            "Live vs-target > 0",
            "UNKNOWN",
            "gap_to_median missing — will not underwrite BUY without a live tape gap",
            data_fields=["gap_to_median", "price_live", "fair_px_med"],
            formula_ids=["F_VS_MEDIAN_PCT", "F_LIVE_VS_SEALED_GATE"],
        )
        blockers.append("Live vs-target unknown")
    elif live_gap > 0:
        node(
            "F3b",
            "Live vs-target > 0",
            "PASS",
            f"gap_to_median={live_gap:.1%}",
            data_fields=["gap_to_median", "price_live", "fair_px_med"],
            formula_ids=["F_VS_MEDIAN_PCT", "F_LIVE_VS_SEALED_GATE"],
        )
    else:
        node(
            "F3b",
            "Live vs-target > 0",
            "FAIL",
            f"gap_to_median={live_gap:.1%} — live tape closed/through the sealed target",
            data_fields=["gap_to_median", "price_live", "fair_px_med"],
            formula_ids=["F_VS_MEDIAN_PCT", "F_LIVE_VS_SEALED_GATE"],
        )
        blockers.append("Live vs-target ≤ 0 — tape closed the sealed MoS gap")

    # Step 4 catalyst
    if l4.status == "known":
        node(
            "F4",
            "Catalyst named",
            "PASS",
            l4.summary,
            data_fields=["L4.status", "dated_anchors"],
        )
    else:
        node(
            "F4",
            "Catalyst named",
            "UNKNOWN",
            l4.unknown_reason or l4.summary,
            data_fields=["L4.status", "dated_anchors"],
        )
        blockers.append("Catalyst clarity UNKNOWN — will not invent why the tape moved")

    # Step 5 score
    if agg_score is None:
        node(
            "F5",
            "Aggregate score ≥ 65",
            "UNKNOWN",
            "No scored ROI runs",
            data_fields=["roi_runs"],
            formula_ids=["F_STANCE_BUY_GATES"],
        )
        blockers.append("No aggregate score")
    elif agg_score >= 65:
        node(
            "F5",
            "Aggregate score ≥ 65",
            "PASS",
            f"score={agg_score}",
            data_fields=["roi_runs"],
            formula_ids=["F_STANCE_BUY_GATES"],
        )
    else:
        node(
            "F5",
            "Aggregate score ≥ 65",
            "FAIL",
            f"score={agg_score}",
            data_fields=["roi_runs"],
            formula_ids=["F_STANCE_BUY_GATES"],
        )
        blockers.append(f"Aggregate score {agg_score} < 65")

    # Confidence
    crit_unknown = (
        l4.status != "known"
        or mos is None
        or live_gap is None
        or grade is None
        or kill_unknown
    )
    if crit_unknown or kill:
        confidence = "none" if (l4.status != "known" or kill or kill_unknown) else "low"
    elif blockers:
        confidence = "low"
    elif agg_score is not None and agg_score >= 75 and l4.status == "known":
        confidence = "high"
    else:
        confidence = "med"

    buy_ok = (
        not kill
        and not kill_unknown
        and grade in ("A", "B")
        and mos is not None
        and mos > 0
        and live_gap is not None
        and live_gap > 0
        and l4.status == "known"
        and agg_score is not None
        and agg_score >= 65
        and confidence in ("med", "high")
    )

    # Horizon from gap size (convergence expectation, not a forecast)
    horizon_years: Optional[int] = None
    horizon_note: Optional[str] = None
    implied: Optional[float] = None
    g_for_h = live_gap if live_gap is not None else mos
    if g_for_h is not None and g_for_h > 0:
        if g_for_h >= 0.6:
            horizon_years = 3
        elif g_for_h >= 0.25:
            horizon_years = 2
        else:
            horizon_years = 1
        implied = _annualized(g_for_h, horizon_years)
        horizon_note = (
            f"If the live→target gap ({g_for_h*100:.0f}%) closes over {horizon_years}y, "
            f"implied ≈ {implied*100:.1f}%/yr. Convergence math — not a forecast; "
            f"do not auto-size from this rate. Distinct from paper HML_RD."
        )

    if buy_ok:
        stance = "BUY"
        node(
            "F6",
            "Stance",
            "BUY",
            f"All gates cleared · confidence={confidence} · {horizon_years}y horizon · clearance ≠ order",
            data_fields=["F1", "F2", "F3", "F3b", "F4", "F5", "confidence"],
            formula_ids=["F_HOLD_HORIZON", "F_IMPLIED_ANN_RETURN"],
        )
    elif kill_unknown:
        stance = "UNKNOWN"
        node(
            "F6",
            "Stance",
            "UNKNOWN",
            "Kill criterion state is unknown — not confident enough to BUY",
            data_fields=["kill_active"],
        )
    elif kill or (mos is not None and mos <= 0):
        stance = "OUT" if kill else "HOLD"
        node(
            "F6",
            "Stance",
            stance,
            "; ".join(blockers) or stance,
            data_fields=["kill_active", "mos_live"],
            formula_ids=["F_MOS_LIVE"],
        )
    elif live_gap is not None and live_gap <= 0:
        stance = "HOLD"
        node(
            "F6",
            "Stance",
            "HOLD",
            "Live tape closed/through sealed target — sealed MoS alone is not underwriting",
            data_fields=["gap_to_median", "mos_live"],
            formula_ids=["F_VS_MEDIAN_PCT", "F_LIVE_VS_SEALED_GATE"],
        )
    elif l4.status != "known" or mos is None or live_gap is None:
        stance = "UNKNOWN"
        node(
            "F6",
            "Stance",
            "UNKNOWN",
            "Critical inputs unknown — not confident enough to BUY",
            data_fields=["L4.status", "mos_live", "gap_to_median"],
        )
    elif grade not in ("A", "B"):
        stance = "WATCH"
        node(
            "F6",
            "Stance",
            "WATCH",
            "Evidence incomplete for underwriting",
            data_fields=["completeness_grade"],
        )
    else:
        stance = "HOLD"
        node(
            "F6",
            "Stance",
            "HOLD",
            "; ".join(blockers) or "Gates not cleared for BUY",
            data_fields=["blockers"],
        )

    # Only attach horizon to BUY or HOLD when gap known
    if stance not in ("BUY", "HOLD"):
        horizon_years = None
        implied = None
        if stance == "UNKNOWN":
            horizon_note = "Horizon withheld — stance UNKNOWN until catalyst/MoS/live gap known."

    aggregate = StanceAggregate(
        score=agg_score,
        confidence=confidence,  # type: ignore[arg-type]
        stance=stance,  # type: ignore[arg-type]
        horizon_years=horizon_years,  # type: ignore[arg-type]
        horizon_note=horizon_note,
        implied_ann_return=implied,
        blockers=blockers,
        flowchart=flowchart,
        precedence_examples=precedence,
        decision_chain_id="D_STANCE_BUY",
        decision_provenance=stance_decision_provenance(),
        engine_version=ENGINE_VERSION,
    )

    return CloseCallWaterfall(
        ticker=t,
        universe_version=universe_version,
        computed_at=now,
        stages=stages,
        roi_runs=roi_runs,
        aggregate=aggregate,
    )
