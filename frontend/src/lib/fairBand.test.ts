import { describe, expect, it } from "vitest"
import { fairBandLayout } from "@/lib/fairBand"

describe("fairBandLayout", () => {
  it("places price left of the band when undervalued", () => {
    const layout = fairBandLayout(90, 200, 250, 290)
    expect(layout).not.toBeNull()
    expect(layout!.zone).toBe("below")
    expect(layout!.zoneLabel).toBe("Below fair band")
    expect(layout!.pricePct!).toBeLessThan(layout!.bandLeft)
  })

  it("places price inside the band when between lo and hi", () => {
    const layout = fairBandLayout(240, 200, 250, 290)
    expect(layout!.zone).toBe("inside")
    expect(layout!.pricePct!).toBeGreaterThan(layout!.bandLeft)
    expect(layout!.pricePct!).toBeLessThan(layout!.bandLeft + layout!.bandWidth)
  })

  it("returns null when band is invalid", () => {
    expect(fairBandLayout(100, null, 120, 140)).toBeNull()
    expect(fairBandLayout(100, 200, 210, 190)).toBeNull()
  })
})
