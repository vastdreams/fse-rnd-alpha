/**
 * PATH: services/pdf-renderer/validate.mjs
 * PURPOSE: Pure validation helpers for the deterministic report renderer.
 * Small functions, explicit inputs/outputs, no browser state.
 */

/** Count pages in a PDF buffer via the document page tree. */
export function pdfPageCount(buffer) {
  const text = buffer.toString("latin1");
  // Chromium writes an uncompressed page tree: prefer /Type /Pages /Count N.
  const counts = [...text.matchAll(/\/Type\s*\/Pages[^>]*?\/Count\s+(\d+)/gs)].map((m) =>
    parseInt(m[1], 10)
  );
  if (counts.length > 0) return Math.max(...counts);
  const pages = text.match(/\/Type\s*\/Page(?![s\w])/g);
  if (pages) return pages.length;
  throw new Error("Could not determine PDF page count");
}

/** Assert the in-browser DOM audit result is a valid two-page document. */
export function assertDomAudit(audit) {
  const errors = [];
  if (audit.pageCount !== 2) {
    errors.push(`expected exactly 2 .report-page elements, found ${audit.pageCount}`);
  }
  for (const page of audit.pages ?? []) {
    if (page.overflowY > 1 || page.overflowX > 1) {
      errors.push(
        `page ${page.index} overflows its A4 container by ${page.overflowX}x${page.overflowY}px`
      );
    }
  }
  if (!audit.ready) errors.push("window.__REPORT_READY__ never became true");
  if (audit.emptyCharts > 0) errors.push(`${audit.emptyCharts} chart svg elements are empty`);
  if (audit.consoleErrors?.length) {
    errors.push(`console errors: ${audit.consoleErrors.slice(0, 3).join(" | ")}`);
  }
  if (audit.failedRequests?.length) {
    errors.push(`failed requests: ${audit.failedRequests.slice(0, 3).join(" | ")}`);
  }
  if (errors.length) throw new Error(`DOM audit failed: ${errors.join("; ")}`);
}

/** Decide whether a request URL is allowed during rendering. */
export function requestAllowed(url, baseOrigin) {
  try {
    const parsed = new URL(url);
    if (parsed.origin === baseOrigin) return true;
    // Self-hosted only: no CDN fonts, no third-party beacons.
    return false;
  } catch {
    return false;
  }
}
