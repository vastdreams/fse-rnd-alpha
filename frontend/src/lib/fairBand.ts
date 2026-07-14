/**
 * Simply Wall St–style fair-value band geometry.
 * Maps price / lo / med / hi onto a 0–100% track for the visual gauge.
 */

export type FairBandZone = "below" | "inside" | "above" | "unknown"

export type FairBandLayout = {
  bandLeft: number
  bandWidth: number
  pricePct: number | null
  medPct: number | null
  zone: FairBandZone
  zoneLabel: string
}

function clamp(n: number, lo = 0, hi = 100): number {
  return Math.max(lo, Math.min(hi, n))
}

export function fairBandLayout(
  price: number | null | undefined,
  lo: number | null | undefined,
  med: number | null | undefined,
  hi: number | null | undefined
): FairBandLayout | null {
  // lo == hi is a legal degenerate band (all lenses agree); only reject inverted bands.
  if (lo == null || hi == null || !Number.isFinite(lo) || !Number.isFinite(hi) || lo > hi) {
    return null
  }

  const values = [lo, hi]
  if (price != null && Number.isFinite(price)) values.push(price)
  if (med != null && Number.isFinite(med)) values.push(med)

  const min = Math.min(...values)
  const max = Math.max(...values)
  const pad = Math.max((max - min) * 0.12, (hi - lo) * 0.05, 0.01)
  const start = min - pad
  const end = max + pad
  const span = end - start
  const pct = (v: number) => clamp(((v - start) / span) * 100)

  const priceOk = price != null && Number.isFinite(price)
  let zone: FairBandZone = "unknown"
  let zoneLabel = "Fair band unavailable"
  if (priceOk) {
    if (price < lo) {
      zone = "below"
      zoneLabel = "Below fair band"
    } else if (price > hi) {
      zone = "above"
      zoneLabel = "Above fair band"
    } else {
      zone = "inside"
      zoneLabel = "Inside fair band"
    }
  }

  return {
    bandLeft: pct(lo),
    bandWidth: Math.max(pct(hi) - pct(lo), 2),
    pricePct: priceOk ? pct(price) : null,
    medPct: med != null && Number.isFinite(med) ? pct(med) : null,
    zone,
    zoneLabel,
  }
}
