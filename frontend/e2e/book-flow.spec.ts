import { expect, test, type Page } from "@playwright/test"

const universeVersion = "univ_book_flow_test"

type TestHolding = {
  ticker: string
  weight_pct: number
  added_at: string
  override_reason: string | null
}

type TestBook = {
  book_id: string
  name: string
  recipe_id: string
  universe_version: string
  lock_version: string | null
  locked_at: string | null
  lock_acknowledgements: string[]
  constraints: { kind: string; limit: number; enabled: boolean }[]
  is_primary: boolean
  revision: number
  holdings: TestHolding[]
}

function holdings(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    ticker: `T${String(index + 1).padStart(2, "0")}`,
    weight_pct: index === 0 ? 10 : 0,
    added_at: "2026-07-13T00:00:00",
    override_reason: null,
  }))
}

function bookWith(count: number): TestBook {
  return {
    book_id: `book-${count}`,
    name: `Research ${count}`,
    recipe_id: "R3",
    universe_version: universeVersion,
    lock_version: null,
    locked_at: null,
    lock_acknowledgements: [],
    constraints: [{ kind: "max_name_pct", limit: 15, enabled: true }],
    is_primary: true,
    revision: 1,
    holdings: holdings(count),
  }
}

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

for (const count of [1, 6, 10]) {
  test(`opens an actionable ${count}-name Book draft without implicit reallocation`, async ({ page }) => {
    const book = bookWith(count)
    await installAuthenticatedShell(page)
    await page.route("**/api/books", async (route) => {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify({ books: [book] }) })
    })
    await page.route(`**/api/books/${book.book_id}`, async (route) => {
      if (route.request().method() !== "PUT") return route.fallback()
      const body = route.request().postDataJSON() as { holdings: typeof book.holdings }
      book.holdings = body.holdings
      book.revision += 1
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ saved: true, revision: book.revision }),
      })
    })

    await page.goto("/app/book")
    await expect(page.locator("tbody tr")).toHaveCount(count)
    await expect(page.locator('input[type="number"]').first()).toHaveValue("10")
    if (count > 1) {
      await expect(page.locator('input[type="number"]').nth(1)).toHaveValue("0")
    }

    await page.getByRole("button", { name: "Rebalance equally" }).click()
    const expectedWeight = count < 7 ? "15" : "10"
    await expect(page.locator('input[type="number"]').first()).toHaveValue(expectedWeight)
    await page.getByRole("button", { name: "Save book" }).click()
    await expect(page.getByText("Saved.")).toBeVisible()
    expect(book.holdings.every((holding) => holding.weight_pct <= 15)).toBe(true)
  })
}

test("preserves custom weights and completes breach, acknowledgement, lock, and export flow", async ({ page }) => {
  const book = bookWith(1)
  book.holdings[0].ticker = "MNDY"
  book.holdings[0].weight_pct = 10
  let firstSave = true

  await installAuthenticatedShell(page)
  await page.route("**/api/books**", async (route) => {
    const url = new URL(route.request().url())
    const method = route.request().method()
    if (url.pathname.endsWith("/audit-pack")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ book: { book_id: book.book_id }, holdings: book.holdings }),
      })
      return
    }
    if (url.pathname.endsWith("/lock")) {
      book.locked_at = "2026-07-13T12:00:00Z"
      book.lock_version = universeVersion
      book.lock_acknowledgements = route.request().postDataJSON().acknowledgements
      book.revision += 1
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          book_id: book.book_id,
          locked: true,
          universe_version: universeVersion,
          acknowledgements: book.lock_acknowledgements,
          revision: book.revision,
        }),
      })
      return
    }
    if (method === "GET") {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify({ books: [book] }) })
      return
    }
    if (method === "PUT") {
      const body = route.request().postDataJSON() as { holdings: typeof book.holdings }
      if (firstSave) {
        firstSave = false
        await route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({
            detail: {
              breaches: [{ kind: "stale", ticker: "NEW", detail: "NEW requires an override reason" }],
            },
          }),
        })
        return
      }
      book.holdings = body.holdings
      book.revision += 1
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ saved: true, revision: book.revision }),
      })
      return
    }
    await route.fallback()
  })

  await page.goto("/app/book")
  await page.getByPlaceholder("Add ticker…").fill("NEW")
  await page.getByRole("button", { name: "Add", exact: true }).click()
  await expect(page.locator("tbody tr")).toHaveCount(2)
  await expect(page.locator('input[type="number"]').nth(0)).toHaveValue("10")
  await expect(page.locator('input[type="number"]').nth(1)).toHaveValue("0")

  await page.getByRole("button", { name: "Save book" }).click()
  await expect(page.getByText("Breach wall — save blocked")).toBeVisible()

  await page.getByPlaceholder("required to bypass a breach").nth(1).fill("Reviewed stale filing and accepted the risk.")
  await page.getByRole("button", { name: "Save book" }).click()
  await expect(page.getByText("Saved.")).toBeVisible()

  const acknowledgements = page.getByRole("checkbox", { name: "Ack" })
  await acknowledgements.nth(0).check()
  await acknowledgements.nth(1).check()
  const download = page.waitForEvent("download")
  await page.getByRole("button", { name: "Lock / Export audit pack" }).click()
  await expect((await download).suggestedFilename()).toContain("audit_pack")
  await expect(page.getByText(/locked 2026-07-13/)).toBeVisible()
  await expect(page.getByRole("link", { name: "MNDY" })).toHaveAttribute(
    "href",
    `/app/company/MNDY?universe_version=${universeVersion}`
  )
})
