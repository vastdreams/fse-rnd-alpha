/**
 * PATH: frontend/src/lib/api/saasPortfolio.ts
 * PURPOSE: SaaS AI mispricing portfolio API (auth-gated; no public static bundle).
 */
import { fetchApi } from "./base"

export type SaasGates = {
  g1_saas_universe: boolean
  g2_fcf_positive: boolean
  g3_base_mos_positive: boolean
  g4_exposed_incumbent_or_workflow: boolean
  g4_core_exposed_incumbent: boolean
  g5_improving_cash: boolean
  g5_moat_quality: boolean
  g6_investable_size: boolean
  g7_overcorrected: boolean
  core_thesis_path: boolean
  research_longlist: boolean
  g3_base_mos_positive_live?: boolean
  core_thesis_path_live?: boolean
  research_longlist_live?: boolean
}

export type SaasCompany = {
  rank: number
  ticker: string
  cohort: string
  wave?: string | null
  vgroup: string
  quadrant: string
  as_of: string
  marketcap_usd?: number | null
  revenue_usd?: number | null
  price?: number | null
  fair_px_lo?: number | null
  fair_px_med?: number | null
  fair_px_hi?: number | null
  mos?: number | null
  mos_pct?: number | null
  upside_med_pct?: number | null
  rev_cagr?: number | null
  rev_cagr_pct?: number | null
  fcfm_sbc_l?: number | null
  d_fcfm_sbc?: number | null
  roic_l?: number | null
  rule40_sbc_l?: number | null
  sbc_pct_l?: number | null
  dilution_ann?: number | null
  wacc?: number | null
  impl_g_l?: number | null
  impl_vs_realised?: number | null
  ev_dcf_fcf?: number | null
  ev_dcf_norm?: number | null
  rd_int_l?: number | null
  rd_prod?: number | null
  universe_score: number
  gates: SaasGates
  mgmt_factors: Record<string, unknown>
  intangible_score: number
  paper_tier?: string | null
  mgmt_score?: string | null
  mgmt_note?: string | null
  kill_criterion?: string | null
  filing_url?: string | null
  accession?: string | null
  fp_overlay?: boolean
  ai_risk_excerpt?: string | null
  live_price?: number | null
  live_marketcap_usd?: number | null
  live_mos?: number | null
  live_name?: string | null
}

export type SaasBundle = {
  provenance: Record<string, unknown>
  selection_paths: Array<{ id: string; label: string; description: string; filter: string }>
  companies: SaasCompany[]
  bucket_presets: Array<{ id: string; label: string; tickers: string[] }>
}

let cached: SaasBundle | null = null

export async function loadSaasBundle(): Promise<SaasBundle> {
  if (cached) return cached
  const api = await fetchApi<{
    provenance: Record<string, unknown>
    selection_paths: SaasBundle["selection_paths"]
    bucket_presets: SaasBundle["bucket_presets"]
  }>("/api/portfolio/saas/provenance")
  const uni = await fetchApi<{ companies: SaasCompany[] }>("/api/portfolio/saas/universe?limit=100")
  cached = {
    provenance: api.provenance,
    selection_paths: api.selection_paths,
    bucket_presets: api.bucket_presets,
    companies: uni.companies || [],
  }
  return cached
}

export function filterByPath(companies: SaasCompany[], pathId: string): SaasCompany[] {
  if (!pathId || pathId === "full_100" || pathId === "all") return companies
  if (pathId === "table20" || pathId === "paper_tier") return companies.filter((c) => !!c.paper_tier)
  if (pathId === "model_10") {
    const set = new Set([
      "FRSH",
      "DOCU",
      "PCTY",
      "WDAY",
      "MNDY",
      "PAYC",
      "NICE",
      "DBX",
      "APPF",
      "BILL",
    ])
    return companies.filter((c) => set.has(c.ticker.toUpperCase()))
  }
  const alias: Record<string, keyof SaasGates | "paper_tier"> = {
    ex_payments: "g1_saas_universe",
    mos_positive: "g3_base_mos_positive_live",
    moat_quality: "g5_moat_quality",
    research_longlist: "research_longlist_live",
    core_thesis: "core_thesis_path_live",
  }
  const key = alias[pathId] ?? pathId
  if (key === "paper_tier") return companies.filter((c) => !!c.paper_tier)
  return companies.filter((c) => {
    const gates = c.gates as unknown as Record<string, boolean | undefined>
    // Live-labeled paths require the live field itself — never silently fall back to snapshot.
    if (key.endsWith("_live")) return gates[key] === true
    return !!gates[key]
  })
}

export const saasPortfolioApi = {
  loadBundle: loadSaasBundle,
  getCompany: (ticker: string) =>
    fetchApi<{ company: SaasCompany; provenance: Record<string, unknown>; in_presets: string[] }>(
      `/api/portfolio/saas/company/${ticker}`
    ),
  getBucket: (tickers: string[]) =>
    fetchApi<{
      n: number
      tickers: string[]
      median_mos: number | null
      mean_intangible: number | null
      companies: SaasCompany[]
      equal_weight: number
    }>(`/api/portfolio/saas/bucket?tickers=${tickers.join(",")}`),
  getFunnel: () =>
    fetchApi<{ funnel: Array<{ id: string; label: string; description: string; n: number }> }>(
      "/api/portfolio/saas/paths/summary"
    ),
}
