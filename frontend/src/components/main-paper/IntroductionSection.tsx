/**
 * PATH: frontend/src/components/main-paper/IntroductionSection.tsx
 * PURPOSE: Section 1 – Introduction of the Main Paper.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - lucide-react BookOpen: section icon
 *  - ui/card: Card + CardContent wrappers
 *  - InfoTooltip: inline term definitions
 */

import { BookOpen } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { InfoTooltip } from "@/components/InfoTooltip"

export function IntroductionSection() {
  return (
    <section id="introduction" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <BookOpen className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">1. Introduction</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
          <p className="text-muted-foreground">
            R&amp;D spending is an investment in intangible capital with uncertain payoffs and multi-year horizons. Because R&amp;D is expensed under U.S.
            GAAP{" "}
            <span className="inline-flex items-center">
              <InfoTooltip term="gaap_expensing" size={12} />
            </span>
            , firms with substantial R&amp;D can often look less profitable in contemporaneous statements even when R&amp;D creates economically valuable
            assets. This accounting treatment is important because it creates a potential disconnect between reported earnings and true economic value.
            These features motivate two broad interpretations for any return premium associated with R&amp;D intensity: investors may
            underweight intangibles{" "}
            <span className="inline-flex items-center">
              (<InfoTooltip term="mispricing" size={12} />)
            </span>
            , or the premium may compensate for innovation-related risks{" "}
            <span className="inline-flex items-center">
              (<InfoTooltip term="risk_compensation" size={12} />)
            </span>
            .
          </p>
          <p className="text-muted-foreground">
            The central, investable question is straightforward: <strong className="text-foreground">does an R&amp;D-intensity sort create a repeatable
            return premium in a large-cap U.S. universe</strong> once we align accounting data to returns using a bias-aware timing convention and
            acknowledge real implementation frictions?
          </p>

          <div className="not-prose rounded-lg border bg-muted/30 p-4">
            <p className="font-semibold text-foreground mb-2">Terminology used in this paper</p>
            <ul className="text-sm text-muted-foreground list-disc list-inside space-y-2">
              <li>
                <span className="font-medium text-foreground">Premium (HML):</span> the return spread between high-R&amp;D and low-R&amp;D portfolios
                formed in the same universe for the same period. In most exhibits this is{" "}
                <span className="font-mono">Q5 - Q1</span> (highest R&amp;D quintile minus lowest R&amp;D quintile).{" "}
                <InfoTooltip term="hml_premium" size={12} />
              </li>
              <li>
                <span className="font-medium text-foreground">Not a benchmark excess return:</span> this premium is not automatically "above the S&amp;P
                500". Benchmark comparisons are shown separately in the investable strategy section (Section 9).
              </li>
              <li>
                <span className="font-medium text-foreground">Absolute return:</span> the average return of a single portfolio (for example, Q5 alone).
                Absolute returns can be high even when the premium is small if both Q5 and Q1 perform similarly.
              </li>
            </ul>
          </div>

          <div className="not-prose grid md:grid-cols-2 gap-4 mt-2">
            <div className="p-4 rounded-lg border bg-muted/30">
              <p className="font-semibold text-foreground mb-2">What we do</p>
              <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                <li>Form annual R&amp;D-intensity quintiles and evaluate subsequent returns under a July-June convention.</li>
                <li>Anchor statistical inference on monthly factor spanning tests and monthly Fama-MacBeth regressions; use the annual non-overlapping premium series for economic context and rolling windows for descriptive stability.</li>
                <li>Show sector composition and robustness diagnostics (factor spanning, stratifications) when available in the snapshot.</li>
                <li>Translate results into a rules-based, long-only implementation with explicit trading-friction assumptions.</li>
              </ul>
            </div>
            <div className="p-4 rounded-lg border bg-muted/30">
              <p className="font-semibold text-foreground mb-2">What we do not claim</p>
              <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                <li>No causal identification: results are an association (a characteristic premium), not a structural estimate.</li>
                <li>No universal coverage: this analysis is scoped to a large-cap U.S. universe with disclosed data limitations.</li>
                <li>No reliance on overlapping-window p-values as primary inference; those windows are autocorrelated.</li>
              </ul>
            </div>
          </div>

          <p className="text-muted-foreground">
            The paper proceeds as follows. Section 2 frames related evidence and hypotheses. Section 3 describes data and sample construction. Section 4
            specifies portfolio formation, return definitions, and inference. Section 5 presents the annual premium evidence and descriptive
            time-variation, Section 6 documents sector structure, and Section 7 reports robustness and factor diagnostics. Sections 8-12 discuss
            interpretation, implementation, limitations, replicability, and conclusion.
          </p>
        </CardContent>
      </Card>
    </section>
  )
}
