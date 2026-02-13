/** PATH: main-paper/ResultsSectionTables.tsx — Cards 5.4 (Horizon summary) + 5.5 (Key takeaways) */
import { AlertTriangle } from "lucide-react"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function ResultsSectionTables({ annualHmlData, headlinePremiums }: { annualHmlData: any; headlinePremiums: any[] }) {
  return (
    <>
      <Card className="bg-card">
        <CardHeader>
          <CardTitle>5.4 Horizon Summary (Rolling Windows)</CardTitle>
          <CardDescription>
            Summary across 5/10/20-year rolling windows (descriptive; inference shown via t-test/ANOVA).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Horizon</TableHead>
                  <TableHead className="text-right">
                    <span className="flex items-center justify-end gap-1">
                      HML Premium (%)
                      <InfoTooltip term="hml_premium" size={12} />
                    </span>
                  </TableHead>
                  <TableHead className="text-right">
                    <span className="flex items-center justify-end gap-1">
                      t-stat
                      <InfoTooltip term="t_statistic" size={12} />
                    </span>
                  </TableHead>
                  <TableHead className="text-right">
                    <span className="flex items-center justify-end gap-1">
                      p-value
                      <InfoTooltip term="p_value" size={12} />
                    </span>
                  </TableHead>
                  <TableHead className="text-right">
                    <span className="flex items-center justify-end gap-1">
                      η²
                      <InfoTooltip term="eta_squared" size={12} />
                    </span>
                  </TableHead>
                  <TableHead className="text-right">
                    <span className="flex items-center justify-end gap-1">
                      Cohen&apos;s d
                      <InfoTooltip term="cohens_d" size={12} />
                    </span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {headlinePremiums.map((row) => (
                  <TableRow key={row.horizon}>
                    <TableCell className="font-medium">{row.horizon.toUpperCase()}</TableCell>
                    <TableCell className="text-right">
                      {row.premiumPct !== undefined ? row.premiumPct.toFixed(2) : "..."}
                    </TableCell>
                    <TableCell className="text-right">{row.t !== undefined ? row.t.toFixed(2) : "..."}</TableCell>
                    <TableCell className="text-right">
                      {row.p !== undefined ? (row.p < 0.001 ? "< 0.001" : row.p.toFixed(4)) : "..."}
                    </TableCell>
                    <TableCell className="text-right">
                      {row.eta2 !== undefined ? row.eta2.toFixed(3) : "..."}
                    </TableCell>
                    <TableCell className="text-right">
                      {row.cohensD !== undefined ? row.cohensD.toFixed(3) : "..."}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 rounded-lg border-2 border-amber-500/30 bg-amber-500/5 p-4 text-sm">
            <p className="font-semibold text-foreground mb-2 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Why does the 20-year premium appear lower?
            </p>
            <p className="text-muted-foreground mb-3">
              <strong className="text-foreground">Critical methodology note:</strong> Rolling windows sort stocks into quintiles <em>once at window start</em> and
              hold those assignments for the entire period. They do <strong>not</strong> re-sort annually based on updated R&D data.
            </p>
            <div className="grid md:grid-cols-2 gap-3 mb-3">
              <div className="p-3 rounded bg-green-500/10 border border-green-500/20">
                <p className="font-semibold text-green-700 dark:text-green-400 text-xs uppercase tracking-wide mb-1">
                  Annual (re-sorted):{" "}
                  {typeof annualHmlData?.mean_premium === "number" ? `${annualHmlData.mean_premium.toFixed(1)}%` : "…"}
                </p>
                <p className="text-xs text-muted-foreground">Re-sorts every year using current R&D intensity. This is the <strong>investable</strong> premium with annual rebalancing.</p>
              </div>
              <div className="p-3 rounded bg-slate-500/10 border border-slate-500/20">
                <p className="font-semibold text-slate-700 dark:text-slate-400 text-xs uppercase tracking-wide mb-1">
                  20-year rolling (fixed-sort):{" "}
                  {(() => {
                    const p20 = headlinePremiums.find((h) => h.horizon === "20yr")?.premiumPct
                    return typeof p20 === "number" ? `${p20.toFixed(1)}%` : "…"
                  })()}
                </p>
                <p className="text-xs text-muted-foreground">Sorts once in year 1, holds for 20 years. Shows what happens if you <strong>never update</strong> the signal.</p>
              </div>
            </div>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>
                <strong className="text-foreground">Signal staleness:</strong> A company's R&D intensity changes over 20 years. A "high R&D" firm in 2000 may be "low R&D" by 2020.
              </li>
              <li>
                <strong className="text-foreground">Competitive diffusion:</strong> R&D advantages erode through imitation, patent expiration, and market evolution.
              </li>
              <li>
                <strong className="text-foreground">Implication for investors:</strong> To capture the full premium, you must rebalance annually. The R&D ETF (Section 9) does exactly this.
              </li>
            </ul>
          </div>

          <p className="text-sm text-muted-foreground mt-4">
            Source: <code>/api/research/publication-snapshot</code> (frozen). Premium values are based on Q5 minus Q1.
          </p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>5.5 Key takeaways</CardTitle>
          <CardDescription>High-signal interpretation of the main results (Sections 5.1-5.4).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-2">
            <li>
              <strong className="text-foreground">Primary evidence is annual:</strong>{" "}
              {typeof annualHmlData?.mean_premium === "number"
                ? `the mean annual premium is ${annualHmlData.mean_premium.toFixed(2)}% with Newey-West inference reported in Table 5.1.`
                : "the mean annual premium and Newey-West inference are reported in Table 5.1."}
            </li>
            <li>
              <strong className="text-foreground">Time variation matters:</strong> rolling windows illustrate regime dependence; they are used for context, not as independent observations.
            </li>
            <li>
              <strong className="text-foreground">Horizon decay reflects signal staleness, not strategy failure:</strong>{" "}
              {(() => {
                const p20 = headlinePremiums.find((h) => h.horizon === "20yr")?.premiumPct
                const pAnnual = typeof annualHmlData?.mean_premium === "number" ? annualHmlData.mean_premium : undefined
                if (typeof p20 === "number" && typeof pAnnual === "number") {
                  return `the 20-year rolling premium (${p20.toFixed(1)}%) is lower because quintile assignments are fixed at window start and never updated. An investable strategy with annual rebalancing captures the full annual premium (${pAnnual.toFixed(1)}%).`
                }
                return "long-horizon rolling windows show lower premiums because the sort is never updated; investable strategies with annual rebalancing capture the full annual premium."
              })()}
            </li>
          </ul>
          <p className="text-xs text-muted-foreground">
            Source: <code>/api/research/publication-snapshot</code> (frozen). This summary is computed from the same snapshot-backed objects shown above.
          </p>
        </CardContent>
      </Card>
    </>
  )
}
