/**
 * PATH: frontend/src/components/main-paper/ConclusionSection.tsx
 * PURPOSE: Section 12 – Conclusion with key findings summary.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - lucide-react BookOpen: section icon
 *  - ui/card: Card + CardContent wrappers
 */

import { BookOpen } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"

export interface ConclusionSectionProps {
  annualHmlData: {
    mean_premium?: number
    hac_adjusted?: { t_statistic: number; p_value: number }
  } | undefined
  headlinePremiums: Array<{ horizon: string; premiumPct: number | undefined }>
  netOfCost5yr: { net_rd_premium_pct?: number } | undefined
  transactionCosts: { premium_capture_rate_pct?: number | null } | undefined
}

export function ConclusionSection({
  annualHmlData,
  headlinePremiums,
  netOfCost5yr,
  transactionCosts,
}: ConclusionSectionProps) {
  return (
    <section id="conclusion" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <BookOpen className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">12. Conclusion</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
          <p className="text-muted-foreground">
            This paper examines whether R&amp;D intensity predicts subsequent stock returns in a U.S. large-cap universe. Using a July-June return
            convention to reduce look-ahead bias and explicit exit handling plus point-in-time membership (when available) to mitigate survivorship bias, we document a positive return
            spread between high-R&amp;D and low-R&amp;D portfolios.
          </p>

          <div className="not-prose p-4 rounded-lg bg-muted/30 border">
            <p className="font-semibold text-foreground mb-2">Key findings</p>
            <ul className="text-muted-foreground text-sm space-y-2">
              <li>
                <strong className="text-foreground">Primary result:</strong> The annual non-overlapping HML premium averages{" "}
                <strong>{typeof annualHmlData?.mean_premium === "number" ? `${annualHmlData.mean_premium.toFixed(2)}%` : "..."}</strong> per year
                (Newey-West t = {typeof annualHmlData?.hac_adjusted?.t_statistic === "number" ? annualHmlData.hac_adjusted.t_statistic.toFixed(2) : "..."},
                p = {typeof annualHmlData?.hac_adjusted?.p_value === "number" ? (annualHmlData.hac_adjusted.p_value < 0.001 ? "<0.001" : annualHmlData.hac_adjusted.p_value.toFixed(4)) : "..."}).
              </li>
              <li>
                <strong className="text-foreground">Horizon dependence:</strong> Rolling-window premiums are{" "}
                {headlinePremiums.map((h) => `${h.horizon.toUpperCase()}: ${typeof h.premiumPct === "number" ? h.premiumPct.toFixed(2) : "..."}%`).join(", ")} (Q5-Q1).
                Longer horizons show smaller premiums, consistent with signal decay and regime mixing.
              </li>
              <li>
                <strong className="text-foreground">Implementability:</strong> Under literature-calibrated transaction costs, the net-of-cost premium
                remains <strong>{typeof netOfCost5yr?.net_rd_premium_pct === "number" ? `${netOfCost5yr.net_rd_premium_pct.toFixed(2)}%` : "..."}</strong> at the
                5-year horizon with a <strong>{typeof transactionCosts?.premium_capture_rate_pct === "number" ? `${transactionCosts.premium_capture_rate_pct.toFixed(1)}%` : "..."}</strong> capture rate.
              </li>
            </ul>
          </div>

          <p className="text-muted-foreground">
            We emphasize that these results document an association rather than a causal effect. The premium is concentrated in Technology and Healthcare
            sectors and is larger in small-cap firms within the sample. Factor spanning tests suggest the premium is not fully explained by standard
            models, but we cannot rule out omitted risk factors.
          </p>

          <p className="text-muted-foreground">
            For practitioners, the results suggest that an R&amp;D-intensity tilt may offer a measurable return premium, but implementation requires
            attention to sector concentration, turnover costs, and capacity constraints. The frozen snapshot approach ensures that all figures in this
            paper are reproducible and can be independently verified.
          </p>
        </CardContent>
      </Card>
    </section>
  )
}
