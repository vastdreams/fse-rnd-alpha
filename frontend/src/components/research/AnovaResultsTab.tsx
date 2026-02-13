/**
 * PATH: src/components/research/AnovaResultsTab.tsx
 * PURPOSE: ANOVA test result cards (5yr / 10yr / 20yr) and publication summary table
 * WHY: Extracted from Research.tsx to keep each file under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, XCircle } from "lucide-react"
import type { AggregateAnova } from "@/lib/api"

interface AnovaResultsTabProps {
  aggregateAnova: Record<string, AggregateAnova> | undefined
  formatPercent: (val: number | null | undefined) => string
  formatPValue: (p: number | null | undefined) => string
}

export function AnovaResultsTab({ aggregateAnova, formatPercent, formatPValue }: AnovaResultsTabProps) {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-3">
        {["5yr", "10yr", "20yr"].map((windowType) => {
          const anova = aggregateAnova?.[windowType]
          return (
            <Card key={windowType}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {windowType} Window
                  {anova?.anova?.significant_005 ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </CardTitle>
                <CardDescription>
                  {anova?.n_windows || 0} rolling windows analyzed
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <h4 className="font-semibold text-sm">ANOVA Test</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">F-statistic</div>
                    <div className="text-right font-mono">{anova?.anova?.f_statistic?.toFixed(2) || "..."}</div>
                    <div className="text-muted-foreground">p-value</div>
                    <div className="text-right font-mono">{formatPValue(anova?.anova?.p_value)}</div>
                    <div className="text-muted-foreground">η² (effect)</div>
                    <div className="text-right font-mono">{anova?.anova?.eta_squared?.toFixed(3) || "..."}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-semibold text-sm">T-Test (High vs Low)</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">t-statistic</div>
                    <div className="text-right font-mono">{anova?.ttest_high_vs_low?.t_statistic?.toFixed(2) || "..."}</div>
                    <div className="text-muted-foreground">p-value</div>
                    <div className="text-right font-mono">{formatPValue(anova?.ttest_high_vs_low?.p_value)}</div>
                    <div className="text-muted-foreground">Mean diff</div>
                    <div className="text-right font-mono">{formatPercent(anova?.ttest_high_vs_low?.mean_difference)}</div>
                    <div className="text-muted-foreground">Cohen's d</div>
                    <div className="text-right font-mono">{anova?.ttest_high_vs_low?.cohens_d?.toFixed(3) || "..."}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-semibold text-sm">Quintile Means</h4>
                  <div className="flex justify-between text-sm">
                    {Object.entries(anova?.quintile_means || {}).map(([q, mean]) => (
                      <div key={q} className="text-center">
                        <div className="text-muted-foreground text-xs">{q}</div>
                        <div className="font-mono">{(mean as number)?.toFixed(1)}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Publication Summary */}
      <Card className="overflow-hidden">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl">Publication Summary</CardTitle>
          <CardDescription>Key findings for research paper</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left py-4 px-6 font-semibold text-foreground min-w-[200px]">Metric</th>
                  <th className="text-center py-4 px-6 font-semibold text-foreground w-[120px]">5-Year</th>
                  <th className="text-center py-4 px-6 font-semibold text-foreground w-[120px]">10-Year</th>
                  <th className="text-center py-4 px-6 font-semibold text-foreground w-[120px]">20-Year</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                  <td className="py-5 px-6 font-medium text-foreground">R&D Premium (Q5-Q1)</td>
                  <td className="py-5 px-6 text-center">
                    <span className="font-mono text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                      {formatPercent(aggregateAnova?.["5yr"]?.ttest_high_vs_low?.mean_difference)}
                    </span>
                  </td>
                  <td className="py-5 px-6 text-center">
                    <span className="font-mono text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                      {formatPercent(aggregateAnova?.["10yr"]?.ttest_high_vs_low?.mean_difference)}
                    </span>
                  </td>
                  <td className="py-5 px-6 text-center">
                    <span className="font-mono text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                      {formatPercent(aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference)}
                    </span>
                  </td>
                </tr>
                <tr className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                  <td className="py-5 px-6 font-medium text-foreground">Statistical Significance</td>
                  <td className="py-5 px-6 text-center">
                    {aggregateAnova?.["5yr"]?.anova?.significant_005 ? (
                      <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600 px-3 py-1">Yes</Badge>
                    ) : (
                      <Badge variant="secondary" className="px-3 py-1">No</Badge>
                    )}
                  </td>
                  <td className="py-5 px-6 text-center">
                    {aggregateAnova?.["10yr"]?.anova?.significant_005 ? (
                      <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600 px-3 py-1">Yes</Badge>
                    ) : (
                      <Badge variant="secondary" className="px-3 py-1">No</Badge>
                    )}
                  </td>
                  <td className="py-5 px-6 text-center">
                    {aggregateAnova?.["20yr"]?.anova?.significant_005 ? (
                      <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600 px-3 py-1">Yes</Badge>
                    ) : (
                      <Badge variant="secondary" className="px-3 py-1">No</Badge>
                    )}
                  </td>
                </tr>
                <tr className="hover:bg-muted/20 transition-colors">
                  <td className="py-5 px-6 font-medium text-foreground">Effect Size (η²)</td>
                  <td className="py-5 px-6 text-center">
                    <span className="font-mono text-lg text-muted-foreground">
                      {aggregateAnova?.["5yr"]?.anova?.eta_squared?.toFixed(3) || "..."}
                    </span>
                  </td>
                  <td className="py-5 px-6 text-center">
                    <span className="font-mono text-lg text-muted-foreground">
                      {aggregateAnova?.["10yr"]?.anova?.eta_squared?.toFixed(3) || "..."}
                    </span>
                  </td>
                  <td className="py-5 px-6 text-center">
                    <span className="font-mono text-lg text-muted-foreground">
                      {aggregateAnova?.["20yr"]?.anova?.eta_squared?.toFixed(3) || "..."}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  )
}
