/**
 * PATH: frontend/src/lib/sellCeiling.ts
 * PURPOSE: First-principles auto-sell ceiling from the research fair-value
 * band vs live price, with the same hold-horizon rule as close_call_service.
 *
 * Definitions (pure maths — not a forecast):
 *   - Band: fair_px_lo ≤ fair_px_med (price target) ≤ fair_px_hi
 *   - Auto-sell: exit when live reaches the research target (median).
 *     If live is already ≥ median but still < high, auto-sell steps up to
 *     the hard band ceiling (high) — trim zone, not a new thesis.
 *   - Hold horizon H: same gap buckets as stance (1y / 2y / 3y).
 *   - Remaining ann. if gap to ceil closes over H: (ceil/live)^(1/H) − 1
 */

import { formatPercent4, formatUsd4 } from "@/lib/formatMetrics"

export type SellZone = "to_target" | "in_upper_band" | "past_ceiling" | "unknown"

export type SellCeiling = {
  /** Price that triggers the research auto-sell / trim */
  sell_ceil: number | null
  /** Which lens is the auto-sell */
  lens: "median" | "high" | null
  fair_lo: number | null
  fair_med: number | null
  fair_hi: number | null
  live: number | null
  /** (sell_ceil / live) − 1 ; null if unknown or live≤0 */
  upside_to_ceil: number | null
  /** Hold horizon years from remaining upside (same buckets as stance) */
  horizon_years: 1 | 2 | 3 | null
  /** (1 + upside)^(1/H) − 1 */
  remaining_ann: number | null
  zone: SellZone
  /** One-line for tooltips / copy */
  note: string
}

/** Same buckets as backend close_call_service horizon selection. */
export function holdHorizonYears(gap: number | null | undefined): 1 | 2 | 3 | null {
  if (gap == null || !Number.isFinite(gap) || gap <= 0) return null
  if (gap >= 0.6) return 3
  if (gap >= 0.25) return 2
  return 1
}

export function annualizedFromPrices(live: number, target: number, years: number): number | null {
  if (!(live > 0) || !(target > 0) || !(years > 0)) return null
  return Math.pow(target / live, 1 / years) - 1
}

/**
 * Compute the auto-sell ceiling for a row.
 * Prefer stanceHorizon when provided (BUY/HOLD already chose H); otherwise
 * derive H from remaining upside to the chosen ceiling.
 */
export function computeSellCeiling(input: {
  fair_px_lo?: number | null
  fair_px_med?: number | null
  fair_px_hi?: number | null
  price_live?: number | null
  /** Optional override from stance aggregate */
  stanceHorizon?: 1 | 2 | 3 | null
}): SellCeiling {
  const lo = input.fair_px_lo ?? null
  const med = input.fair_px_med ?? null
  const hi = input.fair_px_hi ?? null
  const live = input.price_live ?? null

  const base: SellCeiling = {
    sell_ceil: null,
    lens: null,
    fair_lo: lo,
    fair_med: med,
    fair_hi: hi,
    live,
    upside_to_ceil: null,
    horizon_years: null,
    remaining_ann: null,
    zone: "unknown",
    note: "Fair-value band or live price missing — sell ceiling unknown.",
  }

  if (med == null || !(med > 0) || live == null || !(live > 0)) return base

  let sell_ceil: number
  let lens: "median" | "high"
  let zone: SellZone

  if (live < med) {
    sell_ceil = med
    lens = "median"
    zone = "to_target"
  } else if (hi != null && hi > 0 && live < hi) {
    sell_ceil = hi
    lens = "high"
    zone = "in_upper_band"
  } else if (hi != null && hi > 0 && live >= hi) {
    sell_ceil = hi
    lens = "high"
    zone = "past_ceiling"
  } else {
    // No high lens — at/above median counts as target reached
    sell_ceil = med
    lens = "median"
    zone = live >= med ? "past_ceiling" : "to_target"
  }

  const upside = sell_ceil / live - 1
  const horizon =
    zone === "past_ceiling"
      ? null
      : input.stanceHorizon ?? holdHorizonYears(upside > 0 ? upside : null)
  const remaining_ann =
    zone === "past_ceiling" || horizon == null || upside <= 0
      ? null
      : annualizedFromPrices(live, sell_ceil, horizon)

  let note: string
  if (zone === "to_target") {
    note = `Auto-sell at median price target ${formatUsd4(sell_ceil)} (research MoS→0).`
  } else if (zone === "in_upper_band") {
    note = `Past median target — trim ceiling at high lens ${formatUsd4(sell_ceil)}.`
  } else {
    note = `Live is at/above the research band high — past sell ceiling.`
  }

  return {
    sell_ceil,
    lens,
    fair_lo: lo,
    fair_med: med,
    fair_hi: hi,
    live,
    upside_to_ceil: upside,
    horizon_years: horizon,
    remaining_ann,
    zone,
    note,
  }
}

export function fmtSellUpside(u: number | null | undefined): string {
  return formatPercent4(u, true)
}

export function fmtSellAnn(r: number | null | undefined): string {
  const rate = formatPercent4(r, true)
  return rate === "—" ? rate : `${rate}/yr`
}
