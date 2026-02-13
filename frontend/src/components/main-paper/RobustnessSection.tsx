/**
 * PATH: frontend/src/components/main-paper/RobustnessSection.tsx
 * PURPOSE: Section 7 – Robustness & Factor Tests (thin orchestrator).
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 *      Sub-components split out to keep each file under 300 lines.
 */

import { Link } from "react-router-dom"
import { BarChart3, ExternalLink } from "lucide-react"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Card, CardContent } from "@/components/ui/card"
import { RobustnessCharts } from "./RobustnessCharts"
import { RobustnessFactorTests } from "./RobustnessFactorTests"
import { RobustnessFamaMacBeth } from "./RobustnessFamaMacBeth"
import { RobustnessDoubleSort } from "./RobustnessDoubleSort"
import { RobustnessDelisting } from "./RobustnessDelisting"

export function RobustnessSection({ publicationStats, factorPremiumSeries, growthOf1, spanningTests, annualHmlData, snapshotPayload, mispricingTests, doubleSortTableRows, delistingSensitivity }: { publicationStats: any; factorPremiumSeries: any[]; growthOf1: any[]; spanningTests: any; annualHmlData: any; snapshotPayload: any; mispricingTests: any; doubleSortTableRows: any[]; delistingSensitivity: any }) {
  const props = { publicationStats, factorPremiumSeries, growthOf1, spanningTests, annualHmlData, snapshotPayload, mispricingTests, doubleSortTableRows, delistingSensitivity }
  return (
    <>
    <section id="robustness" className="scroll-mt-24 space-y-6">
      <div className="flex items-center gap-3 mb-4">
        <BarChart3 className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">7. Robustness & Factor Tests</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
          <p className="text-muted-foreground">
            This section reports robustness and interpretation diagnostics that complement the annual premium evidence in Section 5.1 and provide higher-power inference via monthly tests. We present
            the annual premium time series, cumulative growth of $1 for Q5 versus Q1, factor spanning tests (when factor inputs are available), and
            stratification and double-sort diagnostics to assess size, sector, and other confounding.
          </p>
          <div className="not-prose grid md:grid-cols-4 gap-3">
            <div className="p-3 rounded border bg-muted/30">
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                Mean premium (annual)
                <InfoTooltip term="hml_premium" size={12} />
              </div>
              <div className="font-semibold">
                {typeof (publicationStats as any)?.rd_factor_premium?.mean === "number"
                  ? `${(publicationStats as any).rd_factor_premium.mean.toFixed(2)}%`
                  : "..."}
              </div>
            </div>
            <div className="p-3 rounded border bg-muted/30">
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                t-stat
                <InfoTooltip term="t_statistic" size={12} />
              </div>
              <div className="font-semibold">
                {typeof (publicationStats as any)?.rd_factor_premium?.t_statistic === "number"
                  ? (publicationStats as any).rd_factor_premium.t_statistic.toFixed(2)
                  : "..."}
              </div>
            </div>
            <div className="p-3 rounded border bg-muted/30">
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                Win rate
                <InfoTooltip title="Win Rate" size={12}>
                  Percentage of years where Q5 (high R&D) outperformed Q1 (low R&D). A win rate above 50% suggests
                  the premium is consistent over time, not driven by a few outlier years.
                </InfoTooltip>
              </div>
              <div className="font-semibold">
                {(() => {
                  const s = (publicationStats as any)?.rd_factor_premium
                  if (!s || typeof s.positive_years !== "number" || typeof s.n_years !== "number" || s.n_years <= 0) return "..."
                  return `${Math.round((s.positive_years / s.n_years) * 100)}%`
                })()}
              </div>
            </div>
            <div className="p-3 rounded border bg-muted/30">
              <div className="text-xs text-muted-foreground">Years</div>
              <div className="font-semibold">
                {typeof (publicationStats as any)?.rd_factor_premium?.n_years === "number"
                  ? (publicationStats as any).rd_factor_premium.n_years
                  : "..."}
              </div>
            </div>
          </div>
          <p className="text-muted-foreground">
            For additional deep-dive commentary and supporting visuals, see{" "}
            <Link to="/papers/3" className="inline-flex items-center gap-2 underline hover:no-underline">
              Sub-Research 3 <ExternalLink className="h-4 w-4" />
            </Link>
            .
          </p>
        </CardContent>
      </Card>

      <RobustnessCharts {...props} />
      <RobustnessFactorTests {...props} />
      <RobustnessFamaMacBeth {...props} />
      <RobustnessDoubleSort {...props} />
      <RobustnessDelisting {...props} />
    </section>
    </>
  )
}
