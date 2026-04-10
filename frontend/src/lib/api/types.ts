/**
 * PATH: src/lib/api/types.ts
 * PURPOSE: All TypeScript interfaces for the R&D Factor Analysis API
 * NOTE: This file contains only type definitions (no runtime code).
 *       It exceeds 300 lines because these are pure interface declarations
 *       that serve as API contract documentation. No logic, no side effects.
 */
// NOTE: 300-line limit exemption — this file contains only TypeScript interface/type
// definitions for the API layer. Splitting would scatter related types across files
// and harm discoverability. No runtime logic exists here.

// ─── Company Types ──────────────────────────────────────────────────────────

export interface Company {
  id: number
  ticker: string
  name: string | null
  cik: string
  sector: string | null
  industry: string | null
  years_available: number
}

export interface CompanyDetail {
  company: {
    id: number
    ticker: string
    name: string | null
    cik: string
    sector: string | null
    industry: string | null
  }
  years: CompanyYear[]
  price_data: {
    price_points: number
  }
}

export interface CompanyYear {
  fiscal_year: number
  filing_date: string | null
  sector: string | null
  industry: string | null
  financials?: {
    income_statement: {
      revenue?: number | null
      cost_of_revenue?: number | null
      gross_profit?: number | null
      rd_expense?: number | null
      sga_expense?: number | null
      operating_income?: number | null
      net_income?: number | null
      eps_basic?: number | null
      eps_diluted?: number | null
    }
    balance_sheet: {
      total_assets?: number | null
      cash_and_equivalents?: number | null
      total_liabilities?: number | null
      total_equity?: number | null
      long_term_debt?: number | null
    }
    cash_flow: {
      cash_from_operations?: number | null
      cash_from_investing?: number | null
      cash_from_financing?: number | null
      capex?: number | null
    }
  }
  ratios?: {
    rd_intensity?: number | null
    gross_margin?: number | null
    operating_margin?: number | null
    net_margin?: number | null
    roe?: number | null
    roa?: number | null
  }
  rd_text_factors?: {
    rd_mentions_count?: number | null
    rd_tone_score?: number | null
    rd_section_length_words?: number | null
    extraction_confidence?: number | null
  }
  annual_report?: {
    file_format?: string | null
    file_size_bytes?: number | null
    extraction_status?: string | null
    word_count?: number | null
  }
}

export interface RDSummary {
  ticker: string
  fiscal_year: number
  rd_intensity: number | null
  rd_mentions: number | null
  rd_tone_score: number | null
}

export interface StatsSummary {
  companies: {
    total: number
    with_financials: number
    with_ratios: number
    with_text_factors: number
  }
  company_years: {
    total: number
    with_financials: number
    with_ratios: number
    with_text_factors: number
  }
  annual_reports: {
    total: number
    total_size_bytes: number
  }
  text_chunks: {
    total: number
  }
  prices: {
    total_records: number
    unique_tickers: number
  }
}

export interface UnifiedFiling {
  company_year_id: number
  company_id: number
  annual_report_id: number | null
  ticker: string
  name: string | null
  cik: string
  fiscal_year: number
  filing_date: string | null
  sec_accession_id: string | null
  report_path: string | null
  file_format: string | null
  file_size_bytes: number | null
  extraction_status: string | null
  form_type: string | null
}

export interface Backtest {
  id: number
  name: string
  factor_id: string
  universe: string[]
  start_year: number
  end_year: number
  status: string
  created_at: string
  completed_at: string | null
  results?: Record<string, unknown>
}

// ─── FMP Types ──────────────────────────────────────────────────────────────

export interface FMPOverview {
  total_companies: number
  total_income_statements: number
  total_balance_sheets: number
  total_cash_flows: number
  total_price_records: number
  total_annual_returns: number
  year_range: { min: number; max: number }
  companies_with_rd: number
  avg_rd_intensity: number | null
}

export interface FMPCompany {
  symbol: string
  name: string | null
  sector: string | null
  sub_sector: string | null
  cik: string | null
  years_data: number
  latest_revenue: number | null
  latest_rd_expense: number | null
  rd_intensity: number | null
}

export interface FMPCompanyFinancials {
  symbol: string
  name: string | null
  sector: string | null
  income_statements: Array<{
    fiscal_year: number
    revenue: number | null
    gross_profit: number | null
    rd_expenses: number | null
    operating_income: number | null
    net_income: number | null
    eps: number | null
    ebitda: number | null
  }>
  balance_sheets: Array<{
    fiscal_year: number
    total_assets: number | null
    total_liabilities: number | null
    total_equity: number | null
    cash: number | null
    total_debt: number | null
  }>
  cash_flows: Array<{
    fiscal_year: number
    operating_cf: number | null
    investing_cf: number | null
    financing_cf: number | null
    free_cash_flow: number | null
    capex: number | null
  }>
  annual_returns: Array<{
    year: number
    annual_return: number | null
    volatility: number | null
  }>
  rd_analysis: {
    total_rd_spend: number
    avg_rd_intensity: number
    years_with_rd: number
    rd_by_year: Array<{
      year: number
      rd_expense: number | null
      revenue: number | null
      rd_intensity: number | null
    }>
  }
}

export interface RDLeader {
  symbol: string
  name: string | null
  sector: string | null
  avg_rd_intensity: number
  total_rd_spend: number
  years_of_data: number
}

// ─── Research Types ─────────────────────────────────────────────────────────

export interface CohortCompany {
  symbol: string
  name: string | null
  sector: string | null
  industry: string | null
  years_with_data: number
  years_with_rd: number
  first_year: number | null
  last_year: number | null
  has_5yr_window: boolean
  has_10yr_window: boolean
  has_20yr_window: boolean
  avg_rd_intensity: number | null
  rd_profile: string | null
  data_quality_score: number | null
}

export interface CohortSummary {
  total_companies: number
  eligible_5yr: number
  eligible_10yr: number
  eligible_20yr: number
  avg_rd_intensity: number
  avg_quality_score: number
  by_sector: Array<{ sector: string; total: number; n_5yr: number; n_10yr: number; n_20yr: number }>
  by_rd_profile: Record<string, number>
}

export interface WindowResult {
  window_type: string
  start_year: number
  end_year: number
  quintiles: Array<{
    quintile: number
    n_companies: number
    avg_rd_intensity: number | null
    avg_return: number | null
    total_return: number | null
    volatility: number | null
    sharpe_ratio: number | null
  }>
  rd_premium: number
}

export interface QuintilePerf {
  quintile: number
  label: string
  n_windows: number
  avg_rd_intensity: number
  avg_return: number
  avg_total_return: number
  avg_volatility: number
  avg_sharpe: number
}

export interface AnovaResultItem {
  window_type: string
  period: string
  f_statistic: number | null
  p_value: number | null
  eta_squared: number | null
  significant_005: boolean
  significant_001: boolean
  group_means: Record<string, number> | null
  high_low_diff: number | null
}

export interface AggregateAnova {
  window_type: string
  n_windows: number
  anova: {
    f_statistic: number
    p_value: number
    eta_squared: number
    omega_squared: number
    significant_005: boolean
    significant_001: boolean
  }
  ttest_high_vs_low: {
    t_statistic: number
    p_value: number
    mean_difference: number
    cohens_d: number
    significant: boolean
  }
  quintile_means: Record<string, number>
  quintile_ns: Record<string, number>
}

export interface FactorPremiumItem {
  year: number
  rd_premium: number | null
  q1_return: number | null
  q2_return: number | null
  q3_return: number | null
  q4_return: number | null
  q5_return: number | null
}

export interface PublicationStats {
  "5yr"?: AggregateAnova
  "10yr"?: AggregateAnova
  "20yr"?: AggregateAnova
  rd_factor_premium?: {
    mean: number
    std: number
    min: number
    max: number
    n_years: number
    t_statistic: number
    p_value: number
    significant: boolean
    positive_years: number
    negative_years: number
  }
}

export interface PublicationSnapshotMeta {
  id: string
  label: string
  is_active: boolean
  return_convention: string
  data_tier: string
  built_at: string
  git_commit?: string | null
  git_branch?: string | null
  notes?: string | null
}

export interface PublicationSnapshotPayload {
  /**
   * NOTE: Keys use snake_case to match the backend snapshot payload.
   * The snapshot is a frozen, submission-grade dataset used by paper pages.
   */
  methodology_parameters?: Record<string, unknown> | { error: string }
  cohort_summary?: CohortSummary | { error: string }
  aggregate_anova?: Record<string, AggregateAnova> | { error: string }
  annual_hml_premium?: AnnualHmlPremiumResult | { error: string }
  rd_by_sector?: Array<{ sector: string; company_count: number; avg_rd_intensity: number; total_rd_spend: number }> | { error: string }
  rd_trends?: Array<{ year: number; companies: number; avg_rd_intensity: number; total_rd_spend: number }> | { error: string }
  rd_leaderboard?: RDLeader[] | { error: string }
  rd_leaderboard_by_sector?: Record<string, RDLeader[]> | { error: string }
  rd_leaderboard_limit?: number
  net_of_cost_returns?: Record<string, NetOfCostReturnsResult> | { error: string }
  rolling_window_aggregates?: Record<string, RollingWindowAggregateRow[]> | { error: string }
  rolling_windows?: Record<string, WindowResult[]> | { error: string }
  transaction_costs?: TransactionCostAnalysisResult | { error: string }
  factor_premiums?: FactorPremiumItem[] | { error: string }
  publication_stats?: PublicationStats | { error: string }
  investable_backtest?: BacktestResult | { error: string }
  spanning_tests_full?: SpanningTestResult | { error: string }
  mispricing_tests?: MispricingTestResult | { error: string }
  double_sort_analysis?: DoubleSortResult | { error: string }
  delisting_sensitivity?: DelistingSensitivityResult | { error: string }
  fama_macbeth_monthly?: FamaMacBethMonthlyResult | { error: string }
  [key: string]: unknown
}

/** Monthly Fama-MacBeth cross-sectional regression results (PRIMARY INFERENCE) */
export interface FamaMacBethMonthlyResult {
  methodology: string
  frequency: string
  return_convention: string
  signal_timing: string
  winsorization: string
  nw_lags: number
  n_months: number
  month_range: string
  avg_n_firms_per_month: number
  avg_r_squared: number
  total_firm_months: number
  intercept: CoefficientStats
  rd_intensity: CoefficientStats
  log_market_cap: CoefficientStats
  book_to_market: CoefficientStats
  rd_predicts_returns: boolean
  rd_predicts_returns_001: boolean
  latex_table: string
  interpretation: string
}

export interface DelistingSensitivityScenario {
  key: string
  name: string
  description: string
  mode: string
  delta?: number
}

export interface DelistingSensitivityResultRow {
  n_years: number
  mean_premium_pct: number
  t_statistic: number
  p_value: number
  significant_005: boolean
  delta_vs_baseline_pct?: number
}

export interface DelistingSensitivityResult {
  use_july_june: boolean
  note: string
  scenarios: DelistingSensitivityScenario[]
  results: Record<
    string,
    | {
        name: string
        description: string
        annual_hml: DelistingSensitivityResultRow
      }
    | {
        name: string
        description: string
        error: unknown
      }
  >
}

export interface RollingWindowAggregateRow {
  quintile: number
  label: string
  n_windows: number
  n_companies: number
  avg_rd_intensity: number | null
  median_rd_intensity: number | null
  avg_return: number | null
  median_return: number | null
  total_return: number | null
  annualized_return: number | null
  volatility: number | null
  sharpe_ratio: number | null
  max_drawdown: number | null
}

export interface PublicationSnapshotResponse {
  meta: PublicationSnapshotMeta
  payload: PublicationSnapshotPayload
}

// ─── Top-Journal Analysis Types ─────────────────────────────────────────────

export interface FamaMacBethResult {
  methodology: string
  n_periods: number
  period_range: string
  avg_n_companies_per_period: number
  avg_r_squared: number
  alpha: CoefficientStats
  rd_intensity: CoefficientStats
  log_size: CoefficientStats
  book_to_market: CoefficientStats
  rd_predicts_returns: boolean
  latex_table: string
  interpretation: string
}

export interface CoefficientStats {
  coefficient: number
  std_dev: number
  t_stat_fm: number
  p_value_fm: number
  t_stat_hac: number
  p_value_hac: number
  significant_005: boolean
  significant_001: boolean
}

export interface DoubleSortResult {
  methodology: string
  n_years: number
  total_observations: number
  matrix: Record<string, Record<string, { mean_return: number | null; std: number | null; n_obs: number }>>
  rd_spreads_by_size: Record<string, { high_minus_low: number; t_stat: number; p_value: number; significant: boolean }>
  key_findings: {
    rd_works_in_small_caps: boolean
    rd_works_in_large_caps: boolean
    rd_is_not_just_size_effect: boolean
  }
  interpretation: string
}

export interface MispricingTestResult {
  tests: {
    by_size: Record<string, { premium: number | null; n_obs: number }>
    by_volatility: Record<string, { premium: number | null; n_obs: number }>
    by_coverage: Record<string, { premium: number | null; n_obs: number }>
  }
  total_observations: number
  n_years: number
  mispricing_evidence_count: number
  interpretation: {
    likely_explanation: "MISPRICING" | "RISK"
    confidence: "High" | "Medium" | "Low"
    explanation: string
  }
  latex_summary: string
}

export interface SpanningTestResult {
  models?: Record<string, {
    alpha: number
    alpha_t: number
    alpha_p: number
    is_spanned: boolean
    r_squared: number
    factor_loadings: Record<string, number>
  }>
  n_years?: number
  interpretation?: {
    is_distinct_factor: boolean
    summary: string
    recommendation: string
  }
  latex_table?: string
  publication_verdict?: {
    can_claim_distinct_factor: boolean
    recommendation: string
  }
  status?: string
  error?: unknown
  note?: string
}

export interface Russell3000Analysis {
  current_universe: {
    name: string
    companies_with_rd: number
    limitation: string
  }
  proposed_expansion: {
    name: string
    expected_companies: number
    expected_with_rd: number
    benefits: string[]
  }
  expansion_requirements: unknown
  expected_impact_on_results: {
    premium_direction: string
    significance: string
    practical_consideration: string
  }
  data_sources: Array<{ name: string; access: string; contains: string }>
}

export interface TopJournalChecklist {
  journal_target: string
  overall_readiness: string
  checklist: {
    core_analyses: Record<string, { status: string; significant?: boolean }>
    robustness_tests: Record<string, { status: string; verdict?: string; endpoint?: string }>
    data_quality: Record<string, { status: string; action_required?: string; method?: string }>
    missing_for_top_journal: string[]
  }
  recommendation: string
}

export interface AnnualHmlPremiumResult {
  /**
   * NOTE: Backend uses July-June labels by default, e.g. "Jul1995-Jun1996".
   * We keep this as a string to avoid misrepresenting the return period.
   */
  annual_premiums: Array<{
    year: string
    formation_year: number
    q1_return: number
    q5_return: number
    hml_premium: number
    q1_n: number
    q5_n: number
    return_type: "july_june" | "calendar"
  }>
  n_years: number
  mean_premium: number
  std_dev: number
  min_premium: number
  max_premium: number
  positive_years: number
  win_rate: number
  hac_adjusted: {
    mean: number
    nw_std_error: number
    t_statistic: number
    p_value: number
    significant: boolean
    lags_used: number
  }
  note: string
}

export interface TransactionCostAnalysisResult {
  gross_rd_premium_pct: number
  net_rd_premium_pct: number
  /**
   * Historical UI field name. IMPORTANT: this is a CAPTURE RATE (net premium / gross premium),
   * not a net premium itself. Can be null when gross premium <= 0 (undefined).
   */
  premium_after_costs_pct: number | null
  /**
   * Preferred clear naming for new UI.
   */
  premium_capture_rate_pct?: number | null
  q5_gross_return_pct: number
  q5_net_return_pct: number
  q1_gross_return_pct: number
  q1_net_return_pct: number
  annual_trading_cost_pct: number
  cost_breakdown: Record<string, unknown>
  methodology_note: string
  is_premium_significant: boolean
  // Canonical period labels for frontends (from publication snapshot)
  period_years?: string // e.g., "2001-2024"
  period_label?: string // e.g., "Jul2001-Jun2025"
  backtest_start_year?: number
  backtest_end_year?: number
  n_periods?: number
}

export interface NetOfCostReturnsResult {
  window_type: string
  quintile_results: Array<{
    quintile: number
    n_companies: number
    avg_rd_intensity: number
    gross_return_pct: number
    trading_cost_pct: number
    net_return_pct: number
  }>
  gross_rd_premium_pct: number
  net_rd_premium_pct: number
  cost_methodology: Record<string, unknown>
  interpretation: string
}

export interface SubperiodAnalysisResult {
  window_type: string
  subperiods: Record<string, {
    label: string
    start_year?: number
    end_year?: number
    n_windows: number
    mean_rd_premium_pct?: number
    std_rd_premium_pct?: number
    min_premium_pct?: number
    max_premium_pct?: number
    pct_windows_positive?: number
    t_statistic?: number
    p_value?: number
    significant_005?: boolean
    message?: string
  }>
  comparison: {
    pre_vs_post_crisis: {
      pre_premium_pct: number
      post_premium_pct: number
      difference_pct: number
      interpretation: string
    }
  }
  methodology_note: string
}

// ─── Robustness Test Types ──────────────────────────────────────────────────

export interface EwVsVwResult {
  window_type: string
  n_windows: number
  equal_weighted: {
    mean_premium: number
    std_dev: number
    t_statistic: number
    methodology: string
  }
  value_weighted: {
    mean_premium: number
    std_dev: number
    t_statistic: number
    methodology: string
  }
  ew_minus_vw_spread: number
  interpretation: string
}

export interface OutlierSensitivityResult {
  window_type: string
  n_windows: number
  baseline_premium: number
  scenarios: Record<string, {
    description: string
    estimated_premium: number
    note: string
  }>
  max_deviation: number
  robustness_verdict: string
  interpretation: string
}

export interface SectorNeutralResult {
  start_year: number
  end_year: number
  annual_premiums: Array<{
    year: number
    sector_neutral_premium: number
  }>
  aggregate_stats: {
    mean_premium: number
    std_dev: number
    t_statistic: number
    p_value: number
    n_years: number
  }
  hac_adjusted?: {
    mean: number
    nw_std_error: number
    t_statistic: number
    p_value: number
  }
}

// ─── Portfolio Types ────────────────────────────────────────────────────────

export interface PortfolioHolding {
  symbol: string
  name: string
  company_name?: string
  sector: string
  weight: number
  rd_intensity: number
  rank?: number
  rd_alpha_score?: number
  momentum_score?: number
  quality_score?: number
}

export interface PortfolioPerformance {
  total_return: number
  annualized_return: number
  volatility: number
  sharpe_ratio: number
  max_drawdown: number
}

export interface YearlyData {
  year: number
  portfolio_return: number
  benchmark_return: number
  sp500_return?: number | null
  excess_return: number
  excess_vs_sp500?: number | null
  turnover_pct?: number
  portfolio_return_net?: number
  benchmark_return_net?: number
  excess_return_net?: number
}

export interface BacktestResult {
  period: string
  meta?: Record<string, unknown>
  holdings: PortfolioHolding[]
  holdings_by_year?: Record<string, PortfolioHolding[]>
  portfolio_performance: PortfolioPerformance
  benchmark_performance: PortfolioPerformance
  sp500_performance?: PortfolioPerformance
  excess_return: number
  excess_vs_sp500?: number | null
  portfolio_performance_net?: PortfolioPerformance
  benchmark_performance_net?: PortfolioPerformance
  excess_return_net?: number
  turnover?: {
    avg_turnover_pct?: number
    max_turnover_pct?: number
    by_year?: Array<Record<string, unknown>>
    note?: string
  }
  cost_assumptions?: Record<string, unknown>
  yearly_data: YearlyData[]
}

export interface SectorAllocation {
  sector: string
  weight: number
}

export interface WindowOption {
  window_id: string
  window_type: string
  start_year: number
  end_year: number
  label: string
}

export interface PortfolioForecast {
  as_of: string
  holdings_count: number
  avg_rd_intensity: number
  methodology: string
  forecast: {
    expected_market_return: number
    expected_rd_premium: number
    expected_portfolio_return: number
    confidence_level: string
    risk_note: string
  }
  top_holdings: Array<{ symbol: string; sector: string; rd_intensity: number }>
}

export interface ForecastVsActual {
  year: number
  is_historical: boolean
  forecast_return: number
  actual_return: number | null
  benchmark_return: number
  forecast_premium: number
  forecast_error: number | null
  holdings_count: number
  avg_rd_intensity: number
  top_holdings: Array<{ symbol: string; sector: string; rd_intensity: number }>
}

export interface AnnualReportSummary {
  fiscal_year: number
  filing_date: string | null
  form_type: string
  accession_id: string | null
  file_format: string | null
  file_size_mb: number | null
  has_xbrl: boolean | null
  word_count: number | null
  sections_found: string[] | null
  rd_mentions: number | null
  rd_tone_score: number | null
  rd_section_length: number | null
  sec_url: string | null
}

export interface AnnualReportsResponse {
  symbol: string
  company_name: string
  total_filings: number
  years_covered: number[]
  filings: AnnualReportSummary[]
  rd_analysis_summary: {
    total_rd_mentions: number
    avg_rd_tone: number | null
    years_with_rd_analysis: number
    trend: string
  }
}


// ─── PNL Efficiency Alpha Types ─────────────────────────────────────────────

export type AlphaFamily = "rd_alpha" | "pnl_efficiency"

export interface PnlEfficiencyScore {
  symbol: string
  name: string
  sector: string
  industry: string | null
  gross_efficiency: number
  overhead_efficiency: number
  operating_efficiency: number
  profit_conversion: number
  gross_efficiency_z: number
  overhead_efficiency_z: number
  operating_efficiency_z: number
  profit_conversion_z: number
  composite_z: number
  sector_percentile: number
  final_score: number
  revenue: number
  fiscal_year_used: number | null
  selection_rank: number
}

export interface PnlQuintile {
  quintile: number
  label: string
  n_companies: number
  avg_composite_z: number
  avg_gross_eff: number
  avg_overhead_eff: number
  avg_operating_eff: number
  avg_profit_conv: number
}

export interface PnlMethodology {
  name: string
  components: Record<string, string>
  scoring_method: string
  normalization: string
  winsorization: string
  phase: string
  excluded: string[]
}

