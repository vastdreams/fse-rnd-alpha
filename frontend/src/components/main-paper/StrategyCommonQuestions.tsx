/**
 * PATH: frontend/src/components/main-paper/StrategyCommonQuestions.tsx
 * PURPOSE: Card 9.7 – FAQ + CTA link to the interactive R&D ETF tool.
 * WHY: Extracted from StrategySection.tsx to keep each file under 300 lines.
 */

import { Link } from "react-router-dom"
import { FlaskConical } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function StrategyCommonQuestions({ investableTurnoverAvgPct }: { investableTurnoverAvgPct: any }) {
  return (
    <Card className="border-slate-500/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold">?</span>
          9.7 Common Questions
        </CardTitle>
        <CardDescription>
          Practical FAQs for implementing the R&D Alpha strategy.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {[
            {
              q: "Can I use fewer than 20 stocks?",
              a: "Yes, but more concentration = more volatility. With 10 stocks, each position is 10% of portfolio. Consider your risk tolerance. The minimum viable portfolio is probably 15-20 stocks for reasonable diversification.",
            },
            {
              q: "What if a stock gets acquired mid-year?",
              a: "Take the cash from the acquisition and hold it until the next rebalance. Don't try to replace the position mid-year because that's extra trading cost with no expected benefit.",
            },
            {
              q: "Should I use sector caps?",
              a: "Optional. Without caps, the portfolio can become concentrated in Technology and Healthcare. With sector caps (e.g., max 25% per sector), you get more diversification but may reduce the R&D signal strength. We show uncapped results in the backtest.",
            },
            {
              q: "How much money do I need to start?",
              a: "Minimum ~$10K for 20 positions of $500 each. Below this, commission costs (if any) and odd-lot execution become proportionally expensive. Ideal is $50K+ for cleaner position sizes.",
            },
            {
              q: "Can I add this to my existing portfolio?",
              a: "Yes. Treat it as a 'sleeve'. Allocate 10-30% of your equity allocation to R&D Alpha, keep the rest in index funds. This reduces tracking error while capturing some of the premium.",
            },
            {
              q: "What about taxes?",
              a:
                typeof investableTurnoverAvgPct === "number"
                  ? `Low turnover (~${investableTurnoverAvgPct.toFixed(1)}%) means most gains are long-term. Annual rebalancing qualifies all held positions for long-term capital gains rates. Consider holding in a tax-advantaged account (IRA, 401k) if concerned about taxes.`
                  : "Low turnover means most gains are long-term. Annual rebalancing qualifies all held positions for long-term capital gains rates. Consider holding in a tax-advantaged account (IRA, 401k) if concerned about taxes.",
            },
            {
              q: "Why not use an ETF instead?",
              a: "No pure R&D intensity ETF exists. Existing 'innovation' ETFs use different signals (patents, themes) and have higher fees. DIY costs ~0 in fees vs 0.5-0.8% for thematic ETFs.",
            },
            {
              q: "What if I miss the June rebalance?",
              a: "Rebalance when you can. A few weeks delay won't materially affect returns. The key is annual rebalancing with fresh R&D data; the exact date matters less than consistency.",
            },
          ].map((faq, i) => (
            <div key={i} className="p-3 rounded-lg border bg-muted/30">
              <p className="font-semibold text-foreground text-sm mb-1">{faq.q}</p>
              <p className="text-muted-foreground text-xs">{faq.a}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
          <p className="font-semibold text-emerald-800 dark:text-emerald-200 text-sm mb-2">🔗 Interactive Tool</p>
          <p className="text-emerald-700 dark:text-emerald-300 text-xs mb-3">
            For current holdings, live rankings, and scenario modeling, use the R&D ETF tool:
          </p>
          <Link to="/portfolio">
            <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white">
              <FlaskConical className="mr-2 h-4 w-4" />
              Open R&D ETF Tool
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
