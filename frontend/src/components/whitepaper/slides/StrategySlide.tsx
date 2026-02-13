/**
 * PATH: frontend/src/components/whitepaper/slides/StrategySlide.tsx
 * PURPOSE: Slide 9 – Investable Strategy: portfolio rules, cost analysis.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Slide } from "../slide-components"

export function StrategySlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const {
    netPremium, invNetExcessVsSPY, invPortfolioNet, invSp500Annualized,
    backtestPeriodLabel, invNHoldings, invTurnoverAvg, invTurnoverMax,
    invTradingCostEstPct, winRate,
  } = data

  return (
    <Slide key="strategy" slideNumber={9} totalSlides={totalSlides} title="Investable Strategy" subtitle="Practical implementation for practitioners" accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Hero */}
        <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 12, padding: 16, marginBottom: 16, textAlign: "center" }}>
          <div style={{ fontSize: 12, color: "#065f46", marginBottom: 6 }}>Investable edge survives costs</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#047857", lineHeight: 1 }}>
            {typeof netPremium === "number" ? `+${netPremium.toFixed(2)} pp/yr` : typeof invNetExcessVsSPY === "number" ? `+${invNetExcessVsSPY.toFixed(2)} pp/yr` : "…"}
          </div>
          <div style={{ fontSize: 12, color: "#065f46", marginTop: 8 }}>
            {typeof invPortfolioNet?.annualized_return === "number" && typeof invSp500Annualized === "number"
              ? `RD20 strategy: ${invPortfolioNet.annualized_return.toFixed(2)}% vs SPY: ${invSp500Annualized.toFixed(2)}% (${backtestPeriodLabel}).`
              : typeof netPremium === "number"
                ? `RD20 strategy spread vs SPY (net of costs): +${netPremium.toFixed(2)}% pp/yr (${backtestPeriodLabel}).`
                : "RD20 strategy spread vs SPY: … (net of costs)."}
          </div>
        </div>

        {/* Main content */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Portfolio Rules */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 16, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 16, borderBottom: "2px solid #059669", paddingBottom: 8 }}>Portfolio Construction Rules</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                { label: "Universe", value: "S&P 500 constituents", icon: "🏛️" },
                { label: "Signal", value: "R&D Expense / Revenue (fiscal year)", icon: "📊" },
                { label: "Portfolio", value: `Top ${invNHoldings} by R&D intensity (or full Q5)`, icon: "📈" },
                { label: "Formation Date", value: "End of June (after 10-K filings)", icon: "📅" },
                { label: "Holding Period", value: "12 months (July-June)", icon: "⏱️" },
                { label: "Weighting", value: `Equal-weight (${Math.round(100 / Math.max(1, invNHoldings))}% each)`, icon: "⚖️" },
                { label: "Rebalance", value: `Annual (avg turnover ${typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"})`, icon: "🔄" },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", background: "white", borderRadius: 10, padding: 10 }}>
                  <span style={{ fontSize: 18 }}>{item.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, color: "#64748b" }}>{item.label}</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "#0f172a" }}>{item.value}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cost Analysis + Metrics */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 16, padding: 20 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 16, borderBottom: "2px solid #3b82f6", paddingBottom: 8 }}>Transaction Cost Analysis</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  { label: "Annual Turnover", value: typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%${typeof invTurnoverMax === "number" ? ` (max ${invTurnoverMax.toFixed(0)}%)` : ""}` : "…", note: "Measured from annual reconstitution" },
                  { label: "Est. Trading Cost", value: typeof invTradingCostEstPct === "number" ? `${invTradingCostEstPct.toFixed(3)}%` : "…", note: "Cost per 100% turnover × turnover" },
                  { label: "Holdings Count", value: String(invNHoldings), note: "ETFlike basket (equal-weight)" },
                  { label: "Return Convention", value: "July-June", note: "Avoid look-ahead (10-K public before formation)" },
                ].map((item, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #e2e8f0" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 500, color: "#334155" }}>{item.label}</div>
                      <div style={{ fontSize: 11, color: "#94a3b8" }}>{item.note}</div>
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#3b82f6", textAlign: "right", minWidth: 100, flexShrink: 0 }}>{item.value}</div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              <div style={{ background: "#eff6ff", border: "2px solid #bfdbfe", borderRadius: 12, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#1d4ed8" }}>{typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"}</div>
                <div style={{ fontSize: 11, color: "#1e40af" }}>Turnover</div>
              </div>
              <div style={{ background: "#faf5ff", border: "2px solid #e9d5ff", borderRadius: 12, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#7e22ce" }}>{invNHoldings}</div>
                <div style={{ fontSize: 11, color: "#6b21a8" }}>Holdings</div>
              </div>
              <div style={{ background: "#fffbeb", border: "2px solid #fde68a", borderRadius: 12, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#b45309" }}>1x</div>
                <div style={{ fontSize: 11, color: "#92400e" }}>Annual</div>
              </div>
            </div>
          </div>
        </div>

        {/* Warning */}
        <div style={{ marginTop: 16, background: "linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%)", border: "2px solid #f59e0b", borderRadius: 12, padding: 16 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <div style={{ fontSize: 32 }}>⚠️</div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#92400e", marginBottom: 4 }}>Patience Required</div>
              <div style={{ fontSize: 13, color: "#78350f", lineHeight: 1.5 }}>
                R&D benefits manifest with a <strong>3-5 year lag</strong>. Short-term underperformance is possible (negative premium years: ~{typeof winRate === "number" ? `${(100 - winRate).toFixed(0)}%` : "…"}). This strategy is designed for <strong>long-term investors with 5+ year horizons</strong>.
              </div>
            </div>
          </div>
        </div>
      </div>
    </Slide>
  )
}
