/**
 * PATH: frontend/src/components/main-paper/StrategyBenchmarkBacktest.tsx
 * PURPOSE: Card 9.4 – Benchmark comparison (growth chart + yearly table).
 * WHY: Extracted from StrategySection.tsx to keep each file under 300 lines.
 */

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend } from "recharts"
import { SafeChart } from "@/components/SafeChart"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function StrategyBenchmarkBacktest({ investableBacktest, investableGrowth }: { investableBacktest: any; investableGrowth: any[] }) {
  return (
    <Card className="border-slate-700/50">
      <CardHeader>
        <CardTitle>9.4 Benchmark comparison (snapshot backtest)</CardTitle>
        <CardDescription>
          Frozen backtest of the implementable portfolio versus an equal-weight benchmark constructed from the cohort.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!investableBacktest ? (
          <p className="text-sm text-muted-foreground">Loading investable backtest...</p>
        ) : (
          <>
            <div className="grid md:grid-cols-5 gap-4 text-sm">
              <div className="p-3 rounded border bg-muted/30">
                <div className="text-xs text-muted-foreground">Portfolio (gross ann.)</div>
                <div className="font-semibold text-green-600 dark:text-green-400">
                  {typeof (investableBacktest as any)?.portfolio_performance?.annualized_return === "number"
                    ? `${(investableBacktest as any).portfolio_performance.annualized_return.toFixed(2)}%`
                    : "..."}
                </div>
              </div>
              <div className="p-3 rounded border bg-muted/30">
                <div className="text-xs text-muted-foreground">EW Cohort (gross ann.)</div>
                <div className="font-semibold">
                  {typeof (investableBacktest as any)?.benchmark_performance?.annualized_return === "number"
                    ? `${(investableBacktest as any).benchmark_performance.annualized_return.toFixed(2)}%`
                    : "..."}
                </div>
              </div>
              <div className="p-3 rounded border bg-muted/30">
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  S&amp;P 500 (gross ann.)
                  <InfoTooltip title="S&P 500 Market Return" size={12}>
                    SPY total-return proxy constructed from split-adjusted close prices plus dividends (reinvested), compounded on the July-June
                    convention used throughout the paper.
                  </InfoTooltip>
                </div>
                <div className="font-semibold">
                  {typeof (investableBacktest as any)?.sp500_performance?.annualized_return === "number"
                    ? `${(investableBacktest as any).sp500_performance.annualized_return.toFixed(2)}%`
                    : "..."}
                </div>
              </div>
              <div className="p-3 rounded border bg-muted/30">
                <div className="text-xs text-muted-foreground">Excess vs S&amp;P 500 (gross)</div>
                <div className="font-semibold">
                  {typeof (investableBacktest as any)?.excess_vs_sp500 === "number"
                    ? `${(investableBacktest as any).excess_vs_sp500 >= 0 ? "+" : ""}${(investableBacktest as any).excess_vs_sp500.toFixed(2)}%`
                    : "..."}
                </div>
              </div>
              <div className="p-3 rounded border bg-muted/30">
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  Avg turnover
                  <InfoTooltip title="Turnover" size={12}>
                    Turnover is computed as 0.5 * sum |w_t - w_(t-1)| across holdings. Higher turnover increases implementation costs and can reduce
                    realized returns after trading frictions.
                  </InfoTooltip>
                </div>
                <div className="font-semibold">
                  {typeof (investableBacktest as any)?.turnover?.avg_turnover_pct === "number"
                    ? `${(investableBacktest as any).turnover.avg_turnover_pct.toFixed(1)}%`
                    : "..."}
                </div>
              </div>
            </div>

            <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
              <p className="font-semibold text-foreground mb-1">Net-of-cost (simple approximation)</p>
              <p>
                {typeof (investableBacktest as any)?.portfolio_performance_net?.annualized_return === "number" &&
                typeof (investableBacktest as any)?.benchmark_performance_net?.annualized_return === "number" &&
                typeof (investableBacktest as any)?.excess_return_net === "number"
                  ? `Portfolio net annualized ${(investableBacktest as any).portfolio_performance_net.annualized_return.toFixed(2)}%, EW cohort net annualized ${(investableBacktest as any).benchmark_performance_net.annualized_return.toFixed(2)}%, net excess vs EW cohort ${(investableBacktest as any).excess_return_net.toFixed(2)} pp.`
                  : "Net-of-cost performance is computed by applying an annual trading cost proportional to realized turnover using literature-calibrated cost parameters."}
              </p>
            </div>

            <div className="h-[340px]">
              {investableGrowth.length > 0 ? (
                <SafeChart height={340} minHeight={300}>
                  <LineChart data={investableGrowth}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                    <YAxis tickFormatter={(v) => `$${(v as number).toFixed(2)}`} stroke="hsl(var(--muted-foreground))" />
                    <RechartsTooltip
                      formatter={(value, name) => [`$${(value as number)?.toFixed(2)}`, name as string]}
                      contentStyle={{
                        backgroundColor: "hsl(var(--popover))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="portfolioIndex" name="R&D Portfolio" stroke="#22c55e" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="benchmarkIndex" name="EW Cohort" stroke="#3b82f6" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="sp500Index" name="S&P 500" stroke="#f59e0b" strokeWidth={2} dot={false} strokeDasharray="5 5" />
                  </LineChart>
                </SafeChart>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">Loading growth series...</div>
              )}
            </div>
            <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground space-y-3">
              <div>
                <p className="font-semibold text-foreground mb-1">What this backtest measures</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong>Portfolio:</strong> Equal-weight Q5 (top 20% by R&amp;D intensity) from the point-in-time S&amp;P 500 cohort,
                    rebalanced annually each July using prior fiscal-year R&amp;D/revenue data.
                  </li>
                  <li>
                    <strong>EW Cohort:</strong> Equal-weight portfolio of all cohort members.
                    This allows a fair comparison of the R&amp;D tilt vs. an uninformed equal-weight strategy in the same universe.
                  </li>
                  <li>
                    <strong>S&amp;P 500:</strong> SPY total-return proxy (split-adjusted close + dividends), compounded on the July-June convention.
                    This is the primary investable benchmark used in the paper.
                  </li>
                  <li>
                    <strong>Excess return:</strong> Portfolio return minus benchmark return. Positive values indicate the R&amp;D tilt
                    outperformed the comparison benchmark.
                  </li>
                </ul>
              </div>
              <div>
                <p className="font-semibold text-foreground mb-1">Turnover and costs</p>
                <p>
                  <strong>Turnover</strong> measures the fraction of the portfolio replaced each year. Low turnover (10-25%) is typical for
                  characteristic-based strategies with annual rebalancing. The <strong>excess net</strong> column subtracts estimated trading
                  costs (proportional to turnover) from gross excess returns.
                </p>
              </div>
              <div>
                <p className="font-semibold text-foreground mb-1">Caveats</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>This is a hypothetical backtest, not a live track record. Actual implementation faces additional frictions.</li>
                  <li>The benchmark is an equal-weight cohort portfolio, not a market-cap-weighted index.</li>
                  <li>Results are snapshot-pinned for reproducibility; read alongside Section 9.1 cost assumptions.</li>
                </ul>
              </div>
            </div>

            {Array.isArray((investableBacktest as any)?.yearly_data) && (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Year</TableHead>
                      <TableHead className="text-right">Portfolio (%)</TableHead>
                      <TableHead className="text-right">EW Cohort (%)</TableHead>
                      <TableHead className="text-right">S&amp;P 500 (%)</TableHead>
                      <TableHead className="text-right">vs S&amp;P 500</TableHead>
                      <TableHead className="text-right">Turnover (%)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(investableBacktest as any).yearly_data.slice(0, 25).map((r: any) => (
                      <TableRow key={r.year}>
                        <TableCell className="font-mono">{r.year}</TableCell>
                        <TableCell className="text-right font-semibold text-green-600 dark:text-green-400">{typeof r.portfolio_return === "number" ? r.portfolio_return.toFixed(2) : "..."}</TableCell>
                        <TableCell className="text-right">{typeof r.benchmark_return === "number" ? r.benchmark_return.toFixed(2) : "..."}</TableCell>
                        <TableCell className="text-right">{typeof r.sp500_return === "number" ? r.sp500_return.toFixed(2) : "..."}</TableCell>
                        <TableCell className={`text-right ${typeof r.excess_vs_sp500 === "number" && r.excess_vs_sp500 >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
                          {typeof r.excess_vs_sp500 === "number" ? `${r.excess_vs_sp500 >= 0 ? "+" : ""}${r.excess_vs_sp500.toFixed(2)}` : "..."}
                        </TableCell>
                        <TableCell className="text-right">{typeof r.turnover_pct === "number" ? r.turnover_pct.toFixed(1) : "..."}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              Source: <code>/api/research/publication-snapshot</code> (frozen; investable backtest).
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}
