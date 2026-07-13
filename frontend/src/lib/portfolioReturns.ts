/**
 * PATH: frontend/src/lib/portfolioReturns.ts
 * PURPOSE: Simply Wall St–style price / fair value / horizon return helpers.
 */

import type { SaasCompany } from "@/lib/api/saasPortfolio"

export function livePrice(c: SaasCompany): number | null {
  const live = (c as { live_price?: number | null }).live_price
  if (live != null && Number.isFinite(live)) return live
  return c.price ?? null
}

export function fairMed(c: SaasCompany): number | null {
  return c.fair_px_med ?? null
}

export function mosLive(c: SaasCompany): number | null {
  const live = (c as { live_mos?: number | null }).live_mos
  if (live != null && Number.isFinite(live)) return live
  return c.mos ?? null
}

/** Total upside if price converges to fair med (fraction). */
export function totalUpside(c: SaasCompany): number | null {
  const p = livePrice(c)
  const f = fairMed(c)
  if (p == null || f == null || p <= 0) return null
  return f / p - 1
}

/**
 * Implied annualised return if price converges to fair med over `years`.
 * Not a forecast — a valuation gap amortised over a horizon.
 */
export function cagrToFair(c: SaasCompany, years: number): number | null {
  const upside = totalUpside(c)
  if (upside == null || years <= 0) return null
  const multiple = 1 + upside
  if (multiple <= 0) return null
  return multiple ** (1 / years) - 1
}

export function fmtPct(x: number | null | undefined, digits = 0): string {
  if (x == null || !Number.isFinite(x)) return "—"
  return `${(x * 100).toFixed(digits)}%`
}

export function fmtMoney(x: number | null | undefined, digits = 2): string {
  if (x == null || !Number.isFinite(x)) return "—"
  return `$${x.toFixed(digits)}`
}

export function fmtUsdCompact(x?: number | null): string {
  if (x == null) return "—"
  if (x >= 1e9) return `$${(x / 1e9).toFixed(1)}B`
  if (x >= 1e6) return `$${(x / 1e6).toFixed(0)}M`
  return `$${x.toFixed(0)}`
}

/** Near-zero gaps stay neutral; only materially negative figures use rose. */
export function toneReturn(x?: number | null): string {
  if (x == null) return "text-foreground"
  if (x < -0.005) return "text-rose-800"
  return "text-foreground"
}

export function equalWeightPortfolioStats(companies: SaasCompany[]) {
  const upsides = companies.map(totalUpside).filter((x): x is number => x != null)
  const mos = companies.map(mosLive).filter((x): x is number => x != null)
  const avg = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null)
  const med = (xs: number[]) => {
    if (!xs.length) return null
    const s = [...xs].sort((a, b) => a - b)
    const hi = Math.floor(s.length / 2)
    const lo = Math.floor((s.length - 1) / 2)
    return (s[lo] + s[hi]) / 2
  }
  const avgUpside = avg(upsides)
  const portfolioCagr3y =
    avgUpside != null && 1 + avgUpside > 0 ? (1 + avgUpside) ** (1 / 3) - 1 : null
  return {
    n: companies.length,
    weight: companies.length ? 1 / companies.length : 0,
    nValued: upsides.length,
    avgUpside,
    medianMos: med(mos),
    avgCagr3y: portfolioCagr3y,
  }
}
