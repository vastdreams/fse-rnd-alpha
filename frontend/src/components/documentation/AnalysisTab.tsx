/**
 * PATH: src/components/documentation/AnalysisTab.tsx
 * PURPOSE: Renders the "Analysis" tab content for the Documentation page
 * WHY: Extracted from Documentation.tsx to keep files under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { AggregateAnova } from "@/lib/api"

export interface AnalysisTabProps {
  premium5yr: number | undefined
  premium20yr: number | undefined
  eta5yr: number | undefined
  eta20yr: number | undefined
  aggregateAnova: Record<string, AggregateAnova> | undefined
}

export function AnalysisTab({ premium5yr, premium20yr, eta5yr, eta20yr, aggregateAnova }: AnalysisTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Understanding the Analysis</CardTitle>
        <CardDescription>How to interpret quintiles, ANOVA, and statistical tests</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Quintile Portfolio Construction</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Companies are ranked by R&D intensity and divided into 5 equal groups:
            </p>
            <div className="grid gap-2 md:grid-cols-5 mt-3">
              <div className="p-2 border rounded text-center">
                <Badge className="bg-red-500">Q1</Badge>
                <p className="text-xs mt-1 text-muted-foreground">Lowest R&D</p>
              </div>
              <div className="p-2 border rounded text-center">
                <Badge className="bg-orange-500">Q2</Badge>
                <p className="text-xs mt-1 text-muted-foreground">Low-Medium</p>
              </div>
              <div className="p-2 border rounded text-center">
                <Badge className="bg-yellow-500">Q3</Badge>
                <p className="text-xs mt-1 text-muted-foreground">Medium</p>
              </div>
              <div className="p-2 border rounded text-center">
                <Badge className="bg-green-500">Q4</Badge>
                <p className="text-xs mt-1 text-muted-foreground">Medium-High</p>
              </div>
              <div className="p-2 border rounded text-center">
                <Badge className="bg-blue-500">Q5</Badge>
                <p className="text-xs mt-1 text-muted-foreground">Highest R&D</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-3">
              Each quintile represents an equal-weighted portfolio. Q5 (high R&D) outperforms
              Q1 (low R&D) by{" "}
              <strong className="text-foreground">
                {premium5yr !== undefined ? `${premium5yr >= 0 ? "+" : ""}${premium5yr.toFixed(2)}%` : "..."} (5yr)
                {" "}to{" "}
                {premium20yr !== undefined ? `${premium20yr >= 0 ? "+" : ""}${premium20yr.toFixed(2)}%` : "..."} (20yr)
              </strong>{" "}
              annually (rolling-window averages; descriptive due to overlap).
            </p>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">ANOVA (Analysis of Variance)</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Tests whether mean returns differ significantly across quintiles:
            </p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li><strong>F-Statistic:</strong> Higher values indicate greater differences between groups</li>
              <li><strong>p-value:</strong> Probability the results occurred by chance
                <ul className="ml-4 mt-1">
                  <li>&lt; 0.05 (*): Significant at 95% confidence</li>
                  <li>&lt; 0.01 (**): Significant at 99% confidence</li>
                  <li>&lt; 0.001 (***): Highly significant</li>
                </ul>
              </li>
              <li><strong>η² (eta-squared):</strong> Effect size - proportion of variance explained</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Rolling Window Analysis</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Performance is analyzed over overlapping time windows:
            </p>
            <div className="grid gap-2 md:grid-cols-3 mt-3">
              <div className="p-3 border rounded">
                <Badge>5-Year Windows</Badge>
                <p className="text-xs mt-2 text-muted-foreground">
                  {aggregateAnova?.["5yr"]?.n_windows ?? "..."} windows
                </p>
                <p className="text-xs text-muted-foreground">
                  η² = {typeof eta5yr === "number" ? eta5yr.toFixed(3) : "..."}
                </p>
              </div>
              <div className="p-3 border rounded">
                <Badge>10-Year Windows</Badge>
                <p className="text-xs mt-2 text-muted-foreground">
                  {aggregateAnova?.["10yr"]?.n_windows ?? "..."} windows
                </p>
                <p className="text-xs text-muted-foreground">
                  η² = {typeof aggregateAnova?.["10yr"]?.anova?.eta_squared === "number" ? aggregateAnova["10yr"].anova.eta_squared.toFixed(3) : "..."}
                </p>
              </div>
              <div className="p-3 border rounded">
                <Badge>20-Year Windows</Badge>
                <p className="text-xs mt-2 text-muted-foreground">
                  {aggregateAnova?.["20yr"]?.n_windows ?? "..."} windows
                </p>
                <p className="text-xs text-muted-foreground">
                  η² = {typeof eta20yr === "number" ? eta20yr.toFixed(3) : "..."}
                </p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-3">
              Longer windows show stronger effects, indicating R&D benefits compound over time.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
