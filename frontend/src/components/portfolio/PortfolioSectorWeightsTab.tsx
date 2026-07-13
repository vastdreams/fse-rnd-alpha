/** Sector Weights tab – target vs actual weights + R&D Alpha holdings + S&P 500 forecasts. */
import type { PortfolioData } from "@/hooks/usePortfolioData"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TabsContent } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Scale, CheckCircle2, TrendingUp, TrendingDown } from "lucide-react"
import { Link } from "react-router-dom"

interface Props { data: PortfolioData }

export function PortfolioSectorWeightsTab({ data }: Props) {
  const { sectorWeights, rdAlphaHoldings, sp500Forecast } = data

  return (
    <TabsContent value="sector-weights" className="space-y-4">
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Scale className="w-5 h-5 text-blue-500" />Sector Weight Targets vs Actual</CardTitle>
          <CardDescription>Sector-agnostic weighting prevents tech/biotech overconcentration</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Sector</TableHead><TableHead className="text-right">Target</TableHead><TableHead className="text-right">Actual</TableHead>
                <TableHead className="text-right">Min</TableHead><TableHead className="text-right">Max</TableHead>
                <TableHead className="text-right">Companies</TableHead><TableHead className="text-center">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(sectorWeights || []).map((sw: any) => (
                <TableRow key={sw.sector} className="hover:bg-muted/50">
                  <TableCell className="font-medium">{sw.sector}</TableCell>
                  <TableCell className="text-right font-mono">{sw.target_weight.toFixed(1)}%</TableCell>
                  <TableCell className="text-right font-mono font-semibold">{sw.actual_weight.toFixed(1)}%</TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">{sw.min_weight.toFixed(1)}%</TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">{sw.max_weight.toFixed(1)}%</TableCell>
                  <TableCell className="text-right font-mono">{sw.company_count}</TableCell>
                  <TableCell className="text-center">
                    {sw.status === "on_target" && (<Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/30"><CheckCircle2 className="w-3 h-3 mr-1" />On Target</Badge>)}
                    {sw.status === "overweight" && (<Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-500/30"><TrendingUp className="w-3 h-3 mr-1" />Overweight</Badge>)}
                    {sw.status === "underweight" && (<Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30"><TrendingDown className="w-3 h-3 mr-1" />Underweight</Badge>)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* R&D Alpha Holdings with Scoring Details */}
      {rdAlphaHoldings && (
        <Card className="border-border">
          <CardHeader>
            <CardTitle>R&amp;D Alpha Holdings with Score Breakdown</CardTitle>
            <CardDescription>{rdAlphaHoldings.selected_count} selected from {rdAlphaHoldings.total_candidates} candidates</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-h-[500px] overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-10">#</TableHead><TableHead>Symbol</TableHead><TableHead>Sector</TableHead>
                    <TableHead className="text-right">R&amp;D %</TableHead><TableHead className="text-right">Capped</TableHead>
                    <TableHead className="text-right">Sector Adj</TableHead><TableHead className="text-right">Quality</TableHead>
                    <TableHead className="text-right">Score</TableHead><TableHead className="text-right">Weight</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rdAlphaHoldings.holdings.map((h: any) => (
                    <TableRow key={h.symbol} className="hover:bg-muted/50">
                      <TableCell className="text-muted-foreground font-mono">{h.rank}</TableCell>
                      <TableCell className="font-mono font-bold"><Link to={`/companies/${h.symbol}`} className="text-primary hover:underline">{h.symbol}</Link></TableCell>
                      <TableCell><Badge variant="outline" className="bg-muted/50 text-xs">{h.sector}</Badge></TableCell>
                      <TableCell className="text-right font-mono text-green-600 dark:text-green-400">{h.rd_intensity.toFixed(1)}%</TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">{h.rd_intensity_capped.toFixed(1)}%</TableCell>
                      <TableCell className="text-right font-mono">{h.sector_adjustment.toFixed(2)}</TableCell>
                      <TableCell className="text-right font-mono">{(h.quality_score * 100).toFixed(0)}%</TableCell>
                      <TableCell className="text-right font-mono font-semibold text-emerald-500">{h.final_score.toFixed(3)}</TableCell>
                      <TableCell className="text-right font-mono">{h.weight.toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* S&P 500 Forecast Attribution */}
      {sp500Forecast && (
        <Card className="border-border">
          <CardHeader>
            <CardTitle>S&amp;P 500 Consensus Forecasts</CardTitle>
            <CardDescription>{sp500Forecast.methodology_summary}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Year</TableHead><TableHead className="text-right">Low</TableHead><TableHead className="text-right">Mid</TableHead>
                  <TableHead className="text-right">High</TableHead><TableHead className="text-right">Return (Mid)</TableHead><TableHead>Type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sp500Forecast.forecasts.slice(0, 8).map((f: any) => (
                  <TableRow key={f.year} className="hover:bg-muted/50">
                    <TableCell className="font-semibold">{f.year}</TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">{f.level_low.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono font-semibold">{f.level_mid.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">{f.level_high.toLocaleString()}</TableCell>
                    <TableCell className={`text-right font-mono ${f.return_mid >= 0 ? "text-green-600" : "text-red-600"}`}>
                      {f.return_mid >= 0 ? "+" : ""}{f.return_mid.toFixed(1)}%
                    </TableCell>
                    <TableCell>
                      <Badge variant={f.is_forecast ? "outline" : "default"} className={f.is_forecast ? "bg-purple-500/10 text-purple-600" : ""}>{f.is_forecast ? "Forecast" : "Actual"}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="border-t border-border pt-4">
              <h4 className="text-sm font-semibold mb-3">Forecast Sources</h4>
              <div className="grid gap-3 md:grid-cols-2">
                {sp500Forecast.sources.map((source: any) => (
                  <div key={source.name} className="bg-muted/30 rounded-lg p-3">
                    <div className="font-semibold text-sm">{source.name}</div>
                    <div className="text-xs text-muted-foreground">{source.division}</div>
                    <div className="text-xs text-muted-foreground mt-1">Updated: {source.last_update} &bull; {source.frequency}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="text-xs text-muted-foreground italic border-t border-border pt-4">{sp500Forecast.disclaimer}</div>
          </CardContent>
        </Card>
      )}
    </TabsContent>
  )
}
