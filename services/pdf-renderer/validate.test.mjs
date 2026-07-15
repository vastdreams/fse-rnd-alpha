/**
 * PATH: services/pdf-renderer/validate.test.mjs
 * PURPOSE: Unit tests for renderer validation helpers (node:test, no deps).
 */

import assert from "node:assert/strict";
import test from "node:test";
import { assertDomAudit, pdfPageCount, requestAllowed } from "./validate.mjs";

const GOOD_AUDIT = {
  ready: true,
  pageCount: 2,
  pages: [
    { index: 1, overflowX: 0, overflowY: 0 },
    { index: 2, overflowX: 0, overflowY: 1 },
  ],
  emptyCharts: 0,
  consoleErrors: [],
  failedRequests: [],
};

test("pdfPageCount reads /Pages /Count", () => {
  const pdf = Buffer.from("%PDF-1.7\n1 0 obj\n<< /Type /Pages /Kids [2 0 R 3 0 R] /Count 2 >>\nendobj");
  assert.equal(pdfPageCount(pdf), 2);
});

test("pdfPageCount falls back to counting /Type /Page objects", () => {
  const pdf = Buffer.from("<< /Type /Page >> << /Type /Page >> << /Type /Page >>");
  assert.equal(pdfPageCount(pdf), 3);
});

test("pdfPageCount rejects unparseable buffers", () => {
  assert.throws(() => pdfPageCount(Buffer.from("not a pdf")), /page count/);
});

test("assertDomAudit passes a clean two-page document", () => {
  assert.doesNotThrow(() => assertDomAudit(GOOD_AUDIT));
});

test("assertDomAudit rejects wrong page count", () => {
  assert.throws(() => assertDomAudit({ ...GOOD_AUDIT, pageCount: 3 }), /exactly 2/);
});

test("assertDomAudit rejects overflowing pages", () => {
  assert.throws(
    () =>
      assertDomAudit({
        ...GOOD_AUDIT,
        pages: [{ index: 1, overflowX: 0, overflowY: 40 }, GOOD_AUDIT.pages[1]],
      }),
    /overflows/
  );
});

test("assertDomAudit rejects missing ready flag, empty charts, console errors", () => {
  assert.throws(() => assertDomAudit({ ...GOOD_AUDIT, ready: false }), /REPORT_READY/);
  assert.throws(() => assertDomAudit({ ...GOOD_AUDIT, emptyCharts: 1 }), /chart/);
  assert.throws(() => assertDomAudit({ ...GOOD_AUDIT, consoleErrors: ["boom"] }), /console/);
  assert.throws(() => assertDomAudit({ ...GOOD_AUDIT, failedRequests: ["x"] }), /failed requests/);
});

test("requestAllowed permits only same-origin", () => {
  const origin = "https://research.finsoeasy.com";
  assert.equal(requestAllowed(`${origin}/api/reports/x`, origin), true);
  assert.equal(requestAllowed("https://fonts.googleapis.com/css", origin), false);
  assert.equal(requestAllowed("not-a-url", origin), false);
});
