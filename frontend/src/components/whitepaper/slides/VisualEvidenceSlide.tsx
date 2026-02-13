/**
 * PATH: frontend/src/components/whitepaper/slides/VisualEvidenceSlide.tsx
 * PURPOSE: Slide 6 – Visual Evidence: bar chart, quintile returns, track record.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Slide } from "../slide-components"

export function VisualEvidenceSlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const { premiumTimeSeriesData, getQuintileReturn, winRate, rdPremium, tStat, etaSquared20yr } = data

  return (
    <Slide key="charts" slideNumber={6} totalSlides={totalSlides} title="Visual Evidence" subtitle="Premium persistence across time and quintiles" accent="blue">
      <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Row 1: Time Series Chart */}
        <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", margin: 0 }}>Annual R&D Premium (Q5-Q1)</h3>
              <p style={{ fontSize: 11, color: "#64748b", margin: "4px 0 0 0" }}>High R&D quintile minus Low R&D quintile returns</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 12, height: 12, borderRadius: 2, background: "#22c55e" }} />
                <span style={{ fontSize: 11, color: "#64748b" }}>{premiumTimeSeriesData.filter(d => d.premium >= 0).length} Positive</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 12, height: 12, borderRadius: 2, background: "#ef4444" }} />
                <span style={{ fontSize: 11, color: "#64748b" }}>{premiumTimeSeriesData.filter(d => d.premium < 0).length} Negative</span>
              </div>
            </div>
          </div>
          {/* Chart */}
          <div style={{ position: "relative", height: 160, marginBottom: 8 }}>
            <div style={{ position: "absolute", left: 36, right: 0, top: 0, height: 1, background: "#f1f5f9" }} />
            <div style={{ position: "absolute", left: 36, right: 0, top: "25%", height: 1, background: "#f1f5f9" }} />
            <div style={{ position: "absolute", left: 36, right: 0, top: "50%", height: 1, background: "#94a3b8" }} />
            <div style={{ position: "absolute", left: 36, right: 0, top: "75%", height: 1, background: "#f1f5f9" }} />
            <div style={{ position: "absolute", left: 36, right: 0, bottom: 0, height: 1, background: "#f1f5f9" }} />
            <div style={{ position: "absolute", left: 0, top: -4, fontSize: 10, color: "#94a3b8", fontWeight: 500 }}>+30%</div>
            <div style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)", fontSize: 10, color: "#64748b", fontWeight: 600 }}>0%</div>
            <div style={{ position: "absolute", left: 0, bottom: -4, fontSize: 10, color: "#94a3b8", fontWeight: 500 }}>-30%</div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: "100%", marginLeft: 40, paddingRight: 4 }}>
              {premiumTimeSeriesData.map((item, i) => {
                const maxVal = 30
                const heightPct = Math.min(50, (Math.abs(item.premium) / maxVal) * 50)
                const isPositive = item.premium >= 0
                return (
                  <div key={i} style={{ height: "100%", flex: 1, position: "relative", maxWidth: 24 }}>
                    <div style={{
                      position: "absolute", left: "50%", transform: "translateX(-50%)", width: "70%", maxWidth: 16, height: `${heightPct}%`,
                      background: isPositive ? "linear-gradient(180deg, #22c55e 0%, #16a34a 100%)" : "linear-gradient(0deg, #ef4444 0%, #dc2626 100%)",
                      borderRadius: 3, ...(isPositive ? { bottom: "50%" } : { top: "50%" }),
                    }} />
                  </div>
                )
              })}
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginLeft: 40, paddingRight: 4, borderTop: "1px solid #e2e8f0", paddingTop: 8 }}>
            <span style={{ fontSize: 10, color: "#64748b", fontWeight: 500 }}>{premiumTimeSeriesData[0]?.year}</span>
            <span style={{ fontSize: 10, color: "#64748b", fontWeight: 500 }}>{premiumTimeSeriesData[Math.floor(premiumTimeSeriesData.length / 2)]?.year}</span>
            <span style={{ fontSize: 10, color: "#64748b", fontWeight: 500 }}>{premiumTimeSeriesData[premiumTimeSeriesData.length - 1]?.year}</span>
          </div>
        </div>

        {/* Row 2: Quintile Returns + Track Record + Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 0.8fr", gap: 14 }}>
          {/* Quintile Returns */}
          <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>Quintile Returns (5-Year Rolling)</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {[
                { name: "Q5", label: "High R&D", color: "#22c55e", return: getQuintileReturn(5) },
                { name: "Q4", label: "", color: "#84cc16", return: getQuintileReturn(4) },
                { name: "Q3", label: "", color: "#eab308", return: getQuintileReturn(3) },
                { name: "Q2", label: "", color: "#f97316", return: getQuintileReturn(2) },
                { name: "Q1", label: "Low R&D", color: "#ef4444", return: getQuintileReturn(1) },
              ].map((item) => (
                <div key={item.name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 26, fontSize: 12, fontWeight: 700, color: item.color }}>{item.name}</div>
                  <div style={{ flex: 1, height: 22, background: "#f1f5f9", borderRadius: 4, overflow: "hidden", position: "relative" }}>
                    {typeof item.return === "number" ? (
                      <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${Math.max(0, Math.min(100, Math.max(30, (item.return / 18) * 100)))}%`, background: `linear-gradient(90deg, ${item.color}, ${item.color}cc)`, borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 8 }}>
                        <span style={{ color: "white", fontSize: 11, fontWeight: 700 }}>{item.return.toFixed(1)}%</span>
                      </div>
                    ) : (
                      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 8 }}>
                        <span style={{ color: "#64748b", fontSize: 11, fontWeight: 700 }}>…</span>
                      </div>
                    )}
                  </div>
                  {item.label && <span style={{ fontSize: 9, color: "#64748b", width: 40 }}>{item.label}</span>}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10, background: "linear-gradient(90deg, #059669 0%, #10b981 100%)", borderRadius: 6, padding: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.9)", fontWeight: 500 }}>Spread (Q5-Q1)</span>
              <span style={{ fontSize: 18, fontWeight: 800, color: "white" }}>
                {(() => { const q5 = getQuintileReturn(5); const q1 = getQuintileReturn(1); if (typeof q5 !== "number" || typeof q1 !== "number") return "…"; const spread = q5 - q1; return `${spread >= 0 ? "+" : ""}${spread.toFixed(1)}%` })()}
              </span>
            </div>
          </div>

          {/* Track Record */}
          <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>Track Record ({premiumTimeSeriesData.length} Years)</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
              <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#16a34a" }}>{premiumTimeSeriesData.filter(d => d.premium >= 0).length}</div>
                <div style={{ fontSize: 10, color: "#15803d", fontWeight: 600 }}>Winning</div>
                <div style={{ fontSize: 9, color: "#64748b" }}>Avg +{(premiumTimeSeriesData.filter(d => d.premium >= 0).reduce((a, b) => a + b.premium, 0) / Math.max(1, premiumTimeSeriesData.filter(d => d.premium >= 0).length)).toFixed(1)}%</div>
              </div>
              <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#dc2626" }}>{premiumTimeSeriesData.filter(d => d.premium < 0).length}</div>
                <div style={{ fontSize: 10, color: "#b91c1c", fontWeight: 600 }}>Losing</div>
                <div style={{ fontSize: 9, color: "#64748b" }}>Avg {(premiumTimeSeriesData.filter(d => d.premium < 0).reduce((a, b) => a + b.premium, 0) / Math.max(1, premiumTimeSeriesData.filter(d => d.premium < 0).length)).toFixed(1)}%</div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, padding: 8, textAlign: "center" }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#16a34a" }}>{premiumTimeSeriesData.length > 0 ? `+${Math.max(...premiumTimeSeriesData.map(d => d.premium)).toFixed(1)}%` : "…"}</div>
                <div style={{ fontSize: 9, color: "#64748b" }}>Best Year</div>
              </div>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, padding: 8, textAlign: "center" }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#dc2626" }}>{premiumTimeSeriesData.length > 0 ? `${Math.min(...premiumTimeSeriesData.map(d => d.premium)).toFixed(1)}%` : "…"}</div>
                <div style={{ fontSize: 9, color: "#64748b" }}>Worst Year</div>
              </div>
            </div>
          </div>

          {/* Key Stats */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "1px solid #a7f3d0", borderRadius: 10, padding: 12, textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: "#059669", lineHeight: 1 }}>{typeof winRate === "number" ? `${winRate}%` : "…"}</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#047857", marginTop: 2 }}>Win Rate</div>
            </div>
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12, textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#2563eb" }}>{typeof rdPremium === "number" ? `+${rdPremium.toFixed(1)}%` : "…"}</div>
              <div style={{ fontSize: 9, color: "#64748b", marginTop: 2 }}>Avg Annual Premium</div>
            </div>
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12, textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#7c3aed" }}>{typeof tStat === "number" ? `t=${tStat.toFixed(1)}` : "t=…"}</div>
              <div style={{ fontSize: 9, color: "#64748b", marginTop: 2 }}>t-statistic (NW)</div>
            </div>
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12, textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#0891b2" }}>{typeof etaSquared20yr === "number" ? etaSquared20yr.toFixed(2) : "…"}</div>
              <div style={{ fontSize: 9, color: "#64748b", marginTop: 2 }}>Effect Size (η²)</div>
            </div>
          </div>
        </div>

        {/* Row 3: Key Insights */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#166534", marginBottom: 4 }}>📊 Consistent Pattern</div>
            <div style={{ fontSize: 11, color: "#15803d" }}>{typeof winRate === "number" ? `Premium persists in ${winRate}% of years across market cycles.` : "Premium is positive in most years across market cycles (see annual series)."}</div>
          </div>
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#1e40af", marginBottom: 4 }}>📈 Monotonic Returns</div>
            <div style={{ fontSize: 11, color: "#1e3a8a" }}>Returns increase linearly from Q1 to Q5; true factor behavior.</div>
          </div>
          <div style={{ background: "#fefce8", border: "1px solid #fde047", borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#a16207", marginBottom: 4 }}>⏳ Patient Capital</div>
            <div style={{ fontSize: 11, color: "#92400e" }}>Premium varies yearly. 3-5+ year holding recommended.</div>
          </div>
        </div>
      </div>
    </Slide>
  )
}
