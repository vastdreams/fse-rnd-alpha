# PATH: services/pdf-renderer/Dockerfile
# PURPOSE: Pinned-Chromium renderer for two-page company brief PDFs.
# The Playwright image version MUST match package.json (1.61.1) so every
# render uses the identical browser build.

FROM mcr.microsoft.com/playwright:v1.61.1-jammy

WORKDIR /renderer
COPY package.json ./
RUN npm install --omit=dev && npx playwright install chromium

COPY render-report.mjs validate.mjs validate.test.mjs ./

ENTRYPOINT ["node", "render-report.mjs"]
