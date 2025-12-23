# Sub-Research 2 (Archived Markdown Mirror): Sector Patterns

**Status:** Archived markdown mirror (December 2025)  
**Authoritative website page:** `/papers/2`  
**Main Paper:** View the consolidated publication-ready paper at `/papers/main`  

---

## Publication safeguard: “0 hallucinations”

This markdown file is intentionally kept **free of hardcoded numeric claims**. Sector-level R&D statistics evolve as
pipeline inputs and cleaning rules change (and Tier-2 upgrades may alter coverage).

For citation-ready results, use the website Sub-Research 2 page and export the underlying tables from the API.

---

## What this sub-research covers

- Which sectors are most R&D intensive in the dataset
- Data coverage and eligibility by sector
- Why sector composition matters for interpreting the R&D return premium

---

## Canonical sources for sector statistics

Use these endpoints (Tier-1) for all sector-level numeric outputs:

- `/api/fmp/rd/by-sector`  
  (sector mean intensity, company counts, and cumulative spend over the dataset period)

- `/api/research/cohort-summary`  
  (eligibility counts by sector across 5/10/20-year windows)

Also see `BASELINE_RESULTS_VERIFIED.md` (Table 4) for the canonical Tier-1 sector summary used for publication.

---

## Interpretation guardrails

- Sector concentration is a real economic exposure for any high-R&D portfolio.
- Sector-neutral tests are required to distinguish “R&D effect” from “sector effect” (see Sub-Research 3 / Appendix).
