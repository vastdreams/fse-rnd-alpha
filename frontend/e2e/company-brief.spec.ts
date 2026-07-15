import { expect, test } from "@playwright/test"

const SNAPSHOT_ID = "rpt_fixture0000000000000000"
const P1 = [
  "variant_perception",
  "business_model",
  "industry_map",
  "moat",
  "financial_trends",
  "thesis",
  "catalysts",
]
const P2 = [
  "consensus_vs_internal",
  "estimate_revisions",
  "management_governance",
  "gates_factor_context",
  "risks_falsification",
  "sizing",
  "methodology",
]

const section = (id: string, extra: Record<string, unknown> = {}) => ({
  section_id: id,
  title: id.replace(/_/g, " "),
  body: "Cited fixture narrative for this section.",
  cite_ids: ["A1"],
  metrics: [],
  scenarios: [],
  ...extra,
})

const report = {
  snapshot_id: SNAPSHOT_ID,
  ticker: "WIX",
  universe_version: "univ_fixture",
  template_version: "brief_2p_v1",
  engine_version: "report_builder_v1",
  created_at: "2026-07-15T08:00:00",
  as_of_date: "2026-07-15",
  status: "published",
  company_name: "Wix.com Ltd",
  exchange: "NASDAQ",
  sector: "Technology",
  industry: "Software - Infrastructure",
  stance: "BUY",
  price: 52.71,
  price_as_of: "2026-07-14",
  fair_px_lo: 101.51,
  fair_px_med: 121.96,
  fair_px_hi: 123.74,
  mos_live: 1.43,
  implied_ann_return: 0.3226,
  horizon_years: 3,
  market_cap: 2.94e9,
  page1: P1.map((id) =>
    id === "financial_trends"
      ? section(id, {
          metrics: [
            { label: "Revenue CAGR", value: 0.131, unit: "%", provenance: "sealed", cite_ids: ["S1"] },
            { label: "Net revenue retention", value: null, provenance: "sealed", cite_ids: [] },
          ],
        })
      : section(id)
  ),
  page2: P2.map((id) =>
    id === "consensus_vs_internal"
      ? section(id, {
          scenarios: [
            { name: "consensus", provenance: "licensed_consensus", fair_px: 95, cite_ids: ["S4"] },
          ],
        })
      : section(id)
  ),
  citations: [
    { cite_id: "S1", provenance: "sealed", title: "Sealed vector", locator: "metric_vectors:univ_fixture:WIX", cite_ids: [] },
    { cite_id: "S4", provenance: "licensed_consensus", title: "Consensus snapshot", locator: "consensus_snapshots:cons_x" },
    {
      cite_id: "A1",
      provenance: "analyst",
      title: "Wix 20-F FY2025",
      locator: "sec:0001628280-26-015222",
      url: "https://www.sec.gov/Archives/edgar/data/1576789/000162828026015222/wix-20251231.htm",
    },
  ],
  disclosures: ["Research only — not investment advice.", "Unknown means unknown."],
}

test("two-page brief renders exactly two A4 pages with resolved citations", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("fse_research_token", "test-token")
    localStorage.setItem(
      "fse_research_user",
      JSON.stringify({ id: "test-user", email: "investor@example.com", role: "user" })
    )
  })
  await page.route("**/api/analytics/**", (route) => route.fulfill({ status: 204 }))
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "test-user",
        email: "investor@example.com",
        role: "user",
        is_active: true,
        email_verified: true,
      }),
    })
  )
  await page.route(`**/api/reports/${SNAPSHOT_ID}`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        snapshot_id: SNAPSHOT_ID,
        status: "published",
        content_sha256: "a".repeat(64),
        reviewed_by: "cursor_final_review_agent",
        published_at: "2026-07-15T09:00:00",
        report,
        note: "Research only — not investment advice.",
      }),
    })
  )

  await page.goto(`/app/company/WIX/report/${SNAPSHOT_ID}`)

  // Exactly two A4 page containers, application chrome absent.
  await expect(page.getByTestId("report-document")).toBeVisible()
  await expect(page.locator(".report-page")).toHaveCount(2)
  await expect(page.locator("aside")).toHaveCount(0)

  // Renderer readiness contract.
  await expect.poll(() => page.evaluate(() => (window as never as { __REPORT_READY__?: boolean }).__REPORT_READY__)).toBe(true)

  // Header decision frame.
  await expect(page.getByTestId("report-header")).toContainText("BUY")
  await expect(page.getByTestId("report-header")).toContainText("univ_fixture")

  // Unknown stays Unknown; sealed metric renders with citation anchor.
  const finTrends = page.getByTestId("report-section-financial_trends")
  await expect(finTrends).toContainText("Unknown")
  await expect(finTrends).toContainText("13.1%")

  // Every citation reference resolves to a target in the citation list.
  const refIds = await page.locator('a.report-cite').evaluateAll((els) =>
    els.map((el) => (el.getAttribute("href") || "").replace("#", ""))
  )
  expect(refIds.length).toBeGreaterThan(0)
  for (const id of refIds) {
    await expect(page.locator(`#${id}`)).toHaveCount(1)
  }

  // Consensus scenario labeled as external.
  await expect(page.getByTestId("report-section-consensus_vs_internal")).toContainText("Consensus")

  // SVG fair-band chart present with street marker.
  await expect(page.getByTestId("fair-band-chart").locator("svg")).toHaveCount(1)
  await expect(page.getByTestId("fair-band-chart")).toContainText("Street $95")

  // No page overflows its fixed A4 container.
  const overflow = await page.evaluate(() =>
    [...document.querySelectorAll(".report-page")].map((el) => el.scrollHeight - el.clientHeight)
  )
  for (const delta of overflow) expect(delta).toBeLessThanOrEqual(1)

  // Print media hides the toolbar but keeps both pages.
  await page.emulateMedia({ media: "print" })
  await expect(page.locator(".report-toolbar")).toBeHidden()
  await expect(page.locator(".report-page")).toHaveCount(2)
})

test("mismatched ticker fails closed instead of showing another company's report", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("fse_research_token", "test-token")
    localStorage.setItem(
      "fse_research_user",
      JSON.stringify({ id: "test-user", email: "investor@example.com", role: "user" })
    )
  })
  await page.route("**/api/analytics/**", (route) => route.fulfill({ status: 204 }))
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "test-user",
        email: "investor@example.com",
        role: "user",
        is_active: true,
        email_verified: true,
      }),
    })
  )
  await page.route(`**/api/reports/${SNAPSHOT_ID}`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        snapshot_id: SNAPSHOT_ID,
        status: "published",
        content_sha256: "a".repeat(64),
        reviewed_by: null,
        published_at: null,
        report,
        note: "",
      }),
    })
  )

  await page.goto(`/app/company/TTD/report/${SNAPSHOT_ID}`)
  await expect(page.getByTestId("report-error")).toContainText("belongs to WIX")
  await expect(page.locator(".report-page")).toHaveCount(0)
})
