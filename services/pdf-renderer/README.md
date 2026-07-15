# Company brief PDF renderer

Deterministic two-page PDF rendering for `company_report_snapshots`, using the
repo-pinned Playwright Chromium (`frontend/package.json` → `playwright@1.61.x`,
CI image `mcr.microsoft.com/playwright:v1.61.1-jammy`).

## Guarantees (fail-closed)

- Only the app origin may load during rendering (network allowlist).
- Waits for `document.fonts.ready` and `window.__REPORT_READY__`.
- Asserts exactly two `.report-page` A4 containers with zero overflow.
- Asserts every SVG chart is populated and no console/page errors occurred.
- Asserts the emitted PDF has exactly 2 pages before writing/registering.

## Usage

```bash
cd frontend && npm ci   # provides the pinned playwright dependency

RENDER_TOKEN="<operator JWT>" node ../services/pdf-renderer/render-report.mjs \
  --base-url https://research.finsoeasy.com \
  --ticker WIX \
  --snapshot-id rpt_xxxxxxxxxxxxxxxxxxxxxxxx \
  --out /tmp/WIX.pdf \
  --register
```

`--register` uploads the PDF to `POST /api/reports/{snapshot_id}/artifact`,
which stores it content-addressed (S3 when `REPORT_ARTIFACT_BUCKET` is set on
the backend, local `REPORT_ARTIFACT_DIR` otherwise) and records checksum,
renderer version, and page count in the `company_report_artifacts` ledger.
Downloads at `GET /api/reports/{snapshot_id}/export.pdf` are checksum-verified
on every read.
