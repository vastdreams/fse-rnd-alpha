<!--
PATH: papers/METHODOLOGY.md
PURPOSE:
  Human-readable methodology note for the R&D Alpha platform (Tier-1 + snapshot).

WHY:
  This repository contains multiple generations of code. This document exists to prevent
  reader confusion by describing the CURRENT publication pipeline (as used by the website
  and the LaTeX paper), without hard-coded result numbers that can drift between snapshots.
-->

# R&D Alpha: Data Sources and Methodology (Platform)

This document describes the methodology implemented in the live platform and the frozen publication snapshot.
For the submission-grade write-up (definitions, caveats, tables), see the LaTeX manuscript in `paper_latex/main.tex`
and the downloadable PDF.

## 1. Data Sources (Tier-1)

### 1.1 Fundamentals (FMP)

Tier-1 fundamentals are sourced from Financial Modeling Prep (FMP) using stable endpoints (subscription required).
We use vendor-standardized financial statement fields rather than parsing raw filings inside the publication pipeline.

Primary fields:
- R&D expense
- Revenue
- Sector/industry labels

### 1.2 Prices (Tier-1 daily)

Tier-1 daily prices are ingested as **split-adjusted close** prices from the provider's stable EOD feed.
This series is NOT dividend-adjusted.

### 1.3 Dividends (Tier-1 events)

Tier-1 dividends are ingested as **ex-dividend events** (per-share dividends, including split-adjusted `adjDividend`
when available). These cashflows are used to construct a total-return proxy when computing returns.

### 1.4 Universe membership (Tier-1 proxy)

Tier-1 enforces index eligibility using a constituent dataset with **addition dates** (inclusion after the add date).
Limitations are disclosed in the paper (Tier-1 does not fully track historical removals or historical constituents
that are no longer in the current list).

## 2. Signal: R&D Intensity

We define R&D intensity as:

```
R&D Intensity (%) = (R&D Expense / Revenue) × 100
```

Notes:
- If R&D expense is missing for a firm-year, that firm-year is not eligible for sorting.
- A minimum revenue filter is applied to avoid micro-cap / pre-revenue distortions.
- Sector-aware caps are applied to prevent extreme outliers from dominating the sort (documented in the paper).

## 3. Returns: July-June Convention + Total-Return Proxy

### 3.1 Timing (look-ahead mitigation)

We follow the Fama-French July-June convention:
- Use fiscal-year \(T\) fundamentals to form portfolios at end of June \(T+1\)
- Measure returns from July \(T+1\) through June \(T+2\)

This avoids trading on accounting information that was not yet public at the start of a calendar year.

### 3.2 Tier-1 total-return proxy (close + dividends)

Tier-1 does not rely on a vendor dividend-adjusted close series. Instead, we construct a dividend-reinvested proxy
using split-adjusted closes plus ex-dividend cashflows:

```
Daily return (no dividend): r_t = P_t / P_{t-1} - 1
Daily return (ex-dividend): r_t = (P_t + D_t) / P_{t-1} - 1
July-Jun total return:      R = ∏(1 + r_t) - 1
```

Where:
- \(P_t\) is split-adjusted close
- \(D_t\) is the split-adjusted dividend per share on the ex-dividend date (0 otherwise)

## 4. Portfolio Construction

### 4.1 Characteristic premium (HML_RD)

Each formation year, we:
1. Rank eligible firms by R&D intensity
2. Split into quintiles (Q1 lowest, Q5 highest)
3. Compute July-Jun returns for each quintile
4. Define the characteristic premium as:

```
HML_RD = Return(Q5) - Return(Q1)
```

Primary inference uses the **non-overlapping annual** HML_RD series (July-Jun windows).

### 4.2 Investable strategy (RD20)

Separately from HML_RD, we also report an implementable long-only strategy:
- Hold the top 20 names by R&D intensity (equal-weighted)
- Reconstitute annually in July
- Compare performance versus SPY using the same return convention and Tier-1 total-return proxy
- Model transaction costs from realized turnover (see paper)

## 5. Statistical Inference (Publication)

Key principles:
- **Non-overlapping annual returns** for primary inference (avoids mechanical overlap)
- **Newey-West (HAC) standard errors** for conservative inference under time-series dependence
- Rolling windows are treated as descriptive (overlapping by construction)

## 6. Reproducibility and Snapshot Pinning

The platform exposes a frozen snapshot used by both:
- the website, and
- the LaTeX asset generator (`paper_latex/scripts/build_assets.py`).

To regenerate end-to-end (local, requires DB + FMP key):
- `scripts/reproduce_publication.sh`

To fetch the active snapshot from a running deployment:
- `GET /api/research/publication-snapshot`

## 7. Known Limitations (Tier-1)

- Tier-1 is a practitioner-grade proxy; Tier-2 (CRSP/Compustat) is required for authoritative delisting returns.
- Membership is addition-date gated but does not fully track removals for all historical cases.
- Vendor series can differ slightly from CRSP total returns due to methodology differences.

---

*Document updated: January 2026*  

