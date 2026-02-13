/** Paper1Results — Results section (charts, tables, ANOVA) */
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { SafeChart } from "@/components/SafeChart"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Cell,
  AreaChart,
  Area,
  ReferenceLine,
} from "recharts"
import { BarChart3 } from "lucide-react"
import { AnnualHMLTable } from "@/components/AnnualHMLTable"

const QUINTILE_COLORS = ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#0d9488"]
const QUINTILE_LABELS = ["Q1 (Low R&D)", "Q2", "Q3", "Q4", "Q5 (High R&D)"]

const formatQuintileData = (data: any) => {
  if (!data) return []
  return data.map((q: any, i: number) => ({
    quintile: `Q${q.quintile}`,
    label: QUINTILE_LABELS[i],
    avgReturn: q.avg_return,
    totalReturn: q.avg_total_return,
    rdIntensity: q.avg_rd_intensity,
    sharpe: q.avg_sharpe,
    volatility: q.avg_volatility,
    fill: QUINTILE_COLORS[i],
  }))
}

interface Paper1ResultsProps {
  annualHmlData: any
  annualHmlLoading: boolean
  aggregateAnova: any
  quintilePerf5yr: any
  rollingWindowData: any[]
}

export function Paper1Results({ annualHmlData, annualHmlLoading, aggregateAnova, quintilePerf5yr, rollingWindowData }: Paper1ResultsProps) {
  return (
    <section id="results" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <BarChart3 className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">5. Results</h2>
      </div>
      
      <div className="space-y-8">
        {/* 5.1 PRIMARY RESULT: Annual HML Premium (Non-Overlapping) */}
        <div>
          <h3 className="text-xl font-semibold mb-4">5.1 Primary Result: Annual R&D Premium</h3>
          <AnnualHMLTable data={annualHmlData} isLoading={annualHmlLoading} />
        </div>

        {/* 5.2 Descriptive Visualization: Rolling Windows */}
        <div>
          <h3 className="text-xl font-semibold mb-4">5.2 Premium Evolution Over Time</h3>
          <p className="text-muted-foreground mb-4">
            The following visualizations show how the R&D premium has evolved across different time periods. 
            These rolling window results are <strong>descriptive</strong>; formal inference is based on the 
            non-overlapping annual observations above.
          </p>

          {/* Quintile Performance Chart */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Figure 1: Average Annual Returns by R&D Quintile (5-Year Windows)</CardTitle>
              <CardDescription>Higher R&D intensity is associated with higher average returns</CardDescription>
            </CardHeader>
            <CardContent style={{ height: 320, minHeight: 320 }}>
              {formatQuintileData(quintilePerf5yr).length > 0 ? (
                <SafeChart height={320} minHeight={300}>
                  <BarChart data={formatQuintileData(quintilePerf5yr)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="quintile" stroke="hsl(var(--muted-foreground))" />
                    <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                    <RechartsTooltip
                      formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Avg Return"]}
                      contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                    />
                    <Bar dataKey="avgReturn" radius={[4, 4, 0, 0]}>
                      {formatQuintileData(quintilePerf5yr).map((entry, index) => (
                        <Cell key={index} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </SafeChart>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  Loading chart data...
                </div>
              )}
            </CardContent>
          </Card>

          {/* Rolling Window Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Figure 2: R&D Premium Over Time (5-Year Rolling Windows)</CardTitle>
              <CardDescription>Q5 minus Q1 returns show consistent positive premium (descriptive visualization)</CardDescription>
            </CardHeader>
            <CardContent style={{ height: 320, minHeight: 320 }}>
              {rollingWindowData.length > 0 ? (
                <SafeChart height={320} minHeight={300}>
                  <AreaChart data={rollingWindowData}>
                    <defs>
                      <linearGradient id="premiumGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="period" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={60} />
                    <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                    <RechartsTooltip
                      formatter={(value) => [`${(value as number)?.toFixed(2)}%`]}
                      contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                    />
                    <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                    <Area type="monotone" dataKey="rdPremium" stroke="#10b981" fill="url(#premiumGradient)" name="R&D Premium" />
                  </AreaChart>
                </SafeChart>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  Loading chart data...
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 5.3 Statistical Robustness */}
        <div>
          <h3 className="text-xl font-semibold mb-4">5.3 Robustness: HAC-Adjusted Rolling Window Analysis</h3>
          <p className="text-muted-foreground mb-4">
            The following table presents ANOVA results from rolling window analysis. Because overlapping windows 
            create autocorrelated observations, we report Newey-West HAC-adjusted standard errors where applicable.
          </p>
          
          <Card>
            <CardHeader>
              <CardTitle>Table 2: ANOVA Results by Investment Horizon</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 text-foreground">Horizon</th>
                      <th className="text-right py-3 text-foreground">F-Statistic</th>
                      <th className="text-right py-3 text-foreground">p-value</th>
                      <th className="text-right py-3 text-foreground">η² (Eta Squared)</th>
                      <th className="text-right py-3 text-foreground">Cohen's d</th>
                      <th className="text-right py-3 text-foreground">Significance</th>
                    </tr>
                  </thead>
                  <tbody className="text-muted-foreground">
                    <tr className="border-b border-border/50">
                      <td className="py-3">5-Year</td>
                      <td className="text-right font-mono">{aggregateAnova?.["5yr"]?.anova?.f_statistic?.toFixed(2) || "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["5yr"]?.anova?.p_value !== undefined && aggregateAnova?.["5yr"]?.anova?.p_value !== null ? (aggregateAnova["5yr"].anova.p_value < 0.001 ? "< 0.001" : aggregateAnova["5yr"].anova.p_value.toFixed(4)) : "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["5yr"]?.anova?.eta_squared?.toFixed(3) || "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["5yr"]?.ttest_high_vs_low?.cohens_d?.toFixed(2) || "..."}</td>
                      <td className="text-right"><Badge variant="outline" className={aggregateAnova?.["5yr"]?.anova?.significant_001 ? "text-green-600 dark:text-emerald-400 border-green-500/30 dark:border-emerald-500/30" : "text-muted-foreground border-border"}>
                        {aggregateAnova?.["5yr"]?.anova?.significant_001 ? "***" : aggregateAnova?.["5yr"]?.anova?.significant_005 ? "**" : "..."}
                      </Badge></td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-3">10-Year</td>
                      <td className="text-right font-mono">{aggregateAnova?.["10yr"]?.anova?.f_statistic?.toFixed(2) || "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["10yr"]?.anova?.p_value !== undefined && aggregateAnova?.["10yr"]?.anova?.p_value !== null ? (aggregateAnova["10yr"].anova.p_value < 0.001 ? "< 0.001" : aggregateAnova["10yr"].anova.p_value.toFixed(4)) : "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["10yr"]?.anova?.eta_squared?.toFixed(3) || "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["10yr"]?.ttest_high_vs_low?.cohens_d?.toFixed(2) || "..."}</td>
                      <td className="text-right"><Badge variant="outline" className={aggregateAnova?.["10yr"]?.anova?.significant_001 ? "text-green-600 dark:text-emerald-400 border-green-500/30 dark:border-emerald-500/30" : "text-muted-foreground border-border"}>
                        {aggregateAnova?.["10yr"]?.anova?.significant_001 ? "***" : aggregateAnova?.["10yr"]?.anova?.significant_005 ? "**" : "..."}
                      </Badge></td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-3">20-Year</td>
                      <td className="text-right font-mono">{aggregateAnova?.["20yr"]?.anova?.f_statistic?.toFixed(2) || "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["20yr"]?.anova?.p_value !== undefined && aggregateAnova?.["20yr"]?.anova?.p_value !== null ? (aggregateAnova["20yr"].anova.p_value < 0.001 ? "< 0.001" : aggregateAnova["20yr"].anova.p_value.toFixed(4)) : "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["20yr"]?.anova?.eta_squared?.toFixed(3) || "..."}</td>
                      <td className="text-right font-mono">{aggregateAnova?.["20yr"]?.ttest_high_vs_low?.cohens_d?.toFixed(2) || "..."}</td>
                      <td className="text-right"><Badge variant="outline" className={aggregateAnova?.["20yr"]?.anova?.significant_001 ? "text-green-600 dark:text-emerald-400 border-green-500/30 dark:border-emerald-500/30" : "text-muted-foreground border-border"}>
                        {aggregateAnova?.["20yr"]?.anova?.significant_001 ? "***" : aggregateAnova?.["20yr"]?.anova?.significant_005 ? "**" : "..."}
                      </Badge></td>
                    </tr>
                  </tbody>
                </table>
                <p className="text-xs text-muted-foreground mt-2">*** p {"<"} 0.001. Note: Rolling window analysis uses HAC-adjusted standard errors.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}
