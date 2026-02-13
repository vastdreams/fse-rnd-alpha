/**
 * PATH: frontend/src/components/main-paper/StrategyTimeline.tsx
 * PURPOSE: Card 9.5 – Implementation timeline (annual calendar view).
 * WHY: Extracted from StrategySection.tsx; Cards 9.5+9.6 combined exceeded 300 lines so split into two files.
 */

import { InfoTooltip } from "@/components/InfoTooltip"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function StrategyTimeline() {
  return (
    <Card className="border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 text-xs font-bold">📅</span>
          9.5 Implementation Timeline
        </CardTitle>
        <CardDescription>
          Annual calendar view: when to do what for the R&D Alpha strategy.{" "}
          <InfoTooltip term="rebalancing_calendar" size={12} />
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Timeline visual */}
        <div className="relative">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Q1: Jan-Mar */}
            <div className="p-4 rounded-lg border bg-slate-50 dark:bg-slate-900/50">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">❄️</span>
                <span className="font-semibold text-foreground">Jan-Mar</span>
              </div>
              <p className="text-xs text-muted-foreground mb-2">10-Ks filing window</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Most Dec fiscal-year 10-Ks filed</li>
                <li>• <strong className="text-foreground">Do nothing</strong> - hold positions</li>
                <li>• Optionally: collect R&D data as filings come in</li>
              </ul>
            </div>

            {/* Q2: Apr-Jun */}
            <div className="p-4 rounded-lg border-2 border-emerald-400 bg-emerald-50 dark:bg-emerald-900/30">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">🌱</span>
                <span className="font-semibold text-foreground">Apr-Jun</span>
                <Badge variant="outline" className="text-[10px] border-emerald-500 text-emerald-700 dark:text-emerald-300">
                  ACTION
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mb-2">Formation period</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• <strong className="text-foreground">Late June:</strong> compute R&D/Rev rankings</li>
                <li>• <strong className="text-foreground">June 25-30:</strong> place rebalance orders</li>
                <li>• Use prior fiscal-year data (now fully available)</li>
                <li>• Spread trades over 3-5 days to minimize impact</li>
              </ul>
            </div>

            {/* Q3: Jul-Sep */}
            <div className="p-4 rounded-lg border bg-slate-50 dark:bg-slate-900/50">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">☀️</span>
                <span className="font-semibold text-foreground">Jul-Sep</span>
              </div>
              <p className="text-xs text-muted-foreground mb-2">New holding period starts</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Portfolio is set for 12 months</li>
                <li>• <strong className="text-foreground">Do nothing</strong> - hold positions</li>
                <li>• Ignore quarterly noise</li>
              </ul>
            </div>

            {/* Q4: Oct-Dec */}
            <div className="p-4 rounded-lg border bg-slate-50 dark:bg-slate-900/50">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">🍂</span>
                <span className="font-semibold text-foreground">Oct-Dec</span>
              </div>
              <p className="text-xs text-muted-foreground mb-2">Continue holding</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• <strong className="text-foreground">Do nothing</strong> - hold positions</li>
                <li>• Dec: consider tax-loss harvesting if applicable</li>
                <li>• Prepare for next year's data collection</li>
              </ul>
            </div>
          </div>

          {/* Arrow indicator */}
          <div className="hidden md:flex items-center justify-center mt-4 text-muted-foreground">
            <div className="flex items-center gap-2 text-xs">
              <span>← Holding Period (12 months)</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400">→ Rebalance → </span>
              <span>Next Holding Period →</span>
            </div>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
          <p className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-1">⚠️ Key insight: You do almost nothing all year</p>
          <p className="text-xs text-amber-700 dark:text-amber-300">
            The strategy requires ~1 day of work per year (computing rankings + placing orders). The rest of the time, you hold.
            This is a feature, not a bug: frequent trading destroys returns through costs.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
