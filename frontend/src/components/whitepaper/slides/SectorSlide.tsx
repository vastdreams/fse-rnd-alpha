/**
 * PATH: frontend/src/components/whitepaper/slides/SectorSlide.tsx
 * PURPOSE: Slide 7 – Sector Analysis: R&D intensity by industry, concentration risk.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Slide } from "../slide-components"

export function SectorSlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const { rdBySector, invSectorMix, invNHoldings } = data

  return (
    <Slide key="sectors" slideNumber={7} totalSlides={totalSlides} title="Sector Analysis" subtitle="R&D intensity varies dramatically by industry" accent="purple">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Top stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
          <div style={{ background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: 10, padding: 14, textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#7e22ce" }}>
              {(() => { const tech = invSectorMix.find((s) => s.sector.toLowerCase().includes("tech"))?.weight; const health = invSectorMix.find((s) => s.sector.toLowerCase().includes("health"))?.weight; if (typeof tech === "number" && typeof health === "number") return `${Math.round(tech + health)}%`; return "…" })()}
            </div>
            <div style={{ fontSize: 12, color: "#6b21a8" }}>Tech + Healthcare</div>
            <div style={{ fontSize: 10, color: "#94a3b8" }}>in top-{invNHoldings} basket (current)</div>
          </div>
          <div style={{ background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: 10, padding: 14, textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#059669" }}>See paper</div>
            <div style={{ fontSize: 12, color: "#047857" }}>Sector-neutral test</div>
            <div style={{ fontSize: 10, color: "#94a3b8" }}>Recommended robustness</div>
          </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: 14, textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#b45309" }}>{rdBySector.length || "…"}</div>
            <div style={{ fontSize: 12, color: "#92400e" }}>Sectors Covered</div>
            <div style={{ fontSize: 10, color: "#94a3b8" }}>GICS classification</div>
          </div>
        </div>

        {/* Main content */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Sector R&D Intensity List */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 16, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 16, borderBottom: "2px solid #9333ea", paddingBottom: 8 }}>R&D Intensity by Sector</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(rdBySector.length ? rdBySector.slice(0, 8) : []).map((row, i) => {
                const sectorName = typeof row?.sector === "string" && row.sector ? row.sector : "Unknown"
                const avg = typeof row?.avg_rd_intensity === "number" ? row.avg_rd_intensity : 0
                const companyCount = typeof row?.company_count === "number" ? row.company_count : 0
                const isHighRD = avg > 8
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 100, fontSize: 12, color: isHighRD ? "#7e22ce" : "#64748b", fontWeight: isHighRD ? 600 : 400 }}>{sectorName}</div>
                    <div style={{ flex: 1, height: 20, background: "#e2e8f0", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${Math.min(100, avg * 5)}%`, background: isHighRD ? "linear-gradient(90deg, #9333ea, #7c3aed)" : "#94a3b8", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 6, minWidth: 36 }}>
                        <span style={{ color: "white", fontSize: 11, fontWeight: 600 }}>{avg.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div style={{ width: 50, fontSize: 10, color: "#94a3b8", textAlign: "right" }}>{companyCount} firms</div>
                  </div>
                )
              })}
            </div>
            <div style={{ marginTop: 12, padding: 10, background: "#f1f5f9", borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>Key insight</div>
              <div style={{ fontSize: 12, color: "#334155" }}>
                <strong>{rdBySector[0]?.sector || "Top sectors"}</strong>{rdBySector[1]?.sector ? ` + ${rdBySector[1]?.sector}` : ""} dominate R&amp;D intensity in this snapshot. Consider sector caps for diversification.
              </div>
            </div>
          </div>

          {/* Insights */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ background: "linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%)", border: "2px solid #9333ea", borderRadius: 16, padding: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: "#6b21a8", marginBottom: 10 }}>⚠️ Sector Concentration Risk</h3>
              <p style={{ fontSize: 12, color: "#581c87", lineHeight: 1.6, marginBottom: 10 }}>
                High-R&amp;D portfolios can be concentrated in a small set of sectors (often Technology and Healthcare). Sector tailwinds can mechanically influence the premium.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <div style={{ background: "white", borderRadius: 8, padding: 10, textAlign: "center" }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#9333ea" }}>{(() => { const tech = invSectorMix.find((s) => s.sector.toLowerCase().includes("tech"))?.weight; return typeof tech === "number" ? `${tech.toFixed(0)}%` : "…" })()}</div>
                  <div style={{ fontSize: 10, color: "#7e22ce" }}>Technology (current)</div>
                </div>
                <div style={{ background: "white", borderRadius: 8, padding: 10, textAlign: "center" }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#9333ea" }}>{(() => { const health = invSectorMix.find((s) => s.sector.toLowerCase().includes("health"))?.weight; return typeof health === "number" ? `${health.toFixed(0)}%` : "…" })()}</div>
                  <div style={{ fontSize: 10, color: "#7e22ce" }}>Healthcare (current)</div>
                </div>
              </div>
            </div>
            <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 16, padding: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: "#047857", marginBottom: 10 }}>✓ Within-Sector Robustness (Recommended)</h3>
              <p style={{ fontSize: 12, color: "#065f46", lineHeight: 1.6, marginBottom: 10 }}>
                A key robustness is to form quintiles <em>within</em> sectors (or run sector-neutral weights) and re-test whether the premium persists after controlling for sector composition.
              </p>
              <div style={{ background: "#047857", borderRadius: 8, padding: 10 }}>
                <div style={{ fontSize: 11, color: "#a7f3d0", textAlign: "center" }}>Next step: sector-neutral premium (see Main Paper / future extensions).</div>
              </div>
            </div>
            <div style={{ background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#92400e", marginBottom: 6 }}>💡 Practical Implication</div>
              <div style={{ fontSize: 11, color: "#78350f", lineHeight: 1.5 }}>
                To reduce sector concentration, apply <strong>sector caps</strong> (e.g., 20% max per sector) during portfolio construction. This improves diversification but can reduce the raw premium; treat caps as a risk-control trade-off.
              </div>
            </div>
          </div>
        </div>

        {/* Bottom takeaway */}
        <div style={{ marginTop: 16, background: "#0f172a", borderRadius: 12, padding: 16, display: "flex", alignItems: "center", justifyContent: "center", gap: 32 }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "#94a3b8" }}>Implication</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "white" }}>Consider sector constraints in implementation to diversify</div>
          </div>
        </div>
      </div>
    </Slide>
  )
}
