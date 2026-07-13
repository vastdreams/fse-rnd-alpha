/**
 * PATH: frontend/src/components/whitepaper/slides/ConclusionSlide.tsx
 * PURPOSE: Slide 11 – Conclusion: summary, key takeaways, call to action.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Slide } from "../slide-components"

export function ConclusionSlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const {
    rdPremium, tStat, winRate, etaSquared5yr, etaSquared20yr,
    ff5AlphaPercent, ff5AlphaPValue, totalCompanies,
    invTurnoverAvg, annualTradingCost, invTradingCostEstPct, premiumCaptureRate,
  } = data

  return (
    <Slide key="conclusion" slideNumber={11} totalSlides={totalSlides} title="Conclusion" accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Main finding */}
        <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 12, padding: 20, marginBottom: 20, textAlign: "center" }}>
          <div style={{ fontSize: 14, color: "#065f46", marginBottom: 8 }}>The R&D Premium is Real, Persistent, and Implementable</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#047857", lineHeight: 1 }}>{typeof rdPremium === "number" ? `+${rdPremium.toFixed(1)}%` : "…"}</div>
          <div style={{ fontSize: 13, color: "#065f46", marginTop: 8 }}>Annual premium for high-R&D (Q5) vs low-R&D (Q1) firms</div>
        </div>

        {/* Key metrics */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
          <div style={{ background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: 10, padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#047857" }}>{typeof rdPremium === "number" ? `+${rdPremium.toFixed(1)}%` : "…"}</div>
            <div style={{ fontSize: 11, color: "#065f46" }}>Annual Premium</div>
          </div>
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#1d4ed8" }}>{typeof etaSquared20yr === "number" ? etaSquared20yr.toFixed(2) : "…"}</div>
            <div style={{ fontSize: 11, color: "#1e40af" }}>20yr Effect Size</div>
          </div>
          <div style={{ background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: 10, padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#7e22ce" }}>{typeof tStat === "number" ? `t=${tStat.toFixed(1)}` : "t=…"}</div>
            <div style={{ fontSize: 11, color: "#6b21a8" }}>Significance</div>
          </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#b45309" }}>{typeof winRate === "number" ? `${winRate}%` : "…"}</div>
            <div style={{ fontSize: 11, color: "#92400e" }}>Win Rate</div>
          </div>
        </div>

        {/* Key takeaways */}
        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 16, padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", marginBottom: 20, textAlign: "center" }}>Key Takeaways for Practitioners</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
            {[
              {
                num: "1",
                text: typeof ff5AlphaPercent === "number" && typeof ff5AlphaPValue === "number"
                  ? `R&D intensity is an economically meaningful predictor of future stock returns (FF5 monthly alpha ${ff5AlphaPercent.toFixed(2)}%, p ${ff5AlphaPValue < 0.001 ? "<0.001" : ff5AlphaPValue.toFixed(3)}), with effects persisting across multiple horizons.`
                  : "R&D intensity is an economically meaningful predictor of future stock returns (FF5 monthly alpha is statistically significant), with effects persisting across multiple horizons.",
              },
              {
                num: "2",
                text: typeof etaSquared5yr === "number" && typeof etaSquared20yr === "number"
                  ? `Effect size grows with horizon (η² ${etaSquared5yr.toFixed(2)} to ${etaSquared20yr.toFixed(2)}), suggesting R&D benefits compound. Patience is rewarded.`
                  : "Effect size grows with horizon (η² rises), suggesting R&D benefits compound. Patience is rewarded.",
              },
              { num: "3", text: "Results align with decades of academic research on intangible asset mispricing (Chan et al., Lev & Sougiannis)." },
              {
                num: "4",
                text: typeof invTurnoverAvg === "number" && (typeof annualTradingCost === "number" || typeof invTradingCostEstPct === "number") && typeof premiumCaptureRate === "number"
                  ? `Strategy is implementable: ~${invTurnoverAvg.toFixed(0)}% turnover, ~${(typeof annualTradingCost === "number" ? annualTradingCost : (invTradingCostEstPct as number)).toFixed(3)}% trading costs/yr, ~${premiumCaptureRate.toFixed(1)}% premium capture rate.`
                  : "Strategy is implementable: annual rebalance, low-to-moderate turnover, and trading costs are small relative to the historical edge (see snapshot cost calibration).",
              },
            ].map((item, i) => (
              <div key={i} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#059669", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, flexShrink: 0 }}>{item.num}</div>
                <div style={{ fontSize: 14, color: "#334155", lineHeight: 1.6 }}>{item.text}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Call to action */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div style={{ background: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)", border: "2px solid #3b82f6", borderRadius: 16, padding: 20 }}>
            <h4 style={{ fontSize: 16, fontWeight: 700, color: "#1e40af", marginBottom: 12 }}>📖 Further Reading</h4>
            <p style={{ fontSize: 13, color: "#1e3a8a", lineHeight: 1.6, marginBottom: 12 }}>Full methodology, interactive charts, and company-level data available at:</p>
            <div style={{ background: "#1e40af", borderRadius: 10, padding: 12, textAlign: "center", marginBottom: 12 }}>
              <span style={{ fontSize: 16, fontWeight: 600, color: "white" }}>research.finsoeasy.com</span>
            </div>
            <div style={{ fontSize: 12, color: "#3b82f6", lineHeight: 1.5 }}>
              <div style={{ marginBottom: 6 }}>✓ Interactive portfolio builder</div>
              <div style={{ marginBottom: 6 }}>✓ 500+ company R&D profiles</div>
              <div>✓ Downloadable data exports</div>
            </div>
          </div>
          <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 16, padding: 20 }}>
            <h4 style={{ fontSize: 16, fontWeight: 700, color: "#047857", marginBottom: 12 }}>📧 Get in Touch</h4>
            <p style={{ fontSize: 13, color: "#065f46", lineHeight: 1.6, marginBottom: 12 }}>Questions, feedback, or collaboration opportunities:</p>
            <div style={{ background: "#047857", borderRadius: 10, padding: 12, textAlign: "center", marginBottom: 12 }}>
              <span style={{ fontSize: 16, fontWeight: 600, color: "white" }}>abhishek@finsoeasy.com</span>
            </div>
            <div style={{ fontSize: 12, color: "#059669", lineHeight: 1.5 }}>
              <div style={{ marginBottom: 6 }}>• Institutional inquiries welcome</div>
              <div style={{ marginBottom: 6 }}>• Research collaboration</div>
              <div>• Media and speaking requests</div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: 20, display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 16, borderTop: "1px solid #e2e8f0" }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#334155" }}>Abhishek Sehgal</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>January 2026</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "#64748b" }}>Data: FMP (Tier-1) | Ken French | {typeof totalCompanies === "number" ? totalCompanies : "..."} S&amp;P 500 firms</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#059669" }}>R&D Alpha Research</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>research.finsoeasy.com</div>
          </div>
        </div>
      </div>
    </Slide>
  )
}
