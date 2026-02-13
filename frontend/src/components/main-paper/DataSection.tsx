/**
 * PATH: frontend/src/components/main-paper/DataSection.tsx
 * PURPOSE: Section 3 – Data & Sample Construction.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - lucide-react Database: section icon
 *  - ui/card: Card + CardContent wrappers
 *  - InfoTooltip: inline term definitions
 *  - Formula: rendered formula components
 */

import { Database } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Formulas } from "@/components/Formula"

export interface DataSectionProps {
  sampleYearRange: string | undefined
}

export function DataSection({ sampleYearRange }: DataSectionProps) {
  return (
    <section id="data" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <Database className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">3. Data &amp; Sample Construction</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            3.1 R&amp;D Intensity
            <InfoTooltip term="rd_intensity" size={16} />
          </h3>
          <p className="text-muted-foreground">
            We define R&amp;D intensity as R&amp;D expense divided by revenue, expressed as a percentage. This ratio captures how much
            a firm invests in research and development relative to its scale. <strong className="text-foreground">Why use revenue as the denominator?</strong>{" "}
            Revenue is a stable, comparable measure of firm size that is less affected by capital structure or accounting choices than
            alternatives like total assets or market capitalization.
          </p>
          <div className="not-prose">
            <Formulas.RDIntensity />
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            <strong className="text-foreground">Typical values:</strong> Technology and Healthcare firms often have R&amp;D intensity of 10-30%,
            while Financials and Utilities are typically below 1%. This wide dispersion is what creates meaningful quintile separation.
          </p>

          <div className="not-prose p-4 rounded-lg bg-blue-500/5 border border-blue-500/20 mt-4">
            <p className="font-semibold text-foreground mb-2">Accounting Standard: SFAS 2 (1974)</p>
            <p className="text-sm text-muted-foreground">
              Consistent R&amp;D reporting in the U.S. began with <strong>FASB Statement No. 2</strong> (SFAS 2), issued in October 1974.
              This standard requires that R&amp;D expenditures be expensed as incurred due to the uncertainty of future economic benefits.
              SFAS 2 is now codified as <strong>ASC Topic 730</strong>. Our sample period ({sampleYearRange || "see header"}) falls entirely within this standardized
              reporting era, ensuring consistent R&amp;D disclosure across firms and years.
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              Note: The "expense as incurred" rule is central to the R&amp;D premium hypothesis. Because R&amp;D is not capitalized, firms
              with high R&amp;D can appear less profitable on traditional metrics even when building valuable intangible assets.
            </p>
          </div>

          <h3 className="text-lg font-semibold text-foreground mt-6 flex items-center gap-2">
            3.2 Return Timing (Look-Ahead Mitigation)
            <InfoTooltip term="look_ahead_bias" size={16} />
          </h3>
          <p className="text-muted-foreground">
            To reduce look-ahead bias, we default to July-June returns{" "}
            <span className="inline-flex items-center gap-1">
              (Fama-French convention)
              <InfoTooltip term="july_june_convention" size={12} />
            </span>
            : fiscal-year R&D data for year <span className="font-mono">T</span> is mapped to returns from July{" "}
            <span className="font-mono">T+1</span> through June <span className="font-mono">T+2</span>.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            <strong className="text-foreground">Why this timing matters:</strong> Most U.S. firms have December fiscal year ends and must file
            10-K reports within 60-90 days (by late February/March). By waiting until July to form portfolios, we ensure all accounting
            data is publicly available. Using calendar-year returns (January-December) would mean trading on data that wasn't yet public,
            inflating apparent performance.
          </p>
          <div className="not-prose mt-3">
            <Formulas.TSR />
          </div>
          <div className="not-prose p-3 rounded-lg bg-muted/30 border mt-3">
            <p className="text-sm text-muted-foreground">
              <strong className="text-foreground">Example timeline:</strong> A firm reports FY2022 R&amp;D in its 10-K filed March 2023.
              We use this data to form portfolios in July 2023 and measure returns through June 2024. This 6+ month lag ensures
              no information leakage.
            </p>
          </div>

          <h3 className="text-lg font-semibold text-foreground mt-6">3.3 Statistical Inference</h3>
          <p className="text-muted-foreground">
            We report three complementary objects with distinct roles: (i) the annual non-overlapping HML series (economic magnitude and year-to-year consistency),
            (ii) rolling-window summaries (descriptive context; autocorrelated by construction), and (iii) monthly tests for statistical inference (factor spanning and
            Fama-MacBeth regressions). <strong className="text-foreground">Why this structure?</strong> With only ~30 annual observations, the annual mean test can be low-power;
            monthly tests provide a much larger sample for hypothesis testing while preserving bias-aware timing.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            Where overlapping windows are used, inference is HAC-adjusted using Newey-West standard errors to account for serial correlation.
          </p>
          <div className="not-prose grid md:grid-cols-2 gap-4 mt-3">
            <Formulas.ANOVA />
            <Formulas.EtaSquared />
            <Formulas.CohensD />
            <Formulas.SharpeRatio />
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            <strong>Reading these formulas:</strong> Each formula box includes a description explaining what it measures and how to interpret typical values.
            Hover or tap the formula label for details.
          </p>
        </CardContent>
      </Card>
    </section>
  )
}
