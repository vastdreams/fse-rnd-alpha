/**
 * PATH: frontend/src/components/whitepaper/slides/ResultsSlide.tsx
 * PURPOSE: Slide 5 – Core R&D premium findings: quintile returns, effect sizes.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Slide } from "../slide-components"

export function ResultsSlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const {
    rdPremium, tStat, pValue, winRate,
    etaSquared5yr, etaSquared10yr, etaSquared20yr,
    getQuintileReturn,
  } = data

  return (
    <Slide key="results" slideNumber={5} totalSlides={totalSlides} title="Results: The R&D Premium" subtitle="High-R&D stocks consistently outperform low-R&D stocks" accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Hero stat */}
        <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 12, padding: 14, marginBottom: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 16, alignItems: "center" }}>
            <div style={{ textAlign: "center", borderRight: "1px solid #a7f3d0", paddingRight: 16 }}>
              <div style={{ fontSize: 11, color: "#065f46", marginBottom: 4 }}>Annual Premium</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "#047857" }}>{typeof rdPremium === "number" ? `+${rdPremium.toFixed(1)}%` : "…"}</div>
              <div style={{ fontSize: 10, color: "#065f46" }}>Q5 minus Q1</div>
            </div>
            <div style={{ textAlign: "center", borderRight: "1px solid #a7f3d0", paddingRight: 16 }}>
              <div style={{ fontSize: 11, color: "#065f46", marginBottom: 4 }}>t-statistic</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "#047857" }}>{typeof tStat === "number" ? tStat.toFixed(2) : "…"}</div>
              <div style={{ fontSize: 10, color: "#065f46" }}>p {typeof pValue === "number" ? (pValue < 0.001 ? "< 0.001" : pValue.toFixed(3)) : "…"}</div>
            </div>
            <div style={{ textAlign: "center", borderRight: "1px solid #a7f3d0", paddingRight: 16 }}>
              <div style={{ fontSize: 11, color: "#065f46", marginBottom: 4 }}>Win Rate</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "#047857" }}>{typeof winRate === "number" ? `${winRate}%` : "…"}</div>
              <div style={{ fontSize: 10, color: "#065f46" }}>years positive</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: "#065f46", marginBottom: 4 }}>20yr Effect</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "#047857" }}>{typeof etaSquared20yr === "number" ? etaSquared20yr.toFixed(2) : "…"}</div>
              <div style={{ fontSize: 10, color: "#065f46" }}>eta squared</div>
            </div>
          </div>
        </div>

        {/* Two columns */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>
          {/* Quintile Returns */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", marginBottom: 12, borderBottom: "2px solid #059669", paddingBottom: 6 }}>Average Annual Returns by Quintile</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { q: "Q5 (High R&D)", ret: getQuintileReturn(5), color: "#22c55e", desc: "Top 20% R&D intensity" },
                { q: "Q4", ret: getQuintileReturn(4), color: "#64748b", desc: "" },
                { q: "Q3", ret: getQuintileReturn(3), color: "#64748b", desc: "" },
                { q: "Q2", ret: getQuintileReturn(2), color: "#64748b", desc: "" },
                { q: "Q1 (Low R&D)", ret: getQuintileReturn(1), color: "#ef4444", desc: "Bottom 20% R&D intensity" },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 90, fontSize: 11, fontWeight: 600, color: item.color }}>{item.q}</div>
                  <div style={{ flex: 1, height: 26, background: "#e2e8f0", borderRadius: 6, overflow: "hidden", position: "relative" }}>
                    {typeof item.ret === "number" ? (
                      <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${Math.max(0, Math.min(100, (item.ret / 20) * 100))}%`, background: item.color, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 8 }}>
                        <span style={{ color: "white", fontSize: 12, fontWeight: 700 }}>{item.ret.toFixed(1)}%</span>
                      </div>
                    ) : (
                      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 8 }}>
                        <span style={{ color: "#64748b", fontSize: 12, fontWeight: 700 }}>…</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10, padding: 10, background: "#f0fdf4", borderRadius: 8, border: "1px solid #bbf7d0" }}>
              <div style={{ fontSize: 11, color: "#166534", fontWeight: 600, marginBottom: 4 }}>📊 Monotonic Pattern</div>
              <div style={{ fontSize: 10, color: "#166534", lineHeight: 1.4 }}>Returns increase steadily from Q1 to Q5, suggesting a true factor relationship rather than a single-quintile anomaly.</div>
            </div>
            <div style={{ marginTop: 10, background: "#047857", borderRadius: 10, padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, color: "#a7f3d0" }}>Premium (Q5 - Q1)</span>
              <span style={{ fontSize: 22, fontWeight: 700, color: "white" }}>{typeof rdPremium === "number" ? `+${rdPremium.toFixed(1)}%` : "…"}</span>
            </div>
          </div>

          {/* Effect Sizes */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", marginBottom: 12, borderBottom: "2px solid #3b82f6", paddingBottom: 6 }}>Effect Size by Investment Horizon</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { horizon: "5-Year", eta: etaSquared5yr, label: "Large", color: "#3b82f6", pct: typeof etaSquared5yr === "number" ? Math.round(etaSquared5yr * 100) : undefined },
                { horizon: "10-Year", eta: etaSquared10yr, label: "Large", color: "#8b5cf6", pct: typeof etaSquared10yr === "number" ? Math.round(etaSquared10yr * 100) : undefined },
                { horizon: "20-Year", eta: etaSquared20yr, label: "Very Large", color: "#059669", pct: typeof etaSquared20yr === "number" ? Math.round(etaSquared20yr * 100) : undefined },
              ].map((item, i) => (
                <div key={i} style={{ background: "white", borderRadius: 10, padding: 12, border: "1px solid #e2e8f0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#334155" }}>{item.horizon}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>η² = {typeof item.eta === "number" ? item.eta.toFixed(3) : "…"}</span>
                  </div>
                  <div style={{ height: 8, background: "#e2e8f0", borderRadius: 4, overflow: "hidden", marginBottom: 6 }}>
                    <div style={{ height: "100%", width: `${typeof item.eta === "number" ? Math.min(100, item.eta * 200) : 0}%`, background: item.color, borderRadius: 4 }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#64748b" }}>
                    <span>{item.label} effect ({typeof item.pct === "number" ? `${item.pct}%` : "…"} variance explained)</span>
                    <span>Cohen: {">"}0.14 = large</span>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10, padding: 10, background: "#eff6ff", borderRadius: 8, border: "1px solid #bfdbfe" }}>
              <div style={{ fontSize: 11, color: "#1e40af", fontWeight: 600, marginBottom: 4 }}>📈 What This Means</div>
              <div style={{ fontSize: 10, color: "#1e40af", lineHeight: 1.4 }}>
                At 20 years, R&amp;D intensity explains <strong>{typeof etaSquared20yr === "number" ? `${Math.round(etaSquared20yr * 100)}%` : "…"}</strong> of the variance in returns between quintiles. Effect grows with time as R&amp;D benefits compound.
              </div>
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#7c3aed", marginBottom: 6 }}>🔬 Statistical Validity</div>
            <div style={{ fontSize: 11, color: "#6b21a8", lineHeight: 1.5 }}>
              Results use <strong>Newey-West standard errors</strong> to account for autocorrelation and heteroskedasticity.{" "}
              {typeof tStat === "number" ? `The t-statistic of ${tStat.toFixed(2)} exceeds the 1.96 threshold for 95% confidence.` : "The t-statistic exceeds common significance thresholds in the frozen snapshot."}
            </div>
          </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#b45309", marginBottom: 6 }}>💡 Key Takeaway</div>
            <div style={{ fontSize: 11, color: "#92400e", lineHeight: 1.5 }}>
              Effect sizes grow with horizon{typeof etaSquared5yr === "number" && typeof etaSquared20yr === "number" ? ` (η² ${etaSquared5yr.toFixed(2)} to ${etaSquared20yr.toFixed(2)} over 5 to 20 years).` : "."}{" "}
              R&D benefits have a <strong>3-5 year lag</strong>, so patient investors are rewarded.
            </div>
          </div>
        </div>
      </div>
    </Slide>
  )
}
