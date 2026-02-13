/**
 * PATH: src/lib/api/portfolio.ts
 * PURPOSE: Portfolio API methods (ETF holdings, backtests, forecasts, sectors)
 */

import { fetchApi } from "./base"
import { API_BASE } from "./base"
import type {
  PortfolioHolding,
  BacktestResult,
  WindowOption,
  SectorAllocation,
  PortfolioForecast,
  ForecastVsActual,
  AnnualReportsResponse,
} from "./types"

// Portfolio API
// NOTE: Default method is "rd_alpha" which uses July-June returns per Fama-French convention
export const portfolioApi = {
  getETFHoldings: (n = 20, method = "rd_alpha", sector?: string, year?: number) => {
    let url = `/api/portfolio/rd-etf?n=${n}&method=${method}`
    if (sector) url += `&sector=${sector}`
    if (year) url += `&year=${year}`
    return fetchApi<PortfolioHolding[]>(url)
  },

  backtest: (startYear: number, endYear: number, nHoldings = 20, method = "rd_alpha", sector?: string) => {
    let url = `/api/portfolio/backtest?start_year=${startYear}&end_year=${endYear}&n_holdings=${nHoldings}&method=${method}`
    if (sector) url += `&sector=${sector}`
    return fetchApi<BacktestResult>(url)
  },

  getWindows: () =>
    fetchApi<WindowOption[]>("/api/portfolio/windows"),

  getSectors: () =>
    fetchApi<Array<{ sector: string; count: number }>>("/api/portfolio/sectors"),

  getSectorAllocation: (n = 20, method = "rd_alpha", year?: number) => {
    let url = `/api/portfolio/sector-allocation?n=${n}&method=${method}`
    if (year) url += `&year=${year}`
    return fetchApi<SectorAllocation[]>(url)
  },

  getPerformanceComparison: (nHoldings = 20, method = "rd_alpha") =>
    fetchApi<Array<{ period: string; portfolio_return: number; benchmark_return: number; excess_return: number; sharpe: number }>>(`/api/portfolio/performance-comparison?n_holdings=${nHoldings}&method=${method}`),

  getForecast: (nHoldings = 20, method = "rd_alpha") =>
    fetchApi<PortfolioForecast>(`/api/portfolio/forecast?n_holdings=${nHoldings}&method=${method}`),

  getForecastVsActual: (year: number, nHoldings = 20, method = "rd_alpha", sector?: string) => {
    let url = `/api/portfolio/forecast-vs-actual?year=${year}&n_holdings=${nHoldings}&method=${method}`
    if (sector) url += `&sector=${sector}`
    return fetchApi<ForecastVsActual>(url)
  },

  // New R&D Alpha endpoints
  getMethodology: () =>
    fetchApi<{
      formula: string
      formula_latex: string
      components: Record<string, string>
      sector_constraints: Record<string, { value: number; description: string }>
      research_citations: string[]
      parameters: Record<string, number>
      last_updated: string
    }>("/api/portfolio/methodology"),

  getRDAlphaHoldings: (n = 20, year?: number) => {
    let url = `/api/portfolio/rd-alpha-holdings?n=${n}`
    if (year) url += `&year=${year}`
    return fetchApi<{
      holdings: Array<{
        symbol: string
        name: string
        sector: string
        weight: number
        rd_intensity: number
        rd_intensity_capped: number
        sector_adjustment: number
        momentum_factor: number
        quality_score: number
        final_score: number
        rank: number
      }>
      sector_weights: Array<{
        sector: string
        target_weight: number
        actual_weight: number
        min_weight: number
        max_weight: number
        company_count: number
        adjustment_needed: number
      }>
      total_candidates: number
      selected_count: number
    }>(url)
  },

  getSectorWeights: (n = 20, year?: number) => {
    let url = `/api/portfolio/sector-weights?n=${n}`
    if (year) url += `&year=${year}`
    return fetchApi<Array<{
      sector: string
      target_weight: number
      actual_weight: number
      min_weight: number
      max_weight: number
      company_count: number
      adjustment_needed: number
      status: "overweight" | "underweight" | "on_target"
    }>>(url)
  },

  getSelectionCandidates: (year?: number, limit = 100) => {
    let url = `/api/portfolio/selection-candidates?limit=${limit}`
    if (year) url += `&year=${year}`
    return fetchApi<{
      candidates: Array<{
        rank: number
        symbol: string
        name: string
        sector: string
        rd_intensity: number
        rd_intensity_capped: number
        sector_adjustment: number
        momentum_factor: number
        quality_score: number
        volatility: number
        final_score: number
        years_of_data: number
      }>
      total_candidates: number
      as_of_year: number | null
    }>(url)
  },

  getSP500Forecast: (yearsForward = 10, includeHistorical = true) =>
    fetchApi<{
      forecasts: Array<{
        year: number
        level_low: number
        level_mid: number
        level_high: number
        return_low: number
        return_mid: number
        return_high: number
        is_forecast: boolean
        source: string
        notes: string | null
      }>
      sources: Array<{
        name: string
        division: string
        frequency: string
        last_update: string
        methodology: string
      }>
      base_year: number
      base_level: number
      methodology_summary: string
      last_updated: string
      disclaimer: string
    }>(`/api/portfolio/sp500-forecast?years_forward=${yearsForward}&include_historical=${includeHistorical}`),

  getUniverses: () =>
    fetchApi<Array<{
      code: string
      name: string
      description: string
      approximate_size: number | null
      market_cap_threshold: string
      reconstitution: string
      index_provider: string
      actual_count: number
      with_rd_data: number
    }>>("/api/portfolio/universes"),
}

// Company API extensions
export const companyApi = {
  getAnnualReports: (ticker: string) =>
    fetchApi<AnnualReportsResponse>(`/api/companies/${ticker}/annual-reports`),
}

// Papers API
export const papersApi = {
  listPapers: () =>
    fetchApi<Array<{ id: string; title: string; filename: string }>>("/api/papers/list"),

  getPaper: (paperId: string) =>
    fetch(`${API_BASE}/api/papers/${paperId}`).then(r => r.text()),
}
