/** Portfolio header with controls + key metric cards. */
import type { PortfolioData } from "@/hooks/usePortfolioData"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Zap, FlaskConical } from "lucide-react"
import { AuditableValue } from "@/components/AuditableValue"

interface Props {
  data: PortfolioData
  asOfYear: number
  setAsOfYear: (y: number) => void
  nHoldings: number
  setNHoldings: (n: number) => void
  selectedSector: string | undefined
  setSelectedSector: (s: string | undefined) => void
}

export function PortfolioHeader({ data, asOfYear, setAsOfYear, nHoldings, setNHoldings, selectedSector, setSelectedSector }: Props) {
  const { sectors, yearOptions, selectedYearMetrics, backtestStart, backtestEnd, CURRENT_YEAR } = data

  return (
    <>
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-500/10 via-card to-card border border-purple-500/20 p-8">
        <div className="absolute inset-0 bg-grid-white/[0.02] dark:bg-grid-white/[0.02]" />
        <div className="relative z-10">
          <div className="flex items-start justify-between flex-wrap gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Zap className="h-8 w-8 text-purple-500" />
                <h1 className="text-4xl font-bold">
                  <span className="text-purple-500">ETF{nHoldings}</span>{" "}
                  <span className="text-foreground">R&D Alpha Selection</span>
                </h1>
              </div>
              <p className="text-lg text-muted-foreground max-w-xl">
                Research-backed basket of {nHoldings} R&D-intensive companies as of <span className="text-purple-500 font-semibold">July {asOfYear}</span>
              </p>
              <p className="text-xs text-muted-foreground mt-2 flex items-center gap-2">
                <FlaskConical className="h-3 w-3" />
                <span><strong>Annual Roll:</strong> July reconstitution • FY(T-1) financials • Point-in-time selection</span>
              </p>
            </div>
            <TooltipProvider delayDuration={300}>
              <div className="flex flex-wrap gap-3">
                <Button onClick={() => setAsOfYear(CURRENT_YEAR)} variant={asOfYear === CURRENT_YEAR ? "default" : "outline"} className={`font-medium ${asOfYear === CURRENT_YEAR ? "bg-purple-600 hover:bg-purple-700 text-white shadow-md" : "border-purple-500/30 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/20"}`}>
                  <Zap className="h-4 w-4 mr-1.5" />Current ETF
                </Button>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex flex-col items-center gap-1">
                      <Select value={asOfYear.toString()} onValueChange={(v) => setAsOfYear(parseInt(v))}>
                        <SelectTrigger className="w-36 bg-white dark:bg-slate-800 border-border shadow-sm"><SelectValue placeholder="As of Year" /></SelectTrigger>
                        <SelectContent className="bg-white dark:bg-slate-800">
                          {yearOptions.map((y) => (<SelectItem key={y} value={y.toString()}>{y} {y === CURRENT_YEAR ? "(Preliminary)" : ""}</SelectItem>))}
                        </SelectContent>
                      </Select>
                      <span className="text-xs text-muted-foreground">Check Backtesting</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs"><p className="text-sm"><strong>Backtest Year:</strong> Select a historical year to see what the portfolio would have held and compare our R&D-based forecast vs actual returns.</p></TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <Select value={nHoldings.toString()} onValueChange={(v) => setNHoldings(parseInt(v))}>
                        <SelectTrigger className="w-28 bg-white dark:bg-slate-800 border-border shadow-sm"><SelectValue /></SelectTrigger>
                        <SelectContent className="bg-white dark:bg-slate-800">
                          <SelectItem value="10">ETF10</SelectItem><SelectItem value="20">ETF20</SelectItem><SelectItem value="50">ETF50</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs"><p className="text-sm"><strong>ETF Size:</strong> ETF10 (concentrated), ETF20 (balanced), ETF50 (diversified).</p></TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <Select value={selectedSector || "all"} onValueChange={(v) => setSelectedSector(v === "all" ? undefined : v)}>
                        <SelectTrigger className="w-40 bg-white dark:bg-slate-800 border-border shadow-sm"><SelectValue placeholder="All Sectors" /></SelectTrigger>
                        <SelectContent className="bg-white dark:bg-slate-800">
                          <SelectItem value="all">All Sectors</SelectItem>
                          {(sectors || []).map((s) => (<SelectItem key={s.sector} value={s.sector}>{s.sector}</SelectItem>))}
                        </SelectContent>
                      </Select>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs"><p className="text-sm"><strong>Sector Filter:</strong> Filter holdings by industry sector.</p></TooltipContent>
                </Tooltip>
              </div>
            </TooltipProvider>
          </div>
        </div>
      </div>

      {/* KEY METRICS */}
      <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
        <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 border-emerald-500/20">
          <CardContent className="p-3">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Annualized Return</p>
            <AuditableValue metricId="annualized_return" metricLabel="Annualized Return" value={selectedYearMetrics?.portfolio.annualized_return?.toFixed(1) || "..."} auditParams={{ startYear: backtestStart, endYear: backtestEnd, nHoldings, value: selectedYearMetrics?.portfolio.annualized_return?.toFixed(1) }}>
              <p className="text-2xl font-bold text-emerald-500">{selectedYearMetrics?.portfolio.annualized_return !== undefined ? `${selectedYearMetrics.portfolio.annualized_return >= 0 ? "+" : ""}${selectedYearMetrics.portfolio.annualized_return.toFixed(1)}%` : "..."}</p>
            </AuditableValue>
            <p className="text-[10px] text-muted-foreground">{backtestStart}-{backtestEnd}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
          <CardContent className="p-3">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">S&P 500</p>
            <AuditableValue metricId="sp500_return" metricLabel="S&P 500 (Annualized)" value={selectedYearMetrics?.sp500.annualized_return?.toFixed(1) || "..."} auditParams={{ startYear: backtestStart, endYear: backtestEnd, value: selectedYearMetrics?.sp500.annualized_return?.toFixed(1) }}>
              <p className="text-2xl font-bold text-blue-500">{selectedYearMetrics?.sp500.annualized_return !== undefined ? `${selectedYearMetrics.sp500.annualized_return >= 0 ? "+" : ""}${selectedYearMetrics.sp500.annualized_return.toFixed(1)}%` : "..."}</p>
            </AuditableValue>
            <p className="text-[10px] text-muted-foreground">Benchmark</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20">
          <CardContent className="p-3">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Excess Return</p>
            <AuditableValue metricId="excess_return" metricLabel="Excess Return (Annual)" value={selectedYearMetrics?.excess_vs_sp500?.toFixed(1) || "..."} auditParams={{ startYear: backtestStart, endYear: backtestEnd, value: selectedYearMetrics?.excess_vs_sp500?.toFixed(1), portfolioReturn: selectedYearMetrics?.portfolio.annualized_return?.toFixed(1), benchmarkReturn: selectedYearMetrics?.sp500.annualized_return?.toFixed(1) }}>
              <p className="text-2xl font-bold text-amber-500">{selectedYearMetrics?.excess_vs_sp500 !== undefined ? `${selectedYearMetrics.excess_vs_sp500 >= 0 ? "+" : ""}${selectedYearMetrics.excess_vs_sp500.toFixed(1)}%` : "..."}</p>
            </AuditableValue>
            <p className="text-[10px] text-muted-foreground">vs S&P 500</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20">
          <CardContent className="p-3">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">$100 Becomes</p>
            <AuditableValue metricId="total_value" metricLabel="$100 Becomes" value={selectedYearMetrics?.portfolio.total_return !== undefined ? ((100 * (1 + selectedYearMetrics.portfolio.total_return / 100))).toLocaleString(undefined, {maximumFractionDigits: 0}) : "..."} auditParams={{ startYear: backtestStart, endYear: backtestEnd, value: selectedYearMetrics?.portfolio.total_return !== undefined ? ((100 * (1 + selectedYearMetrics.portfolio.total_return / 100))).toLocaleString(undefined, {maximumFractionDigits: 0}) : "...", totalReturn: selectedYearMetrics?.portfolio.total_return?.toFixed(2), sp500Value: selectedYearMetrics?.sp500.total_return !== undefined ? ((100 * (1 + selectedYearMetrics.sp500.total_return / 100))).toLocaleString(undefined, {maximumFractionDigits: 0}) : "..." }}>
              <p className="text-2xl font-bold text-purple-500">{selectedYearMetrics?.portfolio.total_return !== undefined ? `$${((100 * (1 + selectedYearMetrics.portfolio.total_return / 100))).toLocaleString(undefined, {maximumFractionDigits: 0})}` : "..."}</p>
            </AuditableValue>
            <p className="text-[10px] text-muted-foreground">S&P: ${selectedYearMetrics?.sp500.total_return !== undefined ? ((100 * (1 + selectedYearMetrics.sp500.total_return / 100))).toLocaleString(undefined, {maximumFractionDigits: 0}) : "..."}</p>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
