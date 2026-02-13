/**
 * PATH: frontend/src/components/main-paper/StrategySection.tsx
 * PURPOSE: Section 9 – Investable Strategy (thin orchestrator).
 * WHY: Delegates to sub-components to keep each file under 300 lines.
 * FLOW:
 * ┌─────────────────────┐   ┌──────────────────────────────┐   ┌────────────────────┐
 * │ Props from parent   │ → │ Route to sub-components       │ → │ Rendered section 9 │
 * └─────────────────────┘   └──────────────────────────────┘   └────────────────────┘
 * DEPENDENCIES:
 * - StrategyPortfolioCosts: Cards 9.1 body + 9.2 + 9.3
 * - StrategyBenchmarkBacktest: Card 9.4
 * - StrategyTimeline: Card 9.5
 * - StrategyChecklist: Card 9.6
 * - StrategyCommonQuestions: Card 9.7
 */

import { FlaskConical } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { StrategyPortfolioCosts } from "./StrategyPortfolioCosts"
import { StrategyBenchmarkBacktest } from "./StrategyBenchmarkBacktest"
import { StrategyTimeline } from "./StrategyTimeline"
import { StrategyChecklist } from "./StrategyChecklist"
import { StrategyCommonQuestions } from "./StrategyCommonQuestions"

export function StrategySection({ transactionCosts, netOfCost5yr, rollingAggregates, investableBacktest, investableGrowth, cohortSummary, investableNetExcessVsSp500Pp, investableUnderperformPct, investableTurnoverAvgPct }: { transactionCosts: any; netOfCost5yr: any; rollingAggregates: any; investableBacktest: any; investableGrowth: any[]; cohortSummary: any; investableNetExcessVsSp500Pp: any; investableUnderperformPct: any; investableTurnoverAvgPct: any }) {
  return (
    <>
    <section id="strategy" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <FlaskConical className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">9. Investable Strategy</h2>
      </div>
      <Card className="bg-card">
        <CardHeader>
          <CardTitle>9.1 Portfolio construction</CardTitle>
          <CardDescription>
            Long-only implementation using a top-20 R&D-intensity portfolio with annual reconstitution and explicit trading-friction assumptions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <StrategyPortfolioCosts transactionCosts={transactionCosts} netOfCost5yr={netOfCost5yr} rollingAggregates={rollingAggregates} />
          <StrategyBenchmarkBacktest investableBacktest={investableBacktest} investableGrowth={investableGrowth} />
          <StrategyTimeline />
          <StrategyChecklist cohortSummary={cohortSummary} investableNetExcessVsSp500Pp={investableNetExcessVsSp500Pp} investableUnderperformPct={investableUnderperformPct} />
          <StrategyCommonQuestions investableTurnoverAvgPct={investableTurnoverAvgPct} />
        </CardContent>
      </Card>
    </section>
    </>
  )
}
