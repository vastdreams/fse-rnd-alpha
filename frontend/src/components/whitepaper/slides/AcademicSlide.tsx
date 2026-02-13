/**
 * PATH: frontend/src/components/whitepaper/slides/AcademicSlide.tsx
 * PURPOSE: Slide 8 – Academic Validation: literature, hypotheses.
 * WHY: Extracted from Whitepaper.tsx to keep parent under 300 lines.
 */

import { Slide } from "../slide-components"

export function AcademicSlide({ totalSlides }: { totalSlides: number }) {
  return (
    <Slide key="academic" slideNumber={8} totalSlides={totalSlides} title="Academic Validation" subtitle="Our findings are consistent with decades of peer-reviewed research" accent="blue">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ background: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)", border: "2px solid #3b82f6", borderRadius: 16, padding: 14, marginBottom: 12 }}>
          <p style={{ fontSize: 13, color: "#1e40af", lineHeight: 1.45, margin: 0, textAlign: "center" }}>
            The R&D-return anomaly has been documented in <strong>top-tier academic journals</strong> since the 1990s. Our findings replicate and extend this literature using modern data sources and robust statistical methods.
          </p>
        </div>

        {/* Key papers */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
          {[
            { authors: "Chan, Lakonishok & Sougiannis", year: "2001", journal: "Journal of Finance", finding: "High R&D-to-market-cap stocks earned significant excess returns over subsequent years. First major documentation of the R&D anomaly." },
            { authors: "Lev & Sougiannis", year: "1996", journal: "J. Accounting & Economics", finding: "R&D-adjusted earnings provide superior return predictions vs. reported GAAP earnings. R&D capitalization improves valuation." },
            { authors: "Eberhart, Maxwell & Siddique", year: "2004", journal: "Journal of Finance", finding: "Firms increasing R&D outperform over 5+ years. Market systematically underreacts to R&D investment announcements." },
            { authors: "Ahmed, Bu & Ye", year: "2025", journal: "Journal of Money, Credit and Banking", finding: "Finds the R&D premium is stronger among illiquid stocks, consistent with information frictions amplifying the return pattern." },
          ].map((paper, i) => (
            <div key={i} style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                <span style={{ fontWeight: 800, color: "#1e40af", fontSize: 13 }}>{paper.authors} ({paper.year})</span>
              </div>
              <div style={{ background: "#eff6ff", borderRadius: 6, padding: "3px 8px", display: "inline-block", marginBottom: 8 }}>
                <span style={{ fontSize: 10, color: "#3b82f6", fontWeight: 600 }}>{paper.journal}</span>
              </div>
              <p style={{ fontSize: 12, color: "#475569", lineHeight: 1.45, margin: 0 }}>{paper.finding}</p>
            </div>
          ))}
        </div>

        {/* Two hypotheses */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ background: "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)", border: "2px solid #f59e0b", borderRadius: 16, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 40, height: 40, borderRadius: "50%", background: "#f59e0b", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 20 }}>💰</span>
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: "#92400e", margin: 0 }}>Mispricing Hypothesis</h3>
            </div>
            <p style={{ fontSize: 12.5, color: "#78350f", lineHeight: 1.55, marginBottom: 10, marginTop: 0 }}>
              Markets systematically undervalue intangible assets because GAAP accounting <strong>expenses R&D immediately</strong>. Investors anchored on traditional P/E ratios miss the economic value of innovation investment.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}><div style={{ fontSize: 11, color: "#92400e" }}>📊 Depressed earnings → inflated P/E → value screens exclude</div></div>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}><div style={{ fontSize: 11, color: "#92400e" }}>📈 Intangible value not on balance sheet → undervalued</div></div>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}><div style={{ fontSize: 11, color: "#92400e" }}>⏳ 3-5 year lag for market recognition → patient alpha</div></div>
            </div>
          </div>

          <div style={{ background: "linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%)", border: "2px solid #9333ea", borderRadius: 16, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 40, height: 40, borderRadius: "50%", background: "#9333ea", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 20 }}>⚠️</span>
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: "#6b21a8", margin: 0 }}>Risk Premium Hypothesis</h3>
            </div>
            <p style={{ fontSize: 12.5, color: "#581c87", lineHeight: 1.55, marginBottom: 10, marginTop: 0 }}>
              High R&D firms carry <strong>unique risks</strong>: technological disruption, project failure, regulatory changes. The return premium may be compensation for bearing these innovation-specific risks.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}><div style={{ fontSize: 11, color: "#6b21a8" }}>🔬 R&D projects have high failure rates (~90% in pharma)</div></div>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}><div style={{ fontSize: 11, color: "#6b21a8" }}>💥 Disruptive tech can make R&D obsolete overnight</div></div>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}><div style={{ fontSize: 11, color: "#6b21a8" }}>📉 Higher volatility → demands higher expected return</div></div>
            </div>
          </div>
        </div>

        {/* Bottom note */}
        <div style={{ marginTop: 10, background: "#0f172a", borderRadius: 12, padding: 10, textAlign: "center" }}>
          <span style={{ fontSize: 12, color: "#94a3b8" }}>
            <strong style={{ color: "white" }}>Interpretation:</strong> Both hypotheses are plausible. This whitepaper focuses on documenting the pattern and implementability rather than isolating a single mechanism.
          </span>
        </div>
      </div>
    </Slide>
  )
}
