# Close-call waterfall → research BUY stance

**Provenance:** every hard gate is data-backed. See
`docs/FIRST_PRINCIPLES_PROVENANCE.md` and decision chain `D_STANCE_BUY` in
`contracts/decision-chains.json`. Flowchart nodes carry `data_fields`,
`formula_ids`, `gate_kind`, and `opinion: false`.

## Flow
L0 tape event (SEP) → L1 dated anchors (verified catalog only) → L2 fundamentals → L3 gates/kill → L4 catalyst clarity → weighted ROI runs → stance.

## BUY gates (all required — hard) — Repriced × R&D-Validated × Survivable
- **F0** `rd_elig` true — top-quintile RD composite within the sealed universe
  (`contracts/thesis-gates.json`). The paper factor spine is the only selection
  component with published inference; cross-sectional evidence only, never a
  per-name return claim.
- kill off
- completeness A|B
- **F2b** `survivable` true — hard floors (cash engine FCF+/Rule-of-40, runway,
  dilution, retention). A dead company collects no factor premium.
- sealed `mos_live` > 0 (frozen research MoS — **not** live intrinsic value)
- live `gap_to_median` > 0 (F3b — tape must still show value vs sealed target)
- **F3c** `payoff_skew` ≥ 3:1 (or price below the low lens) — band asymmetry
  must favour the long; the band is a model output, not market data.
- L4 catalyst **known** with **dated** anchors inside the tape-event window (no invented news)
- aggregate score ≥ 65
- confidence med|high

Otherwise: HOLD / WATCH / OUT / **UNKNOWN** with blockers. Horizon (1/2/3y) only on BUY|HOLD when gap known.

**Implied %/yr** is gap-close maths — not a forecast and not a sizing order.

## Advisory (not a hard BUY gate)
- **P2_FCF** (`fcfm_sbc > 0`) is labeled **advisory — not a BUY gate** in API/UI (`gate_kind=advisory`).
  It is **not** in `buy_ok`. StanceTab shows an ADVISORY badge. Match/fail ≠ underwriting clearance.
- Curves: `backend/app/services/stance_scores.py` (golden-pinned in `test_stance_scores.py`).

## Distinct from paper HML_RD
Paper `HML_RD` / RD20 is a publication factor engine. It does **not** prove the research BUY clearance book. See `GET /api/universe/buy-performance-book`.

## Surfaces
- Company tab **Stance · BUY** + overview teaser
- Sticky digest shows stance + horizon
- `GET /api/universe/company/{ticker}` → `close_call_waterfall` (+ `decision_provenance`)
- `GET /api/universe/stances?stance=BUY` → gated list
- Rank rows include `provenance` (`D_RANK_R3`) + ADV / `liquidity_usd` tradability strip

## Validation (mathematical trust test)
Two separate tracks — never mixed:

1. **Sealed ledger** (`buy_set_snapshots kind='sealed'`) — the only allocator-facing
   track record. Starts 2026-07. Served by `GET /api/universe/buy-performance-book`
   (which filters `kind='sealed'`). Forward returns per
   `backend/app/services/buy_performance_book.py`.
2. **Simulated robustness study** (`sim_proxy_v1`) — pre-registered proxy gates in
   `contracts/simulated-buy-gates.json` (frozen before results; any edit voids the study),
   run by `scripts/simulate_buy_history.py` over the ~3y immutable price cache with SPY
   benchmark (`scripts/cache_benchmark_bars.py`). Newey–West t-stats on monthly
   equal-weight excess returns, hit rate, max drawdown. Stored as `kind='simulated'`
   snapshots + frozen artifact `data/exports/buy_sim_study_v1.json`, served read-only by
   `GET /api/universe/buy-sim-study`.

What the study is **not**: not paper HML_RD, not a clean PIT backtest (fair bands,
completeness grades, and universe membership are today's, applied backwards — every
look-ahead is listed in the contract's `disclosures` and rendered verbatim in the UI).

## Sizing (separate layer — validated evidence only)
Only the frozen paper premium sizes capital: `f_max = 0.25 · max(0, λ_headline −
1.96·SE_NW) / σ²_book` (`backend/app/services/factor_sizing.py`). With today's
frozen numbers (λ=3.73%/yr, NW SE 3.38, t=1.10) the bound is **zero** — the
product says "no validated edge, no size" until the sealed ledger or the factor
evidence strengthens. Skew and p* justify the shape of a bet, never its size.
Falsification rules are pre-registered in `contracts/falsification-rules.json`.

## Engine
`backend/app/services/close_call_service.py` · `close_call_v3`  
Tests: `backend/tests/test_close_call_service.py`, `backend/tests/test_decision_chains.py`, `backend/tests/test_thesis_fields.py`
