import { describe, expect, it } from "vitest"
import { PRIMARY_FACTOR_IDS, isPrimaryFactor } from "@/lib/universeFilters"
import { mosDiffersFromLiveGap } from "@/lib/rankRowInvariants"

type FilterRow = {
  vs_median_pct: number | null
  mos_live: number | null
}

/** Mirrors UniversePage factor predicates — keep in sync with FACTORS filters. */
function passesBelowTarget(r: FilterRow): boolean {
  return r.vs_median_pct != null && r.vs_median_pct > 0
}

function passesUndervaluedMos(r: FilterRow): boolean {
  return r.mos_live != null && r.mos_live > 0
}

describe("universeFilters", () => {
  it("keeps the default chip set short and investor-facing", () => {
    expect(PRIMARY_FACTOR_IDS).toEqual(["below_target", "mos_pos", "fresh"])
    expect(PRIMARY_FACTOR_IDS).toHaveLength(3)
    expect(isPrimaryFactor("below_target")).toBe(true)
    expect(isPrimaryFactor("rd_contrib")).toBe(false)
  })

  it("Below target uses live vs_median_pct; Undervalued uses frozen mos_live", () => {
    const synced = { vs_median_pct: 0.5, mos_live: 0.5 }
    expect(passesBelowTarget(synced)).toBe(true)
    expect(passesUndervaluedMos(synced)).toBe(true)
    expect(mosDiffersFromLiveGap(synced.mos_live, synced.vs_median_pct)).toBe(false)

    // Stale MoS vs live gap: filters can diverge — copy must stay distinct.
    const diverged = { vs_median_pct: 0.2, mos_live: -0.1 }
    expect(passesBelowTarget(diverged)).toBe(true)
    expect(passesUndervaluedMos(diverged)).toBe(false)
    expect(mosDiffersFromLiveGap(diverged.mos_live, diverged.vs_median_pct)).toBe(true)

    const overvaluedLive = { vs_median_pct: -0.8, mos_live: -0.8 }
    expect(passesBelowTarget(overvaluedLive)).toBe(false)
    expect(passesUndervaluedMos(overvaluedLive)).toBe(false)
  })
})
