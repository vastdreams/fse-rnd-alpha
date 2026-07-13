import { describe, expect, it } from "vitest"
import { resolveBuyViewMode } from "./universeBuyView"

describe("resolveBuyViewMode", () => {
  it("defaults to candidates so the table is not blank", () => {
    expect(resolveBuyViewMode(new URLSearchParams("mode=buy"))).toBe("candidates")
    expect(resolveBuyViewMode(new URLSearchParams())).toBe("candidates")
  })

  it("honors explicit cleared-BUY shortlist", () => {
    expect(resolveBuyViewMode(new URLSearchParams("mode=buy&cleared=1"))).toBe("cleared")
    expect(resolveBuyViewMode(new URLSearchParams("mode=buy&review=0"))).toBe("cleared")
  })

  it("keeps review=1 as candidates", () => {
    expect(resolveBuyViewMode(new URLSearchParams("mode=buy&review=1"))).toBe("candidates")
  })
})
