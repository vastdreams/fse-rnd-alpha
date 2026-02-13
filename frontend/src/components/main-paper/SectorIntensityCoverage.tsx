/** PURPOSE: Sector Analysis – Intro card, R&D Intensity (6.1), Coverage (6.2) */

import { AlertTriangle } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Cell, Legend } from "recharts"
import { SafeChart } from "@/components/SafeChart"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function SectorIntensityCoverage({ topSectors, sectorIntensityData, sectorCoverageData }: { topSectors: any[]; sectorIntensityData: any[]; sectorCoverageData: any[] }) {
  return (
    <>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none">
          <p className="text-muted-foreground">
            <strong className="text-foreground">Why sector analysis matters:</strong> Sector composition is a key confounder for any R&amp;D-based sort.
            High-R&amp;D firms are concentrated in a small set of sectors (primarily Technology and Healthcare), and sector-wide shocks
            can mechanically influence the premium. If the R&amp;D premium is entirely driven by sector exposure, an investor could replicate
            it with a simpler sector bet.
          </p>
          <p className="text-muted-foreground mt-2">
            We therefore report (i) R&amp;D intensity by sector, (ii) coverage of eligible firms by sector for long-horizon windows, and
            (iii) descriptive sector trends and leaderboards. These exhibits are descriptive and are intended to support transparent
            interpretation of the return results. The key question is: <em>does the R&amp;D premium exist within sectors, or is it just a sector effect?</em>
          </p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>6.1 R&amp;D Intensity by Sector (from dataset)</CardTitle>
          <CardDescription>
            Sectors with the highest average R&D intensity in the sample (computed from ingested statements).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[380px]">
            {sectorIntensityData.length > 0 ? (
              <SafeChart height={380} minHeight={320}>
                <BarChart data={sectorIntensityData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                  <XAxis type="number" tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                  <YAxis
                    type="category"
                    dataKey="sector"
                    stroke="hsl(var(--muted-foreground))"
                    width={140}
                    tick={{ fontSize: 11 }}
                  />
                  <RechartsTooltip
                    formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Avg R&D Intensity"]}
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="avgRdIntensity" radius={[0, 4, 4, 0]}>
                    {sectorIntensityData.map((entry, index) => (
                      <Cell key={index} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">Loading sector distribution...</div>
            )}
          </div>

          {topSectors.length === 0 ? (
            <p className="text-sm text-muted-foreground">Loading sector summary...</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Sector</TableHead>
                    <TableHead className="text-right">
                      <span className="flex items-center justify-end gap-1">
                        Avg R&D Intensity (%)
                        <InfoTooltip term="rd_intensity" size={12} />
                      </span>
                    </TableHead>
                    <TableHead className="text-right">Companies</TableHead>
                    <TableHead className="text-right">Cumulative R&D ($B)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topSectors.map((s) => (
                    <TableRow key={s.sector}>
                      <TableCell className="font-medium">{s.sector}</TableCell>
                      <TableCell className="text-right">{s.avg_rd_intensity.toFixed(2)}</TableCell>
                      <TableCell className="text-right">{s.company_count}</TableCell>
                      <TableCell className="text-right">{(s.total_rd_spend / 1e9).toFixed(0)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <div className="mt-4 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">How to Read This Chart and Table</p>
            <p className="mb-2">
              The horizontal bar chart shows average R&amp;D intensity by sector. Longer bars indicate sectors where firms invest more in R&amp;D
              relative to their revenue. The table provides additional detail: company count and total R&amp;D dollars.
            </p>
            <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-foreground">Concentration is extreme:</strong> Technology and Healthcare dominate R&amp;D intensity.
                This means high-R&amp;D quintiles (Q4, Q5) will be heavily tilted toward these sectors.
              </li>
              <li>
                <strong className="text-foreground">Implication for the premium:</strong> If the R&amp;D premium is just a "tech bet," it would
                disappear when we control for sectors. Section 7.6 (Double-Sort) tests this directly.
              </li>
              <li>
                <strong className="text-foreground">Dollar magnitude:</strong> Total R&amp;D spend shows the economic significance. Technology
                firms spend the most in absolute terms, even if some Healthcare firms have higher intensity ratios.
              </li>
            </ul>
          </div>

          <div className="mt-4 p-4 bg-muted/30 border rounded-lg flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-muted-foreground">
              <p className="font-semibold text-foreground mb-1">Interpretation caution</p>
              <p>
                Sector composition matters: high-R&D quintiles naturally tilt toward Technology and Healthcare.
                We address this via sector-neutral robustness tests (see Sub-Research 3 / Robustness).
              </p>
            </div>
          </div>

          <p className="text-xs text-muted-foreground mt-3">
            Source: <code>/api/research/publication-snapshot</code> (frozen). Total R&amp;D spend is summed over the dataset period (not annual).
          </p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>6.2 Long-Horizon Coverage by Sector</CardTitle>
          <CardDescription>
            Coverage of eligible firms by sector for 5/10/20-year windows (derived from cohort summary).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-[420px]">
            {sectorCoverageData.length > 0 ? (
              <SafeChart height={420} minHeight={340}>
                <BarChart
                  data={sectorCoverageData.slice().sort((a, b) => (b.coverage20yr || 0) - (a.coverage20yr || 0))}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                  <YAxis type="category" dataKey="sector" stroke="hsl(var(--muted-foreground))" width={160} tick={{ fontSize: 11 }} />
                  <RechartsTooltip
                    formatter={(value) => [`${value}%`, "Coverage"]}
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Bar dataKey="coverage5yr" name="5-Year" fill="#3b82f6" radius={[0, 2, 2, 0]} />
                  <Bar dataKey="coverage10yr" name="10-Year" fill="#8b5cf6" radius={[0, 2, 2, 0]} />
                  <Bar dataKey="coverage20yr" name="20-Year" fill="#22c55e" radius={[0, 2, 2, 0]} />
                </BarChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">Loading coverage...</div>
            )}
          </div>
          <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
            <p className="mb-2">
              Each bar group shows what percentage of firms in that sector have continuous data for 5, 10, and 20-year analysis windows.
              Higher coverage means more firms contribute to the analysis; lower coverage means results are based on fewer observations.
            </p>
            <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-foreground">Coverage declines with horizon:</strong> Fewer firms have 20 years of continuous data than 5 years.
                This is natural: firms merge, go private, or delist over time.
              </li>
              <li>
                <strong className="text-foreground">Sector variation:</strong> Some sectors (e.g., established industries) have higher long-term coverage.
                Newer sectors or those with more M&amp;A activity have lower coverage.
              </li>
              <li>
                <strong className="text-foreground">Implication:</strong> Low coverage doesn't invalidate results, but it increases uncertainty.
                20-year window results should be interpreted with more caution than 5-year results.
              </li>
            </ul>
          </div>
          <p className="text-xs text-muted-foreground">
            Source: <code>/api/research/publication-snapshot</code> (frozen; cohort summary by sector).
          </p>
        </CardContent>
      </Card>
    </>
  )
}
