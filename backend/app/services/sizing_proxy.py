"""
PATH: backend/app/services/sizing_proxy.py
PURPOSE: Declared construction proxy for relative weights among cleared BUY theses.

This is NOT the validated factor sizing bound (factor_sizing.f_max). It only
answers: given a set of BUY-clearance names, how to split a user-chosen book
using sealed weave / score / MoS / skew inputs. Thresholds live in
contracts/sizing-proxy.json.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Any, Optional

from app.contracts.paths import contracts_dir

SIZING_PROXY_FILE = "sizing-proxy.json"


@lru_cache(maxsize=1)
def load_sizing_proxy() -> dict:
    path = contracts_dir() / SIZING_PROXY_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Sealed sizing proxy contract missing: {path}")
    data = json.loads(path.read_text())
    if data.get("id") != "SIZING_PROXY_V1":
        raise ValueError(f"Unexpected sizing proxy contract id in {path}")
    return data


def _softplus(x: float, beta: float = 1.0) -> float:
    # Numerically stable softplus.
    z = beta * x
    if z > 20:
        return z / beta
    if z < -20:
        return math.exp(z) / beta
    return math.log1p(math.exp(z)) / beta


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def raw_score(
    *,
    weave_score: Optional[float],
    stance_score: Optional[float],
    mos_live: Optional[float],
    payoff_skew: Optional[float],
    payoff_skew_label: Optional[str] = None,
    contract: Optional[dict] = None,
) -> float:
    """Non-negative construction score for one eligible BUY name."""
    c = contract or load_sizing_proxy()
    inputs = c["inputs"]
    beta = float(c.get("softplus_beta", 1.0))

    parts: list[float] = []

    w_weave = float(inputs["weave_score"]["weight"])
    wv = _f(weave_score)
    parts.append(w_weave * (_softplus(wv, beta) if wv is not None else 0.0))

    w_stance = float(inputs["stance_score"]["weight"])
    sv = _f(stance_score)
    parts.append(w_stance * (max(0.0, min(1.0, sv / 100.0)) if sv is not None else 0.0))

    w_mos = float(inputs["mos_live"]["weight"])
    mv = _f(mos_live)
    parts.append(w_mos * (max(0.0, min(2.0, mv)) / 2.0 if mv is not None else 0.0))

    w_skew = float(inputs["payoff_skew"]["weight"])
    if payoff_skew_label == "below_band":
        skew_comp = 1.0
    else:
        sk = _f(payoff_skew)
        skew_comp = max(0.0, min(10.0, sk)) / 10.0 if sk is not None else 0.0
    parts.append(w_skew * skew_comp)

    return sum(parts)


def waterfill_weights(
    raw: list[float],
    *,
    cap_pct: float,
    target_sum_pct: float = 100.0,
) -> list[float]:
    """Normalise raw scores to target_sum_pct with a hard per-name cap."""
    n = len(raw)
    if n == 0:
        return []
    if all(r <= 0 for r in raw):
        equal = min(cap_pct, target_sum_pct / n)
        return [round(equal, 2)] * n

    # Iterative waterfill: allocate proportional to residual raw among uncapped.
    remaining_target = float(target_sum_pct)
    remaining = list(range(n))
    out = [0.0] * n
    while remaining and remaining_target > 1e-9:
        s = sum(raw[i] for i in remaining)
        if s <= 0:
            share = remaining_target / len(remaining)
            for i in remaining:
                out[i] = min(cap_pct, share)
            break
        capped_now: list[int] = []
        for i in remaining:
            prop = remaining_target * (raw[i] / s)
            if prop >= cap_pct - 1e-9:
                out[i] = cap_pct
                capped_now.append(i)
        if not capped_now:
            for i in remaining:
                out[i] = remaining_target * (raw[i] / s)
            break
        for i in capped_now:
            remaining.remove(i)
            remaining_target -= cap_pct

    # Round to 2dp and fix residual on the largest weight so sum is exact.
    rounded = [round(x, 2) for x in out]
    drift = round(target_sum_pct - sum(rounded), 2)
    if rounded and abs(drift) >= 0.01:
        # Prefer adjusting an uncapped-looking slot (weight < cap).
        order = sorted(range(n), key=lambda i: (-rounded[i], i))
        for i in order:
            candidate = round(rounded[i] + drift, 2)
            if 0 <= candidate <= cap_pct + 1e-9:
                rounded[i] = candidate
                break
    return rounded


def proxy_weights(
    rows: list[dict[str, Any]],
    contract: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Compute construction weights for cleared-BUY rows.

    Each row may include: ticker, stance, weave_score, stance_score|score,
    mos_live, payoff_skew, payoff_skew_label.
    Non-BUY / missing ticker → excluded.
    """
    c = contract or load_sizing_proxy()
    cap = float(c["per_name_cap_pct"])
    target = float(c["target_sum_pct"])

    eligible: list[dict[str, Any]] = []
    for row in rows:
        ticker = str(row.get("ticker") or "").upper().strip()
        if not ticker:
            continue
        stance = str(row.get("stance") or "").upper()
        if stance != "BUY":
            continue
        score = row.get("stance_score", row.get("score"))
        raw = raw_score(
            weave_score=_f(row.get("weave_score")),
            stance_score=_f(score),
            mos_live=_f(row.get("mos_live")),
            payoff_skew=_f(row.get("payoff_skew")),
            payoff_skew_label=row.get("payoff_skew_label"),
            contract=c,
        )
        eligible.append({"ticker": ticker, "raw": raw, "row": row})

    weights = waterfill_weights(
        [e["raw"] for e in eligible],
        cap_pct=cap,
        # With a 15% per-name hard cap, n names can deploy at most n·15%.
        # Targeting 100% when that is impossible just saturates everyone at the
        # cap and destroys relative ranking — so we target the feasible sum.
        target_sum_pct=min(target, cap * max(len(eligible), 1)),
    )
    holdings = [
        {
            "ticker": e["ticker"],
            "weight_pct": w,
            "raw_score": round(e["raw"], 6),
            "components": {
                "weave_score": e["row"].get("weave_score"),
                "stance_score": e["row"].get("stance_score", e["row"].get("score")),
                "mos_live": e["row"].get("mos_live"),
                "payoff_skew": e["row"].get("payoff_skew"),
                "payoff_skew_label": e["row"].get("payoff_skew_label"),
            },
        }
        for e, w in zip(eligible, weights)
    ]
    return {
        "engine": "sizing_proxy_v1",
        "contract_id": c["id"],
        "n_eligible": len(holdings),
        "per_name_cap_pct": cap,
        "target_sum_pct": target,
        "weights_sum_pct": round(sum(h["weight_pct"] for h in holdings), 2),
        "holdings": holdings,
        "disclosures": c["disclosures"],
        "note": (
            "Construction proxy only — relative split among cleared BUY theses. "
            "Validated f_max is separate and may still be zero."
        ),
    }
