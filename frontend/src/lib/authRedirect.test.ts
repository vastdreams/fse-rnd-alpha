import { describe, expect, it } from "vitest"

import { dashboardNextPath, withDashboardNext } from "@/lib/authRedirect"

describe("dashboard auth return path", () => {
  it("preserves an internal versioned investor destination", () => {
    expect(dashboardNextPath("/app/company/MNDY?universe_version=univ_fixture")).toBe(
      "/app/company/MNDY?universe_version=univ_fixture"
    )
    expect(withDashboardNext("/register", "/app/book?book_id=book_fixture")).toBe(
      "/register?next=%2Fapp%2Fbook%3Fbook_id%3Dbook_fixture"
    )
  })

  it("rejects external and non-dashboard return paths", () => {
    expect(dashboardNextPath("//outside.example")).toBe("/app")
    expect(dashboardNextPath("https://outside.example")).toBe("/app")
    expect(dashboardNextPath("/portfolio")).toBe("/app")
  })
})
