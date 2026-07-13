import { describe, expect, it } from "vitest"

import {
  appendUnallocatedHoldings,
  equalWeightHoldings,
  MAX_POSITION_WEIGHT_PCT,
} from "@/lib/bookOps"

describe("Book allocation helpers", () => {
  it("preserves intentional weights while appending research candidates", () => {
    const holdings = appendUnallocatedHoldings(
      ["NEW", "EXISTING"],
      [
        {
          ticker: "EXISTING",
          weight_pct: 12.5,
          added_at: "2026-07-13T00:00:00",
        },
      ]
    )

    expect(holdings).toEqual([
      {
        ticker: "EXISTING",
        weight_pct: 12.5,
        added_at: "2026-07-13T00:00:00",
      },
      expect.objectContaining({ ticker: "NEW", weight_pct: 0 }),
    ])
  })

  it("makes a sub-seven-name draft actionable without breaching 15%", () => {
    const holdings = equalWeightHoldings(
      ["ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX"]
    )

    expect(holdings).toHaveLength(6)
    expect(holdings.every((holding) => holding.weight_pct === MAX_POSITION_WEIGHT_PCT)).toBe(true)
    expect(holdings.reduce((sum, holding) => sum + holding.weight_pct, 0)).toBe(90)
  })

  it("keeps a seven-name equal-weight book within the cap", () => {
    const holdings = equalWeightHoldings([
      "ONE",
      "TWO",
      "THREE",
      "FOUR",
      "FIVE",
      "SIX",
      "SEVEN",
    ])

    expect(holdings.every((holding) => holding.weight_pct <= MAX_POSITION_WEIGHT_PCT)).toBe(true)
    expect(holdings.reduce((sum, holding) => sum + holding.weight_pct, 0)).toBeCloseTo(99.96)
  })
})
