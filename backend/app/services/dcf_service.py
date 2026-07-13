"""
PATH: backend/app/services/dcf_service.py
PURPOSE: W4 DCF workbench engine — dependency-free mirror of the paper's
valuation formulas (scripts/saas_ai/analysis/valuation_engine.py).

The formulas here MUST stay bit-compatible with the research engine; golden
tests in backend/tests/test_dcf_service.py pin them against known values.
Every run is saved with its full input set + engine version (dcf_runs table)
so any fair value shown in the UI is reproducible from frozen inputs.
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field, model_validator

ENGINE_VERSION = "dcf_service@w4-1.0"
YEARS, GLIDE, GTERM, GCAP = 10, 7, 0.03, 0.30


class DcfInputs(BaseModel):
    """Explicit assumption set. Nothing hardcoded to a result."""

    ticker: str
    scenario: str = "custom"
    # Firm state (frozen from snapshot)
    revenue_usd: Optional[float] = None
    fcf_sbc_usd: Optional[float] = None
    fcfm_sbc: Optional[float] = None
    net_cash_usd: float = 0.0
    ev_mult_usd: Optional[float] = Field(default=None, description="Peer Rule-of-40 fair EV (from panel OLS)")
    shares_fut_implied: Optional[float] = Field(
        default=None, description="Future share count implied by panel fair band (dilution-adjusted)"
    )
    price: Optional[float] = None
    # Assumptions (editable in the workbench)
    growth: float = Field(description="Initial growth rate, fades linearly to terminal")
    wacc: float = 0.10
    terminal_g: float = GTERM
    target_margin: Optional[float] = Field(default=None, description="Steady-state SBC-adj FCF margin")
    years: int = Field(default=YEARS, ge=2, le=30)
    glide_years: int = Field(default=GLIDE, ge=1, le=30)

    @model_validator(mode="after")
    def _horizon_is_sane(self) -> "DcfInputs":
        if self.glide_years > self.years:
            raise ValueError("glide_years cannot exceed years")
        return self


class DcfOutputs(BaseModel):
    ev_dcf_fcf: Optional[float] = None
    ev_dcf_norm: Optional[float] = None
    ev_mult: Optional[float] = None
    fair_ev_lo: Optional[float] = None
    fair_ev_med: Optional[float] = None
    fair_ev_hi: Optional[float] = None
    fair_px_lo: Optional[float] = None
    fair_px_med: Optional[float] = None
    fair_px_hi: Optional[float] = None
    mos: Optional[float] = None
    engine_version: str = ENGINE_VERSION


def two_stage_ev(fcf0: float, g: float, wacc: float, years: int = YEARS, g_term: float = GTERM) -> Optional[float]:
    """2-stage owner-earnings DCF; growth fades linearly to terminal. Mirrors _two_stage_ev."""
    if not (math.isfinite(fcf0) and math.isfinite(g)) or fcf0 <= 0 or wacc <= g_term:
        return None
    pv, fcf = 0.0, fcf0
    for t in range(1, years + 1):
        gt = g + (g_term - g) * (t - 1) / (years - 1)
        fcf *= 1.0 + gt
        pv += fcf / (1.0 + wacc) ** t
    pv += fcf * (1.0 + g_term) / (wacc - g_term) / (1.0 + wacc) ** years
    return pv


def three_stage_ev(
    rev0: float, g0: float, m0: Optional[float], m_tgt: float,
    wacc: float, years: int = YEARS, glide: int = GLIDE, g_term: float = GTERM,
) -> Optional[float]:
    """Path-to-profitability EV; margin glides m0→m_tgt. Mirrors _three_stage_ev."""
    if not (math.isfinite(rev0) and rev0 > 0 and math.isfinite(m_tgt)) or wacc <= g_term:
        return None
    g0 = max(-0.10, min(GCAP, g0 if (g0 is not None and math.isfinite(g0)) else g_term))
    m0 = m0 if (m0 is not None and math.isfinite(m0)) else m_tgt
    pv, rev = 0.0, rev0
    for t in range(1, years + 1):
        gt = g0 + (g_term - g0) * (t - 1) / (years - 1)
        rev *= 1.0 + gt
        m = m0 + (m_tgt - m0) * min(t, glide) / glide
        pv += (rev * m) / (1.0 + wacc) ** t
    pv += (rev * m_tgt) * (1.0 + g_term) / (wacc - g_term) / (1.0 + wacc) ** years
    return pv


def run_dcf(inp: DcfInputs) -> DcfOutputs:
    """Triangulate the three lenses exactly like value_all(); price band via implied shares."""
    ev_fcf = (
        two_stage_ev(inp.fcf_sbc_usd, inp.growth, inp.wacc, inp.years, inp.terminal_g)
        if inp.fcf_sbc_usd is not None and inp.fcf_sbc_usd > 0
        else None
    )
    ev_norm = (
        three_stage_ev(
            inp.revenue_usd, inp.growth, inp.fcfm_sbc, inp.target_margin,
            inp.wacc, inp.years, inp.glide_years, inp.terminal_g,
        )
        if inp.revenue_usd is not None and inp.target_margin is not None
        else None
    )
    methods = [m for m in (ev_fcf, ev_norm, inp.ev_mult_usd) if m is not None and math.isfinite(m)]
    out = DcfOutputs(ev_dcf_fcf=ev_fcf, ev_dcf_norm=ev_norm, ev_mult=inp.ev_mult_usd)
    if not methods:
        return out
    methods.sort()
    out.fair_ev_lo = methods[0]
    out.fair_ev_hi = methods[-1]
    out.fair_ev_med = (
        methods[len(methods) // 2]
        if len(methods) % 2
        else (methods[len(methods) // 2 - 1] + methods[len(methods) // 2]) / 2
    )
    if inp.shares_fut_implied and inp.shares_fut_implied > 0:
        for tag in ("lo", "med", "hi"):
            ev = getattr(out, f"fair_ev_{tag}")
            setattr(out, f"fair_px_{tag}", (ev + inp.net_cash_usd) / inp.shares_fut_implied)
        if inp.price and inp.price > 0 and out.fair_px_med is not None:
            out.mos = max(-0.95, min(5.0, out.fair_px_med / inp.price - 1.0))
    return out
