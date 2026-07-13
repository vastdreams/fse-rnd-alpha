/**
 * PATH: frontend/vite.config.ts
 * PURPOSE:
 *   - Configure Vite build/dev for the R&D Alpha frontend (React + TypeScript).
 *
 * WHY:
 *   - We need fast, deterministic production builds for deployment (static assets served by nginx).
 *   - Avoid importing Storybook / browser-test plugins in the build path, as they can slow or hang
 *     `vite build` in constrained environments.
 *
 * FLOW:
 *   ┌──────────────┐   ┌─────────────┐   ┌──────────────────────┐
 *   │ vite dev     │→  │ proxy /api  │→  │ backend (FastAPI)     │
 *   └──────────────┘   └─────────────┘   └──────────────────────┘
 *          │
 *          ▼
 *   ┌──────────────┐   ┌──────────────────────────┐
 *   │ vite build   │→  │ dist/ (static assets)    │
 *   └──────────────┘   └──────────────────────────┘
 *
 * DEPENDENCIES:
 *   - @vitejs/plugin-react: React fast refresh + JSX transform
 *   - TypeScript: typechecking (`tsc -b`)
 *   - Tailwind (via PostCSS) for styling
 */
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"
import { fileURLToPath } from "node:url"

const dirname =
  typeof __dirname !== "undefined" ? __dirname : path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    // Production builds do not need source maps; disabling speeds up CI and reduces artifact size.
    sourcemap: false,
  },
})