/**
 * PATH: frontend/src/components/paper4/Paper4Methods.tsx
 * PURPOSE: Data & Sample and Methodology sections for Paper 4
 * WHY: Extracted from Paper4.tsx to keep files under 300 lines
 * DEPENDENCIES:
 * - UI components (Card, CardContent): rendering
 * - lucide-react icons: section icons
 */

import { Card, CardContent } from "@/components/ui/card"
import { Database, FlaskConical } from "lucide-react"

interface Paper4MethodsProps {
  totalRdSpend: number
  avgIntensity: number
  cohortSummary: any
  trendData: any[]
}

export function Paper4Methods({ totalRdSpend, avgIntensity, cohortSummary, trendData }: Paper4MethodsProps) {
  return (
    <>
      {/* Data & Sample */}
      <section id="data" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Database className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">3. Data & Sample</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="prose prose-invert max-w-none">
              <p className="text-muted-foreground">
                Our sample comprises {cohortSummary?.total_companies || "..."} S&P 500 companies with 
                R&D data spanning {trendData.length} years. Total cumulative R&D investment in our 
                sample exceeds ${(totalRdSpend / 1e12).toFixed(1)} trillion.
              </p>
            </div>

            {/* Summary Stats */}
            <div className="grid gap-4 md:grid-cols-4">
              <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 text-center">
                <div className="text-2xl font-bold text-amber-400">${(totalRdSpend / 1e12).toFixed(2)}T</div>
                <div className="text-sm text-slate-700 dark:text-slate-200">Total R&D</div>
              </div>
              <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 text-center">
                <div className="text-2xl font-bold text-green-600 dark:text-emerald-400">{avgIntensity.toFixed(1)}%</div>
                <div className="text-sm text-slate-700 dark:text-slate-200">Avg Intensity</div>
              </div>
              <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 text-center">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{cohortSummary?.total_companies || "..."}</div>
                <div className="text-sm text-slate-700 dark:text-slate-200">Companies</div>
              </div>
              <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 text-center">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{trendData.length}</div>
                <div className="text-sm text-slate-700 dark:text-slate-200">Years</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Methodology */}
      <section id="methodology" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <FlaskConical className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">4. Methodology</h2>
        </div>
        <Card>
          <CardContent className="pt-6 max-w-none space-y-6">
            <div>
              <h4 className="text-foreground font-semibold mb-2">4.1 Value Creation Framework</h4>
              <p className="text-muted-foreground">
                We analyze R&D value creation through three lenses: (1) innovation output 
                (patents, new products), (2) operational efficiency (margins, productivity), 
                and (3) competitive position (market share, pricing power).
              </p>
            </div>

            <div>
              <h4 className="text-foreground font-semibold mb-2">4.2 VRIN Analysis</h4>
              <p className="text-muted-foreground mb-2">
                We apply Barney's (1991) VRIN framework to evaluate whether R&D investments 
                create sustainable competitive advantages:
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                  <span className="font-semibold text-blue-600 dark:text-blue-400">V - Valuable:</span>
                  <span className="text-slate-600 dark:text-slate-400 text-sm ml-2">Generates revenue/reduces costs</span>
                </div>
                <div className="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
                  <span className="font-semibold text-purple-600 dark:text-purple-400">R - Rare:</span>
                  <span className="text-slate-600 dark:text-slate-400 text-sm ml-2">Not possessed by competitors</span>
                </div>
                <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                  <span className="font-semibold text-green-600 dark:text-emerald-400">I - Inimitable:</span>
                  <span className="text-slate-600 dark:text-slate-400 text-sm ml-2">Difficult to replicate</span>
                </div>
                <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                  <span className="font-semibold text-amber-600 dark:text-amber-400">N - Non-substitutable:</span>
                  <span className="text-slate-600 dark:text-slate-400 text-sm ml-2">No equivalent alternatives</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-foreground font-semibold mb-2">4.3 Time Lag Analysis</h4>
              <p className="text-muted-foreground">
                We examine the relationship between R&D spending and returns at different 
                horizons (5, 10, and 20 years) to identify the optimal investment period.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
