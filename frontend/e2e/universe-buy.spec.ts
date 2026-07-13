import { expect, test } from "@playwright/test"

const universeVersion = "univ_2026-07-13_test"

const rows = [
  {
    ticker: "MNDY",
    recipe_id: "R3",
    universe_version: universeVersion,
    rank: 1,
    score: 92.5,
    contributions: { mos_live: 0.8, rd_prod: 0.5 },
    completeness_grade: "A",
    freshness_ok: true,
    kill_active: false,
    reviewer_passed: true,
    name: "monday.com",
    industry: "Software - Application",
    fair_px_lo: 160,
    fair_px_med: 220,
    fair_px_hi: 260,
    price_live: 180,
    price_as_of: "2026-07-12",
    price_source: "cached_daily_history",
    price_is_derived: true,
    price_stale: true,
    mos_live: 0.22,
    vs_median_pct: 0.22,
    retention: 1.1,
    rev_cagr: 0.3,
    fcfm_sbc: 0.1,
    gm: 0.9,
    roic: 0.2,
    rd_int: 0.2,
    rd_prod: 1.4,
    revenue_usd: 1_000_000_000,
    fundamentals_as_of: "2025-12-31",
  },
]

test("renders a non-empty What-to-Buy view after rank and stance data load", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("fse_research_token", "test-token")
    localStorage.setItem(
      "fse_research_user",
      JSON.stringify({ id: "test-user", email: "investor@example.com", role: "user" })
    )
  })

  await page.route("**/api/analytics/**", async (route) => {
    await route.fulfill({ status: 204 })
  })
  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "test-user",
        email: "investor@example.com",
        role: "user",
        is_active: true,
        email_verified: true,
      }),
    })
  })
  await page.route("**/api/books", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ books: [] }) })
  })
  await page.route("**/api/universe/rank**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        recipe: {
          recipe_id: "R3",
          name: "Research desk",
          formula_human: "Test formula",
          formula_exact: "test",
          hard_filters: [],
          axes: [],
          benchmark_vs: "test",
          custom: false,
        },
        universe_version: universeVersion,
        n_universe: 1,
        n_ranked: 1,
        rows,
        note: "Research only",
      }),
    })
  })
  await page.route("**/api/universe/stances**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        universe_version: universeVersion,
        stance_filter: null,
        n_universe: 1,
        n_analyzed: 1,
        n: 1,
        rows: [
          {
            ticker: "MNDY",
            stance: "BUY",
            confidence: "high",
            score: 92.5,
            horizon_years: 2,
            implied_ann_return: 0.1,
            horizon_note: "Test only",
            blockers: [],
            watermark: "Research only",
          },
        ],
        note: "Research only",
      }),
    })
  })

  await page.goto("/app/universe?mode=buy")

  await expect(page.getByText(/What to Buy — top 1 matching cleared BUY/)).toBeVisible()
  await expect(page.getByText("MNDY", { exact: true }).first()).toBeVisible()
  await expect(page.getByText("BUY", { exact: true }).first()).toBeVisible()
  await expect(page.getByText("Research price basis", { exact: true })).toBeVisible()
  await expect(page.getByText("quote stale")).toBeVisible()
})

test("applies shortlist filters and sorting to selection and CSV export", async ({ page }) => {
  const shortlist = [
    { ...rows[0], ticker: "MNDY", score: 90, mos_live: 0.22, retention: 1.1 },
    {
      ...rows[0],
      ticker: "ADBE",
      name: "Adobe",
      score: 95,
      mos_live: 0.1,
      vs_median_pct: 0.1,
      retention: null,
    },
  ]
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
  await page.route("**/api/universe/rank**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        recipe: {
          recipe_id: "R3",
          name: "Research desk",
          formula_human: "Test formula",
          formula_exact: "test",
          hard_filters: [],
          axes: [],
          benchmark_vs: "test",
          custom: false,
        },
        universe_version: universeVersion,
        n_universe: shortlist.length,
        n_ranked: shortlist.length,
        rows: shortlist,
        note: "Research only",
      }),
    })
  )
  await page.route("**/api/universe/stances**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        universe_version: universeVersion,
        stance_filter: null,
        n_universe: shortlist.length,
        n_analyzed: shortlist.length,
        n: shortlist.length,
        rows: shortlist.map((row) => ({
          ticker: row.ticker,
          stance: "BUY",
          confidence: "high",
          score: row.score,
          horizon_years: 2,
          implied_ann_return: 0.1,
          horizon_note: "Test only",
          blockers: [],
          watermark: "Research only",
        })),
        note: "Research only",
      }),
    })
  )

  await page.goto("/app/universe?mode=buy")
  const companyLinks = page.locator('a[href^="/app/company/"]')
  await expect(companyLinks.first()).toHaveText("ADBE")
  await page.getByRole("button", { name: "MoS", exact: true }).click()
  await expect(companyLinks.first()).toHaveText("MNDY")

  await page.getByRole("button", { name: "Retention disclosed", exact: true }).click()
  await expect(page.getByText("ADBE", { exact: true })).toHaveCount(0)
  await expect(page.getByRole("checkbox", { name: "Select MNDY" })).toBeChecked()

  const downloadPromise = page.waitForEvent("download")
  await page.getByRole("button", { name: "Export CSV", exact: true }).click()
  const download = await downloadPromise
  const stream = await download.createReadStream()
  if (!stream) throw new Error("Expected CSV download stream")
  let csv = ""
  for await (const chunk of stream) csv += String(chunk)
  expect(csv).toContain("MNDY")
  expect(csv).not.toContain("ADBE")
})

test("keeps the newest mode response and discloses derived stale quotes", async ({ page }) => {
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
  await page.route("**/api/universe/rank**", async (route) => {
    const requestUrl = new URL(route.request().url())
    const recipeId = requestUrl.searchParams.get("recipe_id")
    const isSlowBuy = recipeId === "R3"
    if (isSlowBuy) await new Promise((resolve) => setTimeout(resolve, 350))
    const ticker = isSlowBuy ? "SLOW" : "FAST"
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        recipe: {
          recipe_id: recipeId,
          name: "Test recipe",
          formula_human: "Test",
          formula_exact: "test",
          hard_filters: [],
          axes: [],
          benchmark_vs: "test",
          custom: false,
        },
        universe_version: universeVersion,
        n_universe: 1,
        n_ranked: 1,
        rows: [
          {
            ...rows[0],
            ticker,
            recipe_id: recipeId,
            price_is_derived: !isSlowBuy,
            price_stale: !isSlowBuy,
            price_change_pct: 0.025,
          },
        ],
        note: "Research only",
      }),
    })
  })
  await page.route("**/api/universe/stances**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        universe_version: universeVersion,
        stance_filter: null,
        n_universe: 0,
        n_analyzed: 0,
        n: 0,
        rows: [],
        note: "Research only",
      }),
    })
  )

  await page.goto("/app/universe?mode=buy")
  await page.getByRole("button", { name: /R&D Alpha ETF/ }).click()
  await expect(page.getByText("FAST", { exact: true }).first()).toBeVisible()
  await expect(page.getByText("research price basis")).toBeVisible()
  await expect(page.getByText(/stale/).first()).toBeVisible()
  await page.waitForTimeout(450)
  await expect(page.getByText("SLOW", { exact: true })).toHaveCount(0)
})
