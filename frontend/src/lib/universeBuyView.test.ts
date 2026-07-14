import { describe, expect, it } from "vitest"
import { resolveBuyViewMode } from "./universeBuyView"

describe("resolveBuyViewMode", () => {
  it("defaults plain /app to the strata decision surface", () => {
    expect(resolveBuyViewMode(new URLSearchParams("mode=buy"))).toBe("strata")
    expect(resolveBuyViewMode(new URLSearchParams())).toBe("strata")
  })

  it("honors explicit cleared-BUY shortlist deep links", () => {
    expect(resolveBuyViewMode(new URLSearchParams("mode=buy&cleared=1"))).toBe("cleared")
    expect(resolveBuyViewMode(new URLSearchParams("mode=buy&review=0"))).toBe("cleared")
  })

  it("keeps review=1 as the classic candidates table", () => {
    expect(resolveBuyViewMode(new URLSearchParams("mode=buy&review=1"))).toBe("candidates")
  })
})
