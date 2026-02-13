/** 7.6: Size × R&D double-sort diagnostic. */

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function RobustnessDoubleSort({ doubleSortTableRows }: { publicationStats: any; factorPremiumSeries: any[]; growthOf1: any[]; spanningTests: any; annualHmlData: any; snapshotPayload: any; mispricingTests: any; doubleSortTableRows: any[]; delistingSensitivity: any }) {
  return (
    <Card className="bg-card">
      <CardHeader>
        <CardTitle>7.6 Size × R&amp;D Double-Sort</CardTitle>
        <CardDescription>R&amp;D premium within size groups (diagnostic for size confounding).</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!doubleSortTableRows.length ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>Double-sort results are not available in this snapshot.</p>
          </div>
        ) : (
          <>
            <div className="text-sm text-muted-foreground space-y-2">
              <p>
                This diagnostic asks whether the R&amp;D premium exists after conditioning on size. We first sort firms into size terciles (a scale proxy
                based on log revenue in the snapshot dataset), then sort into R&amp;D terciles within each size group, and report average returns for each
                Size × R&amp;D cell.
              </p>
              <p>
                The key object is the within-size spread: <span className="font-mono">High R&amp;D - Low R&amp;D</span>. A smaller spread in Large does
                not mean returns are low; it means High and Low behave more similarly within that size bucket.
              </p>
              <p>
                These diagnostics are intended to narrow confounds. Inference in this paper is anchored on the annual non-overlapping premium series
                (Table 5.1); the double-sort uses pooled company-year observations and should be read as a robustness check rather than a primary test.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {doubleSortTableRows.map((r) => {
                const low = r.cells.find((c: any) => c.rd === "Low")?.mean
                const high = r.cells.find((c: any) => c.rd === "High")?.mean
                const spread = r.spread
                return (
                  <div key={r.size} className="p-4 rounded-lg bg-muted/30 border text-center">
                    <h4 className="font-semibold mb-2 text-foreground">{r.size}</h4>
                    <div className="text-xs text-muted-foreground">
                      High {typeof high === "number" ? `${high.toFixed(2)}%` : "..."} vs Low {typeof low === "number" ? `${low.toFixed(2)}%` : "..."}
                    </div>
                    <div className="text-2xl font-bold text-primary mt-2">
                      {typeof spread === "number" ? `${spread >= 0 ? "+" : ""}${spread.toFixed(2)}%` : "..."}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      t = {typeof r.t === "number" ? r.t.toFixed(2) : "..."}
                    </div>
                    <Badge
                      className={
                        r.significant === null ? "bg-slate-500 mt-2" : r.significant ? "bg-green-600 mt-2" : "bg-slate-500 mt-2"
                      }
                    >
                      {r.significant === null ? "..." : r.significant ? "Significant" : "Not Sig."}
                    </Badge>
                  </div>
                )
              })}
            </div>

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Size bucket</TableHead>
                    <TableHead className="text-right">Low R&amp;D</TableHead>
                    <TableHead className="text-right">Mid R&amp;D</TableHead>
                    <TableHead className="text-right">High R&amp;D</TableHead>
                    <TableHead className="text-right">High - Low</TableHead>
                    <TableHead className="text-right">t</TableHead>
                    <TableHead className="text-right">p</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {doubleSortTableRows.map((r) => {
                    const byRd = Object.fromEntries(r.cells.map((c: any) => [c.rd, c]))
                    const fmtCell = (c: any) => {
                      if (!c || typeof c.mean !== "number") return <span className="text-muted-foreground">-</span>
                      return (
                        <div className="text-right">
                          <div className="font-mono">{c.mean.toFixed(2)}%</div>
                          <div className="text-xs text-muted-foreground">{typeof c.n === "number" ? `n=${c.n}` : ""}</div>
                        </div>
                      )
                    }

                    return (
                      <TableRow key={r.size}>
                        <TableCell className="font-medium">{r.size}</TableCell>
                        <TableCell>{fmtCell(byRd["Low"])}</TableCell>
                        <TableCell>{fmtCell(byRd["Medium"])}</TableCell>
                        <TableCell>{fmtCell(byRd["High"])}</TableCell>
                        <TableCell className="text-right font-mono">
                          {typeof r.spread === "number" ? `${r.spread >= 0 ? "+" : ""}${r.spread.toFixed(2)}%` : "..."}
                        </TableCell>
                        <TableCell className="text-right font-mono">{typeof r.t === "number" ? r.t.toFixed(2) : "..."}</TableCell>
                        <TableCell className="text-right font-mono">
                          {typeof r.p === "number" ? (r.p < 0.001 ? "< 0.001" : r.p.toFixed(4)) : "..."}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          </>
        )}

        <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
          <p className="font-semibold text-foreground mb-1">Interpretation</p>
          <ul className="list-disc list-inside space-y-2">
            <li>
              If the premium is present within size buckets, it is less likely to be a pure size proxy. Here, the within-size spread is positive in each
              bucket and statistically meaningful in Small and Large in the snapshot.
            </li>
            <li>
              The within-Large spread is smaller than within-Small. This pattern is consistent with the idea that the signal is more informative (or more
              risk-exposed) where dispersion and uncertainty are higher, and less informative where firms are mature, widely covered, and more efficiently
              priced. This is an interpretation, not a proof.
            </li>
            <li>
              Size is proxied by log revenue in this diagnostic. That is a scale and liquidity proxy, not market capitalization, so the size buckets are
              approximate.
            </li>
            <li>
              The reported t-statistics here come from pooled within-bucket comparisons (a Welch t-test on company-year observations). They are useful for
              diagnostics but are not the primary inference target.
            </li>
            <li>These diagnostics narrow confounds but do not establish a causal mechanism.</li>
          </ul>
        </div>
        <p className="text-xs text-muted-foreground mt-3">
          Source: <code>/api/research/publication-snapshot</code> (frozen; double-sort analysis).
        </p>
      </CardContent>
    </Card>
  )
}
