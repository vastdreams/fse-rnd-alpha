import { expect, test, type Page } from "@playwright/test"

async function installAuthenticatedShell(page: Page) {
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
}

test("canonicalizes historical dashboard routes without losing research version context", async ({ page }) => {
  await installAuthenticatedShell(page)

  await page.goto("/app/legacy?mode=buy")
  await expect(page).toHaveURL(/\/app\?mode=buy/)

  await page.goto("/app/legacy/book?book_id=book-fixture")
  await expect(page).toHaveURL(/\/app\/book\?book_id=book-fixture/)

  await page.goto("/app/legacy/company/MNDY?universe_version=univ_fixture")
  await expect(page).toHaveURL(/\/app\/company\/MNDY\?universe_version=univ_fixture/)
})
