# API Reference

**Base URL**: `https://research.finsoeasy.com/api`  
**Docs**: `/docs` (Swagger UI) or `/redoc`

---

## Research Endpoints

### Quintile Performance

```
GET /research/quintile-performance/{window_type}
```

Returns average returns by R&D intensity quintile.

- `window_type`: `5yr`, `10yr`, or `20yr`

### ANOVA Results

```
GET /research/aggregate-anova
```

Returns statistical test results for all window types.

### Data Export

```
GET /research/export/cohort-data.csv
GET /research/export/quintile-performance.csv
GET /research/export/methodology-parameters.json
```

---

## Portfolio Endpoints

### ETF Holdings

```
GET /portfolio/etf-holdings?n_holdings=30&as_of_year=2024
```

Returns current R&D Alpha ETF composition.

### Performance

```
GET /portfolio/performance
```

Returns historical portfolio performance vs S&P 500.

---

## Company Endpoints

### List Companies

```
GET /fmp/companies
```

### Company Detail

```
GET /fmp/companies/{symbol}
```

---

## Health

```
GET /health
```

Returns `{"status": "healthy", "version": "2.1.0"}`
