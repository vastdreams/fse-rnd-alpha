# First principles, provenance, and decision chains

**Authority:** sealed code + `contracts/formula-registry.json` + `contracts/decision-chains.json` + CI auditors.  
Papers and UI tips cite *why*; they do not override the engine.

## What “no opinion” means here

| Situation | Product behaviour |
|---|---|
| Required input missing | **UNKNOWN** or **exclude** — never invent |
| Metric not disclosed (e.g. retention) | Show `n/d` / Unknown — never estimate |
| High R3 score but price above fair band | **Flag** (Option B) — do not silently imply undervalued |
| Precedence row that is not a hard gate | Marked **advisory** (e.g. P2_FCF) — do not assume it blocks BUY |

Imputation of fundamentals or catalysts is **forbidden**.

## Provenance layers (trace without assumptions)

1. **Data source** — sealed universe vector / panel CSV / live quote / dated catalyst anchors  
2. **Formula ID** — `F_*` in `contracts/formula-registry.json` (expression + audit paths + literature cite)  
3. **Decision chain** — `D_*` in `contracts/decision-chains.json` (ordered gates, data fields, pass/fail/unknown)  
4. **Runtime evidence** — stance `flowchart[]` nodes and rank enrich invariants  

To audit any investor number:

1. Read the UI tip `[F_…]` or stance flowchart node id (`F1`…`F6`)  
2. Open the matching formula / decision-chain entry  
3. Open the listed compute path and audit test  

## Decision chains (summary)

| ID | Question answered | Hard gates are |
|---|---|---|
| `D_STANCE_BUY` | Is this a research BUY? | kill off, completeness A\|B, mos>0, catalyst known, score≥65, confidence |
| `D_RANK_R3` | How does it rank under R3? | not killed/carved; all axes present; MAD robust-z |
| `D_SELL_CEILING` | Where is auto-sell / trim? | band+live known; lens from price vs med/hi |
| `D_FILTER_BELOW_TARGET` | Does a filter use live vs or frozen MoS? | explicit field predicates |

**Rank ≠ BUY.** A top R3 score is recipe attractiveness. BUY is a separate underwriting clearance (`D_STANCE_BUY`).

## Metric reference map (primary)

| Investor field | Formula ID | Data dependence |
|---|---|---|
| vs target | `F_VS_MEDIAN_PCT` | live `price_live`, sealed `fair_px_med` |
| Research MoS | `F_MOS_LIVE` | sealed vector (may diverge from live vs) |
| Fair band zone | `F_FAIR_BAND_ZONE` | price vs lo/hi |
| Score | `F_SCORE_ROBUST_Z` | recipe axes only |
| Sell ceiling | `F_SELL_CEILING` | fair band + live |
| Horizon / implied | `F_HOLD_HORIZON`, `F_IMPLIED_ANN_RETURN` | gap maths — not forecasts |
| rd_prod, fcfm, roic, gm, retention | `F_PASS_THROUGH_FUNDAMENTALS` | panel/vector — **documented**, not re-derived in API |

Literature binds for rank axes live in `backend/app/contracts/recipes.py` (`LITERATURE_BINDS`).

## Machine checks

```bash
python3 scripts/audit_formula_registry.py
python3 scripts/audit_decision_chains.py
cd frontend && npm run test:invariants
cd backend && DEBUG=true SECRET_KEY=… python3 -m pytest tests/test_formula_math.py tests/test_decision_chains.py tests/test_sell_ceiling.py tests/test_recipe_engine_parity.py -q
```

## Explicit non-claims

- Universe fair band is **not** a live DCF replay (`F_DCF_TRIANGULATION` is the company workbench).  
- Stance implied annualised return is **convergence maths**, not a forecast.  
- Advisory precedence (P2_FCF) is transparency, not a silent hard gate.
