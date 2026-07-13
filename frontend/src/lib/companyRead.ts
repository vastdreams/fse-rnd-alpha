/**
 * PATH: frontend/src/lib/companyRead.ts
 * PURPOSE: Turn model fields into a readable, evidence-bounded company brief.
 */

import type { SaasCompany } from "@/lib/api/saasPortfolio"
import { fmtMoney, fmtPct, livePrice, mosLive } from "@/lib/portfolioReturns"

export type CompanyRead = {
  conclusion: string
  whyItQualifies: string[]
  whatCouldBreak: string[]
  nextChecks: string[]
}

export function buildCompanyRead(c: SaasCompany): CompanyRead {
  const g = c.gates
  const mf = c.mgmt_factors || {}
  const price = livePrice(c)
  const mos = mosLive(c)
  const tier = (c.paper_tier || "").toLowerCase()

  const whyItQualifies: string[] = []
  if (g.g2_fcf_positive) whyItQualifies.push("Produces positive SBC-adjusted free cash flow.")
  if (g.g5_improving_cash) whyItQualifies.push("Cash conversion is improving under the paper's gate.")
  if (g.g5_moat_quality) whyItQualifies.push("Passes the R&D productivity / Rule-of-40 quality gate.")
  if (c.rev_cagr_pct != null) {
    whyItQualifies.push(`Realised revenue CAGR is ${c.rev_cagr_pct.toFixed(1)}%.`)
  }
  if (price != null && c.fair_px_med != null) {
    whyItQualifies.push(
      `Live price ${fmtMoney(price)} versus median triangulated valuation ${fmtMoney(c.fair_px_med)} (${fmtPct(mos, 0)} gap).`
    )
  }

  const whatCouldBreak: string[] = []
  if (price != null && c.fair_px_lo != null && price > c.fair_px_lo) {
    whatCouldBreak.push(
      `Price is above the low valuation lens (${fmtMoney(c.fair_px_lo)}), so the case depends on the median/high model outputs.`
    )
  }
  if (!g.g5_improving_cash) whatCouldBreak.push("Improving cash conversion is not confirmed.")
  if (!g.g5_moat_quality) whatCouldBreak.push("Moat/quality gate does not pass.")
  if (c.sbc_pct_l != null && c.sbc_pct_l >= 0.1) {
    whatCouldBreak.push(`Stock compensation is ${(c.sbc_pct_l * 100).toFixed(1)}% of revenue.`)
  }
  if (c.dilution_ann != null && c.dilution_ann > 0) {
    whatCouldBreak.push(`Share count is diluting at about ${(c.dilution_ann * 100).toFixed(1)}% annually.`)
  }
  if (mf.nrr_disclosed == null || mf.nrr_disclosed === false) {
    whatCouldBreak.push("Net revenue retention is missing or not disclosed.")
  }
  if (c.kill_criterion) whatCouldBreak.push(c.kill_criterion)
  if (whatCouldBreak.length === 0) {
    whatCouldBreak.push("The extracted data has no explicit kill criterion; this is an evidence gap, not proof of low risk.")
  }

  const nextChecks = [
    "Rebuild the DCF after the next results using updated revenue, margin, dilution, and net-cash inputs.",
    "Read the linked filing for retention, customer concentration, stock compensation, and AI substitution risk.",
    "Reduce or reject the thesis if its stated kill criterion is triggered.",
  ]

  let conclusion =
    "This company is a research candidate. The screen is a starting point; it does not establish a buy."
  if (tier.includes("tier1")) {
    conclusion =
      "Paper Tier 1: it survived the strict operating gates and the conservative valuation lens. That supports deeper underwriting, not an automatic purchase."
  } else if (tier.includes("tier2")) {
    conclusion =
      "Paper Tier 2 watchlist: the base valuation case is positive, but the conservative case is not. Entry price and execution evidence matter."
  } else if (g.core_thesis_path_live === true) {
    conclusion =
      "Core-path research candidate on the live-price MoS gate: it passes the economic screen but was not one of the paper's four final survivors."
  } else if (g.core_thesis_path === true) {
    conclusion =
      "Core-path research candidate on the paper-date snapshot: it passed the economic screen but was not one of the paper's four final survivors."
  } else if (!g.research_longlist && g.research_longlist_live !== true) {
    conclusion =
      "Outside the paper's core research list: the current evidence chain is not strong enough to frame this as a buy."
  }

  return {
    conclusion,
    whyItQualifies: whyItQualifies.length
      ? whyItQualifies
      : ["No positive paper-gate evidence is available in the current bundle."],
    whatCouldBreak,
    nextChecks,
  }
}
