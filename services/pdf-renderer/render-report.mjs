/**
 * PATH: services/pdf-renderer/render-report.mjs
 * PURPOSE: Deterministic two-page PDF rendering for company brief snapshots.
 *
 * Uses the repo-pinned Playwright Chromium (same version as CI browser jobs).
 * Fails closed: wrong page count, overflow, console errors, or unapproved
 * network requests abort the render. On success, optionally registers the
 * artifact with the backend ledger.
 *
 * Usage:
 *   node render-report.mjs --base-url https://research.finsoeasy.com \
 *     --ticker WIX --snapshot-id rpt_abc --out /tmp/wix.pdf [--register]
 *
 * Env: RENDER_TOKEN — JWT for an operator account (required).
 */

import { readFileSync, writeFileSync } from "node:fs"
import { chromium } from "playwright"

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, cur, i, arr) => {
    if (cur.startsWith("--")) acc.push([cur.slice(2), arr[i + 1]?.startsWith("--") || arr[i + 1] === undefined ? "true" : arr[i + 1]])
    return acc
  }, [])
)

const BASE_URL = args["base-url"]
const TICKER = (args.ticker || "").toUpperCase()
const SNAPSHOT_ID = args["snapshot-id"]
const OUT = args.out
const REGISTER = args.register === "true"
const TOKEN = process.env.RENDER_TOKEN

function fail(msg) {
  console.error(`RENDER_FAIL: ${msg}`)
  process.exit(1)
}

if (!BASE_URL || !TICKER || !SNAPSHOT_ID || !OUT) {
  fail("required: --base-url --ticker --snapshot-id --out")
}
if (!TOKEN) fail("RENDER_TOKEN env var is required")

const REPORT_URL = `${BASE_URL}/app/company/${TICKER}/report/${SNAPSHOT_ID}`
const ORIGIN = new URL(BASE_URL).origin

function pdfPageCount(buffer) {
  // Chromium writes a single /Pages object carrying /Count N.
  const text = buffer.toString("latin1")
  const counts = [...text.matchAll(/\/Type\s*\/Pages[^>]*?\/Count\s+(\d+)/gs)].map((m) => Number(m[1]))
  if (counts.length) return Math.max(...counts)
  return [...text.matchAll(/\/Type\s*\/Page[^s]/g)].length
}

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 1240, height: 1754 },
  locale: "en-US",
  timezoneId: "UTC",
})

// Network allowlist: only the app origin may load. Fonts are self-hosted;
// anything else is a determinism leak.
const blocked = []
await context.route("**/*", (route) => {
  const url = route.request().url()
  if (url.startsWith(ORIGIN) || url.startsWith("data:") || url.startsWith("blob:")) {
    return route.continue()
  }
  blocked.push(url)
  return route.abort()
})

await context.addInitScript(
  ([key, token]) => {
    window.localStorage.setItem(key, token)
  },
  ["fse_research_token", TOKEN]
)

const page = await context.newPage()
const consoleErrors = []
page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(msg.text())
})
page.on("pageerror", (err) => consoleErrors.push(String(err)))

await page.goto(REPORT_URL, { waitUntil: "networkidle", timeout: 60_000 })
await page.waitForFunction(() => window.__REPORT_READY__ === true, null, { timeout: 30_000 })
await page.evaluate(() => document.fonts.ready)

// Structural gates before printing.
const pages = await page.locator(".report-page").count()
if (pages !== 2) fail(`expected exactly 2 .report-page elements, found ${pages}`)

const overflow = await page.evaluate(() =>
  [...document.querySelectorAll(".report-page")].map((el, i) => ({
    page: i + 1,
    scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight,
  }))
)
for (const p of overflow) {
  if (p.scrollHeight > p.clientHeight + 1) {
    fail(`page ${p.page} overflows its A4 container (${p.scrollHeight} > ${p.clientHeight})`)
  }
}

const svgs = await page.evaluate(() =>
  [...document.querySelectorAll(".report-page svg")].map((s) => s.childElementCount)
)
if (svgs.some((n) => n === 0)) fail("an SVG chart rendered empty")

const errorBanner = await page.locator('[data-testid="report-error"]').count()
if (errorBanner > 0) fail("report page rendered its error state")
if (consoleErrors.length) fail(`console errors: ${consoleErrors.join(" | ")}`)

const pdf = await page.pdf({
  format: "A4",
  printBackground: true,
  preferCSSPageSize: true,
  margin: { top: 0, bottom: 0, left: 0, right: 0 },
})
const browserVersion = browser.version()
await browser.close()

const nPages = pdfPageCount(pdf)
if (nPages !== 2) fail(`rendered PDF has ${nPages} pages, expected 2`)

writeFileSync(OUT, pdf)
const rendererVersion = `playwright-chromium-${browserVersion}`
console.log(
  JSON.stringify({
    ok: true,
    out: OUT,
    bytes: pdf.length,
    n_pages: nPages,
    renderer_version: rendererVersion,
    blocked_requests: blocked.length,
  })
)

if (REGISTER) {
  const body = {
    kind: "pdf",
    content_base64: readFileSync(OUT).toString("base64"),
    renderer_version: rendererVersion,
    n_pages: nPages,
  }
  const res = await fetch(`${BASE_URL}/api/reports/${SNAPSHOT_ID}/artifact`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN}` },
    body: JSON.stringify(body),
  })
  if (!res.ok) fail(`artifact registration failed: HTTP ${res.status} ${await res.text()}`)
  console.log(JSON.stringify({ registered: await res.json() }))
}
