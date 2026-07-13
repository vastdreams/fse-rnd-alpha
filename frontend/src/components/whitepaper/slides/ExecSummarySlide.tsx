/**
 * PATH: frontend/src/components/whitepaper/slides/ExecSummarySlide.tsx
 * PURPOSE: Slide 2 – Implementation Summary: rules, expectations, drivers.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Slide, MetricCard, SectionBox, GrowthChart } from "../slide-components"

export function ExecSummarySlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const {
    invPortfolioNet, invBenchmarkNet, invSp500Annualized, netPremium,
    invNetExcessVsSPY, invTurnoverAvg, invNHoldings, investableGrowthData,
    invStartYear, invEndYear, invRoundTripCostPer100PctTurnover, invBenchmarkCostPct,
  } = data

  return (
    <Slide key="how-to-make-money" slideNumber={2} totalSlides={totalSlides} title="Implementation Summary" subtitle="Rules, expectations, and what drives the premium" accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Key numbers */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 12 }}>
          <MetricCard value={typeof invPortfolioNet?.annualized_return === "number" ? `${invPortfolioNet.annualized_return.toFixed(1)}%` : "…"} label="Portfolio ann. (net)" accent="emerald" />
          <MetricCard value={typeof invSp500Annualized === "number" ? `${invSp500Annualized.toFixed(1)}%` : "…"} label="SPY ann. (gross)" accent="blue" />
          <MetricCard value={typeof netPremium === "number" ? `+${netPremium.toFixed(1)} pp` : typeof invNetExcessVsSPY === "number" ? `+${invNetExcessVsSPY.toFixed(1)} pp` : "…"} label="Net excess vs SPY /yr" accent="purple" />
          <MetricCard value={typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"} label="Turnover (avg)" accent="amber" />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, alignItems: "start" }}>
          {/* Playbook */}
          <SectionBox title="Playbook (60 seconds)" accent="slate">
            <ol style={{ fontSize: 13, color: "#334155", lineHeight: 1.7, paddingLeft: 18, margin: 0 }}>
              <li><strong>Each June:</strong> compute <strong>R&amp;D / Revenue</strong> using prior fiscal-year fundamentals.</li>
              <li><strong>Rank:</strong> all S&amp;P 500 firms by R&amp;D intensity.</li>
              <li><strong>Buy:</strong> top <strong>{invNHoldings}</strong> names equal-weight (ETF-like), or buy the full top quintile for broad factor exposure.</li>
              <li><strong>Hold:</strong> July-June; <strong>rebalance annually</strong>.</li>
              <li><strong>Time horizon:</strong> treat it like a 5+ year sleeve (innovation pays with a lag).</li>
            </ol>
            <div style={{ marginTop: 12, background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 4 }}>Why this works (in plain English)</div>
              <div style={{ fontSize: 13, color: "#0f172a", lineHeight: 1.6 }}>
                R&amp;D creates intangible assets that are hard to value. Markets tend to underreact, and the payoff shows up over multi-year horizons.
              </div>
            </div>
            <div style={{ marginTop: 12, background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>Defaults (copy/paste)</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {[
                  { k: "Holdings", v: `Top ${invNHoldings} (equal-weight)` },
                  { k: "Rebalance", v: "Annual (end of June)" },
                  { k: "Risk control", v: "Add sector caps (optional)" },
                  { k: "Horizon", v: "5+ years (lagged payoffs)" },
                ].map((row, i) => (
                  <div key={i} style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: 10 }}>
                    <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, marginBottom: 2 }}>{row.k}</div>
                    <div style={{ fontSize: 12, color: "#0f172a", fontWeight: 700, lineHeight: 1.35 }}>{row.v}</div>
                  </div>
                ))}
              </div>
            </div>
          </SectionBox>

          {/* Performance profile */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a" }}>Performance profile (net)</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>{invStartYear}-{invEndYear}</div>
            </div>
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 10, fontSize: 12, color: "#64748b", fontWeight: 700, paddingBottom: 8, borderBottom: "1px solid #e2e8f0" }}>
                <div>Metric</div><div style={{ textAlign: "right" }}>R&amp;D</div><div style={{ textAlign: "right" }}>EW cohort</div>
              </div>
              {[
                { k: "Annualized return", a: typeof invPortfolioNet?.annualized_return === "number" ? `${invPortfolioNet.annualized_return.toFixed(2)}%` : "…", b: typeof invBenchmarkNet?.annualized_return === "number" ? `${invBenchmarkNet.annualized_return.toFixed(2)}%` : "…" },
                { k: "Volatility", a: typeof invPortfolioNet?.volatility === "number" ? `${invPortfolioNet.volatility.toFixed(2)}%` : "…", b: typeof invBenchmarkNet?.volatility === "number" ? `${invBenchmarkNet.volatility.toFixed(2)}%` : "…" },
                { k: "Sharpe", a: typeof invPortfolioNet?.sharpe_ratio === "number" ? invPortfolioNet.sharpe_ratio.toFixed(3) : "…", b: typeof invBenchmarkNet?.sharpe_ratio === "number" ? invBenchmarkNet.sharpe_ratio.toFixed(3) : "…" },
                { k: "Max drawdown", a: typeof invPortfolioNet?.max_drawdown === "number" ? `${invPortfolioNet.max_drawdown.toFixed(2)}%` : "…", b: typeof invBenchmarkNet?.max_drawdown === "number" ? `${invBenchmarkNet.max_drawdown.toFixed(2)}%` : "…" },
              ].map((row, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 10, padding: "10px 0", borderBottom: i === 3 ? "none" : "1px solid #eef2f7", fontSize: 13, color: "#334155", alignItems: "center" }}>
                  <div style={{ fontWeight: 600 }}>{row.k}</div>
                  <div style={{ textAlign: "right", fontWeight: 800, color: "#059669" }}>{row.a}</div>
                  <div style={{ textAlign: "right", fontWeight: 700, color: "#2563eb" }}>{row.b}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10 }}><GrowthChart data={investableGrowthData} width={320} height={140} /></div>
            <div style={{ marginTop: 10, fontSize: 10, color: "#94a3b8", lineHeight: 1.45 }}>
              Costs: round-trip cost per 100% turnover {typeof invRoundTripCostPer100PctTurnover === "number" ? `${invRoundTripCostPer100PctTurnover.toFixed(3)}%` : "…"}; benchmark cost {typeof invBenchmarkCostPct === "number" ? `${invBenchmarkCostPct.toFixed(2)}%` : "…"} (model).
            </div>
          </div>
        </div>

        {/* Bottom: fit + risks */}
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#1e40af", marginBottom: 6 }}>Who this is for</div>
            <ul style={{ fontSize: 12, color: "#1e3a8a", lineHeight: 1.6, paddingLeft: 18, margin: 0 }}>
              <li>Long-horizon investors (5+ years)</li>
              <li>Comfortable with factor volatility and tracking error</li>
              <li>Want systematic exposure to innovation</li>
            </ul>
          </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#92400e", marginBottom: 6 }}>When it hurts</div>
            <ul style={{ fontSize: 12, color: "#78350f", lineHeight: 1.6, paddingLeft: 18, margin: 0 }}>
              <li>Risk-off / high-rate regimes that punish long-duration growth</li>
              <li>Sector concentration (tech/healthcare) without caps</li>
              <li>Short holding periods (innovation needs time)</li>
            </ul>
          </div>
        </div>
      </div>
    </Slide>
  )
}
