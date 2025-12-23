# Sub-Research 1 (Archived Markdown Mirror): Returns & Inference

**Status:** Archived markdown mirror (December 2025)  
**Authoritative website page:** `/papers/1`  
**Main manuscript for submission:** `papers/JPM_FAJ_MAIN.md`  

---

## Publication safeguard: “0 hallucinations”

This markdown file previously contained evolving draft tables and placeholder figures. To prevent drift and accidental
misstatement, it is now an **archived pointer** to the canonical sources of truth.

If you are preparing a journal submission (JPM/FAJ), use:

- `papers/JPM_FAJ_MAIN.md` (single main paper)
- `papers/JPM_FAJ_APPENDIX.md` (online appendix; generated from endpoints)
- `BASELINE_RESULTS_VERIFIED.md` (canonical Tier-1 numbers)

---

## Canonical headline results (Tier-1, verified)

The following rolling-window summary values are taken directly from `BASELINE_RESULTS_VERIFIED.md`.

| Horizon | Q5 Return | Q1 Return | HML Premium (Q5−Q1) | t-stat | p-value | Cohen's d | η² |
|---------|-----------|-----------|---------------------|--------|---------|-----------|-----|
| 5-Year | 23.01% | 15.90% | **+7.11%** | 3.344 | 0.00160 | 0.894 | 0.225 |
| 10-Year | 19.84% | 15.06% | **+4.78%** | 3.921 | 0.00030 | 1.132 | 0.319 |
| 20-Year | 16.87% | 14.25% | **+2.62%** | 4.089 | 0.00037 | 1.446 | 0.458 |

**Interpretation (dataset-conditional):** premium magnitude declines with horizon, while effect size increases.

---

## Primary inference (annual non-overlapping series)

For publication-grade inference, use the annual non-overlapping HML premium series:

- Endpoint: `/api/research/annual-hml-premium`
- Website table: Main Paper → “Primary Result: Annual HML R&D Premium”

Do **not** hardcode the annual summary statistics in this markdown file; export them from the endpoint to avoid drift.

---

## Data tier disclosure

- **Tier-1:** Financial Modeling Prep (FMP) fundamentals + prices, Ken French factor series.
- **Bias mitigation:** July–June returns by default; historical constituent tracking; Tier-1 delisting return adjustments.
- **Limitation:** Tier-1 is not CRSP/Compustat-grade; Tier-2 upgrade path is documented in `DATA_AVAILABILITY.md`.
