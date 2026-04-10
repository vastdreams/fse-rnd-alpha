# Data Availability Statement

**Publication**: P&L Efficiency Alpha: Operating Cost Structure and Long-Term Stock Returns  
**Author**: Abhishek Sehgal  
**Date**: February 2026

---

## Data Access

### Tier-1 Data (FMP)

The primary data source is Financial Modeling Prep (FMP), a commercial API service.

| Component | Access |
|-----------|--------|
| Income Statements | FMP API (commercial subscription required) |
| Daily Prices | FMP API (commercial subscription required) |
| Company Profiles | FMP API (free tier available for basic data) |

**API Documentation**: https://financialmodelingprep.com/developer/docs

### Factor Returns (Ken French)

Fama-French five factors and momentum factor are freely available:
- URL: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
- Files: `F-F_Research_Data_5_Factors_2x3_CSV.zip`, `F-F_Momentum_Factor_CSV.zip`

### S&P 500 Constituents

A curated list of current S&P 500 constituents with addition dates is used. Public sources for verification include Wikipedia's S&P 500 page and index-provider announcements.

---

## Replication Instructions

1. **Obtain FMP API key**: Subscribe to a plan that includes historical income statements and daily prices.
2. **Download factor data**: Obtain the Fama-French 5-factor and momentum datasets from the Ken French library.
3. **Run the research pipeline**: The scoring and portfolio construction code is available in the `backend/app/services/pnl_efficiency_scorer/` directory of the research repository.
4. **Verify against snapshot**: Compare outputs to the frozen publication snapshot to confirm reproducibility.

---

## Code Availability

The research platform code, including the PNL efficiency scorer, research API, and frontend visualization, is hosted at:
- **Repository**: https://github.com/vastdreams/rd-alpha-research
- **Live Platform**: https://research.finsoeasy.com

---

## License

- Research code: MIT License
- Data: Subject to respective provider terms (FMP commercial license, Ken French academic use)
- Paper: All rights reserved by the author
