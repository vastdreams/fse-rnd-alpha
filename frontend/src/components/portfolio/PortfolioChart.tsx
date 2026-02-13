/** Hero performance chart – Growth of $100 with forecast cone overlay. */
import type { PortfolioData } from "@/hooks/usePortfolioData"
import { CHART_COLORS } from "@/hooks/usePortfolioData"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, Line, Area, ComposedChart } from "recharts"
import { AlertTriangle, CheckCircle2, Target, Eye } from "lucide-react"
import { SafeChart } from "@/components/SafeChart"

interface Props {
  data: PortfolioData
  nHoldings: number
  asOfYear: number
  chartsReady: boolean
}

export function PortfolioChart({ data, nHoldings, asOfYear, chartsReady }: Props) {
  const { performanceLineData, forecastVsActual, hasActualsData, actualsYearRange, forecastAccuracy, backtestStart, CURRENT_YEAR } = data

  return (
    <Card className="bg-gradient-to-br from-card to-muted/30 border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-2xl flex items-center gap-3 flex-wrap">
              Portfolio Performance
              <div className="flex items-center gap-2 text-xs font-normal flex-wrap">
                <span className="px-2 py-0.5 bg-cyan-500/20 rounded text-cyan-600 dark:text-cyan-300 border border-cyan-500/30">
                  Historical ({backtestStart}-{asOfYear})
                </span>
                {asOfYear < CURRENT_YEAR - 1 && (
                  <span className={`px-2 py-0.5 rounded border ${hasActualsData ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 border-emerald-500/30' : 'bg-gray-500/20 text-gray-600 dark:text-gray-400 border-gray-500/30'}`}>
                    {hasActualsData
                      ? `Actuals (${actualsYearRange?.min || asOfYear}-${actualsYearRange?.max || CURRENT_YEAR - 1})`
                      : `No Actuals Data`
                    }
                  </span>
                )}
                <span className="px-2 py-0.5 bg-purple-500/20 rounded text-purple-600 dark:text-purple-300 border border-purple-500/30">
                  10yr Forecast
                </span>
              </div>
            </CardTitle>
            <CardDescription className="text-base mt-1">
              Growth of $100 invested in {backtestStart} - ETF{nHoldings} R&D Alpha vs S&amp;P 500 benchmark
            </CardDescription>
          </div>
          {forecastAccuracy && forecastVsActual?.is_historical && (
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
              forecastAccuracy.status === "excellent" ? "bg-emerald-500/10 border border-emerald-500/30" :
              forecastAccuracy.status === "good" ? "bg-yellow-500/10 border border-yellow-500/30" :
              "bg-red-500/10 border border-red-500/30"
            }`}>
              {forecastAccuracy.status === "excellent" ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              ) : forecastAccuracy.status === "good" ? (
                <Target className="h-5 w-5 text-yellow-400" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-400" />
              )}
              <span className={`text-sm font-medium ${
                forecastAccuracy.status === "excellent" ? "text-emerald-400" :
                forecastAccuracy.status === "good" ? "text-yellow-400" : "text-red-400"
              }`}>
                Forecast {forecastAccuracy.status === "excellent" ? "Accurate" : forecastAccuracy.status === "good" ? "Close" : "Divergent"}
              </span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div style={{ height: 384, minHeight: 384 }} className="relative">
          {!chartsReady || performanceLineData.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-muted-foreground">
                <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto mb-2" />
                <p>Loading performance data...</p>
              </div>
            </div>
          ) : (
          <>
            {asOfYear < CURRENT_YEAR - 1 && (
              <div className="absolute top-0 bottom-16 w-px bg-sky-500/70 z-10" style={{
                left: `${((performanceLineData.filter(d => d.historical !== null).length - 0.5) / performanceLineData.length) * 100}%`
              }}>
                <div className="absolute top-5 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-sky-100 dark:bg-sky-500/20 text-xs text-sky-700 dark:text-sky-400 rounded whitespace-nowrap border border-sky-300 dark:border-sky-500/30">
                  Selected: {asOfYear}
                </div>
              </div>
            )}
            {asOfYear < CURRENT_YEAR - 1 && (
              <div className="absolute top-0 bottom-16 w-px bg-green-500/70 z-10" style={{
                left: `${((performanceLineData.filter(d => d.historical !== null || d.actuals !== null).length - 0.5) / performanceLineData.length) * 100}%`
              }}>
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-green-100 dark:bg-green-500/20 text-xs text-green-700 dark:text-green-400 rounded whitespace-nowrap border border-green-300 dark:border-green-500/30">
                  Now ({CURRENT_YEAR - 1})
                </div>
              </div>
            )}
            <SafeChart height={350} debounce={50}>
            <ComposedChart data={performanceLineData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <defs>
                <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_COLORS.forecast} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={CHART_COLORS.forecast} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis dataKey="date" className="text-muted-foreground" tick={{ className: 'fill-muted-foreground', fontSize: 12 }} axisLine={{ className: 'stroke-border' }} tickLine={{ className: 'stroke-border' }} />
              <YAxis className="text-muted-foreground" tickFormatter={(v) => `$${v.toLocaleString()}`} tick={{ className: 'fill-muted-foreground', fontSize: 12 }} axisLine={{ className: 'stroke-border' }} tickLine={{ className: 'stroke-border' }} domain={['dataMin - 10', 'dataMax + 20']} />
              <RechartsTooltip content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const d = payload[0]?.payload
                const isForecast = d?.forecast !== null && d?.forecast !== undefined
                const isActual = d?.actuals !== null && d?.actuals !== undefined
                const portfolioValue = d?.forecast ?? d?.actuals ?? d?.historical ?? 0
                const dataType = isForecast ? "Forecast" : isActual ? "Actuals" : "Historical"
                const dotColor = isForecast ? CHART_COLORS.forecast : isActual ? CHART_COLORS.actuals : CHART_COLORS.historical
                const bgClass = isForecast ? "bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300" : isActual ? "bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-300" : "bg-sky-100 dark:bg-sky-500/20 text-sky-700 dark:text-sky-300"
                return (
                  <div className="bg-popover border border-border rounded-lg p-4 shadow-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-foreground font-medium">{label}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${bgClass}`}>{dataType}</span>
                    </div>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: dotColor }} />
                      <span className="font-bold text-foreground">${portfolioValue?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      <span className="text-muted-foreground text-sm">ETF{nHoldings}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CHART_COLORS.benchmark }} />
                      <span className="font-bold text-foreground">${d?.benchmark?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      <span className="text-muted-foreground text-sm">S&amp;P 500</span>
                    </div>
                    {isForecast && d?.portfolioLow && d?.portfolioHigh && (
                      <div className="mt-2 pt-2 border-t border-border">
                        <div className="text-muted-foreground text-xs flex items-center gap-1">
                          <Eye className="h-3 w-3" />
                          Confidence Range: ${d.portfolioLow.toLocaleString()} - ${d.portfolioHigh.toLocaleString()}
                        </div>
                      </div>
                    )}
                  </div>
                )
              }} />
              <Area type="monotone" dataKey="portfolioHigh" stroke="none" fill="url(#forecastGradient)" fillOpacity={1} connectNulls={false} legendType="none" name="" />
              <Area type="monotone" dataKey="portfolioLow" stroke="none" fill="hsl(var(--background))" fillOpacity={1} connectNulls={false} legendType="none" name="" />
              <Line type="monotone" dataKey="benchmark" name="S&P 500 Benchmark ($)" stroke={CHART_COLORS.benchmark} strokeWidth={2} strokeDasharray="6 4" dot={false} connectNulls={false} activeDot={{ r: 6, fill: CHART_COLORS.benchmark, stroke: '#fff', strokeWidth: 2 }} />
              <Line type="monotone" dataKey="historical" name="R&D Portfolio Historical ($)" stroke={CHART_COLORS.historical} strokeWidth={3} dot={false} connectNulls={false} activeDot={{ r: 8, fill: CHART_COLORS.historical, stroke: '#fff', strokeWidth: 2 }} />
              <Line type="monotone" dataKey="forecast" name="10-Year Forecast ($)" stroke={CHART_COLORS.forecast} strokeWidth={2} strokeDasharray="8 4" dot={(props) => { const { cx, cy, index } = props; if (!cx || !cy) return null; return (<circle key={`forecast-dot-${index}`} cx={cx} cy={cy} r={3} fill={CHART_COLORS.forecast} stroke="#fff" strokeWidth={1} />) }} connectNulls={true} activeDot={{ r: 6, fill: CHART_COLORS.forecast, stroke: '#fff', strokeWidth: 2 }} />
              <Line type="monotone" dataKey="actuals" name="Actual Performance ($)" stroke={CHART_COLORS.actuals} strokeWidth={4} dot={(props) => { const { cx, cy, index } = props; if (!cx || !cy) return null; return (<circle key={`actual-dot-${index}`} cx={cx} cy={cy} r={5} fill={CHART_COLORS.actuals} stroke="#fff" strokeWidth={2} />) }} connectNulls={true} activeDot={{ r: 8, fill: CHART_COLORS.actuals, stroke: '#fff', strokeWidth: 2 }} />
              <Legend verticalAlign="bottom" iconType="circle" wrapperStyle={{ paddingTop: 16, fontSize: 12 }} formatter={(value: string) => { if (!value || value === '') return null; return <span className="text-foreground text-xs">{value}</span> }} />
            </ComposedChart>
            </SafeChart>
          </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
