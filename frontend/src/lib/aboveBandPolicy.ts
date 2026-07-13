/**
 * Above-fair-band policy for R3 What-to-Buy survivors.
 *
 * Product decision (S5): Option B — allow above-band names to remain ranked,
 * but surface an explicit investor-visible warning. Never silent contradiction.
 */

import { fairBandZone } from "@/lib/rankRowInvariants"

export type AboveBandPolicy = "flag" // Option B

export const ABOVE_BAND_POLICY: AboveBandPolicy = "flag"

export type AboveBandFlag = {
  active: boolean
  label: string
  detail: string
}

export function aboveBandFlag(row: {
  price_live?: number | null
  fair_px_lo?: number | null
  fair_px_hi?: number | null
  vs_median_pct?: number | null
}): AboveBandFlag {
  const zone = fairBandZone(row.price_live, row.fair_px_lo, row.fair_px_hi)
  if (zone !== "above") {
    return { active: false, label: "", detail: "" }
  }
  return {
    active: true,
    label: "Above fair band",
    detail:
      "Price is above the research fair-value high. Rank/score may still be high on quality axes — this is not a value gap. Policy: flag (not auto-exclude).",
  }
}
