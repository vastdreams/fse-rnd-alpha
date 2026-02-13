/** Portfolio disclaimers, educational section, and research integration card. */
import type { PortfolioData } from "@/hooks/usePortfolioData"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { AlertTriangle, BookOpen, FlaskConical } from "lucide-react"
import { Link } from "react-router-dom"

interface Props { data: PortfolioData; asOfYear: number; nHoldings: number }

export function PortfolioInfo({ data, asOfYear, nHoldings }: Props) {
  const { annualMeanPremiumPct, annualTStat, annualPValue, annualNYears, annualTradingCostPct, CURRENT_YEAR } = data

  return (
    <>
      {/* Methodology Note */}
      <Card className="border border-red-500/30 bg-gradient-to-br from-red-500/5 to-card">
        <CardContent className="pt-4 pb-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
            <div className="text-sm text-muted-foreground space-y-1">
              <p className="font-medium text-amber-600">⚠️ Backtest Data Note</p>
              <p>This backtest uses <strong>point-in-time S&amp;P 500 membership</strong> from official add-date records (companies are only included after their S&amp;P 500 addition date). However, <strong> historical removals are not tracked</strong> in our Tier-1 source, so some companies that were later removed from the index may appear in earlier years. Returns are computed from split-adjusted close prices plus dividend events (total-return proxy including dividends).</p>
              <p><strong>Publication-grade estimates:</strong> For rigorous premium inference, use the frozen snapshot in the{" "}<Link to="/papers/main" className="text-blue-500 hover:underline font-medium">Main Paper</Link>{typeof annualMeanPremiumPct === "number" ? ` (annual HML_RD mean ≈ ${annualMeanPremiumPct.toFixed(2)}%).` : "."}</p>
              <p className="text-xs">Returns use July-June fiscal year convention per Fama-French methodology.{asOfYear < CURRENT_YEAR - 1 && (<span className="text-amber-600 ml-1">Viewing historical ({asOfYear}); metrics reflect performance through that year only.</span>)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Educational Section */}
      <Card className="border-2 border-purple-500/30 bg-gradient-to-br from-purple-500/5 to-card">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg"><BookOpen className="h-5 w-5 text-purple-500" />How ETF{nHoldings} R&D Alpha Selection Works</CardTitle>
          <CardDescription>Understanding the annual reconstitution, rebalancing, and backtest methodology</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-blue-500/10 rounded-lg p-4 border border-blue-500/20">
              <h4 className="font-semibold text-blue-600 dark:text-blue-400 mb-2">📅 Annual Roll Date</h4>
              <p className="text-sm text-muted-foreground"><strong>July 1</strong> of each year (Fama-French convention). This ensures FY(T-1) annual reports are available before selection.</p>
            </div>
            <div className="bg-green-500/10 rounded-lg p-4 border border-green-500/20">
              <h4 className="font-semibold text-green-600 dark:text-green-400 mb-2">📊 Data Used</h4>
              <p className="text-sm text-muted-foreground"><strong>FY(T-1) financials</strong> for R&D intensity. Trailing 3-year momentum and volatility through June 30. Point-in-time data only.</p>
            </div>
            <div className="bg-purple-500/10 rounded-lg p-4 border border-purple-500/20">
              <h4 className="font-semibold text-purple-600 dark:text-purple-400 mb-2">⚖️ Rebalancing</h4>
              <p className="text-sm text-muted-foreground"><strong>Equal weights</strong> reset at each July reconstitution. Holdings drift during the year; no intra-year rebalancing.</p>
            </div>
          </div>
          <div className="bg-slate-100 dark:bg-slate-800 rounded-lg p-4">
            <h4 className="font-semibold mb-3">Annual Cycle Timeline</h4>
            <div className="flex items-center justify-between text-xs text-muted-foreground relative">
              <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-border -z-10" />
              {[{ color: "bg-amber-500", label: "May-Jun", desc: "10-Ks filed" }, { color: "bg-purple-500", label: "Jul 1", desc: "Reconstitute" }, { color: "bg-blue-500", label: "Jul-Jun", desc: "Hold period" }, { color: "bg-green-500", label: "Jun 30", desc: "Measure return" }].map((step, i) => (
                <div key={i} className="flex flex-col items-center gap-1 bg-slate-100 dark:bg-slate-800 px-2">
                  <div className={`w-3 h-3 rounded-full ${step.color}`} />
                  <span>{step.label}</span>
                  <span className="font-medium text-foreground">{step.desc}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { num: "1", color: "bg-purple-500", title: 'What is "Backtest"?', text: "A simulation of what would have happened if you followed this selection rule historically. We re-select holdings each July using only data available at that time, then measure actual returns through the following June." },
              { num: "2", color: "bg-purple-500", title: 'What is "Forecast"?', text: "An expected return range based on market consensus + historical R&D premium. Not a prediction. Shows probability bands (p10/p50/p90) accounting for market uncertainty and premium variability." },
              { num: "3", color: "bg-purple-500", title: "Rebalancing vs Reconstitution", text: "Reconstitution = changing which stocks are in the basket (annually in July). Rebalancing = resetting weights to equal (also annually). We do both together at the July roll date." },
            ].map((item, i) => (
              <div key={i} className="space-y-3">
                <h4 className="font-semibold text-foreground flex items-center gap-2">
                  <span className={`w-6 h-6 rounded-full ${item.color} text-white text-xs flex items-center justify-center`}>{item.num}</span>{item.title}
                </h4>
                <p className="text-sm text-muted-foreground ml-8">{item.text}</p>
              </div>
            ))}
            <div className="space-y-3">
              <h4 className="font-semibold text-foreground flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-amber-500 text-white text-xs flex items-center justify-center">!</span>Important Caveats
              </h4>
              <ul className="text-sm text-muted-foreground space-y-1 ml-8">
                <li>• Past performance ≠ future results</li>
                <li>• Backtests are subject to data quality limitations</li>
                <li>• Transaction costs{typeof annualTradingCostPct === "number" ? ` (~${annualTradingCostPct.toFixed(3)}% annually in snapshot calibration)` : ""} reduce net returns</li>
                <li>• This is a research tool, not investment advice</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Year Disclaimer */}
      {asOfYear === CURRENT_YEAR && (
        <Card className="bg-amber-500/10 border-amber-500/30">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-600 dark:text-amber-400">{CURRENT_YEAR} Data is Preliminary</p>
                <p className="text-xs text-muted-foreground mt-1">U.S. public companies have varying fiscal year end dates. {CURRENT_YEAR} financial data may be incomplete as many companies have not yet filed their annual reports. For rigorous analysis, we recommend using {CURRENT_YEAR - 1} or earlier data.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Research Integration */}
      <Card className="bg-blue-500/5 border-blue-500/20">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-start gap-3">
            <FlaskConical className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-600 dark:text-blue-400">Research-Backed Construction</p>
              <p className="text-xs text-muted-foreground mt-1">
                This portfolio implements the findings from our <Link to="/papers/main" className="text-blue-500 hover:underline font-medium">R&D Alpha research paper</Link>:{" "}<strong>R&D intensity</strong> (R&D/Revenue) predicts future stock returns with an annual, non-overlapping Q5-Q1 premium of{" "}<strong>{typeof annualMeanPremiumPct === "number" ? `${annualMeanPremiumPct.toFixed(2)}%` : "..."}</strong> per year{" "}
                {typeof annualTStat === "number" && typeof annualPValue === "number" ? <>(Newey-West t = {annualTStat.toFixed(2)}, p = {annualPValue < 0.001 ? "<0.001" : annualPValue.toFixed(3)}{typeof annualNYears === "number" ? `; N = ${annualNYears}` : ""})</> : ""}. Holdings are selected using the July-June return convention to avoid look-ahead bias, with point-in-time membership (when available) and explicit exit handling (cash-after-exit) plus delisting sensitivity analysis.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  )
}
