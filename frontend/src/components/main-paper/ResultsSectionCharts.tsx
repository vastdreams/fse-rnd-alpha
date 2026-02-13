/** PATH: main-paper/ResultsSectionCharts.tsx — Cards 5.2 (Quintile bar) + 5.3 (Rolling premium area) */
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Cell, AreaChart, Area, ReferenceLine } from "recharts"
import { SafeChart } from "@/components/SafeChart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function ResultsSectionCharts({ quintileReturnBar5yr, rollingPremium5yr }: { quintileReturnBar5yr: any[]; rollingPremium5yr: any[] }) {
  return (
    <>
      <Card className="bg-card">
        <CardHeader>
          <CardTitle>5.2 Average Annual Returns by R&amp;D Quintile (5-Year Windows)</CardTitle>
          <CardDescription>
            Quintile-level average returns aggregated across stored 5-year windows (descriptive summary).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-[340px]">
            {quintileReturnBar5yr.length > 0 ? (
              <SafeChart height={340} minHeight={300}>
                <BarChart data={quintileReturnBar5yr}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="quintile" stroke="hsl(var(--muted-foreground))" />
                  <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                  <RechartsTooltip
                    formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Avg Return"]}
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="avgReturn" radius={[4, 4, 0, 0]}>
                    {quintileReturnBar5yr.map((entry, index) => (
                      <Cell key={index} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
              Loading quintile summary...
              </div>
            )}
          </div>
          <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
            <p className="mb-2">
              Each bar shows the average annual return for stocks in that R&amp;D quintile. Q1 contains the 20% of firms with the lowest R&amp;D intensity;
              Q5 contains the 20% with the highest. The difference between Q5 and Q1 is the R&amp;D premium.
            </p>
            <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-foreground">Premium magnitude:</strong>{" "}
                {(() => {
                  const q1 = quintileReturnBar5yr.find((r) => r.quintile === "Q1")?.avgReturn
                  const q5 = quintileReturnBar5yr.find((r) => r.quintile === "Q5")?.avgReturn
                  if (typeof q1 !== "number" || typeof q5 !== "number") return "Q5 outperforms Q1."
                  const diff = q5 - q1
                  return `Q5 averages ${q5.toFixed(1)}% vs Q1's ${q1.toFixed(1)}%, a spread of ${diff.toFixed(2)} percentage points per year.`
                })()}
              </li>
              <li>
                <strong className="text-foreground">Pattern shape:</strong> The relationship need not be perfectly monotonic (Q2 &lt; Q3 &lt; Q4).
                What matters is whether Q5 consistently outperforms Q1. Mid-quintiles often show noise because the R&amp;D signal is strongest at extremes.
              </li>
              <li>
                <strong className="text-foreground">Caveat:</strong> This figure aggregates overlapping 5-year windows and is descriptive only.
                For statistical inference, see the non-overlapping annual series in Table 5.1.
              </li>
            </ul>
          </div>
          <p className="text-xs text-muted-foreground">
            Source: <code>/api/research/publication-snapshot</code> (frozen; derived from stored rolling-window results).
          </p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>5.3 Premium Over Time (5-Year Rolling Windows)</CardTitle>
          <CardDescription>
            Rolling 5-year HML premium series (Q5-Q1). Overlapping windows are descriptive; inference is based on the annual non-overlapping series.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-[340px]">
            {rollingPremium5yr.length > 0 ? (
              <SafeChart height={340} minHeight={300}>
                <AreaChart data={rollingPremium5yr}>
                  <defs>
                    <linearGradient id="premiumGradientMain" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="period"
                    stroke="hsl(var(--muted-foreground))"
                    tick={{ fontSize: 10 }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
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
                  <Area type="monotone" dataKey="rdPremium" stroke="#10b981" fill="url(#premiumGradientMain)" strokeWidth={2} />
                </AreaChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
              Loading rolling-window series...
              </div>
            )}
          </div>
          <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
            <p className="mb-2">
              Each point shows the 5-year rolling premium (Q5 return minus Q1 return) for windows ending at that date.
              For example, the point at "2015-2019" shows the average annual premium over those 5 years.
              The green shaded area highlights when the premium is positive (high R&amp;D outperforms).
            </p>
            <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-foreground">Time variation:</strong> The premium is not constant. It can be strongly positive in some periods
                and negative in others. This is normal for any characteristic premium and reflects changing market conditions.
              </li>
              <li>
                <strong className="text-foreground">Regime dependence:</strong> Look for patterns around major events. The premium often behaves differently
                during market stress (2008-2009) vs expansion periods. Section 8 provides regime-by-regime analysis.
              </li>
              <li>
                <strong className="text-foreground">Important caveat:</strong> Adjacent points share 4 of 5 years of data, making them highly correlated.
                Do not interpret the smoothness of this curve as statistical precision. This chart shows trends, not independent evidence.
              </li>
            </ul>
          </div>
          <p className="text-xs text-muted-foreground">
            Source: <code>/api/research/publication-snapshot</code> (frozen; stored rolling-window series).
          </p>
        </CardContent>
      </Card>
    </>
  )
}
