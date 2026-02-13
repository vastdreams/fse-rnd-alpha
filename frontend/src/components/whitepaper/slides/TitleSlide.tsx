/**
 * PATH: frontend/src/components/whitepaper/slides/TitleSlide.tsx
 * PURPOSE: Slide 1 – Title / cover slide with hero metrics and growth chart.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Badge } from "@/components/ui/badge"
import { Slide, MetricCard, SectionBox, GrowthChart } from "../slide-components"

export function TitleSlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const {
    netPremium, invNetExcessVsSPY, invPortfolioNet, rdPremium, tStat, winRate,
    invTurnoverAvg, investableGrowthData, invStartYear, invEndYear,
    invPortfolioMultiple, invBenchmarkMultiple, invSp500Multiple, invNHoldings,
  } = data

  return (
    <Slide key="title" slideNumber={1} totalSlides={totalSlides} accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
        {/* Top row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Badge style={{ backgroundColor: "#ecfdf5", color: "#047857", borderColor: "#a7f3d0", fontSize: 13, padding: "4px 14px" }}>
            Research Whitepaper
          </Badge>
          <div style={{ fontSize: 12, color: "#64748b" }}>Abhishek Sehgal · January 2026 · PDF-ready</div>
        </div>

        {/* Title */}
        <div style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: 44, fontWeight: 900, color: "#0f172a", margin: 0, lineHeight: 1.05 }}>R&amp;D Alpha</h1>
          <p style={{ fontSize: 15, color: "#475569", marginTop: 8, marginBottom: 0, maxWidth: 640 }}>
            A rules-based tilt toward innovation that has historically delivered long-horizon outperformance.
          </p>
        </div>

        {/* Money row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          <MetricCard
            value={typeof netPremium === "number" ? `+${netPremium.toFixed(1)}%` : typeof invNetExcessVsSPY === "number" ? `+${invNetExcessVsSPY.toFixed(1)}%` : "…"}
            label="Net excess vs SPY /yr"
            accent="emerald"
          />
          <MetricCard value={typeof invPortfolioNet?.sharpe_ratio === "number" ? invPortfolioNet.sharpe_ratio.toFixed(2) : "…"} label="Sharpe (net)" accent="blue" />
          <MetricCard value={typeof invPortfolioNet?.max_drawdown === "number" ? `${invPortfolioNet.max_drawdown.toFixed(1)}%` : "…"} label="Max drawdown" accent="purple" />
          <MetricCard value={typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"} label="Avg turnover" accent="amber" />
        </div>

        {/* Main area */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, alignItems: "start" }}>
          <SectionBox title="Why should I care?" accent="emerald">
            <ul style={{ fontSize: 13, color: "#334155", lineHeight: 1.6, paddingLeft: 18, margin: 0 }}>
              <li><strong>Actionable edge:</strong> buy firms investing heavily in R&amp;D (innovation) and avoid low-R&amp;D laggards.</li>
              <li>
                <strong>Factor evidence:</strong>{" "}
                {typeof rdPremium === "number" ? (
                  <>
                    Q5-Q1 premium is <strong>+{rdPremium.toFixed(1)}%/yr</strong>
                    {typeof tStat === "number" || typeof winRate === "number" ? (
                      <> ({typeof tStat === "number" ? `annual t = ${tStat.toFixed(2)}` : ""}{typeof tStat === "number" && typeof winRate === "number" ? ", " : ""}{typeof winRate === "number" ? `win rate ${winRate}%` : ""}).</>
                    ) : "."}{" "}
                    Statistically significant in monthly factor spanning tests (FF5 p&lt;0.01); cross-sectional Fama-MacBeth is directionally consistent.
                  </>
                ) : <>Premium metrics loading…</>}
              </li>
              <li><strong>Implementable:</strong> annual rebalance, low turnover, costs are small vs. the historical edge.</li>
            </ul>
            <div style={{ marginTop: 10, background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 4 }}>If you only remember one rule</div>
              <div style={{ fontSize: 13, color: "#0f172a", lineHeight: 1.5 }}>
                Treat this like a <strong>5+ year factor sleeve</strong> (innovation benefits take time).
              </div>
            </div>
            <div style={{ marginTop: 10, background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 4 }}>What to do (practical)</div>
              <div style={{ fontSize: 13, color: "#0f172a", lineHeight: 1.5 }}>
                Start with a <strong>small sleeve</strong> (5-15%), rebalance annually, and add <strong>sector caps</strong> if you want more diversification.
              </div>
            </div>
          </SectionBox>

          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a" }}>ETF backtest: growth of $1 (net)</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>{invStartYear}-{invEndYear}</div>
            </div>
            <GrowthChart data={investableGrowthData} width={320} height={140} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginTop: 10 }}>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 900, color: "#059669" }}>{typeof invPortfolioMultiple === "number" ? `${invPortfolioMultiple.toFixed(1)}x` : "-"}</div>
                <div style={{ fontSize: 10, color: "#64748b" }}>R&amp;D portfolio</div>
              </div>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 900, color: "#2563eb" }}>{typeof invBenchmarkMultiple === "number" ? `${invBenchmarkMultiple.toFixed(1)}x` : "-"}</div>
                <div style={{ fontSize: 10, color: "#64748b" }}>EW cohort</div>
              </div>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 900, color: "#94a3b8" }}>{typeof invSp500Multiple === "number" ? `${invSp500Multiple.toFixed(1)}x` : "-"}</div>
                <div style={{ fontSize: 10, color: "#64748b" }}>S&amp;P 500</div>
              </div>
            </div>
            <div style={{ marginTop: 10, fontSize: 10, color: "#94a3b8", lineHeight: 1.4 }}>
              Notes: 20-stock equal-weight basket, annual reconstitution, July-June convention. Backtest is informational (not advice).
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#1e40af", marginBottom: 6 }}>Implementation checklist</div>
            <ul style={{ fontSize: 12, color: "#1e3a8a", lineHeight: 1.55, paddingLeft: 18, margin: 0 }}>
              <li>June: compute R&amp;D/Rev (prior FY)</li>
              <li>Buy top {invNHoldings} equal-weight</li>
              <li>Hold July-June; rebalance annually</li>
            </ul>
          </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#92400e", marginBottom: 6 }}>Risk controls</div>
            <ul style={{ fontSize: 12, color: "#78350f", lineHeight: 1.55, paddingLeft: 18, margin: 0 }}>
              <li>Add sector caps (avoid tech/healthcare crowding)</li>
              <li>Size for drawdowns (don&apos;t lever it)</li>
              <li>Stick to a rules-based rebalance schedule</li>
            </ul>
          </div>
          <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#166534", marginBottom: 6 }}>Expected behavior</div>
            <ul style={{ fontSize: 12, color: "#166534", lineHeight: 1.55, paddingLeft: 18, margin: 0 }}>
              <li>Edge is long-horizon (3-5 year lag)</li>
              <li>Tracking error is normal</li>
              <li>Patience is the &quot;cost&quot; you pay</li>
            </ul>
          </div>
        </div>
      </div>
    </Slide>
  )
}
