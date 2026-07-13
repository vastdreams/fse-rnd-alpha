# Close-call waterfall → research BUY stance

**Shipped 2026-07-12.** MedTwin/FRE-style stage waterfall on each company page.

**Provenance (2026-07-14):** every hard gate is data-backed. See
`docs/FIRST_PRINCIPLES_PROVENANCE.md` and decision chain `D_STANCE_BUY` in
`contracts/decision-chains.json`. Flowchart nodes carry `data_fields`,
`formula_ids`, `gate_kind`, and `opinion: false`.

## Flow
L0 tape event (SEP) → L1 dated anchors (verified catalog only) → L2 fundamentals → L3 gates/kill → L4 catalyst clarity → weighted ROI runs → stance.

## BUY gates (all required — hard)
- kill off
- completeness A|B
- mos_live > 0
- L4 catalyst **known** (no invented news)
- aggregate score ≥ 65
- confidence med|high

Otherwise: HOLD / WATCH / OUT / **UNKNOWN** with blockers. Horizon (1/2/3y) only on BUY|HOLD when gap known.

## Advisory (not a hard BUY gate)
- **P2_FCF** (`fcfm_sbc > 0`) is labeled **advisory — not a BUY gate** in API/UI (`gate_kind=advisory`).
  It is **not** in `buy_ok`. StanceTab shows an ADVISORY badge. Match/fail ≠ underwriting clearance.
- Curves: `backend/app/services/stance_scores.py` (golden-pinned in `test_stance_scores.py`).

## Surfaces
- Company tab **Stance · BUY** + overview teaser
- Sticky digest shows stance + horizon
- `GET /api/universe/company/{ticker}` → `close_call_waterfall` (+ `decision_provenance`)
- `GET /api/universe/stances?stance=BUY` → gated list
- Rank rows include `provenance` (`D_RANK_R3`)

## Engine
`backend/app/services/close_call_service.py` · `close_call_v1`  
Tests: `backend/tests/test_close_call_service.py`, `backend/tests/test_decision_chains.py`
