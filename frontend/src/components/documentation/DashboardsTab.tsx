/**
 * PATH: src/components/documentation/DashboardsTab.tsx
 * PURPOSE: Renders the "Dashboards" tab content for the Documentation page
 * WHY: Extracted from Documentation.tsx to keep files under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

export function DashboardsTab() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Dashboard Guide</CardTitle>
        <CardDescription>What each dashboard shows and how to use it</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Overview Dashboard</h3>
            <p className="text-sm text-muted-foreground mb-2">
              High-level summary of the entire dataset with key statistics:
            </p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Total companies and R&D data coverage</li>
              <li>Average R&D intensity across all companies</li>
              <li>R&D trends over time</li>
              <li>Top R&D spenders by sector</li>
              <li>Returns summary statistics</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Companies Dashboard</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Browse and search all companies in the dataset:
            </p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Company profiles with sector and industry</li>
              <li>R&D intensity rankings</li>
              <li>Filter by sector or R&D profile</li>
              <li>Click any company to see detailed analysis</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Analysis (500) Dashboard</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Comprehensive research analysis with multiple tabs:
            </p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li><strong>Quintile Analysis:</strong> Performance by R&D intensity quintiles</li>
              <li><strong>Factor Premium:</strong> R&D factor returns over time</li>
              <li><strong>ANOVA Results:</strong> Statistical significance tests</li>
              <li><strong>Cohort Companies:</strong> Full list of cohort companies (from API)</li>
              <li><strong>Papers:</strong> Research papers with findings</li>
              <li><strong>Methodology:</strong> Complete methodology documentation</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">ETF R&D Alpha Selection Dashboard</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Portfolio construction and backtesting (ETF10/ETF20/ETF50):
            </p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>ETF10/20/50 R&D Alpha Selection baskets</li>
              <li>Annual July reconstitution with point-in-time data</li>
              <li>Performance vs S&P 500 benchmark</li>
              <li>Historical backtests with eligibility gates</li>
              <li>Forecast distribution (p10/p50/p90 bands)</li>
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
