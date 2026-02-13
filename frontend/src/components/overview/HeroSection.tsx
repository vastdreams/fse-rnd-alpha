/**
 * PATH: src/components/overview/HeroSection.tsx
 * PURPOSE: Hero banner, "So What?" insight section, and Research Question card.
 * WHY: Extracted from Overview.tsx to keep files under 300 lines.
 */

import { Card, CardContent } from "@/components/ui/card"
import { BarChart3, ArrowRight, BookOpen, Target } from "lucide-react"
import { Link } from "react-router-dom"
import { Badge } from "@/components/ui/badge"

interface HeroSectionProps {
  overview: any
  returnPeriodLabel: string
  premium5yr: number | undefined
  premium10yr: number | undefined
  premium20yr: number | undefined
  compoundingMultiplier10y: number | null
}

export function HeroSection({
  overview,
  returnPeriodLabel,
  premium5yr,
  premium10yr,
  premium20yr,
  compoundingMultiplier10y,
}: HeroSectionProps) {
  return (
    <>
      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border border-slate-700 p-8">
        <div className="absolute inset-0 bg-grid-white/[0.02]" />
        <div className="relative">
          <Badge className="mb-4 bg-emerald-500/20 text-emerald-400 border-emerald-500/30">Pre-print Research</Badge>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-3">
            R&D Factor Analysis Platform
          </h1>
          <p className="text-lg text-slate-300 max-w-2xl mb-6">
            Investigating the relationship between Research & Development investment and 
            long-term stock returns across S&P 500 companies (statements: {overview?.year_range?.min ?? "..."}{overview?.year_range?.max ? `-${overview.year_range.max}` : ""}; returns: {returnPeriodLabel}).
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
              <div className="text-2xl font-bold text-emerald-400">
                {premium5yr !== undefined ? `${premium5yr >= 0 ? "+" : ""}${premium5yr.toFixed(2)}%` : "..."}
              </div>
              <div className="text-sm text-slate-400">5-Year R&D Premium (Q5-Q1)</div>
            </div>
            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
              <div className="text-2xl font-bold text-blue-400">
                {premium10yr !== undefined ? `${premium10yr >= 0 ? "+" : ""}${premium10yr.toFixed(2)}%` : "..."}
              </div>
              <div className="text-sm text-slate-400">10-Year R&D Premium</div>
            </div>
            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
              <div className="text-2xl font-bold text-purple-400">
                {premium20yr !== undefined ? `${premium20yr >= 0 ? "+" : ""}${premium20yr.toFixed(2)}%` : "..."}
              </div>
              <div className="text-sm text-slate-400">20-Year R&D Premium</div>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-3">
            <Link to="/research" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors">
              <BarChart3 className="h-4 w-4" />
              View Research Analysis
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/methodology" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white font-medium transition-colors">
              <BookOpen className="h-4 w-4" />
              Read Methodology
            </Link>
          </div>
        </div>
      </div>

      {/* So What? - The Key Insight */}
      <Card className="border-2 border-emerald-500/50 bg-gradient-to-r from-emerald-500/5 to-transparent">
        <CardContent className="pt-6 pb-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <span className="text-emerald-500">💡</span> So What? Why Does This Matter?
          </h2>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
                <h3 className="font-semibold text-lg mb-2 text-slate-900 dark:text-white">For Investors</h3>
                <p className="text-slate-600 dark:text-slate-300 text-sm">
                  Companies that invest heavily in R&D tend to outperform over the long term. 
                  In this dataset, the average Q5-Q1 premium is{" "}
                  <strong className="text-emerald-600 dark:text-emerald-400">
                    {premium5yr !== undefined ? `${premium5yr.toFixed(2)}%` : "..."}
                  </strong>{" "}
                  per year over 5-year windows (and{" "}
                  <strong className="text-emerald-600 dark:text-emerald-400">
                    {premium20yr !== undefined ? `${premium20yr.toFixed(2)}%` : "..."}
                  </strong>{" "}
                  over 20-year windows).
                </p>
              </div>
              
              <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
                <h3 className="font-semibold text-lg mb-2 text-slate-900 dark:text-white">The Compounding Effect</h3>
                <p className="text-slate-600 dark:text-slate-300 text-sm">
                  <strong>Illustrative math (not a guarantee):</strong> if two portfolios differ by an incremental premium{" "}
                  <em>p</em> per year for <em>n</em> years, the higher-return portfolio ends at \((1+p)^n\) times the lower-return portfolio.
                  {compoundingMultiplier10y !== null && (
                    <>
                      {" "}With <em>p</em>={premium5yr?.toFixed(2)}% and <em>n</em>=10, the multiplier is{" "}
                      <strong className="text-emerald-600 dark:text-emerald-400">
                        ×{compoundingMultiplier10y.toFixed(2)}
                      </strong>.
                    </>
                  )}
                </p>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
                <h3 className="font-semibold text-lg mb-2 text-slate-900 dark:text-white">Potential Portfolio Strategy</h3>
                <ul className="text-slate-600 dark:text-slate-300 text-sm space-y-1">
                  <li>• <strong>Tilt toward high-R&D:</strong> Overweight companies investing &gt;10% of revenue in R&D</li>
                  <li>• <strong>Sector diversification:</strong> Don't just buy Tech - find R&D leaders in every sector</li>
                  <li>• <strong>Long-term horizon:</strong> R&D benefits compound over 5+ years, not months</li>
                </ul>
              </div>
              
              <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-700">
                <h3 className="font-semibold text-lg mb-2 text-amber-700 dark:text-amber-400">⚠️ Important Caveats</h3>
                <ul className="text-slate-600 dark:text-slate-300 text-sm space-y-1">
                  <li>• Past performance ≠ future results</li>
                  <li>
                    • Premium varies by horizon (e.g., {premium5yr !== undefined ? `${premium5yr.toFixed(2)}%` : "..."} at 5yr to{" "}
                    {premium20yr !== undefined ? `${premium20yr.toFixed(2)}%` : "..."} at 20yr), and is not guaranteed
                  </li>
                  <li>• High R&D often means higher volatility</li>
                  <li>• Tier-1 survivorship bias is substantially mitigated but not CRSP/Compustat-grade</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Research Question */}
      <Card className="border-l-4 border-l-blue-500">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Target className="h-8 w-8 text-blue-500 flex-shrink-0" />
            <div>
              <h2 className="text-xl font-semibold mb-2">The Research Question</h2>
              <p className="text-muted-foreground">
                <strong>Do companies that invest heavily in R&D generate better long-term returns for shareholders?</strong>
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                We analyze 31 years of financial data from S&P 500 companies, ranking them into quintiles by R&D intensity 
                (R&D expense ÷ revenue) and comparing their subsequent stock returns. High-R&D companies (Q5) are 
                compared against low-R&D companies (Q1) to measure the "R&D premium."
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  )
}
