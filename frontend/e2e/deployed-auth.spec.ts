import { expect, test } from "@playwright/test"

const email = process.env.E2E_EMAIL
const password = process.env.E2E_PASSWORD
const expectedTicker = process.env.E2E_EXPECTED_BUY_TICKER
const expectedSourceSha = process.env.E2E_EXPECTED_SOURCE_SHA
const expectedDataManifestSha = process.env.E2E_EXPECTED_DATA_MANIFEST_SHA256

test.skip(
  !email || !password || !expectedTicker || !expectedSourceSha || !expectedDataManifestSha,
  "Set deployed-smoke credentials, ticker, source SHA, and data-manifest SHA."
)

test("an authenticated investor can render a live BUY row and sell ceiling", async ({ page }) => {
  const pageErrors: string[] = []
  page.on("pageerror", (error) => pageErrors.push(error.message))

  const readinessResponse = await page.request.get("/ready")
  expect(readinessResponse.status()).toBe(200)
  const readiness = await readinessResponse.json()
  expect(readiness).toMatchObject({
    ready: true,
    release: {
      source_sha: expectedSourceSha,
      data_manifest_sha256: expectedDataManifestSha,
    },
  })

  await page.goto("/login?next=%2Fapp%2Funiverse%3Fmode%3Dbuy")
  await page.getByLabel("Email").fill(email!)
  await page.getByLabel("Password").fill(password!)
  await page.getByRole("button", { name: "Continue" }).click()

  await expect(page).toHaveURL(/\/app\/universe\?mode=buy/)
  await expect(page.getByText(/What to Buy/).first()).toBeVisible()
  await expect(page.getByText(/Unable to load What to Buy/)).not.toBeVisible()
  await expect(page.getByRole("link", { name: expectedTicker!, exact: true }).first()).toBeVisible()
  await expect(page.getByText("Sell ceiling", { exact: true }).first()).toBeVisible()
  expect(pageErrors).toEqual([])
})
