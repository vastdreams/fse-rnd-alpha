/**
 * PATH: frontend/src/components/main-paper/LimitationsSection.tsx
 * PURPOSE: Section 10 – Limitations of the study.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - lucide-react AlertTriangle: section icon
 *  - ui/card: Card + CardContent wrappers
 *  - InfoTooltip: inline term definitions
 */

import { AlertTriangle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { InfoTooltip } from "@/components/InfoTooltip"

export function LimitationsSection() {
  return (
    <section id="limitations" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <AlertTriangle className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">10. Limitations</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
          <h3 className="text-lg font-semibold text-foreground">10.1 Data limitations</h3>
          <p className="text-muted-foreground">
            This paper uses Tier-1 fundamentals from Financial Modeling Prep (FMP) and standard factor series from Ken French.{" "}
            <span className="inline-flex items-center gap-1">
              Survivorship bias
              <InfoTooltip term="survivorship_bias" size={12} />
            </span>{" "}
            is substantially mitigated using historical S&amp;P 500 membership and{" "}
            <span className="inline-flex items-center gap-1">
              cash-after-exit return construction + delisting sensitivity
              <InfoTooltip term="delisting_adjustment" size={12} />
            </span>
            , but Tier-2 CRSP/Compustat replication remains the gold standard for academic publication.
          </p>
          <ul className="text-muted-foreground list-disc list-inside space-y-1">
            <li>R&amp;D expense data relies on GAAP-reported figures; capitalized development costs (e.g., under IFRS) are not harmonized.</li>
            <li>S&amp;P 500 membership is used as a liquidity and coverage proxy; small-cap and international firms are not analyzed.</li>
            <li>Factor inputs (FF5 + MOM) are sourced from Ken French; any factor construction differences are inherited.</li>
          </ul>

          <h3 className="text-lg font-semibold text-foreground">10.2 Methodological limitations</h3>
          <p className="text-muted-foreground">
            We document an association (a characteristic premium) and do not claim causal identification. The July-June convention reduces
            look-ahead bias but does not eliminate all timing issues (e.g., intra-year disclosure variations).
          </p>
          <ul className="text-muted-foreground list-disc list-inside space-y-1">
            <li>Quintile sorts are unconditional; industry-adjusted or risk-adjusted sorts may yield different results.</li>
            <li>Rolling-window analysis uses overlapping periods for descriptive purposes; primary inference uses monthly spanning and cross-sectional tests.</li>
            <li>Regime splits are post-hoc and should not be interpreted as independent tests.</li>
          </ul>

          <h3 className="text-lg font-semibold text-foreground">10.3 Implementation limitations</h3>
          <p className="text-muted-foreground">
            Implementation results rely on stylized, literature-calibrated cost parameters and do not model fund-level frictions:
          </p>
          <ul className="text-muted-foreground list-disc list-inside space-y-1">
            <li>No taxes, borrowing costs, or margin requirements modeled.</li>
            <li>No capacity constraints; large AUM would face additional market impact.</li>
            <li>Equal-weight rebalancing assumes all positions are tradable at quoted spreads.</li>
            <li>Backtest uses point-in-time data but does not simulate real execution slippage.</li>
          </ul>

          <h3 className="text-lg font-semibold text-foreground">10.4 External validity</h3>
          <p className="text-muted-foreground">
            Results are specific to U.S. large-cap equities over the sample period. Generalization to other markets, time periods, or firm sizes
            requires separate analysis. The premium may be sensitive to accounting regime changes, disclosure practices, and market structure evolution.
          </p>
        </CardContent>
      </Card>
    </section>
  )
}
