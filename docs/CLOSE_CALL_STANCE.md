# Close-call waterfall → research BUY stance

**Provenance:** every hard gate is data-backed. See
`docs/FIRST_PRINCIPLES_PROVENANCE.md` and decision chain `D_STANCE_BUY` in
`contracts/decision-chains.json`. Flowchart nodes carry `data_fields`,
`formula_ids`, `gate_kind`, and `opinion: false`.

## Flow
L0 tape event (SEP) → L1 dated anchors (verified catalog only) → L2 fundamentals → L3 gates/kill → L4 catalyst clarity → weighted ROI runs → stance.

## BUY gates (all required — hard)
- kill off
- completeness A|B
- sealed `mos_live` > 0 (frozen research MoS — **not** live intrinsic value)
- live `gap_to_median` > 0 (F3b — tape must still show value vs sealed target)
- L4 catalyst **known** (no invented news)
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

## Engine
`backend/app/services/close_call_service.py` · `close_call_v2`  
Tests: `backend/tests/test_close_call_service.py`, `backend/tests/test_decision_chains.py`
