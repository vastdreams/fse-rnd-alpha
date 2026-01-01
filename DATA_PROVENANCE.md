# Data Provenance Documentation

**Publication**: R&D Intensity and Long-Term Shareholder Returns  
**Author**: Abhishek Sehgal  
**Date**: December 2025  
**Version**: 1.1.0

> **See Also**: [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md) for replication instructions and licensing details.

---

## Overview

This document provides complete data provenance for the R&D return premium research project. All data sources, transformations, and limitations are documented for reproducibility and peer review.

### Two-Tier Framework

This research employs a two-tier data framework:

| Tier | Source | Purpose |
|------|--------|---------|
| **Tier-1** | Financial Modeling Prep (FMP) | Primary analysis, accessible to practitioners |
| **Tier-2** | WRDS/CRSP/Compustat | Academic gold standard, robustness verification |

Both tiers use the same methodology (July-June returns, quintile sorting) but differ in data source. Tier-2 provides official CRSP delisting returns and PERMNO-based tracking.

---

## Primary Data Sources

### 1. Financial Modeling Prep (FMP) API

| Field | Value |
|-------|-------|
| **Provider** | Financial Modeling Prep (financialmodelingprep.com) |
| **License** | Commercial API subscription |
| **Data Types** | Income statements, balance sheets, daily prices, company profiles |
| **Coverage** | S&P 500 constituents, 1995-2024 |
| **Update Frequency** | Daily for prices, quarterly for financials |
| **Last Ingestion** | December 2025 |

**Fields Used:**
- `rd_expenses` (R&D Expenses from Income Statement)
- `revenue` (Total Revenue)
- `adj_close` (Split and dividend-adjusted daily closing price)
- `sector`, `industry` (Company classification)

**Limitations:**
- Historical data completeness varies by company
- R&D expense reporting is not mandatory for all companies
- Some companies report R&D within SG&A (not captured separately)

### 2. Ken French Data Library

| Field | Value |
|-------|-------|
| **Provider** | Dartmouth Tuck School of Business |
| **URL** | mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html |
| **License** | Free for academic use |
| **Data Types** | Fama-French factors (MKT-RF, SMB, HML, RMW, CMA, MOM) |
| **Coverage** | 1926-present (monthly), 1963-present (daily) |
| **Last Download** | December 2025 |

**Files Used:**
- `F-F_Research_Data_5_Factors_2x3_CSV.zip`
- `F-F_Momentum_Factor_CSV.zip`

**Limitations:**
- Factor definitions may differ from our R&D-sorted portfolios
- Monthly frequency limits granular analysis

### 3. S&P 500 Historical Constituents

| Field | Value |
|-------|-------|
| **Primary Source** | FMP Historical Constituent API |
| **Secondary Source** | Optional manual cross-check against index-provider change logs (not a required pipeline input) |
| **Coverage** | 1994-present (API), manually curated for earlier dates |
| **Last Update** | December 2025 |

**Known Issues:**
- Some historical add dates are estimated from first available financial data
- Removal dates are accurate; add dates may have ~1 year uncertainty for older records
- Ticker changes (e.g., FB → META) require manual mapping

---

## Data Transformations

### R&D Intensity Calculation

```
R&D Intensity (%) = (R&D Expenses / Revenue) × 100
```

**Filters Applied:**
- Revenue ≥ $100 million (excludes micro-caps)
- R&D Intensity capped at 100% (200% for Healthcare/Biotech)
- Companies must have ≥ 1 year of data

### Return Calculation (July-June Convention)

```
Total Return = (June End Adj Close / July Start Adj Close) - 1
```

**Methodology:**
- Uses adjusted close prices (includes dividends and splits)
- July T to June T+1 returns for FY(T-1) R&D data
- Eliminates look-ahead bias: FY 2019 data → July 2020 portfolio

### Delisting Returns

| Removal Reason | Estimated Return | Source |
|----------------|------------------|--------|
| Merger/Acquisition | 0% | Premium typically priced in |
| Bankruptcy/Distress | -30% | CRSP-style proxy |
| Market Cap Drop | -10% | Size effect |
| Other/Unknown | -5% | Conservative estimate |

**Note:** Price-based estimation is used when available; heuristics are fallback.

---

## Quintile Portfolio Construction

1. Each year, rank all eligible S&P 500 companies by R&D Intensity
2. Divide into 5 equal-sized quintiles (Q1=lowest, Q5=highest)
3. Track subsequent July-June returns for each quintile
4. Rebalance annually (equal-weighted within quintiles)

---

## Known Limitations and Biases

### Survivorship Bias (Two-Tier Framework)

We employ a two-tier framework for addressing survivorship bias:

#### Tier 1: Current Implementation (FMP-Based)

| Aspect | Status | Mitigation |
|--------|--------|------------|
| Historical constituents | Substantially mitigated | FMP API provides add/remove events since 1994 |
| Membership source | Tracked | `membership_source` field records data origin |
| Delisting returns | Price-based + heuristic | Last available price or CRSP-style proxy |
| Add date accuracy | ±1 year for older records | Estimated from first financial data when API unavailable |
| Coverage | ~95% of S&P 500 changes | Manual verification for major events |

**Limitations of Tier 1:**
- FMP data is a commercial API proxy, not the authoritative source (CRSP)
- Some historical add dates are estimated, not precise
- Delisting returns are estimates, not actual CRSP delisting returns
- Ticker changes require manual mapping

#### Tier 2: Ideal Implementation (CRSP/Compustat - Future Upgrade)

| Aspect | Requirement | Source |
|--------|-------------|--------|
| Historical constituents | Point-in-time membership | CRSP S&P 500 Index Constituent History |
| Delisting returns | Actual `dlret` values | CRSP Delisting Returns dataset |
| PERMNO identifiers | Stable cross-time | CRSP security master |
| Compustat integration | GVKEY linkage | WRDS CCM Link Tables |
| Coverage | 1926-present | CRSP/Compustat merged |

**Why Tier 2 Matters:**
- CRSP delisting returns can differ significantly from estimates
- PERMNO tracking handles ticker changes and spin-offs correctly
- Compustat R&D data may be more complete than SEC filings
- Standard in top-tier academic publications (JF, JFE, RFS)

**Current Status:**
The research uses Tier 1 (FMP-based) implementation. Results should be interpreted as "substantially mitigated for survivorship bias" rather than "fully corrected." A Tier 2 upgrade would require WRDS institutional access.

**Impact Estimate:**
Based on academic literature (Shumway 2003, Bessembinder 2018), unaddressed survivorship bias inflates returns by ~0.5-1.5% annually. Our Tier 1 implementation likely reduces this to ~0.2-0.5%.

### Look-Ahead Bias

| Aspect | Status | Mitigation |
|--------|--------|------------|
| Financial data timing | Addressed | July-June returns for prior FY data |
| Index composition | Addressed | Use constituents at portfolio formation |

### Sample Limitations

- **Universe**: S&P 500 only (large-cap US equities)
- **Period**: 1995-2024 (data availability dependent)
- **Sectors**: Overweight Technology and Healthcare in high R&D quintiles

---

## Reproducibility

### Single-Command Reproduction

```bash
./scripts/reproduce_publication.sh
```

### Output Files

| File | Description |
|------|-------------|
| `publication_tables/all_tables.json` | All statistical tables |
| `publication_tables/delisting_sensitivity.txt` | Sensitivity analysis |
| Publication snapshot (`/api/research/publication-snapshot`) | Frozen canonical values used by the on-site paper |

### Version Control

- All code and scripts are version-controlled in Git
- This document is updated with each data refresh

---

## Result Versioning Schema (Dec 2025)

All computed results are now tagged with metadata fields for reproducibility:

| Field | Values | Description |
|-------|--------|-------------|
| `return_convention` | `july_june`, `calendar` | Return calculation method |
| `data_tier` | `tier1`, `tier2` | Data source tier |
| `computation_run_id` | UUID | Unique identifier for each computation run |

These fields are stored in:
- `rolling_window_results`
- `anova_results`
- `factor_premiums`

This allows:
- Storing multiple result sets (e.g., calendar vs July-June) without overwriting
- Clear provenance for peer review
- Comparison across methodologies

---

## Tier-2 Upgrade Path: CRSP/Compustat

The current implementation (Tier 1) uses FMP API data. For top-tier journal publication (JF, JFE, RFS), a Tier-2 upgrade to CRSP/Compustat is recommended.

### Stub Tables Available

The database schema includes placeholder tables for CRSP/Compustat data:

| Table | Purpose |
|-------|---------|
| `crsp_monthly_stock` | CRSP monthly returns with PERMNO identifiers |
| `crsp_compustat_link` | CCM link table for PERMNO-GVKEY mapping |
| `compustat_annual` | Annual fundamentals including XRD (R&D expense) |
| `crsp_sp500_constituents` | Official S&P 500 point-in-time membership |

### Key Advantages of Tier 2

| Aspect | Tier 1 (FMP) | Tier 2 (CRSP/Compustat) |
|--------|--------------|-------------------------|
| Delisting returns | Estimated from last price | Actual CRSP `dlret` values |
| Security tracking | Ticker-based (breaks on changes) | PERMNO (permanent) |
| Index membership | FMP API + estimation | Official CRSP constituent history |
| R&D data | FMP income statements | Compustat XRD field |
| Coverage | 1995-present | 1963-present |
| Academic acceptance | Working papers, SSRN | Top-tier journals |

### Implementation Requirements

1. **WRDS Access**: Institutional subscription required
2. **Data Download**: CRSP Monthly Stock File, CCM Link, Compustat Annual
3. **Ingestion Scripts**: Update `ingest_*.py` to populate Tier-2 tables
4. **Service Updates**: Modify `RollingWindowAnalyzer` to query Tier-2 tables when `data_tier="tier2"`

### Migration Path

```bash
# 0. Apply migrations (psql requires a psql-compatible URL, not SQLAlchemy-style)
PSQL_DATABASE_URL="${DATABASE_URL/postgresql+psycopg2/postgresql}"
PSQL_DATABASE_URL="${PSQL_DATABASE_URL/postgresql+asyncpg/postgresql}"
psql "$PSQL_DATABASE_URL" -f scripts/migrations/001_add_result_versioning.sql

# 1. Download CRSP/Compustat data from WRDS
# 2. Run Tier-2 ingestion
python scripts/ingest_crsp_compustat.py  # (to be created)

# 3. Recompute with Tier-2 data
python scripts/compute_research_metrics.py --data-tier=tier2

# 4. Compare results
python scripts/compare_tier1_tier2.py  # (to be created)
```

---

## Contact

For data questions or replication assistance:
- **Website**: research.finsoeasy.com
- **Email**: [Contact via website]

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | Dec 2025 | Added result versioning schema and Tier-2 upgrade path |
| 1.0.0 | Dec 2025 | Initial publication-ready documentation |

