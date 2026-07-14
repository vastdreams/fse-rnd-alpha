/**
 * First-principles invariants for ranked Universe rows.
 *
 * These are machine-checkable contracts — not ad-hoc screenshots or
 * one-off CDP math. Call `auditRankRow` on fixtures or live API payloads;
 * any returned violation is a break.
 */

export type RankRowNumbers = {
  ticker?: string
  price_live?: number | null
  fair_px_lo?: number | null
  fair_px_med?: number | null
  fair_px_hi?: number | null
  mos_live?: number | null
  vs_median_pct?: number | null
  revenue_usd?: number | null
  score?: number | null
  contributions?: Record<string, number> | null
}

export type RankViolationCode =
  | "VS_MEDIAN_MISMATCH"
  | "FAIR_BAND_ORDER"
  | "FAIR_BAND_ZONE_CONTRADICTION"
  | "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET"
  | "SCORE_WITHOUT_DRIVERS"
  | "NON_FINITE_METRIC"

export type RankViolation = {
  code: RankViolationCode
  ticker?: string
  detail: string
}

const EPS = 1e-6
const MOS_UI_EPS = 0.005

function finite(n: number | null | undefined): n is number {
  return n != null && Number.isFinite(n)
}

/** Live quote gap: (target − price) / price. */
export function computeLiveVsTargetPct(
  price: number | null | undefined,
  fairMed: number | null | undefined
): number | null {
  if (!finite(price) || !finite(fairMed) || price <= 0) return null
  return (fairMed - price) / price
}

/**
 * True when frozen MoS disagrees with the live quote gap enough that the UI
 * should surface MoS separately. When false, showing both is a trust bug.
 */
export function mosDiffersFromLiveGap(
  mos: number | null | undefined,
  vs: number | null | undefined,
  eps = MOS_UI_EPS
): boolean {
  if (mos == null || !Number.isFinite(mos)) return false
  if (vs == null || !Number.isFinite(vs)) return true
  return Math.abs(mos - vs) >= eps
}

export function fairBandZone(
  price: number | null | undefined,
  lo: number | null | undefined,
  hi: number | null | undefined
): "below" | "inside" | "above" | "unknown" {
  // lo == hi is a legal degenerate band; only inverted bands are unknown.
  if (!finite(price) || !finite(lo) || !finite(hi) || lo > hi) return "unknown"
  if (price < lo) return "below"
  if (price > hi) return "above"
  return "inside"
}

/**
 * Audit one ranked row. Returns [] when first-principles contracts hold.
 */
export function auditRankRow(row: RankRowNumbers, eps = EPS): RankViolation[] {
  const violations: RankViolation[] = []
  const ticker = row.ticker

  const numericFields: Array<[string, number | null | undefined]> = [
    ["price_live", row.price_live],
    ["fair_px_lo", row.fair_px_lo],
    ["fair_px_med", row.fair_px_med],
    ["fair_px_hi", row.fair_px_hi],
    ["mos_live", row.mos_live],
    ["vs_median_pct", row.vs_median_pct],
    ["revenue_usd", row.revenue_usd],
    ["score", row.score],
  ]
  for (const [name, v] of numericFields) {
    if (v != null && !Number.isFinite(v)) {
      violations.push({
        code: "NON_FINITE_METRIC",
        ticker,
        detail: `${name} is non-finite (${String(v)})`,
      })
    }
  }

  const expectedVs = computeLiveVsTargetPct(row.price_live, row.fair_px_med)
  if (expectedVs != null && finite(row.vs_median_pct)) {
    if (Math.abs(expectedVs - row.vs_median_pct) > eps) {
      violations.push({
        code: "VS_MEDIAN_MISMATCH",
        ticker,
        detail: `vs_median_pct=${row.vs_median_pct} but (target−price)/price=${expectedVs}`,
      })
    }
  }

  if (finite(row.fair_px_lo) && finite(row.fair_px_med) && finite(row.fair_px_hi)) {
    if (!(row.fair_px_lo <= row.fair_px_med && row.fair_px_med <= row.fair_px_hi)) {
      violations.push({
        code: "FAIR_BAND_ORDER",
        ticker,
        detail: `fair band not ordered lo≤med≤hi (${row.fair_px_lo}, ${row.fair_px_med}, ${row.fair_px_hi})`,
      })
    }
  }

  const zone = fairBandZone(row.price_live, row.fair_px_lo, row.fair_px_hi)
  if (zone === "below" && finite(row.vs_median_pct) && row.vs_median_pct <= 0) {
    violations.push({
      code: "FAIR_BAND_ZONE_CONTRADICTION",
      ticker,
      detail: `price below fair band but vs_median_pct=${row.vs_median_pct} is not positive`,
    })
  }
  if (zone === "above" && finite(row.vs_median_pct) && row.vs_median_pct >= 0) {
    violations.push({
      code: "FAIR_BAND_ZONE_CONTRADICTION",
      ticker,
      detail: `price above fair band but vs_median_pct=${row.vs_median_pct} is not negative`,
    })
  }

  // MoS is fair_med/price − 1 when defined the same way as live gap.
  // A positive MoS while trading above target is a first-principles break.
  if (finite(row.mos_live) && finite(row.price_live) && finite(row.fair_px_med)) {
    const aboveTarget = row.price_live > row.fair_px_med
    const belowTarget = row.price_live < row.fair_px_med
    if (aboveTarget && row.mos_live > eps) {
      violations.push({
        code: "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET",
        ticker,
        detail: `mos_live=${row.mos_live} > 0 while price ${row.price_live} > target ${row.fair_px_med}`,
      })
    }
    if (belowTarget && row.mos_live < -eps) {
      violations.push({
        code: "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET",
        ticker,
        detail: `mos_live=${row.mos_live} < 0 while price ${row.price_live} < target ${row.fair_px_med}`,
      })
    }
  }

  if (finite(row.score) && row.score !== 0) {
    const contribs = row.contributions ?? {}
    const hasDriver = Object.values(contribs).some((v) => Number.isFinite(v) && v !== 0)
    if (!hasDriver) {
      violations.push({
        code: "SCORE_WITHOUT_DRIVERS",
        ticker,
        detail: `score=${row.score} but contributions are empty/zero`,
      })
    }
  }

  return violations
}

/** Audit a batch; fails closed with every violation across rows. */
export function auditRankRows(rows: RankRowNumbers[], eps = EPS): RankViolation[] {
  return rows.flatMap((row) => auditRankRow(row, eps))
}

/** Format violations for CI logs. */
export function formatRankViolations(violations: RankViolation[]): string {
  if (violations.length === 0) return "ok"
  return violations.map((v) => `[${v.code}] ${v.ticker ?? "?"} — ${v.detail}`).join("\n")
}
