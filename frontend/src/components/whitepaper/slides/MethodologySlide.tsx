/**
 * PATH: frontend/src/components/whitepaper/slides/MethodologySlide.tsx
 * PURPOSE: Slide 4 – Methodology: quintile formation, statistical analysis, timeline.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Slide } from "../slide-components"

export function MethodologySlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const { totalCompanies, invTurnoverAvg, invTradingCostEstPct, sampleStartYear, sampleEndYear } = data

  return (
    <Slide key="methodology" slideNumber={4} totalSlides={totalSlides} title="Methodology" subtitle="How we form quintile portfolios and estimate the premium" accent="blue">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12, alignItems: "start" }}>
          {/* Step 1 */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#3b82f6", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, flexShrink: 0 }}>1</div>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#1e40af", margin: 0 }}>Calculate R&D Intensity</h3>
            </div>
            <div style={{ background: "#3b82f6", borderRadius: 8, padding: 12, marginBottom: 12, textAlign: "center" }}>
              <div style={{ fontSize: 13, color: "white", marginBottom: 4 }}>R&D Intensity</div>
              <div style={{ fontSize: 11, color: "#bfdbfe", marginBottom: 6 }}>=</div>
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 12, color: "white", fontWeight: 500 }}>R&D Expense</span>
                <span style={{ fontSize: 14, color: "#bfdbfe" }}>/</span>
                <span style={{ fontSize: 12, color: "white", fontWeight: 500 }}>Revenue</span>
              </div>
            </div>
            <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.5 }}>
              Normalizes R&D by firm size for fair comparison. A 15% intensity means $15 R&D per $100 revenue.
            </div>
          </div>

          {/* Step 2 */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#8b5cf6", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, flexShrink: 0 }}>2</div>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#6b21a8", margin: 0 }}>Form Quintile Portfolios</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
              {[
                { q: "Q1 (Low)", range: "0-3%", color: "#dc2626", bg: "#fef2f2" },
                { q: "Q2", range: "3-6%", color: "#64748b", bg: "white" },
                { q: "Q3", range: "6-10%", color: "#64748b", bg: "white" },
                { q: "Q4", range: "10-15%", color: "#64748b", bg: "white" },
                { q: "Q5 (High)", range: "15%+", color: "#16a34a", bg: "#f0fdf4" },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: item.bg, padding: "6px 10px", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: item.color }}>{item.q}</span>
                  <span style={{ fontSize: 12, color: "#475569" }}>{item.range}</span>
                </div>
              ))}
            </div>
            <div style={{ fontSize: 11, color: "#64748b" }}>~{typeof totalCompanies === "number" ? Math.round(totalCompanies / 5) : "..."} firms per quintile</div>
          </div>

          {/* Step 3 */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#059669", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, flexShrink: 0 }}>3</div>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#047857", margin: 0 }}>Statistical Analysis</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { test: "ANOVA", desc: "Quintile means differ?" },
                { test: "t-test", desc: "Q5 vs Q1 significance" },
                { test: "Newey-West", desc: "HAC standard errors" },
                { test: "Effect size", desc: "η² magnitude" },
                { test: "Rolling", desc: "5, 10, 20yr windows" },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "white", padding: "6px 10px", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: "#047857" }}>{item.test}</span>
                  <span style={{ fontSize: 11, color: "#64748b" }}>{item.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Key methodological choices */}
        <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, overflow: "hidden" }}>
          <div style={{ background: "#1e40af", padding: "8px 14px" }}>
            <h3 style={{ fontSize: 12, fontWeight: 600, color: "white", margin: 0 }}>Key Methodological Choices</h3>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", fontSize: 11 }}>
            {[
              { label: "Return Convention", value: "July-June (Fama-French), ensuring 10-K is public before formation" },
              { label: "Survivorship Bias", value: "Point-in-time membership (where available) + cash-after-exit + delisting sensitivity (not a single injected proxy)" },
              { label: "Data Sources", value: "FMP for fundamentals/prices; Ken French for factors" },
              { label: "Portfolio Weights", value: "Equal-weight within quintiles (no mega-cap bias)" },
              { label: "Inference", value: "Non-overlapping annual HML; Newey-West standard errors" },
              { label: "Rebalancing", value: `Annual (June); avg turnover ${typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"}; est. cost ${typeof invTradingCostEstPct === "number" ? `${invTradingCostEstPct.toFixed(3)}%` : "…"}` },
            ].map((item, i) => (
              <div key={i} style={{ padding: "8px 14px", borderBottom: i < 4 ? "1px solid #e2e8f0" : "none", borderRight: i % 2 === 0 ? "1px solid #e2e8f0" : "none", background: i % 2 === 0 ? "#f8fafc" : "white" }}>
                <div style={{ fontWeight: 600, color: "#1e40af", marginBottom: 2 }}>{item.label}</div>
                <div style={{ color: "#475569", lineHeight: 1.4 }}>{item.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Formation timeline */}
        <div style={{ marginTop: 12, background: "linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%)", border: "1px solid #bfdbfe", borderRadius: 10, padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#1e40af", marginBottom: 8 }}>Formation timeline (no look-ahead)</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
            {[
              { t: "Fiscal year ends", d: "Companies close FY" },
              { t: "10-K filed", d: "Fundamentals become public" },
              { t: "End of June", d: "Rank by R&D/Rev" },
              { t: "July-June", d: "Hold for 12 months" },
            ].map((x, i) => (
              <div key={i} style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: "#1e40af", marginBottom: 4 }}>{x.t}</div>
                <div style={{ fontSize: 10, color: "#475569", lineHeight: 1.35 }}>{x.d}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 8, fontSize: 10, color: "#1e3a8a" }}>
            We use <strong>July-June returns</strong> so filings are public before portfolio formation.
          </div>
        </div>

        {/* Sample info footer */}
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          {[
            { label: "Universe", value: "S&P 500" },
            { label: "Sample", value: `${sampleStartYear}-${sampleEndYear}` },
            { label: "Firms", value: typeof totalCompanies === "number" ? String(totalCompanies) : "…" },
            { label: "Obs/Year", value: typeof totalCompanies === "number" ? `~${Math.round(totalCompanies * 0.6)}` : "…" },
          ].map((item, i) => (
            <div key={i} style={{ background: "#3b82f6", borderRadius: 8, padding: 10, textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#bfdbfe" }}>{item.label}</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "white" }}>{item.value}</div>
            </div>
          ))}
        </div>
      </div>
    </Slide>
  )
}
