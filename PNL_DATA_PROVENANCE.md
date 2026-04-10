# Data Provenance Documentation

**Publication**: P&L Efficiency Alpha: Operating Cost Structure and Long-Term Stock Returns  
**Author**: Abhishek Sehgal  
**Date**: February 2026  
**Version**: 1.0.0

> **See Also**: [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md) for replication instructions and licensing details.

---

## Overview

This document provides complete data provenance for the P&L Efficiency Alpha research project. All data sources, transformations, and limitations are documented for reproducibility and peer review.

### Data Framework

This research uses Tier-1 data (FMP) consistent with the companion R&D Alpha study. The same two-tier verification approach (FMP primary, WRDS/Compustat secondary) will be applied when Tier-2 validation is conducted.

| Tier | Source | Purpose |
|------|--------|---------|
| **Tier-1** | Financial Modeling Prep (FMP) | Primary analysis, accessible to practitioners |
| **Tier-2** | WRDS/CRSP/Compustat | Academic gold standard, robustness verification (planned) |

---

## Primary Data Sources

### 1. Financial Modeling Prep (FMP) API

| Field | Value |
|-------|-------|
| **Provider** | Financial Modeling Prep (financialmodelingprep.com) |
| **License** | Commercial API subscription |
| **Data Types** | Income statements, daily prices, company profiles |
| **Coverage** | Typically 1995–present (varies by company); primary inference window Jul 2001–Jun 2025 |
| **Update Frequency** | Daily (prices), quarterly (financials) |
| **Last Ingestion** | February 2026 |

**Income Statement Fields Used:**

| Field | FMP Key | Description |
|-------|---------|-------------|
| Revenue | `revenue` | Total revenue |
| Cost of Goods Sold | `costOfRevenue` | Direct production costs |
| SG&A | `sellingGeneralAndAdministrative` | Selling, general, and administrative expenses |
| Operating Income | `operatingIncome` | Revenue − CoGS − SG&A − other operating expenses |
| Net Income | `netIncome` | Bottom-line earnings |

**Price/Return Fields Used:**

| Field | Description |
|-------|-------------|
| `close` | Split-adjusted daily closing price (stable EOD endpoint) |
| Dividend events | Ex-dividend dates; `adjDividend` (split-adjusted per-share dividend) |
| `sector`, `industry` | GICS sector and industry classification |

### 2. Ken French Data Library

| Field | Value |
|-------|-------|
| **Provider** | Dartmouth Tuck School of Business |
| **URL** | mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html |
| **License** | Free for academic use |
| **Data Types** | Fama-French factors (MKT-RF, SMB, HML, RMW, CMA, MOM) |
| **Coverage** | 1926–present (monthly) |
| **Last Download** | February 2026 |

### 3. S&P 500 Constituents

| Field | Value |
|-------|-------|
| **Source** | Curated constituent dataset with S&P 500 addition dates (Tier-1 proxy) |
| **Coverage** | Current constituents with addition dates; historical removals not fully tracked |
| **Last Update** | February 2026 |

---

## Variable Construction Pipeline

### Step 1: Income Statement Retrieval
- Fetch annual income statements for all S&P 500 constituents from FMP
- Filter: revenue > 0, fiscal year end before July 1 of formation year

### Step 2: Efficiency Ratio Computation
- Gross Efficiency: `1 - costOfRevenue / revenue`
- Overhead Efficiency: `1 - sellingGeneralAndAdministrative / revenue`
- Operating Efficiency: `operatingIncome / revenue`
- Profit Conversion: `netIncome / operatingIncome` (set to 0 if operating income ≤ 0)

### Step 3: Sector-Relative Z-Scoring
- Group firms by GICS sector at formation date
- Require minimum 5 firms per sector
- Compute within-sector mean and standard deviation for each ratio
- Standardize: z = (ratio − sector_mean) / sector_std
- Winsorize z-scores at ±3.0σ

### Step 4: Composite Score
- Equal-weighted average of four winsorized z-scores
- Compute percentile rank within full cross-section

### Step 5: Return Construction
- July 1 formation, June 30 evaluation
- Split-adjusted total returns (price + dividends)
- Cash-after-exit treatment for delistings

---

## Data Quality Notes

1. **CoGS classification**: Some firms include depreciation and amortization in CoGS; others report it separately. FMP's `costOfRevenue` follows the as-reported convention, which may differ across firms.

2. **SG&A completeness**: A small number of firms report zero SG&A (rolling all costs into CoGS). These firms will have overhead efficiency = 1.0 and are retained but flagged.

3. **Negative operating income**: Firms with operating income ≤ 0 have profit conversion set to 0. This affects approximately 2–5% of the universe in any given year.

4. **Sector reclassifications**: GICS sector assignments may change over time. We use the sector reported at the time of the most recent annual filing.

---

## Limitations

- FMP data completeness varies by company age and listing history
- Some firms report R&D within SG&A (not separable without footnote parsing)
- CoGS vs. SG&A boundary is not standardized across all firms
- Historical constituent tracking is incomplete (survivorship bias)
