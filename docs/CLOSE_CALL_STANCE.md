# Close-call waterfall → research BUY stance

**Shipped 2026-07-12.** MedTwin/FRE-style stage waterfall on each company page.

## Flow
L0 tape event (SEP) → L1 dated anchors (verified catalog only) → L2 fundamentals → L3 gates/kill → L4 catalyst clarity → weighted ROI runs → stance.

## BUY gates (all required)
- kill off
- completeness A|B
- mos_live > 0
- L4 catalyst **known** (no invented news)
- aggregate score ≥ 65
- confidence med|high

Otherwise: HOLD / WATCH / OUT / **UNKNOWN** with blockers. Horizon (1/2/3y) only on BUY|HOLD when gap known.

## Surfaces
- Company tab **Stance · BUY** + overview teaser
- Sticky digest shows stance + horizon
- `GET /api/universe/company/{ticker}` → `close_call_waterfall`
- `GET /api/universe/stances?stance=BUY` → gated list

## Engine
`backend/app/services/close_call_service.py` · `close_call_v1`  
Tests: `backend/tests/test_close_call_service.py`
