# Data Acquisition Guide for Publication-Ready Research

This document outlines the external data sources required for peer-reviewed journal submission quality research.

## Current Data Sources (Already Implemented)

| Data | Source | Coverage | Limitations |
|------|--------|----------|-------------|
| Financial statements | FMP API | 1994-2025 | Current constituents only |
| Annual returns | FMP API | 1994-2025 | Calendar year |
| Daily prices | FMP API | 2000-2025 | Split-adjusted |

## Required External Data for Journal Submission

### 1. Historical S&P 500 Constituents

**Purpose:** Eliminate survivorship bias

**Source Options:**
- **CRSP (via WRDS)** - Gold standard
  - Table: `crsp.dsf` joined with `crsp.msenames`
  - Fields: `permno`, `ticker`, `comnam`, `shrcd`, `exchcd`
  
- **Compustat Index Constituents**
  - Table: `comp.idxcst_his`
  
- **S&P Capital IQ**
  - Historical index membership data

**Schema:**
```sql
CREATE TABLE sp500_historical_constituents (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    permno INTEGER,
    added_date DATE NOT NULL,
    removed_date DATE,
    removal_reason VARCHAR(50),
    company_name VARCHAR(255),
    sector VARCHAR(100)
);
```

**Loading Script:** `scripts/load_historical_constituents.py`

### 2. Delisting Returns

**Purpose:** Avoid return bias from excluding delisted companies

**Source:** CRSP `dsedelist` table
- Field: `dlret` (delisting return)
- Field: `dlstcd` (delisting code)

**Schema:**
```sql
CREATE TABLE delisting_returns (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    permno INTEGER,
    delist_date DATE NOT NULL,
    delist_return FLOAT NOT NULL,
    delist_code INTEGER,
    reason VARCHAR(100)
);
```

### 3. Fama-French Factors

**Purpose:** Factor spanning tests

**Source:** Kenneth French Data Library (free)
- URL: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
- Files:
  - `F-F_Research_Data_Factors` (MKT-RF, SMB, HML, RF)
  - `F-F_Research_Data_5_Factors_2x3` (adds RMW, CMA)
  - `F-F_Momentum_Factor` (MOM)

**Schema:**
```sql
CREATE TABLE ff_factors (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    frequency VARCHAR(10) NOT NULL,
    mkt_rf FLOAT,
    smb FLOAT,
    hml FLOAT,
    rmw FLOAT,
    cma FLOAT,
    mom FLOAT,
    rf FLOAT
);
```

**Loading Script:** `scripts/load_ff_factors.py`

### 4. Risk-Free Rates

**Purpose:** Sharpe ratio calculations

**Source:** Ken French Data Library or FRED (DGS1MO)

**Schema:**
```sql
CREATE TABLE risk_free_rates (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    rate_annual_pct FLOAT NOT NULL,
    source VARCHAR(50) DEFAULT 'FF_RF'
);
```

## Data Loading Workflow

1. **Acquire WRDS access** (requires institutional subscription)
2. **Download historical constituents:**
   ```bash
   python scripts/load_historical_constituents.py --source crsp
   ```
3. **Download FF factors:**
   ```bash
   python scripts/load_ff_factors.py
   ```
4. **Load delisting returns:**
   ```bash
   python scripts/load_delisting_returns.py
   ```
5. **Recompute all results:**
   ```bash
   python scripts/recompute_with_historical.py
   ```

## Impact on Results

After loading historical data, expect:

1. **Lower premiums:** Survivorship bias typically inflates returns by 0.5-1% annually
2. **Different quintile composition:** More companies in Q1 (bankruptcies often had low R&D)
3. **More robust inference:** Larger, more representative sample
4. **Journal-ready claims:** Can state "survivorship-bias-free analysis"

## Validation Checklist

- [ ] Historical constituents loaded (1990-2025)
- [ ] Delisting returns incorporated
- [ ] FF factors loaded (monthly and annual)
- [ ] Risk-free rates time series complete
- [ ] Results recomputed with new data
- [ ] Premium comparison: with vs without survivorship correction

