/**
 * PATH: frontend/src/components/paper3/Paper3Methods.tsx
 * PURPOSE: Data & Sample and Methodology sections for Paper 3
 * WHY: Extracted from Paper3.tsx to keep files under 300 lines
 */

import { Card, CardContent } from "@/components/ui/card"
import { Database, FlaskConical } from "lucide-react"

interface Paper3MethodsProps {
  premiumData: any[]
  rdPremiumStats: any
}

export function Paper3Methods({ premiumData, rdPremiumStats }: Paper3MethodsProps) {
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
                Our sample spans {premiumData.length} years of annual observations. We construct 
                quintile portfolios based on R&D intensity (R&D/Revenue) each year and track 
                subsequent returns. The R&D premium (HML_RD) is defined as Q5 (highest R&D intensity) minus 
                Q1 (lowest R&D intensity) annual returns.
              </p>
            </div>

            {/* Time Series Summary */}
            <div className="grid gap-4 md:grid-cols-4">
              <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 text-center">
                <div className="text-2xl font-bold text-purple-400">{premiumData.length}</div>
                <div className="text-sm text-slate-700 dark:text-slate-200">Years</div>
              </div>
              <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 text-center">
                <div className="text-2xl font-bold text-green-600 dark:text-emerald-400">{typeof rdPremiumStats?.positive_years === "number" ? rdPremiumStats.positive_years : "..."}</div>
                <div className="text-sm text-slate-700 dark:text-slate-200">Positive Years</div>
              </div>
              <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 text-center">
                <div className="text-2xl font-bold text-red-400">{typeof rdPremiumStats?.negative_years === "number" ? rdPremiumStats.negative_years : "..."}</div>
                <div className="text-sm text-slate-700 dark:text-slate-200">Negative Years</div>
              </div>
              <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 text-center">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">5</div>
                <div className="text-sm text-slate-700 dark:text-slate-200">Quintiles</div>
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
              <h4 className="text-foreground font-semibold mb-2">4.1 Premium Construction</h4>
              <p className="text-muted-foreground mb-2">The R&D return premium (HML_RD) is constructed as:</p>
              <div className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-4 rounded-lg font-mono text-sm text-center text-slate-800 dark:text-slate-200">
                RMW_RD = Return(Q5) - Return(Q1)
              </div>
              <p className="text-muted-foreground mt-2">
                where Q5 represents the equal-weighted portfolio of companies in the highest R&D 
                intensity quintile, and Q1 the lowest.
              </p>
            </div>

            <div>
              <h4 className="text-foreground font-semibold mb-2">4.2 Statistical Testing</h4>
              <p className="text-muted-foreground mb-2">We test whether the mean premium differs from zero:</p>
              <div className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-4 rounded-lg font-mono text-sm text-center text-slate-800 dark:text-slate-200">
                t = (Mean Premium) / (Std / √n)
              </div>
              <p className="text-muted-foreground mt-2">
                Under the null hypothesis of no premium, the t-statistic follows a t-distribution 
                with n-1 degrees of freedom.
              </p>
            </div>

            <div>
              <h4 className="text-foreground font-semibold mb-2">4.3 Factor Model Regression</h4>
              <p className="text-muted-foreground mb-2">
                We regress the R&D premium on the Fama-French three factors to test for alpha:
              </p>
              <div className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-4 rounded-lg font-mono text-sm text-center text-slate-800 dark:text-slate-200">
                RMW_RD = α + β₁(Rm-Rf) + β₂(SMB) + β₃(HML) + ε
              </div>
              <p className="text-muted-foreground mt-2">
                A significant positive α indicates the R&D premium is not explained by existing factors.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
