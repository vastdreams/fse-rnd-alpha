/**
 * PATH: frontend/src/components/main-paper/StrategyPortfolioCosts.tsx
 * PURPOSE: Cards 9.1 body (portfolio construction + transaction costs) + 9.2 (net-of-cost table) + 9.3 (risk & drawdown).
 * WHY: Extracted from StrategySection.tsx to keep each file under 300 lines.
 */

import { Link } from "react-router-dom"
import { FlaskConical } from "lucide-react"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Formulas } from "@/components/Formula"

export function StrategyPortfolioCosts({ transactionCosts, netOfCost5yr, rollingAggregates }: { transactionCosts: any; netOfCost5yr: any; rollingAggregates: any }) {
  return (
    <>
      <div className="not-prose p-4 rounded-lg bg-primary/5 border border-primary/20 mb-4">
        <p className="font-semibold text-foreground mb-2 flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-primary" />
          R&amp;D ETF Strategy Tool
        </p>
        <p className="text-sm text-muted-foreground mb-2">
          This section documents the methodology behind the research-grade R&amp;D intensity strategy. For an interactive implementation
          with portfolio analytics, current holdings, and scenario modeling, see the{" "}
          <Link to="/portfolio" className="text-primary hover:underline font-medium">
            R&amp;D ETF page
          </Link>
          .
        </p>
        <p className="text-xs text-muted-foreground">
          The ETF page applies the same July-June formation rules documented here but provides live portfolio composition,
          expected premium forecasts, and implementation metrics.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="p-4 border rounded-lg">
          <p className="font-semibold mb-2 text-foreground">Portfolio Construction Rules</p>
          <ul className="text-sm text-muted-foreground space-y-2 list-disc list-inside">
            <li>
              <strong className="text-foreground">Universe:</strong> point-in-time S&amp;P 500 constituents{" "}
              <InfoTooltip term="point_in_time" size={12} />
            </li>
            <li>
              <strong className="text-foreground">Signal:</strong> prior fiscal-year R&amp;D intensity (R&amp;D / revenue)
            </li>
            <li>
              <strong className="text-foreground">Holdings:</strong> top-20 stocks by R&amp;D intensity (equal-weight)
            </li>
            <li>
              <strong className="text-foreground">Formation:</strong> end of June; hold July through June{" "}
              <InfoTooltip term="july_june_convention" size={12} />
            </li>
            <li>
              <strong className="text-foreground">Rebalance:</strong> annual (once per year)
            </li>
            <li>
              <strong className="text-foreground">Weights:</strong> equal-weight within the selected portfolio{" "}
              <InfoTooltip term="equal_weight" size={12} />
            </li>
          </ul>
          <div className="mt-3">
            <Formulas.Turnover />
          </div>
        </div>

        <div className="p-4 border rounded-lg">
          <p className="font-semibold mb-2 text-foreground">Transaction-cost assumptions</p>
          <p className="text-sm text-muted-foreground mb-3">
            We use the Novy-Marx &amp; Velikov (2016) methodology, calibrated for S&amp;P 500 liquidity characteristics.
            Trading costs include bid-ask spread, market impact, and commissions.
          </p>
          <div className="mb-3">
            <Formulas.TradingCost />
          </div>
          {transactionCosts ? (
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    Annual trading cost
                    <InfoTooltip term="annual_trading_cost" size={12} />
                  </div>
                  <div className="font-semibold">
                    {typeof transactionCosts.annual_trading_cost_pct === "number" ? `${transactionCosts.annual_trading_cost_pct.toFixed(3)}%` : "..."}
                  </div>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    Net premium vs SPY (pp/yr, {transactionCosts.period_label || "N/A"})
                    <InfoTooltip term="net_premium_after_costs" size={12} />
                  </div>
                  <div className="font-semibold">
                    {typeof transactionCosts.net_rd_premium_pct === "number" ? `${transactionCosts.net_rd_premium_pct.toFixed(2)}%` : "..."}
                  </div>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    Premium capture rate
                    <InfoTooltip term="premium_capture_rate" size={12} />
                  </div>
                  <div className="font-semibold">
                    {(() => {
                      const capture = transactionCosts.premium_capture_rate_pct ?? transactionCosts.premium_after_costs_pct
                      if (capture === null || capture === undefined) return "..."
                      return `${capture.toFixed(1)}%`
                    })()}
                  </div>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground">Realized turnover (avg)</div>
                  <div className="font-semibold">
                    {typeof (transactionCosts as any)?.turnover?.avg_turnover_pct === "number"
                      ? `${(transactionCosts as any).turnover.avg_turnover_pct.toFixed(1)}%`
                      : "..."}
                  </div>
                </div>
              </div>

              <div className="p-3 rounded border bg-muted/30 text-sm">
                <p className="font-semibold text-foreground mb-1">Definitions / assumptions (snapshot)</p>
                <pre className="text-xs overflow-auto">
                  {JSON.stringify(
                    {
                      definition: (transactionCosts as any).definition,
                      cost_assumptions: (transactionCosts as any).cost_assumptions,
                    },
                    null,
                    2
                  )}
                </pre>
              </div>

              <p className="text-xs text-muted-foreground">{(transactionCosts as any)?.note || ""}</p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Loading transaction cost model...</p>
          )}
          <p className="text-xs text-muted-foreground mt-3">
            Source: <code>/api/research/publication-snapshot</code> (frozen; transaction cost model).
          </p>
        </div>
      </div>

      <Card className="border-slate-700/50">
        <CardHeader>
          <CardTitle>9.2 Net-of-cost returns (5-year horizon)</CardTitle>
          <CardDescription>Gross vs net returns for each quintile under the transaction-cost model.</CardDescription>
        </CardHeader>
        <CardContent>
          {!netOfCost5yr ? (
            <p className="text-sm text-muted-foreground">Loading net-of-cost results...</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>
                        <span className="flex items-center gap-1">
                          Quintile
                          <InfoTooltip term="quintile" size={12} />
                        </span>
                      </TableHead>
                      <TableHead className="text-right">Gross Return (%)</TableHead>
                      <TableHead className="text-right">Trading Cost (%)</TableHead>
                      <TableHead className="text-right">Net Return (%)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {netOfCost5yr.quintile_results.map((q: any) => (
                      <TableRow key={q.quintile}>
                        <TableCell className="font-medium">Q{q.quintile}</TableCell>
                        <TableCell className="text-right">{q.gross_return_pct.toFixed(2)}</TableCell>
                        <TableCell className="text-right">{q.trading_cost_pct.toFixed(3)}</TableCell>
                        <TableCell className="text-right">{q.net_return_pct.toFixed(2)}</TableCell>
                      </TableRow>
                    ))}
                    <TableRow className="bg-muted/30">
                      <TableCell className="font-semibold">HML (Q5-Q1)</TableCell>
                      <TableCell className="text-right font-semibold">{netOfCost5yr.gross_rd_premium_pct.toFixed(2)}</TableCell>
                      <TableCell className="text-right">-</TableCell>
                      <TableCell className="text-right font-semibold">{netOfCost5yr.net_rd_premium_pct.toFixed(2)}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
              <div className="mt-4 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">How to Read This Table</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">Gross Return:</strong> Average annual return before any trading costs.
                  </li>
                  <li>
                    <strong className="text-foreground">Trading Cost:</strong> Estimated annual cost from rebalancing (bid-ask + impact + commissions).
                  </li>
                  <li>
                    <strong className="text-foreground">Net Return:</strong> What you actually keep after trading costs.
                  </li>
                  <li>
                    <strong className="text-foreground">HML row:</strong> The premium (Q5 minus Q1). This is what matters for the strategy.
                    A gross premium of {netOfCost5yr.gross_rd_premium_pct.toFixed(2)}% becomes {netOfCost5yr.net_rd_premium_pct.toFixed(2)}% after costs.
                  </li>
                </ul>
              </div>
            </>
          )}
          <p className="text-xs text-muted-foreground mt-3">
            Source: <code>/api/research/publication-snapshot</code> (frozen; net-of-cost returns).
          </p>
        </CardContent>
      </Card>

      <Card className="border-slate-700/50">
        <CardHeader>
          <CardTitle>9.3 Risk and drawdown context (descriptive)</CardTitle>
          <CardDescription>Rolling 5-year aggregates for volatility, Sharpe, and maximum drawdown by quintile.</CardDescription>
        </CardHeader>
        <CardContent>
          {!rollingAggregates?.["5yr"] ? (
            <p className="text-sm text-muted-foreground">Loading rolling-window aggregates...</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>
                      <span className="flex items-center gap-1">
                        Quintile
                        <InfoTooltip term="quintile" size={12} />
                      </span>
                    </TableHead>
                    <TableHead className="text-right">Avg Return (%)</TableHead>
                    <TableHead className="text-right">Volatility (%)</TableHead>
                    <TableHead className="text-right">
                      <span className="flex items-center justify-end gap-1">
                        Sharpe
                        <InfoTooltip term="sharpe_ratio" size={12} />
                      </span>
                    </TableHead>
                    <TableHead className="text-right">
                      <span className="flex items-center justify-end gap-1">
                        Max Drawdown (%)
                        <InfoTooltip term="max_drawdown" size={12} />
                      </span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rollingAggregates["5yr"].map((q: any) => (
                    <TableRow key={q.quintile}>
                      <TableCell className="font-medium">{q.label}</TableCell>
                      <TableCell className="text-right">{q.avg_return !== null && q.avg_return !== undefined ? q.avg_return.toFixed(2) : "..."}</TableCell>
                      <TableCell className="text-right">{q.volatility !== null && q.volatility !== undefined ? q.volatility.toFixed(2) : "..."}</TableCell>
                      <TableCell className="text-right">{q.sharpe_ratio !== null && q.sharpe_ratio !== undefined ? q.sharpe_ratio.toFixed(3) : "..."}</TableCell>
                      <TableCell className="text-right">{q.max_drawdown !== null && q.max_drawdown !== undefined ? q.max_drawdown.toFixed(2) : "..."}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-3">
            Source: <code>/api/research/publication-snapshot</code> (frozen; rolling-window aggregates).
          </p>
        </CardContent>
      </Card>
    </>
  )
}
