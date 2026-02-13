/** Stats row beneath the hero chart + four summary metric cards. */
import type { PortfolioData } from "@/hooks/usePortfolioData"
import { formatPercent, CHART_COLORS } from "@/hooks/usePortfolioData"
import { Card, CardContent } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Target, BarChart3 } from "lucide-react"
import { AuditableValue } from "@/components/AuditableValue"

interface Props {
  data: PortfolioData
  nHoldings: number
}

export function PortfolioSummary({ data, nHoldings }: Props) {
  const { performanceLineData, cumulativeExcessVsSp500, forecastVsActual, selectedYearMetrics, backtestStart, backtestEnd } = data

  const lastPoint = performanceLineData[performanceLineData.length - 1]

  return (
    <>
      {/* Stats Row - Compact */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-border">
        <div className="text-center p-3 rounded-lg bg-purple-50 dark:bg-purple-500/10">
          <p className="text-xl font-bold text-purple-600 dark:text-purple-400">
            ${(lastPoint?.forecast || lastPoint?.actuals || lastPoint?.historical)?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || "..."}
          </p>
          <p className="text-xs text-muted-foreground">Portfolio Value</p>
        </div>
        <div className="text-center p-3 rounded-lg bg-slate-100 dark:bg-slate-800">
          <p className="text-xl font-bold text-slate-600 dark:text-slate-300">
            ${lastPoint?.benchmark?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || "..."}
          </p>
          <p className="text-xs text-muted-foreground">S&amp;P 500</p>
        </div>
        <div className={`text-center p-3 rounded-lg ${
          cumulativeExcessVsSp500 === null ? 'bg-slate-100 dark:bg-slate-800'
            : cumulativeExcessVsSp500 >= 0 ? 'bg-green-50 dark:bg-green-500/10' : 'bg-red-50 dark:bg-red-500/10'
        }`}>
          <p className={`text-xl font-bold ${
            cumulativeExcessVsSp500 === null ? 'text-slate-600 dark:text-slate-300'
              : cumulativeExcessVsSp500 >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
          }`}>
            {formatPercent(cumulativeExcessVsSp500)}
          </p>
          <p className="text-xs text-muted-foreground">Excess vs S&amp;P</p>
        </div>
        <div className="text-center p-3 rounded-lg bg-amber-50 dark:bg-amber-500/10">
          <p className="text-xl font-bold text-amber-600 dark:text-amber-400">
            +{(forecastVsActual?.forecast_premium ?? 5.0).toFixed(1)}%
          </p>
          <p className="text-xs text-muted-foreground">R&amp;D Premium</p>
        </div>
      </div>

      {/* Summary Stats Cards - Compact */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 border-emerald-500/20 hover:border-emerald-500/40 transition-colors">
          <CardContent className="p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">Annualized</span>
              <TrendingUp className="h-3 w-3 text-emerald-500" />
            </div>
            <AuditableValue metricId="annualized_return" metricLabel="Annualized Portfolio" value={selectedYearMetrics?.portfolio.annualized_return?.toFixed(1) || "..."} auditParams={{ startYear: backtestStart, endYear: backtestEnd, nHoldings, value: selectedYearMetrics?.portfolio.annualized_return?.toFixed(1) }} showHoverIndicator={false}>
              <div className="text-xl font-bold text-emerald-400">{formatPercent(selectedYearMetrics?.portfolio.annualized_return)}</div>
            </AuditableValue>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20 hover:border-blue-500/40 transition-colors">
          <CardContent className="p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">S&amp;P 500</span>
              <BarChart3 className="h-3 w-3 text-blue-500" />
            </div>
            <AuditableValue metricId="sp500_return" metricLabel="Annualized S&P 500" value={selectedYearMetrics?.sp500.annualized_return?.toFixed(1) || "..."} auditParams={{ startYear: backtestStart, endYear: backtestEnd, value: selectedYearMetrics?.sp500.annualized_return?.toFixed(1) }} showHoverIndicator={false}>
              <div className="text-xl font-bold text-blue-400">{formatPercent(selectedYearMetrics?.sp500.annualized_return)}</div>
            </AuditableValue>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20 hover:border-purple-500/40 transition-colors">
          <CardContent className="p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">Alpha</span>
              {(selectedYearMetrics?.excess_vs_sp500 || 0) >= 0 ? (
                <TrendingUp className="h-3 w-3 text-purple-500" />
              ) : (
                <TrendingDown className="h-3 w-3 text-red-500" />
              )}
            </div>
            <AuditableValue metricId="excess_return" metricLabel="Alpha Generated" value={selectedYearMetrics?.excess_vs_sp500?.toFixed(1) || "..."} auditParams={{ startYear: backtestStart, endYear: backtestEnd, value: selectedYearMetrics?.excess_vs_sp500?.toFixed(1), portfolioReturn: selectedYearMetrics?.portfolio.annualized_return?.toFixed(1), benchmarkReturn: selectedYearMetrics?.sp500.annualized_return?.toFixed(1) }} showHoverIndicator={false}>
              <div className={`text-xl font-bold ${(selectedYearMetrics?.excess_vs_sp500 || 0) >= 0 ? 'text-purple-400' : 'text-red-400'}`}>{formatPercent(selectedYearMetrics?.excess_vs_sp500)}</div>
            </AuditableValue>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20 hover:border-amber-500/40 transition-colors">
          <CardContent className="p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">Sharpe</span>
              <Target className="h-3 w-3 text-amber-500" />
            </div>
            <AuditableValue metricId="sharpe_ratio" metricLabel="Sharpe Ratio" value={selectedYearMetrics?.portfolio.sharpe_ratio?.toFixed(2) || "..."} auditParams={{ startYear: backtestStart, endYear: backtestEnd, value: selectedYearMetrics?.portfolio.sharpe_ratio?.toFixed(2), portfolioReturn: selectedYearMetrics?.portfolio.annualized_return?.toFixed(1), volatility: selectedYearMetrics?.portfolio.volatility?.toFixed(1) }} showHoverIndicator={false}>
              <div className="text-xl font-bold text-amber-400">{selectedYearMetrics?.portfolio.sharpe_ratio?.toFixed(2) || "..."}</div>
            </AuditableValue>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
