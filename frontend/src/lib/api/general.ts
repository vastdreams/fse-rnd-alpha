/**
 * PATH: src/lib/api/general.ts
 * PURPOSE: General API methods (companies, factors, stats, backtests, FMP, research)
 */

import { fetchApi } from "./base"
import type {
  Company,
  CompanyDetail,
  RDSummary,
  StatsSummary,
  UnifiedFiling,
  Backtest,
  FMPOverview,
  FMPCompany,
  FMPCompanyFinancials,
  RDLeader,
  CohortCompany,
  CohortSummary,
  WindowResult,
  QuintilePerf,
  AnovaResultItem,
  AggregateAnova,
  FactorPremiumItem,
  PublicationStats,
  PublicationSnapshotResponse,
  FamaMacBethResult,
  DoubleSortResult,
  MispricingTestResult,
  SpanningTestResult,
  Russell3000Analysis,
  TopJournalChecklist,
  AnnualHmlPremiumResult,
  TransactionCostAnalysisResult,
  NetOfCostReturnsResult,
  SubperiodAnalysisResult,
  EwVsVwResult,
  OutlierSensitivityResult,
  SectorNeutralResult,
} from "./types"

export const api = {
  // Companies
  listCompanies: (limit = 100, offset = 0) =>
    fetchApi<Company[]>(`/api/companies?limit=${limit}&offset=${offset}`),

  getCompany: (ticker: string) =>
    fetchApi<CompanyDetail>(`/api/companies/${ticker}`),

  // Factors
  getRDSummary: () =>
    fetchApi<RDSummary[]>("/api/factors/rd/summary"),

  // Stats
  getStatsSummary: () =>
    fetchApi<StatsSummary>("/api/stats/summary"),

  getUnifiedFilings: (limit = 500, offset = 0) =>
    fetchApi<{ rows: UnifiedFiling[]; total: number }>(`/api/stats/unified/filings?limit=${limit}&offset=${offset}`),

  // Backtests
  listBacktests: () =>
    fetchApi<Backtest[]>("/api/backtests"),

  getBacktest: (id: number) =>
    fetchApi<Backtest>(`/api/backtests/${id}`),

  runBacktest: (data: { factor_id: string; universe: string[]; start_year: number; end_year: number; name?: string }) =>
    fetchApi<{ id: number; status: string; message: string }>("/api/backtests/run", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // FMP Data
  getFMPOverview: () =>
    fetchApi<FMPOverview>("/api/fmp/overview"),

  listFMPCompanies: (sector?: string, limit = 100, skip = 0) =>
    fetchApi<FMPCompany[]>(`/api/fmp/companies?limit=${limit}&skip=${skip}${sector ? `&sector=${sector}` : ""}`),

  getFMPCompany: (symbol: string) =>
    fetchApi<FMPCompanyFinancials>(`/api/fmp/companies/${symbol}`),

  getFMPPrices: (symbol: string, days = 252) =>
    fetchApi<Array<{ date: string; open: number; high: number; low: number; close: number; adj_close: number; volume: number }>>(`/api/fmp/companies/${symbol}/prices?days=${days}`),

  getRDLeaderboard: (limit = 50) =>
    fetchApi<RDLeader[]>(`/api/fmp/rd/leaderboard?limit=${limit}`),

  getRDBySector: () =>
    fetchApi<Array<{ sector: string; company_count: number; avg_rd_intensity: number; total_rd_spend: number }>>("/api/fmp/rd/by-sector"),

  getRDTrends: () =>
    fetchApi<Array<{ year: number; companies: number; avg_rd_intensity: number; total_rd_spend: number }>>("/api/fmp/rd/trends"),

  getReturnsSummary: () =>
    fetchApi<Array<{ year: number; companies: number; avg_return: number; avg_volatility: number | null; min_return: number; max_return: number }>>("/api/fmp/returns/summary"),

  getSectors: () =>
    fetchApi<Array<{ sector: string; count: number }>>("/api/fmp/sectors"),

  // Research V2 - 500 Company Cohort Analysis
  getCohort500: (window?: string, sector?: string) =>
    fetchApi<CohortCompany[]>(`/api/research/cohort-500?${window ? `window=${window}&` : ""}${sector ? `sector=${sector}` : ""}`),

  getCohortSummary: () =>
    fetchApi<CohortSummary>("/api/research/cohort-summary"),

  getWindowCompanies: (windowType: string) =>
    fetchApi<CohortCompany[]>(`/api/research/windows/${windowType}`),

  getRollingWindows: (windowType: string) =>
    fetchApi<WindowResult[]>(`/api/research/rolling/${windowType}`),

  getQuintilePerformance: (windowType: string) =>
    fetchApi<QuintilePerf[]>(`/api/research/quintile-performance?window_type=${windowType}`),

  getAnovaResults: (windowType: string) =>
    fetchApi<AnovaResultItem[]>(`/api/research/anova/${windowType}`),

  getAggregateAnova: () =>
    fetchApi<Record<string, AggregateAnova>>("/api/research/anova-aggregate"),

  getFactorPremiums: () =>
    fetchApi<FactorPremiumItem[]>("/api/research/factor-premium"),

  getPublicationStats: () =>
    fetchApi<PublicationStats>("/api/research/publication-stats"),

  // Frozen, publication-ready snapshot (pins paper numbers for submission)
  getPublicationSnapshot: () =>
    fetchApi<PublicationSnapshotResponse>("/api/research/publication-snapshot"),

  triggerComputation: () =>
    fetchApi<{ status: string; message: string }>("/api/research/compute-all", { method: "POST" }),

  classifyCohort: () =>
    fetchApi<{ total_companies: number; cohort_5yr: number; cohort_10yr: number; cohort_20yr: number }>("/api/research/classify-cohort", { method: "POST" }),

  computeWindows: (windowType: string) =>
    fetchApi<{ window_type: string; windows_computed: number }>(`/api/research/compute-windows/${windowType}`, { method: "POST" }),

  computePremiums: () =>
    fetchApi<{ years_computed: number }>("/api/research/compute-premiums", { method: "POST" }),

  // Top-Journal Analysis Endpoints
  getFamaMacBethControls: (startYear?: number, endYear?: number) =>
    fetchApi<FamaMacBethResult>(`/api/research/fama-macbeth-controls?start_year=${startYear || 1995}&end_year=${endYear || 2024}`),

  getDoubleSortAnalysis: (startYear?: number, endYear?: number) =>
    fetchApi<DoubleSortResult>(`/api/research/double-sort-analysis?start_year=${startYear || 1995}&end_year=${endYear || 2024}`),

  getMispricingTests: (startYear?: number, endYear?: number) =>
    fetchApi<MispricingTestResult>(`/api/research/mispricing-tests?start_year=${startYear || 1995}&end_year=${endYear || 2024}`),

  getSpanningTestsFull: () =>
    fetchApi<SpanningTestResult>("/api/research/spanning-tests-full"),

  getRussell3000Analysis: () =>
    fetchApi<Russell3000Analysis>("/api/research/russell-3000-analysis"),

  getTopJournalChecklist: () =>
    fetchApi<TopJournalChecklist>("/api/research/top-journal-checklist"),

  getAnnualHmlPremium: () =>
    fetchApi<AnnualHmlPremiumResult>("/api/research/annual-hml-premium"),

  getSubperiodAnalysis: (windowType: string) =>
    fetchApi<SubperiodAnalysisResult>(`/api/research/subperiod-analysis?window_type=${windowType}`),

  // Transaction cost endpoints (publication/practitioner implementability)
  getTransactionCostAnalysis: (params?: {
    rd_premium?: number
    market_return?: number
    n_holdings?: number
    universe?: string
  }) => {
    const search = new URLSearchParams()
    if (params?.rd_premium !== undefined) search.set("rd_premium", String(params.rd_premium))
    if (params?.market_return !== undefined) search.set("market_return", String(params.market_return))
    if (params?.n_holdings !== undefined) search.set("n_holdings", String(params.n_holdings))
    if (params?.universe) search.set("universe", params.universe)
    const qs = search.toString()
    return fetchApi<TransactionCostAnalysisResult>(`/api/research/transaction-costs${qs ? `?${qs}` : ""}`)
  },

  getNetOfCostReturns: (windowType: string) =>
    fetchApi<NetOfCostReturnsResult>(`/api/research/net-of-cost-returns/${windowType}`),

  // Robustness Tests (Publication Requirements)
  getEwVsVwComparison: (windowType: string = "5yr") =>
    fetchApi<EwVsVwResult>(`/api/research/ew-vs-vw-comparison?window_type=${windowType}`),

  getOutlierSensitivity: (windowType: string = "5yr") =>
    fetchApi<OutlierSensitivityResult>(`/api/research/outlier-sensitivity?window_type=${windowType}`),

  getSectorNeutralPremiumSeries: (startYear: number = 1995, endYear: number = 2024) =>
    fetchApi<SectorNeutralResult>(`/api/research/sector-neutral-premium-series?start_year=${startYear}&end_year=${endYear}`),
}
