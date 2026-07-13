/**
 * PATH: frontend/src/lib/sellCeiling.test.ts
 */
import { describe, expect, it } from "vitest"
import { computeSellCeiling, fmtSellUpside, holdHorizonYears } from "@/lib/sellCeiling"

describe("holdHorizonYears", () => {
  it("buckets like close_call_service", () => {
    expect(holdHorizonYears(0.1)).toBe(1)
    expect(holdHorizonYears(0.25)).toBe(2)
    expect(holdHorizonYears(0.6)).toBe(3)
    expect(holdHorizonYears(0)).toBeNull()
  })
})

describe("computeSellCeiling", () => {
  it("auto-sells at median when below target", () => {
    const s = computeSellCeiling({
      fair_px_lo: 80,
      fair_px_med: 100,
      fair_px_hi: 130,
      price_live: 80,
    })
    expect(s.zone).toBe("to_target")
    expect(s.lens).toBe("median")
    expect(s.sell_ceil).toBe(100)
    expect(s.upside_to_ceil).toBeCloseTo(0.25)
    expect(s.horizon_years).toBe(2)
    expect(s.remaining_ann).not.toBeNull()
    expect(s.note).toContain("$100")
  })

  it("comma-groups large sell ceilings in the explanation", () => {
    const s = computeSellCeiling({
      fair_px_lo: 800_000_000,
      fair_px_med: 1_234_567_890,
      fair_px_hi: 1_500_000_000,
      price_live: 800_000_000,
    })
    expect(s.note).toContain("$1,235,000,000")
  })

  it("steps to high lens in upper band", () => {
    const s = computeSellCeiling({
      fair_px_lo: 80,
      fair_px_med: 100,
      fair_px_hi: 130,
      price_live: 110,
    })
    expect(s.zone).toBe("in_upper_band")
    expect(s.lens).toBe("high")
    expect(s.sell_ceil).toBe(130)
  })

  it("marks past ceiling above high", () => {
    const s = computeSellCeiling({
      fair_px_lo: 80,
      fair_px_med: 100,
      fair_px_hi: 130,
      price_live: 140,
    })
    expect(s.zone).toBe("past_ceiling")
    expect(s.horizon_years).toBeNull()
  })
})

describe("fmtSellUpside", () => {
  it("formats remaining upside with a percent sign", () => {
    expect(fmtSellUpside(0.25)).toBe("+25%")
    expect(fmtSellUpside(null)).toBe("—")
  })
})
