# Sub-Research 3 (Archived Markdown Mirror): Factor Tests

**Status:** Archived markdown mirror (December 2025)  
**Authoritative website page:** `/papers/3`  
**Main manuscript for submission:** `papers/JPM_FAJ_MAIN.md`  

---

## Publication safeguard: “0 hallucinations”

This markdown file previously contained evolving draft factor-test numbers (e.g., alpha/t-stats) that can drift across
versions and data tiers.

To keep the repo publication-safe, this file is now a **pointer** to the canonical factor-test endpoints and the
website’s Sub-Research 3 implementation.

---

## What this sub-research covers

- Whether the R&D premium is distinct from standard factor exposures
- Robustness tests (sector-neutral, outlier sensitivity, EW vs VW)
- Factor spanning diagnostics
- Control regressions (Fama–MacBeth / double sorts)

---

## Canonical endpoints (export tables from here)

- **Annual non-overlapping premium (primary inference):** `/api/research/annual-hml-premium`
- **Factor premiums (time series):** `/api/research/factor-premium`
- **Spanning tests:** `/api/research/spanning-tests-full`
- **Fama–MacBeth with controls:** `/api/research/fama-macbeth-controls?start_year=1995&end_year=2024`
- **Double-sort analysis:** `/api/research/double-sort-analysis?start_year=1995&end_year=2024`
- **Mispricing tests:** `/api/research/mispricing-tests?start_year=1995&end_year=2024`
- **Sector-neutral premium series:** `/api/research/sector-neutral-premium-series?start_year=1995&end_year=2024`
- **Outlier sensitivity:** `/api/research/outlier-sensitivity?window_type=5yr`

---

## Tier-1 disclosure

Spanning/control tests are **diagnostic** under Tier-1. Definitive top-journal factor certification requires Tier-2
(CRSP/Compustat) replication and identifier-quality mapping (PERMNO/GVKEY).
