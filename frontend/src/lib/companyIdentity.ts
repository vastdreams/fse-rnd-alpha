/**
 * PATH: frontend/src/lib/companyIdentity.ts
 * PURPOSE: Readable company name + sector + sub-industry line for portfolio tables.
 *
 * Sector/sub-industry come from the paper cohort taxonomy (scripts/saas_ai/analysis/cohorts.py).
 * The SaaS bundle does not currently ship Sharadar industry strings, so curated product
 * categories are the transparent sub-industry source of truth.
 */

import type { SaasCompany } from "@/lib/api/saasPortfolio"

/** Product / seat category from the paper's curated cohort lists. */
const SUB_INDUSTRY: Record<string, string> = {
  // AI-native
  PLTR: "AI/ML platform",
  AI: "Enterprise AI apps",
  SNOW: "Data cloud",
  DDOG: "Observability + AI",
  MDB: "AI-era database",
  CFLT: "Data streaming",
  ESTC: "Search / AI",
  PATH: "Automation / AI",
  NET: "Edge / AI inference",
  S: "AI-native security",
  CRWD: "AI-native security",
  BBAI: "AI analytics",
  SOUN: "Voice AI",
  GTLB: "AI developer tools",
  // Exposed incumbents
  CRM: "CRM",
  ADBE: "Creative software",
  NOW: "Workflow / ITSM",
  WDAY: "HCM",
  INTU: "SMB / finance",
  HUBS: "Marketing",
  TEAM: "Developer collaboration",
  DOCU: "E-signature",
  ZM: "Meetings",
  ASAN: "Work management",
  MNDY: "Work management",
  PEGA: "BPM",
  NICE: "Contact center",
  SMAR: "Work management",
  BOX: "Content collaboration",
  DBX: "Content / storage",
  FRSH: "Customer support",
  BRZE: "Customer engagement",
  APPF: "Vertical SaaS",
  BILL: "AP/AR",
  PCTY: "Payroll / HCM",
  PAYC: "Payroll / HCM",
  DAY: "HCM",
  ADSK: "Design software",
  // Neutral infra
  PANW: "Network security",
  FTNT: "Network security",
  ZS: "Zero-trust security",
  OKTA: "Identity",
  QLYS: "Vulnerability management",
  TENB: "Vulnerability management",
  RBRK: "Data resilience",
  FROG: "Artifact management",
  TWLO: "Communications API",
  FSLY: "Edge / CDN",
  // Payments carve-out
  STNE: "Payments",
  PAGS: "Payments",
  DLO: "Cross-border payments",
  FLYW: "Payments",
  PAY: "Bill-pay",
  TOST: "Restaurant payments",
  FOUR: "Payment processing",
  NVEI: "Payment processing",
  RPAY: "Payment processing",
  EVTC: "Payment processing",
  RELY: "Remittance",
  MQ: "Card issuing",
  GPN: "Payment processing",
  GDOT: "Banking / cards",
  WEX: "Payment processing",
  AVDX: "AP payments",
}

const COHORT_SECTOR: Record<string, string> = {
  ai_native: "AI / data platform",
  exposed_incumbent: "SaaS",
  exposed_other: "SaaS",
  neutral_infra: "Infrastructure software",
  infra_other: "Infrastructure software",
  payments_fintech: "Payments / fintech",
  other: "Software",
}

const COHORT_SUB_FALLBACK: Record<string, string> = {
  ai_native: "AI product",
  exposed_incumbent: "Application software",
  exposed_other: "Application software",
  neutral_infra: "Infrastructure software",
  infra_other: "Infrastructure software",
  payments_fintech: "Payments",
  other: "Software",
}

export type CompanyIdentity = {
  ticker: string
  name: string
  sector: string
  subIndustry: string | null
  /** Single readable line: Name · Sector · Sub-industry */
  line: string
  /** One-line plain-English description under the identity line */
  description: string
}

const PRODUCT_BLURB: Record<string, string> = {
  FRSH: "Sells customer-support SaaS seats; AI automation is the main narrative threat to seat demand.",
  DOCU: "E-signature and agreement workflow SaaS; exposed to cheaper AI-assisted document flows.",
  PCTY: "Payroll / HCM SaaS for mid-market employers; base valuation case clears, conservative case does not.",
  WDAY: "Enterprise HCM / finance SaaS; watchlist because the conservative valuation lens fails.",
  MNDY: "Work-management SaaS; research candidate outside Table 20 — needs full underwriting.",
  PAYC: "Payroll / HCM SaaS peer; research candidate — check dilution, retention, and valuation refresh.",
  NICE: "Contact-center software; research candidate with moat-gate pass, not a paper survivor.",
  DBX: "Content / cloud storage SaaS; research candidate — thin live valuation gap.",
  APPF: "Vertical property-management SaaS; research candidate — MoS may be thin or negative.",
  BILL: "AP/AR automation with payments adjacency; research candidate — re-check carve-out risk.",
  CRM: "Enterprise CRM seats; large exposed incumbent in the paper's AI-threat cohort.",
  ADBE: "Creative-suite seats; exposed incumbent in the AI-threat cohort.",
  NOW: "Workflow / ITSM seats; exposed incumbent in the AI-threat cohort.",
}

export function companyName(c: SaasCompany): string {
  const name = (c as { live_name?: string | null }).live_name?.trim()
  return name || c.ticker
}

function descriptionFor(c: SaasCompany, sector: string, subIndustry: string | null): string {
  const ticker = c.ticker.toUpperCase()
  if (PRODUCT_BLURB[ticker]) return PRODUCT_BLURB[ticker]
  const note = (c.mgmt_note || "").trim()
  if (note) return note.length > 140 ? `${note.slice(0, 137)}…` : note
  const tier = (c.paper_tier || "").toLowerCase()
  if (tier.includes("tier1")) {
    return `${sector}${subIndustry ? ` · ${subIndustry}` : ""} — Paper Tier 1 survivor; qualifies for underwriting, not an automatic buy.`
  }
  if (tier.includes("tier2")) {
    return `${sector}${subIndustry ? ` · ${subIndustry}` : ""} — Paper Tier 2 watchlist; base case only.`
  }
  if (c.gates?.core_thesis_path || c.gates?.core_thesis_path_live) {
    return `${sector}${subIndustry ? ` · ${subIndustry}` : ""} — core-path research candidate; not a Table 20 survivor.`
  }
  return `${sector}${subIndustry ? ` · ${subIndustry}` : ""} — SaaS universe name under paper gates.`
}

export function companyIdentity(c: SaasCompany): CompanyIdentity {
  const ticker = c.ticker.toUpperCase()
  const name = companyName(c)
  const cohort = (c.cohort || "").toLowerCase()
  const sector = COHORT_SECTOR[cohort] || "SaaS"
  const subIndustry = SUB_INDUSTRY[ticker] || COHORT_SUB_FALLBACK[cohort] || null
  const parts = [name, sector]
  if (subIndustry && subIndustry.toLowerCase() !== sector.toLowerCase()) {
    parts.push(subIndustry)
  }
  return {
    ticker,
    name,
    sector,
    subIndustry,
    line: parts.join(" · "),
    description: descriptionFor(c, sector, subIndustry),
  }
}
