import { expect, test } from "@playwright/test"

const universeVersion = "univ_2026-07-13_company_test"
const asOf = "2026-07-12"

const metric = (value: number | null = null) => ({
  value,
  as_of_date: asOf,
  available_date: asOf,
  claim_ids: value === null ? [] : ["claim-test"],
  formula: "test fixture",
  engine_version: "test",
})

const metricKeys = [
  "retention",
  "concentration",
  "offering_quality_z",
  "fair_px_lo",
  "fair_px_med",
  "fair_px_hi",
  "mos_snapshot",
  "mos_live",
  "rd_int",
  "rd_gp",
  "rd_mom",
  "rd_capital",
  "rd_prod",
  "rd_cap_to_ev",
  "gm",
  "fcfm_sbc",
  "roic",
  "rule40",
  "sbc_intensity",
  "rev_cagr",
  "dilution_ann",
  "runway_yrs",
  "ret_1m",
  "ret_3m",
  "ret_12m",
  "drawdown_from_peak",
  "ai_text_stance",
  "float_fcf_share",
]

const vector = {
  ...Object.fromEntries(metricKeys.map((key) => [key, metric()])),
  ticker: "MNDY",
  universe_version: universeVersion,
  computed_at: "2026-07-13T00:00:00Z",
  fair_px_lo: metric(160),
  fair_px_med: metric(220),
  fair_px_hi: metric(260),
  mos_snapshot: metric(0.2),
  mos_live: metric(0.22),
  rd_prod: metric(1.4),
  gm: metric(0.9),
  fcfm_sbc: metric(0.1),
  roic: metric(0.2),
  rule40: metric(0.4),
  ret_12m: metric(0.3),
  product_map_complete: true,
  competitor_set_n: 4,
  table20_pass_count: 12,
  kill_active: false,
  cohort: "SaaS",
  carve_out: false,
  route: "fcf_positive",
  completeness: {
    grade: "A",
    filing_fetched: true,
    claims_n: 1,
    dcf_reproducible: true,
    overlay_fill_rate: 1,
    competitor_map_filled: true,
    asof_freshness_days: 10,
    stale: false,
  },
}

test("renders Company Research from the URL-pinned universe version", async ({ page }) => {
  let companyRequestUrl = ""
  let dcfRequests = 0
  let memoSaved = false
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
  await page.route("**/api/books", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ books: [] }) })
  )
  await page.route("**/api/universe/company/MNDY**", async (route) => {
    companyRequestUrl = route.request().url()
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ticker: "MNDY",
        universe_version: universeVersion,
        identity: { name: "monday.com", industry: "Software - Application" },
        profile: {
          name: "monday.com",
          description: "Work management software.",
          price_live: 180,
          price_as_of: asOf,
          price_source: "Sharadar SEP adjusted close",
          price_stale: false,
        },
        valuation_range: {
          fair_px_lo: 160,
          fair_px_med: 220,
          fair_px_hi: 260,
          price_snapshot: 180,
          price_live: 180,
          price_as_of: asOf,
          price_source: "Sharadar SEP adjusted close",
          fair_value_source: "Frozen universe vector",
          invalid_band: false,
          mos_snapshot: 0.2,
          quadrant: null,
          cohort: "SaaS",
          wave: null,
          rev_cagr: 0.3,
          wacc: 0.1,
          zone: "between conservative and median lens",
          gap_to_median: 0.22,
          note: "Test valuation lenses.",
        },
        close_call_waterfall: null,
        vector,
        gates: [],
        deepseek_runs: [],
        final_review: null,
        reviewer_passed: true,
        dcf_runs: [],
      }),
    })
  })
  await page.route("**/api/universe/financials/MNDY", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ ticker: "MNDY", annual: [], quarterly: [], note: "test" }),
    })
  )
  await page.route("**/api/universe/price-history/MNDY**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ticker: "MNDY",
        source: "Sharadar SEP adjusted close",
        fetched_at: "2026-07-13T00:00:00Z",
        price_as_of: asOf,
        price_source: "Sharadar SEP adjusted close",
        cache_stale: false,
        n: 0,
        start: asOf,
        end: asOf,
        last: 180,
        bars: [],
        note: "test",
      }),
    })
  )
  await page.route("**/api/universe/dcf/MNDY**", async (route) => {
    dcfRequests += 1
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "dcf-test-run",
        universe_version: universeVersion,
        inputs: { ticker: "MNDY", scenario: "custom", growth: 0.12, wacc: 0.1, terminal_g: 0.03 },
        outputs: {
          ev_dcf_fcf: null,
          ev_dcf_norm: 4000,
          ev_mult: null,
          fair_px_lo: 160,
          fair_px_med: 220,
          fair_px_hi: 260,
          mos: 0.22,
          engine_version: "test",
        },
      }),
    })
  })
  await page.route("**/api/universe/audit-pack/MNDY**", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ ticker: "MNDY", watermark: {} }) })
  )
  await page.route("**/api/universe/memo/MNDY**", async (route) => {
    if (route.request().method() === "POST") {
      memoSaved = true
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ memo_id: "memo-test", version: 1, universe_version: universeVersion }),
      })
      return
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        universe_version: universeVersion,
        memos: memoSaved
          ? [
              {
                memo_id: "memo-test",
                version: 1,
                thesis: "Filing-backed test thesis.",
                risks: null,
                created_at: "2026-07-13T00:00:00Z",
                analyst_judgment_ack: false,
                citations: ["claim-test"],
                citation_records: [{ claim_id: "claim-test", value_text: "fixture evidence", excerpt_locator: "item-7" }],
              },
            ]
          : [],
      }),
    })
  })

  await page.goto(`/app/company/MNDY?universe_version=${universeVersion}`)

  await expect(page.getByText("MNDY", { exact: true }).first()).toBeVisible()
  await expect(page.getByRole("button", { name: /Vs price target/ })).toBeVisible()
  await expect(page.getByRole("button", { name: "Stance · Unknown", exact: true })).toBeVisible()
  await expect(page.getByRole("rowheader", { name: "Quote (as-of)" })).toBeVisible()
  await expect(page.getByText(/Frozen universe vector/).first()).toBeVisible()
  await expect.poll(() => companyRequestUrl).toContain(`universe_version=${universeVersion}`)

  await page.getByRole("button", { name: "Valuation", exact: true }).click()
  await expect(page.getByText("DCF workbench (saved, reproducible runs)")).toBeVisible()
  await page.getByRole("button", { name: "Run + save scenario" }).click()
  await expect.poll(() => dcfRequests).toBe(1)
  await expect(page.getByText("Fair px median")).toBeVisible()

  await page.getByRole("button", { name: "Stance · Unknown", exact: true }).click()
  await expect(page.getByText("Close-call waterfall unavailable for this ticker.")).toBeVisible()

  await page.getByRole("button", { name: "Financials", exact: true }).click()
  await expect(page.getByText(/Current overlay from Sharadar SF1/)).toBeVisible()

  await page.getByRole("button", { name: "Business", exact: true }).click()
  await expect(page.getByText("Disclosure status")).toBeVisible()

  await page.getByRole("button", { name: "Research scores", exact: true }).click()
  await expect(page.getByText("R&D Alpha constructs (Paper-1)")).toBeVisible()

  await page.getByRole("button", { name: "Audit", exact: true }).click()
  const auditDownload = page.waitForEvent("download")
  await page.getByRole("button", { name: "Export audit pack (watermarked JSON)" }).click()
  await expect((await auditDownload).suggestedFilename()).toBe("MNDY_audit_pack.json")

  await page.getByRole("button", { name: "Memo", exact: true }).click()
  await page.getByPlaceholder("Thesis…").fill("Filing-backed test thesis.")
  await page.getByRole("button", { name: "claim-test", exact: true }).click()
  await page.getByRole("button", { name: "Save version" }).click()
  await expect(page.getByText("Filing-backed test thesis.")).toBeVisible()
})
