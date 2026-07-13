import { expect, test } from "@playwright/test"
import { mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import { formatNumber4, formatPercent4, formatUsd4, formatUsdCompact } from "../src/lib/formatMetrics"
import { mosDiffersFromLiveGap } from "../src/lib/rankRowInvariants"
import { aboveBandFlag } from "../src/lib/aboveBandPolicy"

const here = dirname(fileURLToPath(import.meta.url))
const golden = JSON.parse(
  readFileSync(join(here, "../src/fixtures/rank-golden.json"), "utf8")
) as {
  meta: { universe_version: string; recipe_id: string }
  rows: Array<{
    ticker: string
    recipe_id: string
    universe_version: string
    rank: number
    score: number
    contributions: Record<string, number>
    completeness_grade: string
    freshness_ok: boolean
    kill_active: boolean
    reviewer_passed: boolean | null
    name: string
    industry: string
    price_live: number
    fair_px_lo: number
    fair_px_med: number
    fair_px_hi: number
    mos_live: number
    vs_median_pct: number
    revenue_usd: number
    rev_cagr: number | null
    gm: number | null
    fcfm_sbc: number | null
    roic: number | null
    rd_prod: number | null
    retention: number | null
    edge_tags?: string[]
  }>
}

const parityTickers = ["KSPI", "APP", "GRND"] as const

test("number parity: sealed golden tickers match card formatters and MoS/above-band policy", async ({
  page,
}) => {
  const rows = golden.rows.filter((r) => (parityTickers as readonly string[]).includes(r.ticker))
  expect(rows.length).toBe(3)

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
          recipe_id: golden.meta.recipe_id,
          name: "Golden parity",
          formula_human: "Sealed fixture",
          formula_exact: "fixture",
          hard_filters: [],
          axes: [],
          benchmark_vs: "test",
          custom: false,
        },
        universe_version: golden.meta.universe_version,
        n_universe: rows.length,
        n_ranked: rows.length,
        rows,
        note: "Research only",
      }),
    })
  )
  await page.route("**/api/universe/stances**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        universe_version: golden.meta.universe_version,
        stance_filter: null,
        n_universe: rows.length,
        n_analyzed: 0,
        n: 0,
        rows: [],
        note: "Research only",
      }),
    })
  )

  await page.goto("/app/universe?mode=buy")

  const bundleSrc =
    (await page.locator('script[src*="assets/index-"]').first().getAttribute("src")) ||
    (await page.locator('script[type="module"]').first().getAttribute("src"))

  const report: Record<string, unknown> = {
    universe_version: golden.meta.universe_version,
    recipe_id: golden.meta.recipe_id,
    bundle_src: bundleSrc,
    captured_at: new Date().toISOString(),
    tickers: {},
  }

  for (const row of rows) {
    const card = page.locator("article").filter({ hasText: row.ticker }).first()
    await expect(card).toBeVisible()
    await expect(card.getByText(formatUsd4(row.price_live), { exact: true })).toBeVisible()
    await expect(card.getByText(formatUsdCompact(row.revenue_usd), { exact: true })).toBeVisible()
    await expect(card.getByText(formatPercent4(row.vs_median_pct, true), { exact: true })).toBeVisible()
    await expect(card.getByText(formatNumber4(row.score), { exact: true })).toBeVisible()

    const showMos = mosDiffersFromLiveGap(row.mos_live, row.vs_median_pct)
    if (!showMos) {
      await expect(card.getByText(/^MoS$/)).toHaveCount(0)
      await expect(card.getByText(/Research MoS/)).toHaveCount(0)
    } else {
      await expect(card.getByText(/Research MoS/)).toBeVisible()
    }

    const flag = aboveBandFlag(row)
    const aboveBandExact = card.getByText("Above fair band", { exact: true })
    if (flag.active) {
      await expect(aboveBandExact.first()).toBeVisible()
      expect(await aboveBandExact.count()).toBeGreaterThanOrEqual(1)
    } else {
      await expect(aboveBandExact).toHaveCount(0)
    }

    ;(report.tickers as Record<string, unknown>)[row.ticker] = {
      price: formatUsd4(row.price_live),
      revenue: formatUsdCompact(row.revenue_usd),
      vs: formatPercent4(row.vs_median_pct, true),
      score: formatNumber4(row.score),
      showMos,
      aboveBand: flag.active,
    }
  }

  // Retained machine-checkable artifact for CI / local audit
  const outDir = join(here, "../test-results")
  mkdirSync(outDir, { recursive: true })
  const outPath = join(outDir, "universe-number-parity-report.json")
  writeFileSync(outPath, JSON.stringify(report, null, 2))
  expect(readFileSync(outPath, "utf8")).toContain(golden.meta.universe_version)
  expect(report.bundle_src).toBeTruthy()

  await page.screenshot({
    path: join(outDir, "universe-number-parity.png"),
    fullPage: true,
  })
})
