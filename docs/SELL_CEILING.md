# Sell ceiling (auto-sell) — first principles

**Source of truth (math):** `frontend/src/lib/sellCeiling.ts`  
**Design canvas:** `canvases/sell-ceiling-design.canvas.tsx` (duraloop-paper Cursor canvases)

## Invariant

Derived only from `fair_px_lo / med / hi` and `price_live`. Same hold-horizon
buckets as stance (`close_call_service`). Not a forecast.

| Zone | When | Auto-sell |
|------|------|-----------|
| to_target | live &lt; median | **median** (price target; MoS→0) |
| in_upper_band | median ≤ live &lt; high | **high** (trim) |
| past_ceiling | live ≥ high | through band |

Remaining ann. if gap closes over H: `(sell_ceil ÷ live)^(1/H) − 1`.

## Surfaces

- Universe table column **Sell ceil** (sortable by upside)
- Valuation tab band card **Auto-sell ceiling**
