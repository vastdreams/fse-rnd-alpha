/**
 * PATH: frontend/src/components/whitepaper/slides/LimitationsSlide.tsx
 * PURPOSE: Slide 10 – Important Caveats: methodological + practical limitations.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import { Slide } from "../slide-components"

export function LimitationsSlide({ totalSlides }: { totalSlides: number }) {
  return (
    <Slide key="limitations" slideNumber={10} totalSlides={totalSlides} title="Important Caveats" subtitle="Limitations, risks, and honest assessment" accent="red">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Warning header */}
        <div style={{ background: "#dc2626", borderRadius: 16, padding: 16, marginBottom: 20, textAlign: "center" }}>
          <p style={{ fontSize: 16, fontWeight: 600, color: "white", margin: 0 }}>⚠️ Past performance does not guarantee future results. This is research, not investment advice.</p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Methodological */}
          <div style={{ background: "#fef2f2", border: "2px solid #fca5a5", borderRadius: 16, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#991b1b", marginBottom: 16, borderBottom: "2px solid #dc2626", paddingBottom: 8 }}>Methodological Limitations</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {[
                { icon: "🛡️", title: "Survivorship Bias", text: "Survivorship and exits matter: long horizons include delistings and index turnover. We enforce point-in-time membership where constituent spans are available and handle exits via return construction (cash-after-exit), with delisting uncertainty reported via sensitivity analysis." },
                { icon: "👀", title: "Look-Ahead Bias", text: "10-K filings are available 60-90 days after fiscal year-end. We use July-June returns to ensure data is public before portfolio formation." },
                { icon: "📊", title: "Data Quality", text: "Tier-1 data (Financial Modeling Prep) may have gaps vs. CRSP/Compustat. Professional implementation should validate with academic-grade sources." },
                { icon: "📐", title: "Multiple Testing", text: "We examined multiple horizons and specifications. Some findings may be sample-specific. Out-of-sample validation recommended." },
              ].map((item, i) => (
                <div key={i} style={{ background: "white", borderRadius: 10, padding: 14 }}>
                  <div style={{ fontWeight: 600, color: "#991b1b", marginBottom: 6 }}>{item.icon} {item.title}</div>
                  <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>{item.text}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Practical */}
          <div style={{ background: "#fffbeb", border: "2px solid #fde68a", borderRadius: 16, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#92400e", marginBottom: 16, borderBottom: "2px solid #f59e0b", paddingBottom: 8 }}>Practical Considerations</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {[
                { icon: "🏭", title: "Sector Concentration", text: "High-R&D portfolios are concentrated in Technology and Healthcare. Sector exposure can influence results; consider sector-neutralized versions as a robustness check." },
                { icon: "📉", title: "Regime Dependence", text: "The R&D premium varies by market regime and can be negative in some years. Persistence is not guaranteed." },
                { icon: "💰", title: "Capacity Constraints", text: "Capacity depends on implementation. Concentrated equal-weight strategies can face market-impact constraints at scale; large allocators may prefer value-weight or cap-weighted variations." },
                { icon: "⏳", title: "Timing Risk", text: "R&D benefits have 3-5 year lags. Multi-year underperformance is possible. Not suitable for short-term investors." },
              ].map((item, i) => (
                <div key={i} style={{ background: "white", borderRadius: 10, padding: 14 }}>
                  <div style={{ fontWeight: 600, color: "#92400e", marginBottom: 6 }}>{item.icon} {item.title}</div>
                  <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>{item.text}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom disclaimer */}
        <div style={{ marginTop: 16, background: "#0f172a", borderRadius: 12, padding: 16 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 24 }}>⚖️</span>
            <span style={{ fontSize: 13, color: "#e2e8f0" }}>
              This research is provided for <strong style={{ color: "white" }}>educational and informational purposes only</strong>. It does not constitute investment advice. Always consult a qualified financial advisor before making investment decisions.
            </span>
          </div>
        </div>
      </div>
    </Slide>
  )
}
