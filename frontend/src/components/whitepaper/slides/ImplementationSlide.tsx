/**
 * PATH: frontend/src/components/whitepaper/slides/ImplementationSlide.tsx
 * PURPOSE: Slide 3 – Implementation Reality Check: coverage, concentration, signal.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import type { WhitepaperData } from "@/hooks/useWhitepaperData"
import { Slide, MetricCard } from "../slide-components"

export function ImplementationSlide({ data, totalSlides }: { data: WhitepaperData; totalSlides: number }) {
  const {
    eligible5yr, eligible10yr, eligible20yr, eligible5yrPct, eligible10yrPct, eligible20yrPct,
    invTurnoverAvg, invRoundTripCostPer100PctTurnover, invNHoldings,
    invSectorMix, invTopHoldings, rdProfileHigh, rdProfileMedium, rdProfileLow,
  } = data

  return (
    <Slide key="implementation-reality" slideNumber={3} totalSlides={totalSlides} title="Implementation Reality Check" subtitle="Coverage, concentration, and what you're really signing up for" accent="blue">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Top row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 12 }}>
          <MetricCard value={`${eligible20yr}`} label={`20yr coverage (${eligible20yrPct}%)`} accent="blue" />
          <MetricCard value={typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"} label="Avg turnover" accent="purple" />
          <MetricCard value={typeof invRoundTripCostPer100PctTurnover === "number" ? `${invRoundTripCostPer100PctTurnover.toFixed(3)}%` : "…"} label="Cost / 100% turnover" accent="amber" />
          <MetricCard value={`${invNHoldings}`} label="Holdings (ETF)" accent="emerald" />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, flex: 1 }}>
          {/* Left: what you own */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a", marginBottom: 10 }}>What you end up owning (ETFlike)</div>
            {/* Sector mix */}
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 8 }}>Sector mix of the {invNHoldings}-stock basket</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(invSectorMix.length ? invSectorMix : [{ sector: "Healthcare", weight: 50 }, { sector: "Technology", weight: 30 }, { sector: "Other", weight: 20 }])
                  .slice(0, 6)
                  .map((s, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 140, fontSize: 12, color: "#334155" }}>{s.sector}</div>
                      <div style={{ flex: 1, height: 20, background: "#e2e8f0", borderRadius: 6, overflow: "hidden" }}>
                        <div style={{ height: "100%", width: `${Math.min(100, s.weight)}%`, background: "linear-gradient(90deg, #2563eb, #60a5fa)", borderRadius: 6 }} />
                      </div>
                      <div style={{ width: 42, textAlign: "right", fontSize: 12, fontWeight: 800, color: "#1d4ed8" }}>{s.weight.toFixed(0)}%</div>
                    </div>
                  ))}
              </div>
              <div style={{ marginTop: 8, fontSize: 10, color: "#94a3b8" }}>Tip: add sector caps if you want a purer &quot;innovation&quot; sleeve.</div>
            </div>
            {/* Top holdings */}
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
                <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700 }}>Example names (highest R&amp;D intensity)</div>
                <div style={{ fontSize: 10, color: "#94a3b8" }}>R&amp;D/Rev can exceed 100% pre-revenue</div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 0.7fr", gap: 10, fontSize: 11, color: "#64748b", fontWeight: 700, paddingBottom: 8, borderBottom: "1px solid #eef2f7" }}>
                <div>Ticker</div><div>Sector</div><div style={{ textAlign: "right" }}>R&amp;D%</div>
              </div>
              {(invTopHoldings.length ? invTopHoldings : [{ symbol: "VRTX", sector: "Healthcare", rd_intensity: 142.4 }])
                .slice(0, 6)
                .map((h, i) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 0.7fr", gap: 10, padding: "9px 0", borderBottom: i === 5 ? "none" : "1px solid #eef2f7", alignItems: "center" }}>
                    <div style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace", fontWeight: 800, color: "#0f172a" }}>{String(h.symbol)}</div>
                    <div style={{ fontSize: 12, color: "#475569" }}>{String(h.sector || "-")}</div>
                    <div style={{ textAlign: "right", fontWeight: 800, color: "#059669" }}>{typeof h.rd_intensity === "number" ? `${h.rd_intensity.toFixed(1)}%` : "-"}</div>
                  </div>
                ))}
            </div>
          </div>

          {/* Right: coverage + signal */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a", marginBottom: 8 }}>Data coverage (why long horizon is hard)</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  { label: "Eligible 5-year windows", n: eligible5yr, pct: eligible5yrPct, color: "#22c55e" },
                  { label: "Eligible 10-year windows", n: eligible10yr, pct: eligible10yrPct, color: "#3b82f6" },
                  { label: "Eligible 20-year windows", n: eligible20yr, pct: eligible20yrPct, color: "#8b5cf6" },
                ].map((row, i) => (
                  <div key={i} style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                      <div style={{ fontSize: 12, color: "#334155", fontWeight: 700 }}>{row.label}</div>
                      <div style={{ fontSize: 12, color: "#64748b" }}>{row.n} firms ({typeof row.pct === "number" ? `${row.pct}%` : "…"})</div>
                    </div>
                    <div style={{ height: 10, background: "#e2e8f0", borderRadius: 6, overflow: "hidden" }}>
                      <div style={{ width: `${Math.min(100, row.pct ?? 0)}%`, height: "100%", background: row.color, borderRadius: 6 }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 12, padding: 14, flex: 1, display: "flex", flexDirection: "column" }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#1e40af", marginBottom: 10 }}>Signal + formation (no look-ahead)</div>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>Signal</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a" }}>R&amp;D Intensity = R&amp;D Expense / Revenue</div>
                <div style={{ fontSize: 12, color: "#475569", marginTop: 6, lineHeight: 1.6 }}>
                  Use prior fiscal-year fundamentals and form portfolios in June (July-June returns) so the 10-K is public before formation.
                </div>
              </div>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, flex: 1 }}>
                <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 8 }}>R&amp;D profile (cohort)</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                  {[
                    { label: "High", n: rdProfileHigh, color: "#059669" },
                    { label: "Medium", n: rdProfileMedium, color: "#2563eb" },
                    { label: "Low", n: rdProfileLow, color: "#94a3b8" },
                  ].map((r, i) => (
                    <div key={i} style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, textAlign: "center" }}>
                      <div style={{ fontSize: 20, fontWeight: 900, color: r.color }}>{r.n}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>{r.label}</div>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 10, fontSize: 11, color: "#475569", lineHeight: 1.6 }}>
                  Interpretation: most firms are &quot;Low&quot; intensity; the signal is strongest at the extremes (Q5 vs Q1).
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 12, background: "#0f172a", borderRadius: 12, padding: 14, textAlign: "center" }}>
          <span style={{ fontSize: 13, color: "#e2e8f0" }}>
            Practical takeaway: run it <strong style={{ color: "white" }}>systematically</strong>, size for drawdowns, and give it time.
          </span>
        </div>
      </div>
    </Slide>
  )
}
