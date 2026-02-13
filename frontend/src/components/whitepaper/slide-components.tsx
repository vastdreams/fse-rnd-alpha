/**
 * PATH: frontend/src/components/whitepaper/slide-components.tsx
 * PURPOSE: Shared presentation components for the Whitepaper slide deck.
 * WHY: Extracted from Whitepaper.tsx to keep files under 300 lines.
 * DEPENDENCIES:
 *  - react: ReactNode type
 */

import type { ReactNode } from "react"

// A4 dimensions in pixels at 96 DPI (portrait)
export const A4_WIDTH = 794
export const A4_HEIGHT = 1123

// Accent hex colors for html2canvas compatibility
export const accentHexColors: Record<string, string> = {
  emerald: "#059669",
  blue: "#2563eb",
  purple: "#9333ea",
  amber: "#d97706",
  red: "#dc2626",
}

// Color palette for cards and section boxes (html2canvas-safe)
export const hexColors = {
  emerald: { bg: "#ecfdf5", border: "#a7f3d0", text: "#047857" },
  blue: { bg: "#eff6ff", border: "#bfdbfe", text: "#1d4ed8" },
  purple: { bg: "#faf5ff", border: "#e9d5ff", text: "#7e22ce" },
  amber: { bg: "#fffbeb", border: "#fde68a", text: "#b45309" },
  red: { bg: "#fef2f2", border: "#fecaca", text: "#dc2626" },
  slate: { bg: "#f8fafc", border: "#e2e8f0", text: "#334155" },
}

// ── Slide wrapper ────────────────────────────────────────────────────────────

export interface SlideProps {
  children: ReactNode
  slideNumber: number
  totalSlides: number
  title?: string
  subtitle?: string
  accent?: "emerald" | "blue" | "purple" | "amber" | "red"
}

export function Slide({ children, slideNumber, totalSlides, title, subtitle, accent = "emerald" }: SlideProps) {
  return (
    <div
      className="slide-page rounded-lg shadow-2xl flex flex-col"
      style={{
        width: A4_WIDTH,
        height: A4_HEIGHT,
        minWidth: A4_WIDTH,
        minHeight: A4_HEIGHT,
        maxWidth: A4_WIDTH,
        maxHeight: A4_HEIGHT,
        backgroundColor: "#ffffff",
        color: "#1e293b",
        overflow: "hidden",
      }}
    >
      {/* Header bar */}
      <div style={{ height: 8, minHeight: 8, backgroundColor: accentHexColors[accent], flexShrink: 0 }} />

      {/* Title section */}
      {title && (
        <div style={{ padding: "32px 48px 16px 48px", flexShrink: 0 }}>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: 0 }}>{title}</h2>
          {subtitle && <p style={{ fontSize: "0.875rem", color: "#64748b", marginTop: 4, marginBottom: 0 }}>{subtitle}</p>}
        </div>
      )}

      {/* Content */}
      <div
        style={{
          flex: 1,
          padding: title ? "8px 48px 24px 48px" : "32px 48px",
          overflow: "hidden",
          minHeight: 0,
        }}
      >
        {children}
      </div>

      {/* Footer */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 48px",
          borderTop: "1px solid #e2e8f0",
          fontSize: "0.75rem",
          color: "#94a3b8",
          flexShrink: 0,
        }}
      >
        <span>R&D Alpha Research</span>
        <span>January 2026</span>
        <span>{slideNumber} / {totalSlides}</span>
      </div>
    </div>
  )
}

// ── MetricCard ───────────────────────────────────────────────────────────────

export function MetricCard({
  value,
  label,
  accent = "emerald",
}: {
  value: string | number
  label: string
  accent?: "emerald" | "blue" | "purple" | "amber"
}) {
  const c = hexColors[accent]
  return (
    <div
      className="p-4 rounded-lg text-center"
      style={{ backgroundColor: c.bg, border: `1px solid ${c.border}`, color: c.text }}
    >
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs mt-1" style={{ opacity: 0.8 }}>{label}</div>
    </div>
  )
}

// ── SectionBox ───────────────────────────────────────────────────────────────

export function SectionBox({
  title,
  children,
  accent = "slate",
}: {
  title?: string
  children: ReactNode
  accent?: "emerald" | "blue" | "purple" | "amber" | "red" | "slate"
}) {
  const c = hexColors[accent]
  return (
    <div className="p-4 rounded-lg" style={{ backgroundColor: c.bg, border: `1px solid ${c.border}` }}>
      {title && <h3 className="font-semibold mb-2" style={{ color: c.text }}>{title}</h3>}
      {children}
    </div>
  )
}

// ── GrowthChart (SVG-based) ──────────────────────────────────────────────────

export function GrowthChart({
  data,
  width = 320,
  height = 140,
  showLegend = true,
}: {
  data: Array<{ year: number; portfolioIndex: number; benchmarkIndex: number; sp500Index?: number }>
  width?: number
  height?: number
  showLegend?: boolean
}) {
  if (!data || data.length < 2) {
    return (
      <div
        style={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#64748b",
          fontSize: 12,
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
        }}
      >
        Loading chart…
      </div>
    )
  }

  const leftPad = 36
  const rightPad = 12
  const topPad = 12
  const bottomPad = 20
  const xs = data.map((_, i) => i)
  const pVals = data.map((d) => d.portfolioIndex)
  const bVals = data.map((d) => d.benchmarkIndex)
  const sVals = data.map((d) => (typeof d.sp500Index === "number" ? d.sp500Index : NaN)).filter((v) => Number.isFinite(v)) as number[]
  const all = [...pVals, ...bVals, ...sVals]
  const min = Math.min(...all)
  const max = Math.max(...all)
  const range = max - min || 1

  const x = (i: number) => leftPad + (i / Math.max(1, xs.length - 1)) * (width - leftPad - rightPad)
  const y = (v: number) => topPad + (1 - (v - min) / range) * (height - topPad - bottomPad)
  const pathFn = (vals: number[]) => vals.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(v)}`).join(" ")

  const pPath = pathFn(pVals)
  const bPath = pathFn(bVals)
  const sPath = sVals.length === data.length ? pathFn(data.map((d) => d.sp500Index as number)) : null

  const yLabels = [max, (max + min) / 2, min].map((v) => v.toFixed(0) + "x")
  const startYear = data[0]?.year || 2010
  const endYear = data[data.length - 1]?.year || 2024

  return (
    <div style={{ position: "relative" }}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ display: "block", background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 12 }}
      >
        {/* Y-axis labels */}
        <text x={leftPad - 4} y={topPad + 4} textAnchor="end" fontSize="9" fill="#94a3b8">{yLabels[0]}</text>
        <text x={leftPad - 4} y={(height - bottomPad + topPad) / 2 + 3} textAnchor="end" fontSize="9" fill="#94a3b8">{yLabels[1]}</text>
        <text x={leftPad - 4} y={height - bottomPad + 4} textAnchor="end" fontSize="9" fill="#94a3b8">{yLabels[2]}</text>
        {/* X-axis labels */}
        <text x={leftPad} y={height - 6} textAnchor="start" fontSize="9" fill="#94a3b8">{startYear}</text>
        <text x={width - rightPad} y={height - 6} textAnchor="end" fontSize="9" fill="#94a3b8">{endYear}</text>
        {/* grid */}
        {[0, 0.5, 1].map((t) => (
          <line key={t} x1={leftPad} x2={width - rightPad} y1={topPad + t * (height - topPad - bottomPad)} y2={topPad + t * (height - topPad - bottomPad)} stroke="#eef2f7" strokeWidth="1" />
        ))}
        {/* lines */}
        {sPath && <path d={sPath} fill="none" stroke="#94a3b8" strokeWidth="2" strokeDasharray="5 4" />}
        <path d={bPath} fill="none" stroke="#2563eb" strokeWidth="2.5" />
        <path d={pPath} fill="none" stroke="#059669" strokeWidth="3" />
        {/* endpoints */}
        <circle cx={x(pVals.length - 1)} cy={y(pVals[pVals.length - 1])} r="4" fill="#059669" />
        <circle cx={x(bVals.length - 1)} cy={y(bVals[bVals.length - 1])} r="3" fill="#2563eb" />
      </svg>
      {showLegend && (
        <div style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 12, height: 3, background: "#059669", borderRadius: 1 }} />
            <span style={{ fontSize: 9, color: "#059669", fontWeight: 600 }}>R&D Portfolio</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 12, height: 3, background: "#2563eb", borderRadius: 1 }} />
            <span style={{ fontSize: 9, color: "#2563eb", fontWeight: 600 }}>Benchmark</span>
          </div>
          {sPath && (
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{ width: 12, height: 2, background: "#94a3b8", borderRadius: 1, opacity: 0.7 }} />
              <span style={{ fontSize: 9, color: "#94a3b8" }}>S&P 500</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
