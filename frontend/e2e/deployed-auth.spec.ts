import { expect, test } from "@playwright/test"

const email = process.env.E2E_EMAIL
const password = process.env.E2E_PASSWORD

test.skip(!email || !password, "Set E2E_EMAIL and E2E_PASSWORD for an authenticated deployed smoke.")

test("an authenticated investor can load What-to-Buy on the deployed release", async ({ page }) => {
  await page.goto("/login?next=%2Fapp%2Funiverse%3Fmode%3Dbuy")
  await page.getByLabel("Email").fill(email!)
  await page.getByLabel("Password").fill(password!)
  await page.getByRole("button", { name: "Continue" }).click()

  await expect(page).toHaveURL(/\/app\/universe\?mode=buy/)
  await expect(page.getByText(/What to Buy/).first()).toBeVisible()
  await expect(page.getByText(/Unable to load What to Buy/)).not.toBeVisible()
})
