/**
 * PATH: frontend/src/components/methodology/MethodologyAnalysis.tsx
 * PURPOSE: Quintile Construction, Return Calculation, and Statistical Tests sections
 * WHY: Split from Methodology.tsx to stay under 300-line limit
 * DEPENDENCIES:
 *   - ui/card: layout primitives
 *   - lucide-react: section icons
 *   - Formula: math formula rendering (TSR, ANOVA, effect sizes, etc.)
 */

import { Card, CardContent } from "@/components/ui/card"
import { Scale, Calculator, FlaskConical } from "lucide-react"
import { Sub, Sup, Var, Greek, Formulas } from "@/components/Formula"

export function MethodologyAnalysis() {
  return (
    <>
      {/* Quintile Construction */}
      <section id="quintile-construction" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Scale className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">3. Quintile Portfolio Construction</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <h3 className="text-lg font-semibold text-foreground">Process</h3>
            <p className="text-muted-foreground leading-relaxed">
              At portfolio formation (July 1 each year, per the Fama-French convention), we construct 5 portfolios:
            </p>

            <div className="p-4 bg-muted/50 rounded-lg border border-border font-mono text-sm space-y-2">
              <p className="text-muted-foreground"># Step 1: Gather R&D intensity using fiscal-year data (FY T-1 for returns starting in July T)</p>
              <p className="text-emerald-500">intensities = get_rd_intensity(companies, fiscal_year=T-1)</p>
              <p className="text-muted-foreground mt-3"># Step 2: Rank all companies by R&D intensity</p>
              <p className="text-emerald-500">ranked = intensities.sort_values(ascending=True)</p>
              <p className="text-muted-foreground mt-3"># Step 3: Assign to quintiles (equal-sized groups)</p>
              <p className="text-emerald-500">quintile = pd.qcut(ranked, q=5, labels=[1, 2, 3, 4, 5])</p>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Quintile Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 text-foreground">Quintile</th>
                    <th className="text-left py-3 text-foreground">Percentile</th>
                    <th className="text-left py-3 text-foreground">Typical Intensity</th>
                    <th className="text-left py-3 text-foreground">Example Sectors</th>
                  </tr>
                </thead>
                <tbody className="text-muted-foreground">
                  <tr className="border-b border-border/50"><td className="py-2">Q1 (Lowest)</td><td>0-20%</td><td>0-2%</td><td>Utilities, REITs, Banks</td></tr>
                  <tr className="border-b border-border/50"><td className="py-2">Q2</td><td>20-40%</td><td>2-5%</td><td>Consumer Goods, Industrials</td></tr>
                  <tr className="border-b border-border/50"><td className="py-2">Q3</td><td>40-60%</td><td>5-8%</td><td>Mixed Industries</td></tr>
                  <tr className="border-b border-border/50"><td className="py-2">Q4</td><td>60-80%</td><td>8-12%</td><td>Tech Hardware, Pharma</td></tr>
                  <tr><td className="py-2">Q5 (Highest)</td><td>80-100%</td><td>12%+</td><td>Biotech, Software, Semiconductors</td></tr>
                </tbody>
              </table>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Portfolio Weighting</h3>
            <p className="text-muted-foreground leading-relaxed">
              <strong>Equal-weighted portfolios:</strong> Each company in a quintile receives equal weight (1/N). 
              This prevents large-cap companies from dominating results and provides a cleaner test of the R&D effect.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Return Calculation */}
      <section id="return-calculation" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Calculator className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">4. Return Calculation</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="flex flex-wrap items-start gap-4 mb-4">
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-1">Total Shareholder Return</h3>
                <p className="text-xs text-muted-foreground">
                  where <Var>P</Var> is the split-adjusted close; dividends are incorporated via ex-dividend cashflows to form a total-return proxy
                </p>
              </div>
              <Formulas.TSR />
            </div>

            <div className="flex flex-wrap items-start gap-4">
              <h3 className="text-lg font-semibold text-foreground">Annualization:</h3>
              <div className="flex flex-wrap gap-2">
                <Formulas.Cumulative />
                <Formulas.Annualized />
              </div>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Benchmark</h3>
            <p className="text-muted-foreground leading-relaxed">
              The core research object is the within-universe premium (Q5 − Q1). Benchmark comparisons (e.g., vs an S&P 500 proxy) are reported
              separately in the investable strategy exhibits, using consistent return conventions and cost assumptions.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Statistical Tests */}
      <section id="statistical-tests" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <FlaskConical className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">5. Statistical Tests</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="flex flex-wrap items-start gap-4 mb-2">
              <div>
                <h3 className="text-lg font-semibold text-foreground">ANOVA</h3>
                <p className="text-xs text-muted-foreground">Tests if mean returns differ across quintiles</p>
              </div>
              <Formulas.ANOVA />
            </div>
            <div className="flex flex-wrap gap-2 ml-0 md:ml-4">
              <Formulas.NullHypothesis />
              <Formulas.AltHypothesis />
            </div>
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-sm font-semibold text-amber-500 mb-2">⚠️ ANOVA Limitation</p>
              <p className="text-xs text-muted-foreground">
                Standard ANOVA assumes independent, normally distributed observations. Our quintile returns 
                may violate normality. We supplement with non-parametric tests (Kruskal-Wallis) for robustness.
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground">T-Tests: Welch's vs Student's</h3>
            <p className="text-muted-foreground leading-relaxed">
              When comparing Q5 (high R&D) vs Q1 (low R&D), we use <strong className="text-foreground">Welch's t-test</strong> 
              (unequal variance) rather than Student's t-test:
            </p>
            <div className="p-4 bg-muted/50 rounded-lg border border-border font-mono text-sm">
              <p className="text-slate-500 dark:text-slate-400"># Python implementation:</p>
              <p className="text-emerald-500">t_stat, p_value = scipy.stats.ttest_ind(q5_returns, q1_returns, equal_var=False)</p>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              <strong>Why Welch's?</strong> High R&D quintiles (Q5) often have higher volatility than low R&D quintiles (Q1) 
              due to sector concentration (biotech, tech). Welch's t-test accounts for unequal variances.
            </p>

            <h3 className="text-lg font-semibold text-foreground">HAC Corrections for Overlapping Windows</h3>
            <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <p className="text-sm font-semibold text-blue-500 mb-2">Critical: Newey-West HAC Adjustment</p>
              <p className="text-xs text-muted-foreground mb-2">
                Rolling k-year windows overlap by k-1 years, creating strong autocorrelation. Standard errors 
                are understated without correction, leading to overly optimistic p-values.
              </p>
              <div className="font-mono text-xs bg-muted/50 p-2 rounded mt-2">
                <p className="text-slate-500 dark:text-slate-400"># For k-year overlapping windows:</p>
                <p className="text-emerald-500">lags = k - 1  # e.g., 4 lags for 5-year windows</p>
                <p className="text-emerald-500">hac_se = newey_west_standard_error(returns, nlags=lags)</p>
              </div>
            </div>

            <div className="flex flex-wrap items-start gap-4 mb-2">
              <h3 className="text-lg font-semibold text-foreground">Effect Size:</h3>
              <div className="flex flex-wrap gap-2">
                <Formulas.EtaSquared />
                <Formulas.CohensD />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mb-4 ml-0 md:ml-4">
              <Greek>η</Greek><Sup>2</Sup> {">"} 0.14 = large effect • <Var>d</Var> {">"} 0.8 = large • <Var>d</Var> {">"} 1.2 = very large
            </p>

            <div className="flex flex-wrap items-start gap-4">
              <div>
                <h3 className="text-lg font-semibold text-foreground">Sharpe Ratio</h3>
                <p className="text-xs text-muted-foreground"><Var>R</Var><Sub>f</Sub> = 2% annually</p>
              </div>
              <Formulas.SharpeRatio />
            </div>
            <p className="text-xs text-muted-foreground mt-1 ml-0 md:ml-4">
              Sharpe {">"} 1.0 = excellent risk-adjusted returns. Uses time-series volatility across rolling windows.
            </p>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
