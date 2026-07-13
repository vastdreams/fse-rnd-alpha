import { describe, expect, it } from "vitest"
import { aboveBandFlag } from "@/lib/aboveBandPolicy"

describe("aboveBandFlag (S5 option B)", () => {
  it("flags APP-class above-band rows", () => {
    const flag = aboveBandFlag({
      price_live: 506.98,
      fair_px_lo: 64.08,
      fair_px_hi: 93.84,
      vs_median_pct: -0.84,
    })
    expect(flag.active).toBe(true)
    expect(flag.label).toBe("Above fair band")
  })

  it("does not flag below-band KSPI-class rows", () => {
    const flag = aboveBandFlag({
      price_live: 89.67,
      fair_px_lo: 207.59,
      fair_px_hi: 291.96,
      vs_median_pct: 1.78,
    })
    expect(flag.active).toBe(false)
  })
})
