/**
 * PATH: src/components/documentation/MetricsTab.tsx
 * PURPOSE: Renders the "Metrics" tab content for the Documentation page
 * WHY: Extracted from Documentation.tsx to keep files under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { FlaskConical, TrendingUp, Target, BarChart3 } from "lucide-react"
import { Formulas } from "@/components/Formula"

export function MetricsTab() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Key Metrics Explained</CardTitle>
        <CardDescription>Understanding the metrics used throughout the platform</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-emerald-500" />
              R&D Intensity
            </h3>
            <p className="text-sm text-muted-foreground mb-2">
              <strong>Definition:</strong> R&D Intensity = (R&D Expense / Total Revenue) × 100
            </p>
            <p className="text-sm text-muted-foreground">
              This measures how much a company invests in R&D relative to its revenue. Higher values indicate
              greater innovation focus. For example, a company with 20% R&D intensity spends $20 on R&D for
              every $100 of revenue.
            </p>
            <div className="mt-3 flex gap-2">
              <Badge variant="outline">Rule of thumb (illustrative)</Badge>
            </div>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-blue-500" />
              July-June Total Return (Bias-Reduced)
            </h3>
            <p className="text-sm text-muted-foreground mb-2">
              <strong>Definition:</strong> Total shareholder return measured over July-June to align fiscal-year R&D timing
            </p>
            <div className="my-2">
              <Formulas.TSR />
            </div>
            <p className="text-sm text-muted-foreground">
              We default to July-June returns (Fama-French convention) to reduce look-ahead bias when forming
              portfolios from fiscal-year financial statements. Total returns are constructed from split-adjusted close prices plus dividend events (reinvested).
            </p>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <Target className="h-4 w-4 text-purple-500" />
              Sharpe Ratio
            </h3>
            <p className="text-sm text-muted-foreground mb-2">
              <strong>Definition:</strong> Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Volatility
            </p>
            <p className="text-sm text-muted-foreground">
              Measures risk-adjusted returns. Higher values indicate better risk-adjusted performance.
              Generally, values &gt;1 are good, &gt;2 are very good, and &gt;3 are excellent.
            </p>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-amber-500" />
              Effect Size (η²)
            </h3>
            <Formulas.EtaSquared />
            <p className="text-sm text-muted-foreground mt-2">
              Measures the proportion of variance in returns explained by R&D intensity. Values range from
              0 to 1, where higher values indicate stronger relationships.
            </p>
            <div className="mt-3 flex gap-2">
              <Badge variant="outline">Small: 0.01-0.06</Badge>
              <Badge variant="outline">Medium: 0.06-0.14</Badge>
              <Badge variant="outline">Large: &gt;0.14</Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
