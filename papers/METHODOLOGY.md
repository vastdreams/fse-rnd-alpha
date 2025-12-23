# R&D Factor Analysis: Data Sources and Methodology

## 1. Data Sources

### 1.1 Primary Data Source: Financial Modeling Prep (FMP) API

All financial data was retrieved from the **Financial Modeling Prep API** (https://financialmodelingprep.com/).

**API Endpoints Used:**

| Endpoint | Purpose | Data Retrieved |
|----------|---------|----------------|
| `/api/v3/sp500_constituent` | S&P 500 constituents | Ticker, company name, sector |
| `/api/v3/income-statement/{symbol}` | Annual income statements | Revenue, R&D expenses, operating income |
| `/api/v3/balance-sheet-statement/{symbol}` | Balance sheets | Total assets, equity, debt |
| `/api/v3/cash-flow-statement/{symbol}` | Cash flow statements | Operating CF, CapEx, FCF |
| `/api/v3/historical-price-full/{symbol}` | Daily stock prices | Adjusted close prices |

**API Key:** Data retrieved using FMP Ultimate Plan subscription.

### 1.2 Secondary Data Sources (Historical Reference)

- **SEC EDGAR:** Annual 10-K filings for XBRL validation
- **Company Disclosures:** R&D expense line items from income statements

---

## 2. R&D Intensity Calculation

### 2.1 Definition

**R&D Intensity** is defined as:

```
R&D Intensity (%) = (R&D Expense / Total Revenue) × 100
```

Where:
- **R&D Expense**: `researchAndDevelopmentExpenses` from FMP income statement
- **Total Revenue**: `revenue` from FMP income statement

### 2.2 Data Extraction Process

1. **Fetch Income Statement**: Query FMP API for each company's historical income statements (up to 30 years)
2. **Extract R&D Expense**: Field `researchAndDevelopmentExpenses` (null if not reported)
3. **Calculate Intensity**: R&D / Revenue for each fiscal year
4. **Average Intensity**: Mean R&D intensity across all available years

### 2.3 Handling Missing Data

| Scenario | Treatment |
|----------|-----------|
| R&D expense = null | Company excluded from R&D analysis for that year |
| Revenue = 0 or null | R&D intensity = null for that year |
| Company has <5 years R&D data | Excluded from cohort analysis |

### 2.4 Sample Code

```python
def calculate_rd_intensity(income_statement: dict) -> float | None:
    """Calculate R&D intensity from income statement."""
    rd_expense = income_statement.get('researchAndDevelopmentExpenses')
    revenue = income_statement.get('revenue')
    
    if rd_expense is None or revenue is None or revenue == 0:
        return None
    
    return (rd_expense / revenue) * 100
```

---

## 3. Annual Return Calculation

### 3.1 Definition

**Annual Stock Return** is calculated as:

```
Annual Return = (Price_Dec31_Y - Price_Jan1_Y) / Price_Jan1_Y
```

### 3.2 Data Source

- **Endpoint**: `/api/v3/historical-price-full/{symbol}`
- **Field Used**: `adjClose` (dividend-adjusted closing price)
- **Frequency**: Daily prices aggregated to annual

### 3.3 Calculation Method

```python
async def calculate_annual_returns(symbol: str, daily_prices: List[dict]) -> List[dict]:
    """Calculate annual returns from daily prices."""
    # Group by year
    by_year = {}
    for p in daily_prices:
        year = int(p['date'][:4])
        if year not in by_year:
            by_year[year] = {'first': None, 'last': None}
        by_year[year]['last'] = p['adjClose']
        if by_year[year]['first'] is None:
            by_year[year]['first'] = p['adjClose']
    
    # Calculate returns
    returns = []
    for year, prices in by_year.items():
        if prices['first'] and prices['last']:
            annual_return = (prices['last'] - prices['first']) / prices['first']
            returns.append({'year': year, 'return': annual_return})
    
    return returns
```

---

## 4. Quintile Portfolio Construction

### 4.1 Methodology

For each rolling window (5-year, 10-year, 20-year):

1. **Calculate Average R&D Intensity**: Average each company's R&D intensity over the window period
2. **Sort Companies**: Rank by average R&D intensity
3. **Create Quintiles**: Divide into 5 groups:
   - Q1: Bottom 20% (lowest R&D)
   - Q2: 20-40%
   - Q3: 40-60%
   - Q4: 60-80%
   - Q5: Top 20% (highest R&D)
4. **Calculate Returns**: Equal-weighted portfolio return for each quintile

### 4.2 Rolling Window Analysis

| Window Type | Period Length | Number of Windows (1995-2024) |
|-------------|---------------|-------------------------------|
| 5-Year | 5 years | 28 overlapping windows |
| 10-Year | 10 years | 23 overlapping windows |
| 20-Year | 20 years | 13 overlapping windows |

---

## 5. Statistical Tests

### 5.1 One-Way ANOVA

**Purpose**: Test if mean returns differ significantly across quintiles.

```python
from scipy import stats

f_statistic, p_value = stats.f_oneway(
    returns_q1, returns_q2, returns_q3, returns_q4, returns_q5
)
```

**Effect Size (η²)**:
```
η² = SS_between / SS_total
```

### 5.2 Independent Samples t-Test

**Purpose**: Compare Q5 (high R&D) vs Q1 (low R&D) portfolios.

```python
t_stat, p_value = stats.ttest_ind(returns_q5, returns_q1)
cohens_d = (mean_q5 - mean_q1) / pooled_std
```

### 5.3 Significance Thresholds

| Symbol | Threshold | Interpretation |
|--------|-----------|----------------|
| * | p < 0.05 | Significant at 95% confidence |
| ** | p < 0.01 | Significant at 99% confidence |
| *** | p < 0.001 | Highly significant |

---

## 6. Data Quality Measures

### 6.1 Data Quality Score

Each company receives a quality score based on:

```python
data_quality_score = (
    years_with_rd_data / total_years_available * 50 +
    years_with_return_data / total_years_available * 50
)
```

Range: 0-100, where higher = more complete data.

### 6.2 Cohort Eligibility Criteria

| Window | Minimum Years R&D Data Required |
|--------|--------------------------------|
| 5-Year | ≥ 5 years |
| 10-Year | ≥ 10 years |
| 20-Year | ≥ 20 years |

---

## 7. Potential Limitations

1. **Survivorship Bias (Tier-1)**: substantially mitigated via historical S&P 500 constituent tracking + delisting return adjustments, but not CRSP/Compustat-grade
2. **R&D Reporting Variation**: Not all companies report R&D separately
3. **Industry Differences**: R&D intensity norms vary by sector
4. **Accounting Changes**: R&D capitalization rules may vary over time
5. **FMP Data Accuracy**: Relies on third-party data aggregation

---

## 8. Reproducibility

### 8.1 Environment

- **Python Version**: 3.11
- **Key Libraries**: pandas, numpy, scipy, statsmodels, sqlalchemy, aiohttp
- **Database**: PostgreSQL 15

### 8.2 Data Retrieval Date

- **Data Snapshot Date**: December 18, 2025 (see `/api/research/publication-snapshot` meta)
- **Live Coverage Ranges**: Export from `/api/fmp/overview` and `/api/research/annual-hml-premium` in the running deployment

### 8.3 Code Repository

All analysis code is available at the project repository, including:
- `/backend/app/services/statistics.py` - Statistical analysis
- `/backend/app/services/rolling_window.py` - Window calculations
- `/scripts/compute_research_analysis.py` - Full pipeline

---

## 9. Summary Statistics

### 9.1 Final Dataset

| Metric | Value |
|--------|-------|
| Total Companies | 503 |
| Companies with 5yr R&D data | 202 |
| Companies with 10yr R&D data | 171 |
| Companies with 20yr R&D data | 123 |
| Total Income Statement Records | ~15,000 |
| Total Price Records | ~3.5 million |
| Analysis Period | July–June returns (Fama-French convention); see `/api/research/annual-hml-premium` for exact range |

### 9.2 Key Findings Summary

| Window | Q5 Return | Q1 Return | Q5−Q1 Premium | N Windows |
|--------|-----------|-----------|---------------|-----------|
| 5-Year | 23.01% | 15.90% | **+7.11%** | 28 |
| 10-Year | 19.84% | 15.06% | **+4.78%** | 24 |
| 20-Year | 16.87% | 14.25% | **+2.62%** | 16 |

> **Note**: Rolling-window summaries are descriptive because windows overlap. Primary inference is based on the annual, non-overlapping HML premium series: `/api/research/annual-hml-premium` (Newey-West reported as conservative default).

### 9.3 Data Quality Considerations

| Issue | Impact | Status |
|-------|--------|--------|
| R&D Reporting Coverage | Only ~40% of companies report R&D as separate line item (pre-2010: <30%) | ⚠️ Major limitation |
| Survivorship Bias | Substantially mitigated using historical S&P 500 constituents + delisting returns (Tier-1 proxy). Residual bias remains without CRSP/Compustat Tier-2. | Mitigated (Tier-1) |
| 20-Year Fixed Cohort | Same companies tracked for 20 years ignores changes | ⚠️ Methodology concern |
| SEC 10-K Parsing | Baseline replication uses FMP financials; SEC parsing exists but is not required for Tier-1 replication | ⚠️ Optional verification layer |

---

*Document Generated: December 2025*  
*Data Source: Financial Modeling Prep (FMP) API (Tier-1)*  
*Return Convention: July–June (Fama-French)*  

