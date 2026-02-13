/**
 * PATH: src/components/documentation/InterpretationTab.tsx
 * PURPOSE: Renders the "Interpretation" tab content for the Documentation page
 * WHY: Extracted from Documentation.tsx to keep files under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

export interface InterpretationTabProps {
  premium5yr: number | undefined
  premium20yr: number | undefined
  eta5yr: number | undefined
  eta20yr: number | undefined
  periodLabel: string
}

export function InterpretationTab({ premium5yr, premium20yr, eta5yr, eta20yr, periodLabel }: InterpretationTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>How to Interpret Results</CardTitle>
        <CardDescription>Guidelines for understanding and using the findings</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="p-4 border rounded-lg bg-emerald-500/10 border-emerald-500/20">
            <h3 className="font-semibold mb-2 text-emerald-400">Key Finding</h3>
            <p className="text-sm text-muted-foreground">
              High-R&amp;D companies (Q5) outperform low-R&amp;D companies (Q1) by{" "}
              <strong>
                {premium5yr !== undefined ? `${premium5yr >= 0 ? "+" : ""}${premium5yr.toFixed(2)}%` : "..."} (5yr){" "}
                to{" "}
                {premium20yr !== undefined ? `${premium20yr >= 0 ? "+" : ""}${premium20yr.toFixed(2)}%` : "..."} (20yr)
              </strong>{" "}
              annually (rolling-window averages; descriptive due to overlap). ANOVA effect size rises with horizon (η²{" "}
              {eta5yr !== undefined ? eta5yr.toFixed(3) : "..."} → {eta20yr !== undefined ? eta20yr.toFixed(3) : "..."}).
            </p>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">What This Means</h3>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li>
                <strong>For Investors:</strong> Tilting portfolios toward high-R&D companies may generate
                superior long-term returns across multi-year horizons (see Main Paper for the primary annual series).
              </li>
              <li>
                <strong>For Researchers:</strong> R&D intensity is associated with a significant return premium that
                is statistically significant across horizons in this dataset, with effect size increasing at longer windows.
              </li>
              <li>
                <strong>For Corporate Managers:</strong> R&D investments are rewarded by markets over time,
                consistent with long-run value creation mechanisms (association, not causation).
              </li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Important Caveats</h3>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Past performance does not guarantee future results</li>
              <li>Universe is S&P 500; Tier-1 survivorship bias is substantially mitigated but not CRSP/Compustat-grade</li>
              <li>R&D reporting varies by industry and accounting standards</li>
              <li>Short-term volatility may be higher for R&D-intensive companies</li>
              <li>Results are based on historical data ({periodLabel})</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Using the Platform</h3>
            <ol className="text-sm text-muted-foreground space-y-2 list-decimal list-inside">
              <li>Start with the <strong>Overview</strong> to understand the dataset</li>
              <li>Explore <strong>Companies</strong> to see individual R&D profiles</li>
              <li>Review <strong>Analysis (500)</strong> for statistical findings</li>
              <li>Check <strong>R&D ETF</strong> for portfolio construction ideas</li>
              <li>Read the <strong>Papers</strong> and <strong>Methodology</strong> for detailed explanations</li>
            </ol>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
