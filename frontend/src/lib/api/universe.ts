/**
 * PATH: src/lib/api/universe.ts
 * PURPOSE: Client for the evidence-ranked universe APIs (W2a–W4).
 * Types mirror backend/app/contracts/research.py (snake_case preserved:
 * these payloads are research artifacts and the field names are part of
 * the audit trail).
 */

import { ApiError, fetchApi, fetchApiCached } from "./base"
import { formatNumber4, formatPercent4 } from "../formatMetrics"

export interface MetricValue {
  value: number | null
  as_of_date: string | null
  available_date: string | null
  claim_ids: string[]
  formula: string | null
  engine_version: string | null
}

export interface ResearchCompleteness {
  grade: "A" | "B" | "C" | "Incomplete"
  filing_fetched: boolean
  claims_n: number
  dcf_reproducible: boolean
  overlay_fill_rate: number
  competitor_map_filled: boolean
  asof_freshness_days: number | null
  stale: boolean
}

export interface MetricVector {
  ticker: string
  universe_version: string
  computed_at: string
  product_map_complete: boolean | null
  competitor_set_n: number | null
  retention: MetricValue
  concentration: MetricValue
  moat_direction: string | null
  offering_quality_z: MetricValue
  mos_snapshot: MetricValue
  mos_live: MetricValue
  table20_pass_count: number | null
  kill_active: boolean | null
  cohort: string | null
  rd_int: MetricValue
  rd_gp: MetricValue
  rd_mom: MetricValue
  rd_capital: MetricValue
  rd_prod: MetricValue
  rd_cap_to_ev: MetricValue
  gm: MetricValue
  fcfm_sbc: MetricValue
  roic: MetricValue
  rule40: MetricValue
  sbc_intensity: MetricValue
  rev_cagr: MetricValue
  dilution_ann: MetricValue
  runway_yrs: MetricValue
  ret_1m: MetricValue
  ret_3m: MetricValue
  ret_12m: MetricValue
  drawdown_from_peak: MetricValue
  ai_text_stance: MetricValue
  float_fcf_share: MetricValue
  fair_px_lo: MetricValue
  fair_px_med: MetricValue
  fair_px_hi: MetricValue
  carve_out: boolean | null
  route: "fcf_positive" | "pre_fcf" | "carved_out" | null
  completeness: ResearchCompleteness
}

export interface RankRecipe {
  recipe_id: string
  name: string
  formula_human: string
  formula_exact: string
  hard_filters: string[]
  axes: string[]
  benchmark_vs: string
  custom: boolean
}

export interface RowEnrichment {
  name?: string | null
  industry?: string | null
  size?: string | null
  description?: string | null
  fair_px_lo?: number | null
  fair_px_med?: number | null
  fair_px_hi?: number | null
  price_snapshot?: number | null
  price_live?: number | null
  price_as_of?: string | null
  price_source?: string | null
  price_stale?: boolean | null
  price_is_derived?: boolean
  price_change?: number | null
  price_change_pct?: number | null
  vs_median_usd?: number | null
  vs_median_pct?: number | null
  quadrant?: string | null
  mos_live?: number | null
  fair_value_band_valid?: boolean
  fair_value_band_note?: string | null
  retention?: number | null
  rev_cagr?: number | null
  /** Baseline panel date used by period-based productivity metrics. */
  fundamentals_baseline_as_of?: string | null
  /** Panel date for revenue / margin / FCF snapshot. */
  fundamentals_as_of?: string | null
  /** Latest panel revenue (USD) — drives DCF / fair-value guide */
  revenue_usd?: number | null
  /** Net profit margin (panel npm_l) */
  npm?: number | null
  /** Net profit ≈ revenue × npm when both known */
  net_profit_usd?: number | null
  opm?: number | null
  gm?: number | null
  fcfm_sbc?: number | null
  fcf_usd?: number | null
  roic?: number | null
  /** R&D spend / revenue. */
  rd_int?: number | null
  /** Gross profit created per $ of cumulative R&D. */
  rd_prod?: number | null
  rule40?: number | null
}

export interface RankedRow extends RowEnrichment {
  ticker: string
  recipe_id: string
  universe_version: string
  rank: number
  score: number
  contributions: Record<string, number>
  completeness_grade: "A" | "B" | "C" | "Incomplete"
  freshness_ok: boolean
  kill_active: boolean | null
  reviewer_passed: boolean | null
}

export interface ExcludedRow extends RowEnrichment {
  ticker: string
  reasons: string[]
  completeness_grade: "A" | "B" | "C" | "Incomplete"
  route: string
  kill_active: boolean | null
}

export interface RankResponse {
  recipe: RankRecipe
  universe_version: string
  n_universe: number
  n_ranked: number
  rows: RankedRow[]
  excluded?: ExcludedRow[]
  n_excluded?: number
  note: string
}

export interface EvidenceClaim {
  claim_id: string
  snapshot_id: string
  ticker: string
  field: string
  value_text: string
  value_numeric: number | null
  operator: string | null
  unit: string | null
  excerpt_locator: string
  extractor: string
  extracted_at: string
}

export interface SourceSnapshot {
  snapshot_id: string
  kind: string
  ticker: string
  as_of_date: string
  available_date: string
  locator: string
  notes: string | null
}

export interface AuditTrail {
  ticker: string
  axis: string
  metric: MetricValue
  claims: EvidenceClaim[]
  snapshots: SourceSnapshot[]
  literature: { axis: string; bib_key: string; citation: string; paper_section: string | null }[]
  deepseek_run: { run_id: string; job: string; status: string; severity: string | null } | null
  final_review: { review_id: string; passed: boolean } | null
}

export interface CompanyIdentity {
  name?: string | null
  exchange?: string | null
  sector?: string | null
  industry?: string | null
  size?: string | null
  location?: string | null
}

export interface CompanyProfile {
  name?: string | null
  description?: string | null
  website?: string | null
  industry?: string | null
  sector?: string | null
  ceo?: string | null
  employees?: string | number | null
  ipo_date?: string | null
  price_live?: number | null
  price_as_of?: string | null
  price_source?: string | null
  price_stale?: boolean
  price_change?: number | null
  price_change_pct?: number | null
  range_52w?: string | null
  beta?: number | null
  market_cap?: number | null
  source?: string
}

export interface ValuationRange {
  fair_px_lo: number | null
  fair_px_med: number | null
  fair_px_hi: number | null
  price_snapshot: number | null
  price_live: number | null
  price_as_of?: string | null
  price_source?: string | null
  fair_value_source?: string | null
  invalid_band?: boolean
  mos_snapshot: number | null
  quadrant: string | null
  cohort: string | null
  wave: string | null
  rev_cagr: number | null
  wacc: number | null
  zone: string | null
  gap_to_median: number | null
  note: string
}

export interface WaterfallClaim {
  claim_id: string
  field: string
  value_text: string
  value_numeric?: number | null
  locator?: string | null
  as_of_date?: string | null
}

export interface WaterfallStage {
  id: string
  title: string
  status: "known" | "unknown" | "partial"
  score: number | null
  summary: string
  claims: WaterfallClaim[]
  unknown_reason?: string | null
}

export interface RoiRun {
  id: string
  label: string
  weight: number
  score: number | null
  contributions: Record<string, number>
  unknown_axes: string[]
  note: string
}

export interface PrecedenceExample {
  id: string
  label: string
  rule: string
  matched: boolean | null
  evidence: string
}

export interface StanceAggregate {
  score: number | null
  confidence: "high" | "med" | "low" | "none"
  stance: "BUY" | "HOLD" | "WATCH" | "OUT" | "UNKNOWN"
  horizon_years: 1 | 2 | 3 | null
  horizon_note: string | null
  implied_ann_return: number | null
  blockers: string[]
  flowchart: { id: string; label: string; result: string; detail: string }[]
  precedence_examples: PrecedenceExample[]
  engine_version: string
  watermark: string
}

export interface CloseCallWaterfall {
  ticker: string
  universe_version: string
  computed_at: string
  stages: WaterfallStage[]
  roi_runs: RoiRun[]
  aggregate: StanceAggregate
}

export interface CompanyResearch {
  ticker: string
  universe_version: string
  identity?: CompanyIdentity | null
  profile?: CompanyProfile | null
  valuation_range?: ValuationRange | null
  close_call_waterfall?: CloseCallWaterfall | null
  close_call_data_mode?: "current_overlay" | "frozen_universe"
  vector: MetricVector
  gates: { gate_id: string; passed: boolean; threshold: string; observed: string | null }[]
  deepseek_runs: { run_id: string; job: string; output_kind: string; status: string; severity: string | null }[]
  final_review: { review_id: string; passed: boolean; trigger: string; notes: string | null } | null
  reviewer_passed: boolean | null
  dcf_runs: DcfRunRecord[]
}

export interface DcfInputs {
  ticker: string
  scenario: string
  revenue_usd: number | null
  fcf_sbc_usd: number | null
  fcfm_sbc: number | null
  net_cash_usd: number
  ev_mult_usd: number | null
  shares_fut_implied: number | null
  price: number | null
  growth: number
  wacc: number
  terminal_g: number
  target_margin: number | null
  years?: number
  glide_years?: number
}

export interface DcfOutputs {
  ev_dcf_fcf: number | null
  ev_dcf_norm: number | null
  ev_mult: number | null
  fair_px_lo: number | null
  fair_px_med: number | null
  fair_px_hi: number | null
  mos: number | null
  engine_version: string
}

export interface DcfRunRecord {
  run_id: string
  scenario: string
  inputs: DcfInputs
  outputs: DcfOutputs
  engine_version: string
  created_at: string
  user_id?: string | null
  universe_version: string
  visibility?: "private" | "reference"
}

export interface BookConstraint {
  kind: string
  limit: number | null
  enabled: boolean
}

export interface BookHolding {
  ticker: string
  weight_pct: number
  added_at: string
  override_reason?: string | null
}

export interface SavedBookRecord {
  book_id: string
  name: string
  recipe_id: string | null
  universe_version: string | null
  constraints: BookConstraint[]
  holdings: BookHolding[]
  updated_at: string
  is_primary: boolean
  locked_at: string | null
  lock_acknowledgements: string[]
  lock_version: string | null
  revision: number
}

export interface Breach {
  kind: string
  ticker?: string
  detail: string
}

// ---------------------------------------------------------------------------

export const getRecipes = () =>
  fetchApiCached<{ recipes: RankRecipe[]; default_recipe: string }>("/api/universe/recipes")

export const getRank = (
  recipeId: string,
  universeVersion?: string,
  includeExcluded = false,
  signal?: AbortSignal
) =>
  fetchApiCached<RankResponse>(
    `/api/universe/rank?recipe_id=${recipeId}${universeVersion ? `&universe_version=${universeVersion}` : ""}${
      includeExcluded ? "&include_excluded=true" : ""
    }`,
    { signal }
  )

export const rankCustom = (name: string, axes: string[]) =>
  fetchApi<RankResponse>("/api/universe/rank/custom", {
    method: "POST",
    body: JSON.stringify({ name, axes }),
  })

export interface StanceListRow {
  ticker: string
  stance: "BUY" | "HOLD" | "WATCH" | "OUT" | "UNKNOWN"
  confidence: "high" | "med" | "low" | "none"
  score: number | null
  horizon_years: 1 | 2 | 3 | null
  implied_ann_return: number | null
  horizon_note: string | null
  blockers: string[]
  watermark: string
}

export const getResearchStances = (
  stance?: string,
  limit?: number,
  universeVersion?: string,
  signal?: AbortSignal
) => {
  const query = new URLSearchParams()
  if (stance) query.set("stance", stance)
  if (limit != null) query.set("limit", String(limit))
  if (universeVersion) query.set("universe_version", universeVersion)
  const suffix = query.toString() ? `?${query.toString()}` : ""
  return fetchApi<{
    universe_version: string
    stance_filter: string | null
    n_universe?: number
    n_analyzed?: number
    n: number
    rows: StanceListRow[]
    data_mode?: "frozen_universe" | "current_overlay"
    note: string
  }>(`/api/universe/stances${suffix}`, { signal })
}

export interface FinancialRow {
  calendardate: string
  datekey: string
  revenue: number | null
  gp: number | null
  opex: number | null
  rnd: number | null
  sgna: number | null
  opinc: number | null
  ebitda: number | null
  netinc: number | null
  epsdil: number | null
  ncfo: number | null
  capex: number | null
  fcf: number | null
  sbcomp: number | null
  assets: number | null
  equity: number | null
  debt: number | null
  cashnequsd: number | null
  liabilities: number | null
  grossmargin: number | null
  netmargin: number | null
  ebitdamargin: number | null
  roa: number | null
  roe: number | null
  roic: number | null
  ros: number | null
  de: number | null
  currentratio: number | null
  pe: number | null
  ps: number | null
  pb: number | null
  divyield: number | null
  payoutratio: number | null
  shareswadil: number | null
  marketcap: number | null
  ev: number | null
  [key: string]: string | number | null
}

export interface FinancialsResponse {
  ticker: string
  source: string
  fetched_at: string
  n_years: number
  annual: FinancialRow[]
  quarterly: FinancialRow[]
  note: string
}

export interface PriceBar {
  date: string
  close: number
  volume: number | null
}

export interface PriceHistoryResponse {
  ticker: string
  source: string
  fetched_at: string
  price_as_of?: string | null
  price_source?: string | null
  cache_stale?: boolean
  n: number
  start: string
  end: string
  last: number
  bars: PriceBar[]
  note: string
}

export const getFinancials = (ticker: string, signal?: AbortSignal) =>
  fetchApiCached<FinancialsResponse>(`/api/universe/financials/${ticker}`, { signal })

export const getPriceHistory = (ticker: string, years = 3, signal?: AbortSignal) =>
  fetchApiCached<PriceHistoryResponse>(`/api/universe/price-history/${ticker}?years=${years}`, { signal })

export const getCompanyResearch = (ticker: string, universeVersion?: string, signal?: AbortSignal) =>
  fetchApiCached<CompanyResearch>(
    `/api/universe/company/${ticker}${universeVersion ? `?universe_version=${encodeURIComponent(universeVersion)}` : ""}`,
    { signal }
  )

export const getAuditTrail = (
  ticker: string,
  axis: string,
  universeVersion?: string,
  signal?: AbortSignal
) =>
  fetchApiCached<AuditTrail>(
    `/api/universe/audit/${ticker}/${axis}${universeVersion ? `?universe_version=${encodeURIComponent(universeVersion)}` : ""}`,
    { signal }
  )

export const getAuditPack = (ticker: string, universeVersion?: string, signal?: AbortSignal) =>
  fetchApi<Record<string, unknown>>(
    `/api/universe/audit-pack/${ticker}${universeVersion ? `?universe_version=${encodeURIComponent(universeVersion)}` : ""}`,
    { signal }
  )

export const runDcf = (
  ticker: string,
  inputs: DcfInputs,
  save = true,
  universeVersion?: string,
  signal?: AbortSignal
) =>
  fetchApi<{ run_id: string | null; inputs: DcfInputs; outputs: DcfOutputs; universe_version: string }>(
    `/api/universe/dcf/${ticker}?save=${save}${universeVersion ? `&universe_version=${encodeURIComponent(universeVersion)}` : ""}`,
    { method: "POST", body: JSON.stringify(inputs), signal }
  )

export type MemoCitationRecord = {
  claim_id: string
  value_text: string
  excerpt_locator: string
  snapshot_id: string
  extractor: string
}

export type CompanyMemo = {
  memo_id: string
  version: number
  thesis: string
  risks: string | null
  created_at: string
  analyst_judgment_ack: boolean
  citations: string[]
  citation_records: MemoCitationRecord[]
  universe_version: string
}

export const getMemos = (ticker: string, universeVersion?: string, signal?: AbortSignal) =>
  fetchApi<{ universe_version: string; memos: CompanyMemo[] }>(
    `/api/universe/memo/${ticker}${universeVersion ? `?universe_version=${encodeURIComponent(universeVersion)}` : ""}`,
    { signal }
  )

export const saveMemo = (
  ticker: string,
  body: { thesis: string; risks?: string; citations: string[]; analyst_judgment_ack: boolean; universe_version?: string },
  signal?: AbortSignal
) => fetchApi<{ memo_id: string; version: number; universe_version: string }>(`/api/universe/memo/${ticker}`, {
  method: "POST",
  body: JSON.stringify(body),
  signal,
})

// Books ---------------------------------------------------------------------

export const listBooks = (signal?: AbortSignal) =>
  fetchApi<{ books: SavedBookRecord[] }>("/api/books", { signal })

export const createBook = (
  name: string,
  recipeId?: string,
  universeVersion?: string,
  makePrimary = true
) =>
  fetchApi<{ book_id: string }>("/api/books", {
    method: "POST",
    body: JSON.stringify({
      name,
      recipe_id: recipeId,
      universe_version: universeVersion,
      make_primary: makePrimary,
    }),
  })

export async function saveBook(
  bookId: string,
  holdings: BookHolding[],
  constraints?: BookConstraint[],
  revision?: number
): Promise<{ saved: true; revision: number } | { breaches: Breach[] }> {
  try {
    return await fetchApi<{ saved: true; revision: number }>(`/api/books/${bookId}`, {
      method: "PUT",
      body: JSON.stringify({ holdings, constraints, revision }),
    })
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 422 &&
      typeof error.detail === "object" &&
      error.detail !== null &&
      Array.isArray((error.detail as { breaches?: unknown }).breaches)
    ) {
      return { breaches: (error.detail as { breaches: Breach[] }).breaches }
    }
    throw error
  }
}

export const checkBook = (bookId: string, holdings: BookHolding[]) =>
  fetchApi<{ breaches: Breach[] }>(`/api/books/${bookId}/check`, {
    method: "POST",
    body: JSON.stringify({ holdings }),
  })

export const deleteBook = (bookId: string) =>
  fetchApi<{ deleted: string }>(`/api/books/${bookId}`, { method: "DELETE" })

export const setPrimaryBook = (bookId: string) =>
  fetchApi<{ book_id: string; is_primary: true }>(`/api/books/${bookId}/primary`, { method: "POST" })

export const lockBook = (bookId: string, acknowledgements: string[], revision?: number) =>
  fetchApi<{ book_id: string; locked: true; universe_version: string; acknowledgements: string[]; revision: number }>(
    `/api/books/${bookId}/lock`,
    { method: "POST", body: JSON.stringify({ acknowledgements, revision }) }
  )

export const unlockBook = (bookId: string) =>
  fetchApi<{ book_id: string; locked: false; revision: number }>(`/api/books/${bookId}/unlock`, { method: "POST" })

export const getBookAuditPack = (bookId: string) =>
  fetchApi<Record<string, unknown>>(`/api/books/${bookId}/audit-pack`)

// Formatting helpers ---------------------------------------------------------

export const fmtVal = (m: MetricValue | null | undefined, pct = false): string => {
  if (!m || m.value === null || m.value === undefined) return "Unknown"
  return pct ? formatPercent4(m.value) : formatNumber4(m.value)
}

export const gradeTone = (g: string): string =>
  g === "A"
    ? "border-emerald-300 bg-emerald-50 text-emerald-900"
    : g === "B"
      ? "border-sky-300 bg-sky-50 text-sky-900"
      : g === "C"
        ? "border-amber-300 bg-amber-50 text-amber-900"
        : "border-neutral-300 bg-neutral-100 text-neutral-700"
