# Data Availability Statement

**Publication**: R&D Intensity and Long-Term Shareholder Returns  
**Author**: Abhishek Sehgal  
**Date**: December 2025  
**Version**: 1.0.0

---

## Overview

This document describes the data sources used in this research and provides instructions for replicating the analysis. We employ a two-tier data framework to balance accessibility with academic rigor.

---

## Data Tiers

### Tier-1: Financial Modeling Prep (FMP)

**Source**: Financial Modeling Prep API (https://financialmodelingprep.com)

**License**: Commercial API subscription required

**Data Types**:
- Income statements (R&D expenses, revenue)
- Daily stock prices (adjusted for splits and dividends)
- Company profiles (sector, industry)
- S&P 500 constituent list

**Coverage**: 
- Companies: S&P 500 constituents
- Period: 1995-2024 (varies by company)

**Replication Instructions**:

1. **Obtain FMP API Key**: Subscribe to FMP at https://financialmodelingprep.com
   - Minimum tier: "Starter" for basic data
   - Recommended: "Professional" for historical constituents

2. **Set Environment Variable**:
   ```bash
   export FMP_API_KEY=your_api_key_here
   ```

3. **Run Ingestion**:
   ```bash
   python scripts/ingest_fmp_ultimate.py
   python scripts/ingest_sp500_historical.py
   ```

4. **Compute Returns**:
   ```bash
   python scripts/compute_july_june_returns.py --data-tier tier1
   ```

**Limitations**:
- Not the authoritative source for academic finance research
- Some historical constituent dates are estimated
- Delisting returns are heuristic-based, not CRSP official

**Redistribution**: FMP data cannot be redistributed under their terms of service. Replicators must obtain their own subscription.

---

### Tier-2: WRDS/CRSP/Compustat (Academic Gold Standard)

**Source**: Wharton Research Data Services (https://wrds-www.wharton.upenn.edu)

**License**: Institutional subscription required (most universities have access)

**Data Types**:
- CRSP Monthly Stock File (RET, DLRET, PRC, SHROUT)
- CRSP-Compustat Merged (CCM) Link Tables
- Compustat Annual Fundamentals (XRD, REVT, AT)
- CRSP S&P 500 Constituent History

**Coverage**:
- Companies: Full CRSP universe (can be filtered to S&P 500)
- Period: 1926-present (CRSP), 1950-present (Compustat)

**Replication Instructions**:

1. **Obtain WRDS Access**: 
   - Through your institution's library
   - Or request individual researcher access at https://wrds-www.wharton.upenn.edu

2. **Download Required Files** from WRDS Web Interface or SAS/Python:

   **CRSP Monthly Stock File** (`crsp_monthly.csv`):
   ```
   Library: crsp
   Table: msf (or msenames for identifiers)
   Columns: permno, date, ret, dlret, prc, shrout, cfacpr, cfacshr
   Date Range: 1990-01-01 to present
   ```

   **CRSP-Compustat Link** (`ccm_link.csv`):
   ```
   Library: crsp
   Table: ccmxpf_linktable
   Columns: permno, gvkey, linkdt, linkenddt, linktype, linkprim
   ```

   **Compustat Annual** (`compustat_annual.csv`):
   ```
   Library: comp
   Table: funda
   Columns: gvkey, datadate, fyear, xrd, revt, at, ceq, csho, prcc_f, ni, oibdp, sale, sic, naics
   Date Range: FY 1990 to present
   Filters: indfmt='INDL', datafmt='STD', popsrc='D', consol='C'
   ```

   **CRSP S&P 500 Constituents** (`crsp_sp500.csv`):
   ```
   Library: crsp
   Table: dsp500list (or msp500list)
   Columns: permno, start, ending, ticker, comnam
   ```

3. **Place Files** in `data/wrds/` directory:
   ```
   data/
   └── wrds/
       ├── crsp_monthly.csv
       ├── ccm_link.csv
       ├── compustat_annual.csv
       └── crsp_sp500.csv
   ```

4. **Run Ingestion**:
   ```bash
   python scripts/ingest_wrds_tier2.py --input-dir data/wrds/
   ```

5. **Compute Returns**:
   ```bash
   python scripts/compute_july_june_returns.py --data-tier tier2
   ```

**Redistribution**: WRDS/CRSP/Compustat data cannot be redistributed. Replicators must have their own institutional access.

---

## Full Replication Pipeline

### Option A: Tier-1 Only (Most Accessible)

```bash
# Set API key
export FMP_API_KEY=your_key

# Run full pipeline
./scripts/reproduce_publication.sh
```

Produces: `publication_tables/` with all results

### Option B: Both Tiers (Academic Standard)

```bash
# Set API key
export FMP_API_KEY=your_key

# Place WRDS files in data/wrds/

# Run full pipeline (includes Tier-1)
./scripts/reproduce_publication.sh

# Run Tier-2
python scripts/ingest_wrds_tier2.py --input-dir data/wrds/
python scripts/compute_july_june_returns.py --data-tier tier2

# Run rolling windows for Tier-2
python -c "
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'backend'))
from app.db.session import async_session_factory
from app.services.rolling_window import RollingWindowAnalyzer

async def main():
    async with async_session_factory() as session:
        analyzer = RollingWindowAnalyzer(session, use_july_june=True, data_tier='tier2')
        for wt in ['5yr', '10yr', '20yr']:
            await analyzer.compute_all_rolling_windows(wt, save_results=True)
        await session.commit()

asyncio.run(main())
"

# Generate comparison
python scripts/compare_tier1_tier2.py
```

---

## Code Availability

All analysis code is available in this repository:

- **Backend Services**: `backend/app/services/`
- **Data Ingestion**: `scripts/ingest_*.py`
- **Analysis Pipeline**: `scripts/compute_*.py`
- **Reproduction Script**: `scripts/reproduce_publication.sh`

**Requirements**:
- Python 3.10+
- PostgreSQL 13+
- See `requirements.txt` for Python dependencies

---

## Verification

To verify replication, compare against canonical values:

| Metric | Expected (Tier-1) | Tolerance |
|--------|------------------|-----------|
| Mean 5yr HML Premium | ~5-7% | ±2% |
| T-statistic (NW) | >2.0 | - |
| Win Rate | >65% | - |

See `/api/research/publication-snapshot` for the frozen canonical values used by the on-site paper.

---

## Contact

For replication assistance:
- **Repository Issues**: File an issue in this repository
- **Website**: research.finsoeasy.com

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Dec 2025 | Initial Tier-1 + Tier-2 framework |

