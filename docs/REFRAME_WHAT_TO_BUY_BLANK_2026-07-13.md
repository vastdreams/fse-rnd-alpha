# Reframe — What-to-Buy blank screen
1. **Symptom:** `/app/universe?mode=buy` initially renders its shell, then `#root` becomes empty after `/api/universe/rank?recipe_id=R3` and `/api/universe/stances` both return HTTP 200.
2. **Attempt 1:** deployed comma-grouped / explained dense metrics + optional rank fields; production page blanked after data load.
3. **Attempt 2:** moved top-10 selection seeding from an effect into the rank-load callback; production page blanked identically.
4. **Minimal reproduction:** authenticated Cursor browser, production URL above, wait ~3s; backend logs both GETs as 200; DOM inspection shows `<div id="root"></div>`.
5. **Hypothesis A:** a `BuyDenseRow` data-dependent render path or format helper throws only against the real top-10 payload (component fixture render passes).
6. **Hypothesis B:** `UniversePage` selection lifecycle / StrictMode causes React to unmount after the async rank result.
7. **Hypothesis C:** response shape/cache incompatibility appears only in the browser’s production session.
8. **Root cause (confirmed):** `frontend/src/lib/sellCeiling.ts` called `formatPercent4` inside `fmtSellUpside` / `fmtSellAnn` without importing it. Any below-target BUY row hits that path in `BuyDenseRow` (“… to sell”) and throws `ReferenceError`, wiping `#root`. Fixture tests missed it because they used a past-ceiling row.
9. **Fix:** import `formatPercent4`; add `fmtSellUpside` + below-target `BuyDenseRow` regression tests.
10. **Next:** redeploy frontend; smoke `/app/universe?mode=buy`; continue sell-ceiling polish + compact table only after smoke is green.
