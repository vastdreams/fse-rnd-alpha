/** 7.1-7.2: Annual R&D Premium + Growth of $1 charts. */

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Cell, AreaChart, Area, ReferenceLine, Legend } from "recharts"
import { SafeChart } from "@/components/SafeChart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function RobustnessCharts({ factorPremiumSeries, growthOf1 }: { publicationStats: any; factorPremiumSeries: any[]; growthOf1: any[]; spanningTests: any; annualHmlData: any; snapshotPayload: any; mispricingTests: any; doubleSortTableRows: any[]; delistingSensitivity: any }) {
  return (
    <>
      <Card className="bg-card">
        <CardHeader>
          <CardTitle>7.1 Annual R&amp;D Premium (Time Series)</CardTitle>
          <CardDescription>Annual Q5-Q1 premium (from snapshot factor premium series).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-[360px]">
            {factorPremiumSeries.length > 0 ? (
              <SafeChart height={360} minHeight={300}>
                <BarChart data={factorPremiumSeries.filter((d) => d.rdPremium !== null)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                  <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                  <RechartsTooltip
                    formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Premium (Q5-Q1)"]}
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                  <Bar dataKey="rdPremium" radius={[4, 4, 0, 0]}>
                    {factorPremiumSeries
                      .filter((d) => d.rdPremium !== null)
                      .map((entry, index) => (
                        <Cell key={index} fill={(entry.rdPremium || 0) >= 0 ? "#22c55e" : "#ef4444"} />
                      ))}
                  </Bar>
                </BarChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">Loading factor premium series...</div>
            )}
          </div>
          <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
            <p className="mb-2">
              Each bar shows the annual R&amp;D premium (Q5 return minus Q1 return) for that year. Green bars indicate years when high-R&amp;D
              stocks outperformed; red bars indicate years when low-R&amp;D stocks outperformed. This is the raw, year-by-year evidence.
            </p>
            <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-foreground">Variability is normal:</strong> Even a "real" premium will have negative years.
                The question is whether the long-run average is positive and economically meaningful (see Table 5.1 for annual results and Table 7.2 for monthly factor spanning tests).
              </li>
              <li>
                <strong className="text-foreground">Win rate:</strong> Count the green vs red bars. A win rate above 50% suggests the premium
                is consistent, not just driven by a few outlier years.
              </li>
              <li>
                <strong className="text-foreground">Drawdown periods:</strong> Look for clusters of red bars. These represent periods when
                the strategy underperformed and help set realistic expectations for implementation.
              </li>
              <li>
                <strong className="text-foreground">Statistical approach:</strong> We use Newey-West standard errors on this annual series
                to account for potential autocorrelation. This is more conservative than assuming independence.
              </li>
            </ul>
          </div>
          <p className="text-xs text-muted-foreground">
            Source: <code>/api/research/publication-snapshot</code> (frozen; factor premium series).
          </p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>7.2 Cumulative Portfolio Performance</CardTitle>
          <CardDescription>Growth of $1 invested in Q5 (high R&amp;D) vs Q1 (low R&amp;D) from annual return series.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-[360px]">
            {growthOf1.length > 0 ? (
              <SafeChart height={360} minHeight={300}>
                <AreaChart data={growthOf1}>
                  <defs>
                    <linearGradient id="q5GradientMain" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="q1GradientMain" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
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
                  <Area
                    type="monotone"
                    dataKey="q5Cumulative"
                    name="Q5 (High R&D)"
                    stroke="#22c55e"
                    fill="url(#q5GradientMain)"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="q1Cumulative"
                    name="Q1 (Low R&D)"
                    stroke="#ef4444"
                    fill="url(#q1GradientMain)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">Loading cumulative series...</div>
            )}
          </div>
          <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
            <p className="mb-2">
              This shows what $1 invested at the start of the sample period would grow to over time. The green line (Q5) represents
              the high-R&amp;D portfolio; the red line (Q1) represents the low-R&amp;D portfolio. The widening gap between lines
              visualizes the cumulative effect of the annual premium.
            </p>
            <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-foreground">Compounding effect:</strong> Small annual differences compound dramatically over time.
                {(() => {
                  const lastQ5 = growthOf1[growthOf1.length - 1]?.q5Cumulative
                  const lastQ1 = growthOf1[growthOf1.length - 1]?.q1Cumulative
                  if (typeof lastQ5 === "number" && typeof lastQ1 === "number") {
                    return ` $1 in Q5 grew to $${lastQ5.toFixed(2)} vs $${lastQ1.toFixed(2)} in Q1.`
                  }
                  return ""
                })()}
              </li>
              <li>
                <strong className="text-foreground">Path dependence:</strong> The final value depends heavily on the sequence of returns.
                A large drawdown early in the period has a bigger impact than one late in the period because there's more time to recover (or not).
              </li>
              <li>
                <strong className="text-foreground">Not risk-adjusted:</strong> This chart shows raw wealth growth, not risk-adjusted performance.
                Q5 may have higher volatility (see Section 9.3). Higher returns with higher risk may or may not be attractive depending on your risk tolerance.
              </li>
              <li>
                <strong className="text-foreground">Hindsight bias warning:</strong> This is a backtest. Actual implementation would face
                trading costs, timing differences, and behavioral challenges not reflected here.
              </li>
            </ul>
          </div>
          <p className="text-xs text-muted-foreground">
            Source: <code>/api/research/publication-snapshot</code> (frozen; computed from annual Q1/Q5 returns).
          </p>
        </CardContent>
      </Card>
    </>
  )
}
