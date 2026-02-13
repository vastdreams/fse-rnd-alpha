/** PURPOSE: Sector Analysis – Radar (6.3), Trends (6.4), Leaders (6.5) */

import { Link } from "react-router-dom"
import { XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, LineChart, Line, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from "recharts"
import { SafeChart } from "@/components/SafeChart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function SectorRadarTrendsLeaders({ sectorRadarData, rdTrendData, rdLeadersBySector }: { sectorRadarData: any[]; rdTrendData: any[]; rdLeadersBySector: any[] }) {
  return (
    <>
      <Card className="bg-card">
        <CardHeader>
          <CardTitle>6.3 Sector Profile (Radar)</CardTitle>
          <CardDescription>Intensity vs. company count across top sectors by R&amp;D intensity.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-[420px]">
            {sectorRadarData.length > 0 ? (
              <SafeChart height={420} minHeight={340}>
                <RadarChart data={sectorRadarData}>
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis dataKey="sector" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} />
                  <PolarRadiusAxis angle={30} domain={[0, "auto"]} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} />
                  <RechartsTooltip
                    formatter={(value, name) => [
                      name === "intensity" ? `${(value as number).toFixed(1)}%` : (value as number).toFixed(0),
                      name === "intensity" ? "R&D Intensity" : "Companies",
                    ]}
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Radar name="R&D Intensity" dataKey="intensity" stroke="#22c55e" fill="#22c55e" fillOpacity={0.25} />
                  <Radar name="Companies" dataKey="companies" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
                </RadarChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">Loading sector radar...</div>
            )}
          </div>
          <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
            <p className="mb-2">
              This radar chart overlays two different concepts for the same sectors: <strong className="text-foreground">R&amp;D intensity</strong> (how
              R&amp;D-heavy the sector is on average) and <strong className="text-foreground">company count</strong> (how many firms from that sector are in
              the sample). The goal is to separate "high intensity" from "broad participation."
            </p>
            <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-foreground">High intensity, few firms:</strong> These sectors can dominate the top quintile even with a small number
                of names, which increases concentration risk.
              </li>
              <li>
                <strong className="text-foreground">Many firms, moderate intensity:</strong> These sectors contribute breadth. Broad participation reduces
                idiosyncratic concentration but may dilute the signal.
              </li>
              <li>
                <strong className="text-foreground">Investor implication:</strong> If the high-R&amp;D portfolio is concentrated in a few sectors, the
                observed premium may come with sector drawdowns and capacity constraints that matter for real allocations.
              </li>
            </ul>
          </div>
          <p className="text-xs text-muted-foreground">
            Source: <code>/api/research/publication-snapshot</code> (frozen; derived from sector aggregates).
          </p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>6.4 R&amp;D Trends Over Time (Context)</CardTitle>
          <CardDescription>Yearly R&amp;D intensity and aggregate R&amp;D spend (Tier-1 descriptive series).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-[380px]">
            {rdTrendData.length > 0 ? (
              <SafeChart height={380} minHeight={320}>
                <LineChart data={rdTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                  <YAxis yAxisId="left" tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tickFormatter={(v) => `$${(v as number).toFixed(0)}B`}
                    stroke="hsl(var(--muted-foreground))"
                  />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                    formatter={(value, name) => {
                      if (name === "avgIntensity") return [`${(value as number).toFixed(2)}%`, "Avg R&D Intensity"]
                      if (name === "totalSpendB") return [`$${(value as number).toFixed(0)}B`, "Total R&D Spend"]
                      return [String(value), String(name)]
                    }}
                  />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="avgIntensity"
                    name="Avg R&D Intensity (%)"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="totalSpendB"
                    name="Total R&D Spend ($B)"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </SafeChart>
            ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">Loading trends...</div>
            )}
          </div>
          <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
            <p className="mb-2">
              The green line (left axis) shows the <strong className="text-foreground">average R&amp;D intensity</strong> in the dataset by year. The blue
              line (right axis) shows <strong className="text-foreground">total R&amp;D dollars</strong> across the covered firms (a scale measure, not a
              return metric). This chart is context for interpretation, not a return test.
            </p>
            <p className="font-semibold text-foreground mb-1 mt-3">Why this matters for the paper</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-foreground">Signal environment shifts:</strong> If the economy becomes more R&amp;D-intensive over time, the
                cross-sectional separation between "high" and "low" can compress or expand, affecting observed premiums.
              </li>
              <li>
                <strong className="text-foreground">Regime interpretation:</strong> Large macro episodes can coincide with changes in financing conditions for
                innovative firms (risk appetite, rates), which can change the premium's behavior without changing the definition of the signal.
              </li>
              <li>
                <strong className="text-foreground">Non-causal:</strong> This is not evidence that higher aggregate R&amp;D "causes" returns. It helps explain
                why event and subperiod splits (Section 8) are informative and why long-horizon results can mix different economic regimes.
              </li>
            </ul>
          </div>
          <p className="text-xs text-muted-foreground">
            Source: <code>/api/research/publication-snapshot</code> (frozen; Tier-1 descriptive series from income statements).
          </p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>6.5 R&amp;D Leaders (Snapshot)</CardTitle>
          <CardDescription>Top 3 firms by average R&amp;D intensity within each sector (snapshot-pinned).</CardDescription>
        </CardHeader>
        <CardContent>
          {!rdLeadersBySector || rdLeadersBySector.length === 0 ? (
            <p className="text-sm text-muted-foreground">Loading leaderboard...</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Sector</TableHead>
                    <TableHead>Top 1</TableHead>
                    <TableHead>Top 2</TableHead>
                    <TableHead>Top 3</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rdLeadersBySector.map(({ sector, leaders }) => {
                    const renderLeader = (r: any) => {
                      if (!r) return <span className="text-muted-foreground">-</span>
                      const intensity =
                        typeof r.avg_rd_intensity === "number" ? `${r.avg_rd_intensity.toFixed(2)}%` : "..."
                      const years = typeof r.years_of_data === "number" ? `${r.years_of_data}y` : "..."
                      return (
                        <div className="min-w-[200px] leading-tight">
                          <div className="font-mono">
                            <Link to={`/companies/${r.symbol}`} className="underline hover:no-underline">
                              {r.symbol}
                            </Link>
                          </div>
                          <div className="text-xs text-muted-foreground">{`${intensity} | ${years}`}</div>
                          {typeof r.name === "string" && r.name ? (
                            <div className="text-xs text-muted-foreground truncate">{r.name}</div>
                          ) : null}
                        </div>
                      )
                    }

                    return (
                      <TableRow key={sector}>
                        <TableCell className="font-medium whitespace-nowrap">{sector}</TableCell>
                        <TableCell>{renderLeader(leaders?.[0])}</TableCell>
                        <TableCell>{renderLeader(leaders?.[1])}</TableCell>
                        <TableCell>{renderLeader(leaders?.[2])}</TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-3">
            Source: <code>/api/research/publication-snapshot</code> (frozen; cohort-based leaderboard).
          </p>
        </CardContent>
      </Card>
    </>
  )
}
