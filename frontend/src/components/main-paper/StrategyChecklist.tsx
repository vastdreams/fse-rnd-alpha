/**
 * PATH: frontend/src/components/main-paper/StrategyChecklist.tsx
 * PURPOSE: Card 9.6 – Practical implementation checklist (setup, rebalance, during year, expectations).
 * WHY: Extracted from StrategySection.tsx; Cards 9.5+9.6 combined exceeded 300 lines so split into two files.
 */

import { CheckCircle2, TrendingUp, TrendingDown, Target, Scale } from "lucide-react"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function StrategyChecklist({ cohortSummary, investableNetExcessVsSp500Pp, investableUnderperformPct }: { cohortSummary: any; investableNetExcessVsSp500Pp: any; investableUnderperformPct: any }) {
  return (
    <Card className="border-blue-500/30 bg-blue-50/30 dark:bg-blue-950/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs font-bold">✓</span>
          9.6 Practical Implementation Checklist
        </CardTitle>
        <CardDescription>
          Step-by-step guide for implementing the R&D Alpha strategy with real money.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid md:grid-cols-2 gap-4">
          {/* Setup (one-time) */}
          <div className="p-4 rounded-lg border">
            <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white text-xs">1</span>
              One-Time Setup
            </p>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <span>
                  <strong className="text-foreground">Open brokerage account</strong>{" "}
                  <InfoTooltip term="broker_selection" size={12} />
                  <br />
                  <span className="text-xs">Schwab, Fidelity, or Interactive Brokers recommended</span>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <span>
                  <strong className="text-foreground">Decide portfolio size</strong>{" "}
                  <InfoTooltip term="position_sizing" size={12} />
                  <br />
                  <span className="text-xs">Minimum ~$10K for reasonable position sizes (20 × $500)</span>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <span>
                  <strong className="text-foreground">Bookmark data sources</strong>{" "}
                  <InfoTooltip term="data_sources" size={12} />
                  <br />
                  <span className="text-xs">SEC EDGAR (10-Ks), point-in-time S&amp;P 500 constituent history (index provider)</span>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <span>
                  <strong className="text-foreground">Set calendar reminder</strong>
                  <br />
                  <span className="text-xs">June 20: "Compute R&D rankings and rebalance"</span>
                </span>
              </li>
            </ul>
          </div>

          {/* Annual rebalance */}
          <div className="p-4 rounded-lg border">
            <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white text-xs">2</span>
              Annual Rebalance (June)
            </p>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-blue-500 font-mono text-xs mt-0.5">A.</span>
                <span>
                  <strong className="text-foreground">Get current S&P 500 list</strong>
                  <br />
                  <span className="text-xs">
                    ~{typeof cohortSummary?.total_companies === "number" ? cohortSummary.total_companies : "..."} tickers (incl. share classes)
                  </span>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-500 font-mono text-xs mt-0.5">B.</span>
                <span>
                  <strong className="text-foreground">Collect R&D + Revenue</strong>
                  <br />
                  <span className="text-xs">From most recent 10-K (prior fiscal year)</span>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-500 font-mono text-xs mt-0.5">C.</span>
                <span>
                  <strong className="text-foreground">Compute R&D/Revenue, rank, select top 20</strong>{" "}
                  <InfoTooltip term="rd_intensity" size={12} />
                  <br />
                  <span className="text-xs">Exclude firms with 0 R&D (banks, utilities)</span>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-500 font-mono text-xs mt-0.5">D.</span>
                <span>
                  <strong className="text-foreground">Place orders over 3-5 days</strong>{" "}
                  <InfoTooltip term="execution_slippage" size={12} />
                  <br />
                  <span className="text-xs">Limit orders, avoid market-on-open</span>
                </span>
              </li>
            </ul>
          </div>

          {/* During the year */}
          <div className="p-4 rounded-lg border">
            <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-400 text-white text-xs">3</span>
              During the Year (Jul-May)
            </p>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-slate-400">-</span>
                <span>
                  <strong className="text-foreground">Do nothing</strong>{" "}
                  <InfoTooltip term="holding_period" size={12} />
                  <br />
                  <span className="text-xs">Avoid mid-year trading.</span>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-slate-400">-</span>
                <span>
                  <strong className="text-foreground">Reinvest dividends</strong>
                  <br />
                  <span className="text-xs">Set to DRIP or accumulate cash for next rebalance</span>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-slate-400">-</span>
                <span>
                  <strong className="text-foreground">Ignore earnings surprises</strong>
                  <br />
                  <span className="text-xs">Quarterly noise is not signal</span>
                </span>
              </li>
            </ul>
          </div>

          {/* What to expect */}
          <div className="p-4 rounded-lg border bg-purple-50/50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800">
            <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-purple-500 text-white text-xs">!</span>
              What to Expect
            </p>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li className="flex items-start gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <span>
                  <strong className="text-foreground">Long-term edge:</strong>{" "}
                  {typeof investableNetExcessVsSp500Pp === "number"
                    ? `${investableNetExcessVsSp500Pp >= 0 ? "+" : ""}${investableNetExcessVsSp500Pp.toFixed(1)} pp/yr net vs S&P 500 (historical backtest)`
                    : "Net excess vs S&P 500 is reported in the investable backtest results."}
                </span>
              </li>
              <li className="flex items-start gap-2">
                <TrendingDown className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                <span>
                  <strong className="text-foreground">Painful years:</strong>{" "}
                  {typeof investableUnderperformPct === "number"
                    ? `${investableUnderperformPct.toFixed(0)}% of years underperform`
                    : "Some years underperform"}{" "}
                  <InfoTooltip term="tracking_error" size={12} />
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Target className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <span>
                  <strong className="text-foreground">Time horizon:</strong> 5+ years to see the edge
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Scale className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                <span>
                  <strong className="text-foreground">Sector tilt:</strong> Overweight tech/healthcare{" "}
                  <InfoTooltip term="sector_tilt" size={12} />
                </span>
              </li>
            </ul>
          </div>
        </div>

        {/* Quick reference */}
        <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800/50 border">
          <p className="font-semibold text-foreground mb-2">📋 Quick Reference</p>
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-muted-foreground">Holdings:</span>{" "}
              <span className="font-semibold text-foreground">20 stocks (equal-weight)</span>
            </div>
            <div>
              <span className="text-muted-foreground">Rebalance:</span>{" "}
              <span className="font-semibold text-foreground">Annual (June)</span>
            </div>
            <div>
              <span className="text-muted-foreground">Signal:</span>{" "}
              <span className="font-semibold text-foreground">R&D / Revenue</span>
            </div>
            <div>
              <span className="text-muted-foreground">Universe:</span>{" "}
              <span className="font-semibold text-foreground">S&P 500</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
