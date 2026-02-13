/**
 * PATH: src/components/documentation/PortfolioTab.tsx
 * PURPOSE: Renders the "Portfolio" tab content for the Documentation page
 * WHY: Extracted from Documentation.tsx to keep files under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export function PortfolioTab() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>ETF R&D Alpha Selection</CardTitle>
        <CardDescription>Understanding the portfolio construction, annual rolls, and backtesting</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="p-4 border rounded-lg bg-purple-500/5 border-purple-500/20">
            <h3 className="font-semibold mb-2 text-purple-400">ETF Basket Sizes</h3>
            <div className="grid gap-2 md:grid-cols-3 mt-3">
              <div className="p-3 border rounded bg-purple-500/10">
                <Badge className="bg-purple-500">ETF10</Badge>
                <p className="text-xs mt-2 text-muted-foreground">Concentrated (10 holdings)</p>
                <p className="text-xs text-muted-foreground">Higher tracking error</p>
              </div>
              <div className="p-3 border rounded bg-purple-500/10">
                <Badge className="bg-purple-500">ETF20</Badge>
                <p className="text-xs mt-2 text-muted-foreground">Balanced (20 holdings)</p>
                <p className="text-xs text-muted-foreground">Default basket</p>
              </div>
              <div className="p-3 border rounded bg-purple-500/10">
                <Badge className="bg-purple-500">ETF50</Badge>
                <p className="text-xs mt-2 text-muted-foreground">Diversified (50 holdings)</p>
                <p className="text-xs text-muted-foreground">Lower tracking error</p>
              </div>
            </div>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Annual Roll Date: July 1</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Following the Fama-French convention:
            </p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li><strong>Formation:</strong> July 1 of year T</li>
              <li><strong>Data used:</strong> FY(T-1) financials for R&D intensity</li>
              <li><strong>Holding period:</strong> July T to June T+1</li>
              <li><strong>Weighting:</strong> Equal-weight at formation, drift during year</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Portfolio Selection (R&D Alpha Method)</h3>
            <p className="text-sm text-muted-foreground mb-2">
              The R&D Alpha scoring formula:
            </p>
            <code className="block bg-slate-900 text-emerald-400 p-2 rounded text-sm my-2">
              Score = (RD_Intensity × Sector_Adj × Momentum × Quality) / Volatility
            </code>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li><strong>R&D Intensity:</strong> FY(T-1) R&D/Revenue, capped by sector</li>
              <li><strong>Sector Adjustment:</strong> Prevents tech/biotech overconcentration</li>
              <li><strong>Momentum:</strong> Trailing 3-year excess return vs benchmark</li>
              <li><strong>Quality:</strong> Data quality and coverage score</li>
              <li><strong>Volatility:</strong> Trailing 3-year annualized volatility</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Backtesting with Eligibility Gates</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Anti-lookahead rules to prevent survivorship bias:
            </p>
            <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
              <li><strong>Membership gate:</strong> S&P 500 constituent as of formation date</li>
              <li><strong>Listing gate:</strong> Trading for ≥1 year before formation</li>
              <li><strong>Filing gate:</strong> FY(T-1) 10-K filed before formation</li>
              <li><strong>Liquidity gate:</strong> Median 60-day volume ≥ $1M</li>
            </ol>
            <p className="text-xs text-muted-foreground mt-2 italic">
              Mode shown as "Published" when historical S&P 500 membership available, otherwise "Provisional".
            </p>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Performance Metrics</h3>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li><strong>Total Return:</strong> Cumulative return over the period</li>
              <li><strong>Annualized Return (CAGR):</strong> Compound annual growth rate</li>
              <li><strong>Excess Return:</strong> Portfolio return minus S&P 500 return</li>
              <li><strong>Sharpe Ratio:</strong> Risk-adjusted return (using time-varying RF)</li>
              <li><strong>Max Drawdown:</strong> Largest peak-to-trough decline</li>
              <li><strong>Turnover:</strong> Annual portfolio turnover percentage</li>
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
