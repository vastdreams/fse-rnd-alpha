# API Documentation

**Base URL**: `https://research.finsoeasy.com/api`  

---

## Overview

The R&D Alpha Research API provides access to research on R&D Investment Intensity and Stock Returns. The API follows RESTful conventions and returns JSON responses.

### Authentication

Currently the API is open for research purposes. Rate limiting may be applied in production.

### Response Format

All responses follow this structure:

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2025-01-01T00:00:00Z",
    "version": "2.1.0"
  }
}
```

Error responses:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```

---

## Research Endpoints

### GET /research/publication-snapshot

Returns the frozen research results used by the on-site paper.

**Response:**
```json
{
  "snapshot_id": "pub_2024_12",
  "git_commit": "abc123",
  "built_at": "2025-01-01T00:00:00Z",
  "data": {
    "quintile_performance": { ... },
    "rolling_windows": { ... },
    "statistical_tests": { ... }
  }
}
```

---

### GET /research/quintile-performance/{window_type}

Returns performance metrics by R&D quintile.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `window_type` | string | Yes | One of: `5yr`, `10yr`, `20yr`, `full` |

**Response:**
```json
{
  "window_type": "5yr",
  "quintiles": [
    {
      "quintile": 1,
      "label": "Low R&D",
      "mean_return": 0.0812,
      "std_dev": 0.1523,
      "t_stat": 2.45,
      "sharpe": 0.53,
      "n_observations": 150
    },
    ...
  ],
  "hml_premium": {
    "value": 0.0755,
    "t_stat": 2.78,
    "p_value": 0.0107
  }
}
```

---

### GET /research/rolling-windows/{window_type}

Returns time-series of R&D premium.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `window_type` | string | Yes | One of: `5yr`, `10yr`, `20yr` |

**Response:**
```json
{
  "window_type": "5yr",
  "windows": [
    {
      "end_year": 2000,
      "premium": 0.0823,
      "t_stat": 2.12,
      "win_rate": 0.80
    },
    ...
  ]
}
```

---

### GET /research/aggregate-anova

Returns ANOVA test results for quintile returns.

**Response:**
```json
{
  "f_statistic": 4.23,
  "p_value": 0.0021,
  "df_between": 4,
  "df_within": 119,
  "quintile_means": [0.081, 0.092, 0.103, 0.118, 0.156]
}
```

---

### GET /research/fama-macbeth/{window_type}

Returns Fama-MacBeth regression results.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `window_type` | string | Yes | One of: `5yr`, `10yr`, `20yr`, `full` |

**Response:**
```json
{
  "window_type": "5yr",
  "coefficients": {
    "rd_intensity": {
      "estimate": 0.0321,
      "t_stat_nw": 2.45,
      "p_value": 0.0234
    },
    "size": { ... },
    "value": { ... }
  },
  "r_squared": 0.142
}
```

---

### GET /research/summary-statistics

Returns summary statistics for the research cohort.

**Response:**
```json
{
  "cohort_size": 487,
  "date_range": {
    "start": "1995-07-01",
    "end": "2024-06-30"
  },
  "rd_intensity": {
    "mean": 0.0523,
    "median": 0.0312,
    "std": 0.0845,
    "min": 0.0001,
    "max": 0.4521
  }
}
```

---

### GET /research/subperiod-analysis

Returns analysis broken down by time periods.

**Response:**
```json
{
  "periods": [
    {
      "label": "1995-2004",
      "premium": 0.0892,
      "t_stat": 2.15
    },
    {
      "label": "2005-2014",
      "premium": 0.0723,
      "t_stat": 1.98
    },
    {
      "label": "2015-2024",
      "premium": 0.0651,
      "t_stat": 1.87
    }
  ]
}
```

---

### GET /research/transaction-costs

Returns transaction cost analysis.

**Response:**
```json
{
  "gross_premium": 0.0755,
  "estimated_costs": {
    "bid_ask_spread": 0.0010,
    "market_impact": 0.0005,
    "turnover": 0.15,
    "total_annual_cost": 0.0022
  },
  "net_premium": 0.0533
}
```

---

### GET /research/net-of-cost-returns/{window_type}

Returns net-of-cost quintile returns.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `window_type` | string | Yes | One of: `5yr`, `10yr`, `20yr`, `full` |

---

## Portfolio Endpoints

### GET /portfolio/etf-holdings

Returns current R&D ETF holdings.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | int | No | Number of holdings (default: 50) |
| `sort` | string | No | Sort by: `weight`, `rd_intensity`, `ticker` |

**Response:**
```json
{
  "as_of_date": "2025-01-01",
  "total_holdings": 50,
  "holdings": [
    {
      "ticker": "NVDA",
      "name": "NVIDIA Corporation",
      "weight": 0.025,
      "rd_intensity": 0.2156,
      "sector": "Technology",
      "quintile": 5
    },
    ...
  ]
}
```

---

### GET /portfolio/sector-weights

Returns sector allocation of the R&D ETF.

**Response:**
```json
{
  "sectors": [
    {
      "sector": "Technology",
      "weight": 0.42,
      "holdings_count": 21
    },
    {
      "sector": "Healthcare",
      "weight": 0.28,
      "holdings_count": 14
    },
    ...
  ]
}
```

---

### GET /portfolio/all-candidates

Returns all candidate stocks for the R&D ETF.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `min_rd` | float | No | Minimum R&D intensity filter |
| `sector` | string | No | Sector filter |

---

### GET /portfolio/forecast-vs-actual

Returns forecast vs actual performance comparison.

---

### GET /portfolio/backtest

Returns backtested ETF performance.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `start_year` | int | No | Backtest start (default: 1995) |
| `end_year` | int | No | Backtest end (default: current) |
| `transaction_cost` | float | No | Annual cost (default: 0.002) |

**Response:**
```json
{
  "cumulative_return": 8.23,
  "annual_return": 0.0812,
  "volatility": 0.1823,
  "sharpe_ratio": 0.45,
  "max_drawdown": -0.42,
  "annual_returns": [
    { "year": 1996, "return": 0.12 },
    ...
  ]
}
```

---

## Data Export Endpoints

### GET /research/export/cohort-data.csv

Downloads full research cohort as CSV.

**Response:** CSV file with columns:
- `ticker`, `year`, `rd_expense`, `revenue`, `rd_intensity`, `return`, `quintile`

---

### GET /research/export/quintile-performance.csv

Downloads quintile performance as CSV.

---

### GET /research/export/rolling-windows.csv

Downloads rolling window data as CSV.

---

### GET /research/export/statistical-results.csv

Downloads statistical test results as CSV.

---

### GET /research/export/methodology-parameters.json

Downloads methodology parameters as JSON.

**Response:**
```json
{
  "return_convention": "july_june",
  "universe": "sp500_point_in_time",
  "sample_period": "Jul2001-Jun2025 (snapshot primary annual inference)",
  "quintile_method": "annual_sorting",
  "inference": "newey_west_hac",
  "delisting_method": "shumway_1997"
}
```

---

## Company Endpoints

### GET /companies

Returns list of companies in the research universe.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `sector` | string | No | Filter by sector |
| `min_rd` | float | No | Minimum R&D intensity |
| `limit` | int | No | Number of results |

---

### GET /companies/{ticker}

Returns company details.

**Response:**
```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "cik": "0000320193",
  "rd_history": [
    { "year": 2023, "rd_intensity": 0.0723, "quintile": 4 },
    ...
  ]
}
```

---

## Factor Endpoints

### GET /factors/rd

Returns R&D factor returns.

---

### GET /factors/spanning

Returns factor spanning test results.

**Response:**
```json
{
  "spanning_tests": {
    "capm": {
      "alpha": 0.0612,
      "t_stat": 2.45
    },
    "ff3": {
      "alpha": 0.0523,
      "t_stat": 2.12
    },
    "ff5": {
      "alpha": 0.0445,
      "t_stat": 1.89
    }
  }
}
```

---

## Backtest Endpoints

### GET /backtests

Returns list of backtest runs.

---

### GET /backtests/{id}

Returns specific backtest results.

---

### POST /backtests

Creates a new backtest.

**Request Body:**
```json
{
  "factor_id": "RND_v1_numeric",
  "universe": "sp500",
  "start_year": 1995,
  "end_year": 2024,
  "num_buckets": 5,
  "holding_period": 1
}
```

---

## Statistics Endpoints

### GET /stats/correlation-matrix

Returns factor correlation matrix.

---

### GET /stats/descriptive

Returns descriptive statistics for the dataset.

---

## Health Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.0"
}
```

---

### GET /ready

Release-readiness endpoint. Unlike `/health`, this fails closed unless the
database has exactly one sealed active universe with vectors, a committed
source SHA, and a data-manifest hash matching the mounted release artifact.

**Response fields:** `ready`, diagnostic `checks`, and the attested
`release.universe_version`, `release.source_sha`, and
`release.data_manifest_sha256`.

---

### GET /

API root with documentation links.

**Response:**
```json
{
  "name": "R&D Alpha Research API",
  "version": "2.1.0",
  "documentation": {
    "swagger": "/docs",
    "redoc": "/redoc"
  }
}
```

---

## Rate Limiting

In production, rate limiting is applied:
- **100 requests/minute** per IP
- **1000 requests/hour** per IP

Rate limit headers:
- `X-RateLimit-Limit-Minute: 100`
- `X-RateLimit-Remaining-Minute: 95`

---

## Error Codes

| Code | Description |
|------|-------------|
| `400` | Bad Request - Invalid parameters |
| `404` | Not Found - Resource doesn't exist |
| `429` | Too Many Requests - Rate limit exceeded |
| `500` | Internal Server Error |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | Dec 2025 | Added export endpoints, factor spanning |
| 2.0.0 | Nov 2025 | Tier-2 data support, rolling windows |
| 1.0.0 | Oct 2025 | Initial release |

---

## Citation

If you use this API in academic research, please cite:

```
R&D Alpha Research Platform (2025). research.finsoeasy.com
```
