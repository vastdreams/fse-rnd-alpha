# Labor-Data Engineering Workstream

**Project**: Labor Efficiency Alpha  
**Date**: February 27, 2026  
**Status**: Not Started — Prerequisite for Phase 2 Empirical Sections

---

## Overview

This document defines the engineering workstream required to construct the labor-data panel (employee count and payroll by symbol and fiscal year) that gates the empirical sections of the Labor Efficiency Alpha paper.

---

## Required Outputs

| Output | Format | Coverage Target |
|--------|--------|----------------|
| Employee count panel | symbol × fiscal_year → employee_count | ≥70% of S&P 500 per formation year |
| Payroll panel | symbol × fiscal_year → total_payroll_usd | ≥50% of S&P 500 per formation year |
| Coverage diagnostics | year × sector → coverage_pct | All years and sectors |
| QA report | per-record flags for outliers, cross-source disagreements | ≥95% clean records |

---

## Pipeline Architecture

```
┌──────────────────────┐
│ SEC EDGAR XBRL API   │
│ (10-K annual filings)│
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ XBRL Tag Extraction  │
│ EntityNumberOfEmployees│
│ LaborAndRelatedExpense │
│ SalariesAndWages      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐     ┌────────────────────┐
│ Coverage Check       │────▶│ NLP Fallback       │
│ (missing employee ct)│     │ 10-K Text Parsing  │
└──────────┬───────────┘     │ Item 1 "Employees" │
           │                 └────────┬───────────┘
           ▼                          ▼
┌──────────────────────────────────────┐
│ Panel Construction                    │
│ CIK ↔ Ticker Mapping                │
│ Fiscal Year Alignment                │
│ Merge with FMP Income Statements     │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ QA & Coverage Diagnostics            │
│ YoY change filter (>50% flagged)    │
│ Cross-source reconciliation          │
│ Outlier detection                    │
│ Coverage rate by year × sector       │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ Integration with Research API        │
│ Labor efficiency scorer              │
│ Factor test pipeline                 │
│ Publication snapshot builder         │
└──────────────────────────────────────┘
```

---

## Phase 1: XBRL Ingestion (Est. 1 week)

### Tasks
1. **SEC EDGAR Full-Text Search API**: Set up programmatic access to download 10-K filings for all S&P 500 constituents (current and historical)
2. **XBRL Fact Extraction**: Parse XBRL instance documents for target tags:
   - `dei:EntityNumberOfEmployees` (DEI header — highest coverage)
   - `us-gaap:LaborAndRelatedExpense`
   - `us-gaap:SalariesAndWages`
   - `us-gaap:ShareBasedCompensation`
   - `us-gaap:EmployeeBenefitsAndShareBasedCompensation`
3. **Filing Metadata**: Extract CIK, accession number, filing date, fiscal year end, form type
4. **Storage**: PostgreSQL table `labor_data_raw` with columns: cik, ticker, fiscal_year, filing_date, employee_count, payroll_total_usd, source_tag, confidence_score

### Acceptance Criteria
- Downloaded 10-K filings for ≥95% of current S&P 500 for fiscal years 2005–2025
- XBRL employee count extracted for ≥60% of filings (expected coverage for DEI tag)

---

## Phase 2: NLP Text Extraction Fallback (Est. 1 week)

### Tasks
1. **10-K Section Parsing**: Identify Item 1 (Business Description) sections using SEC filing structure markers
2. **Employee Count Extraction**: Pattern matching for:
   - "approximately [N] employees"
   - "[N] full-time equivalent employees"
   - "total headcount of [N]"
   - "[N] full-time and [N] part-time employees" (sum both)
3. **Confidence Scoring**: Assign confidence based on pattern specificity and context
4. **Manual Review Queue**: Flag extractions with confidence < 0.8 for human review

### Acceptance Criteria
- NLP extraction fills ≥50% of the employee count gaps left by XBRL
- Combined (XBRL + NLP) employee count coverage reaches ≥70% per formation year for years 2010+

---

## Phase 3: Panel Construction (Est. 0.5 weeks)

### Tasks
1. **CIK → Ticker Mapping**: Use SEC EDGAR company search + FMP profile to link CIK to ticker symbols
2. **Fiscal Year Alignment**: Map fiscal year end to formation year (July convention)
3. **Merge with FMP Data**: Join labor panel with existing income statement data on ticker + fiscal_year
4. **Payroll Aggregation**: For firms with multiple labor cost tags, compute total payroll as max(LaborAndRelatedExpense, SalariesAndWages + ShareBasedCompensation)

### Acceptance Criteria
- Panel has one row per ticker × fiscal_year with employee_count and/or payroll
- Merge rate with FMP data ≥90%

---

## Phase 4: QA and Coverage Diagnostics (Est. 0.5 weeks)

### Quality Checks
1. **Year-over-year change filter**: Flag employee counts changing >50% YoY (potential M&A or data error)
2. **Cross-source reconciliation**: Where both XBRL and NLP counts exist, require agreement within ±10%
3. **Revenue-per-employee sanity**: Flag RPE < $10,000 or RPE > $10,000,000
4. **Revenue-per-payroll sanity**: Flag RPP < 0.5 or RPP > 50
5. **Sector coverage**: Require ≥3 firms per sector per year for z-scoring
6. **Overall coverage rates**: Compute and report coverage by year, sector, and data source

### Coverage Thresholds

| Metric | Threshold | Action if Below |
|--------|-----------|-----------------|
| Employee count per year | ≥70% | Do not run empirical tests for that year |
| Payroll per year | ≥50% | Run RPE-only composite; exclude RPP |
| Firms per sector | ≥5 | Exclude sector from z-scoring |
| Clean record rate | ≥95% | Manual review of flagged records |

---

## Phase 5: Integration (Est. 1 week)

### Tasks
1. **Labor Efficiency Scorer**: New service `backend/app/services/labor_efficiency_scorer/` following the same pattern as `pnl_efficiency_scorer/`
2. **Research API Endpoints**: `GET /api/research/labor-efficiency/scores`, `/quintiles`, `/methodology`
3. **Portfolio Method**: Add `method="labor_efficiency"` and `method="combined_efficiency"` to portfolio selection
4. **Factor Tests**: Integrate labor efficiency with factor test pipeline for spanning regressions and Fama-MacBeth
5. **Frontend**: Add Labor Efficiency tab to Research page and Company Detail
6. **Publication Snapshot**: Include labor efficiency in snapshot builder for paper table generation

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|-------------|
| 1. XBRL Ingestion | 1 week | SEC EDGAR API access |
| 2. NLP Fallback | 1 week | Phase 1 coverage assessment |
| 3. Panel Construction | 0.5 weeks | Phases 1–2 |
| 4. QA & Diagnostics | 0.5 weeks | Phase 3 |
| 5. Integration | 1 week | Phase 4 passing QA |
| **Total** | **4 weeks** | |

---

## Go/No-Go Decision

After Phase 4, evaluate:
- If employee count coverage ≥70% for ≥15 years: **GO** — proceed with full empirical analysis
- If coverage 50–70%: **CONDITIONAL GO** — proceed with caveats, note coverage limitations
- If coverage <50%: **NO GO** — pivot to alternative data sources (Compustat employee count from WRDS, BLS industry-level proxies)
