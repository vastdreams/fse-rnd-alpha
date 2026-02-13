/**
 * PATH: src/components/documentation/OverviewTab.tsx
 * PURPOSE: Renders the "Overview" tab content for the Documentation page
 * WHY: Extracted from Documentation.tsx to keep files under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Database, BarChart3 } from "lucide-react"
import type { FMPOverview } from "@/lib/api"

export interface OverviewTabProps {
  fmpOverview: FMPOverview | undefined
  periodLabel: string
  eta5yr: number | undefined
  eta20yr: number | undefined
}

export function OverviewTab({ fmpOverview, periodLabel, eta5yr, eta20yr }: OverviewTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Platform Overview</CardTitle>
        <CardDescription>What is the R&D Factor Analysis Platform?</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground">
          The R&D Factor Analysis Platform is a comprehensive research tool that analyzes the relationship
          between Research & Development (R&D) investment intensity and long-term stock returns across
          {fmpOverview?.total_companies ?? "..."} S&P 500 companies over the return period{" "}
          <strong className="text-foreground">{periodLabel}</strong>.
        </p>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <Database className="h-4 w-4" />
              Data Coverage
            </h3>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>{fmpOverview?.total_companies ?? "..."} companies</li>
              <li>
                Income statements: {fmpOverview?.total_income_statements ?? "..."} (annual)
              </li>
              <li>
                Price records: {fmpOverview?.total_price_records ?? "..."} (daily)
              </li>
              <li>
                Annual return records: {fmpOverview?.total_annual_returns ?? "..."}
              </li>
              <li>Primary data: Financial Modeling Prep (FMP) API</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Key Features
            </h3>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Quintile portfolio analysis</li>
              <li>Rolling window performance (5/10/20 years)</li>
              <li>Statistical significance testing (ANOVA)</li>
              <li>R&D ETF backtesting</li>
              <li>Industry sector breakdown</li>
            </ul>
          </div>
        </div>

        <div className="p-4 border rounded-lg bg-muted/30">
          <h3 className="font-semibold mb-2">Research Hypothesis</h3>
          <p className="text-sm text-muted-foreground">
            <strong>H1:</strong> Companies with higher R&D investment intensity are associated with higher
            subsequent shareholder returns; we test how this relationship varies across investment horizons.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            <strong>Finding:</strong> The analysis supports this hypothesis with statistically significant results
            (ANOVA p &lt; 1e-6) and increasing effect sizes over longer windows (η²{" "}
            {eta5yr !== undefined ? eta5yr.toFixed(3) : "..."} at 5yr →{" "}
            {eta20yr !== undefined ? eta20yr.toFixed(3) : "..."} at 20yr).
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
