/**
 * PATH: frontend/src/lib/priceGuides.ts
 * PURPOSE: Honest valuation-band reads and research statuses.
 *
 * The paper produces a present-value low / median / high band. It does not
 * produce 1/2/3-year target prices or fixed-percentage buy ratings. For a
 * chosen convergence horizon we therefore show only the annualized price
 * return required to move from today's price to each CURRENT fair-value lens.
 */

import type { SaasCompany } from "@/lib/api/saasPortfolio"
import { livePrice, mosLive } from "@/lib/portfolioReturns"

export type YearGuide = {
  year: 1 | 2 | 3
  low: number | null
  mid: number | null
  high: number | null
}

export type PriceGuideSet = {
  today: { low: number | null; mid: number | null; high: number | null }
  years: YearGuide[]
  methodNote: string
}

export type ResearchAction =
  | "core"
  | "watchlist"
  | "candidate"
  | "triggered"
  | "outside"
  | "insufficient"

export type ResearchGuideline = {
  action: ResearchAction
  label: string
  summary: string
  reasons: string[]
  valuationAnchors: {
    conservative: number | null
    median: number | null
    high: number | null
  }
  mos: number | null
  price: number | null
}

function annualizedReturn(price: number | null, value: number | null, years: number) {
  if (price == null || value == null || price <= 0 || value <= 0 || years <= 0) return null
  return Math.pow(value / price, 1 / years) - 1
}

export function buildPriceGuides(c: SaasCompany): PriceGuideSet {
  const price = livePrice(c)
  const today = {
    low: c.fair_px_lo ?? null,
    mid: c.fair_px_med ?? null,
    high: c.fair_px_hi ?? null,
  }

  return {
    today,
    years: ([1, 2, 3] as const).map((year) => ({
      year,
      low: annualizedReturn(price, today.low, year),
      mid: annualizedReturn(price, today.mid, year),
      high: annualizedReturn(price, today.high, year),
    })),
    methodNote:
      "Annualized price return if the market reaches each current fair-value lens after 1, 2, or 3 years. These are convergence calculations—not forecasts—and exclude dividends, future estimate changes, and taxes.",
  }
}

/**
 * Paper-faithful research status. This deliberately does not emit Buy / Sell.
 */
export function buildResearchGuideline(c: SaasCompany): ResearchGuideline {
  const price = livePrice(c)
  const mos = mosLive(c)
  const reasons: string[] = []
  const g = c.gates
  const tier = (c.paper_tier || "").toLowerCase()

  if (g.g2_fcf_positive) reasons.push("SBC-adjusted FCF-positive")
  else reasons.push("Fails the paper's FCF-positive core gate")
  if (g.g5_improving_cash) reasons.push("Cash conversion improving")
  else reasons.push("Cash-conversion improvement not confirmed")
  if (g.g5_moat_quality) reasons.push("Moat/quality gate passes")
  else reasons.push("Moat/quality gate fails")
  if (mos != null) reasons.push(`Live price is ${fmtMos(mos)} versus the median fair-value lens`)
  if (c.mgmt_score) reasons.push(`Management overlay: ${c.mgmt_score}`)
  if (c.kill_criterion) reasons.push(`Monitor: ${c.kill_criterion}`)

  const shared = {
    reasons,
    valuationAnchors: {
      conservative: c.fair_px_lo ?? null,
      median: c.fair_px_med ?? null,
      high: c.fair_px_hi ?? null,
    },
    mos,
    price,
  }

  // A paper survivor whose live-price margin of safety has gone negative has
  // hit the paper's own kill trigger — say so instead of showing a stale tier.
  if (tier && mos != null && mos <= 0) {
    return {
      action: "triggered",
      label: "Kill criterion triggered · on hold",
      summary:
        "This paper survivor's margin of safety is gone at the live price — its own kill criterion (base MoS → negative) has fired. The paper protocol is hold off / trim, not buy.",
      ...shared,
    }
  }
  if (tier.includes("tier1")) {
    return {
      action: "core",
      label: "Paper Tier 1 snapshot · core research",
      summary:
        "Cleared the paper's strict gates and remained below independently estimated value on the conservative lens. This qualifies it for underwriting, not an automatic buy.",
      ...shared,
    }
  }
  if (tier.includes("tier2")) {
    return {
      action: "watchlist",
      label: "Paper Tier 2 snapshot · watchlist",
      summary:
        "Cleared the core economic gates on the base case but not the conservative valuation lens. The paper treats this as watchlist evidence, not a buy signal.",
      ...shared,
    }
  }
  if (g.core_thesis_path_live === true || g.research_longlist_live === true) {
    return {
      action: "candidate",
      label: "Screen candidate · not a paper survivor",
      summary:
        "Passes the relaxed 6-of-12 gate screen at live prices, but fails at least one of the paper's full Table-20 conditions. Watchlist evidence only.",
      ...shared,
    }
  }
  if (g.core_thesis_path === true || g.research_longlist === true) {
    return {
      action: "candidate",
      label: "Screen candidate · paper snapshot",
      summary:
        "Passed the relaxed screen on the paper date but is not one of the four Table-20 survivors, and its live-price gate no longer holds.",
      ...shared,
    }
  }
  return {
    action: price == null ? "insufficient" : "outside",
    label: price == null ? "Insufficient data" : "Outside paper core",
    summary:
      price == null
        ? "A live price and complete valuation band are required."
        : "This name does not clear the paper's strict core/watchlist evidence chain.",
    ...shared,
  }
}

function fmtMos(m: number) {
  return `${(m * 100).toFixed(0)}%`
}

export function researchStatusTone(action: ResearchAction): string {
  switch (action) {
    case "core":
      return "border-neutral-300 bg-neutral-100 text-neutral-900"
    case "watchlist":
      return "border-amber-300 bg-amber-50 text-amber-950"
    case "candidate":
      return "border-sky-300 bg-sky-50 text-sky-950"
    case "triggered":
      return "border-rose-400 bg-rose-50 text-rose-950"
    case "outside":
      return "border-neutral-200 bg-neutral-50 text-neutral-700"
    case "insufficient":
      return "border-rose-300 bg-rose-50 text-rose-950"
  }
}

