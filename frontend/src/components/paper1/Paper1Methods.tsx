/** Paper1Methods — Data & Sample + Methodology sections */
import { Card, CardContent } from "@/components/ui/card"
import { Database, FlaskConical } from "lucide-react"
import { Formulas } from "@/components/Formula"

interface Paper1MethodsProps {
  cohortSummary: any
  annualHmlData: any
  rollingWindows5yr: any
}

export function Paper1Methods({ cohortSummary, annualHmlData, rollingWindows5yr }: Paper1MethodsProps) {
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
              <p className="text-muted-foreground leading-relaxed">
                Our sample comprises all companies that have been constituents of the S&P 500 index 
                over the return period covered by the dataset (see the Annual HML table above for the exact
                July-June range). Financial statement and price data are sourced via Financial Modeling Prep (FMP).
              </p>
            </div>

            {/* Data Summary Stats */}
            <div className="grid md:grid-cols-3 gap-4">
              <div className="p-4 bg-muted/50 rounded-lg border border-border">
                <p className="text-2xl font-bold text-primary">{cohortSummary?.total_companies || "..."}</p>
                <p className="text-sm text-muted-foreground">Total Companies</p>
              </div>
              <div className="p-4 bg-muted/50 rounded-lg border border-border">
                <p className="text-2xl font-bold text-primary">{annualHmlData?.n_years ?? "..."}</p>
                <p className="text-sm text-muted-foreground">Annual HML Observations</p>
              </div>
              <div className="p-4 bg-muted/50 rounded-lg border border-border">
                <p className="text-2xl font-bold text-primary">{rollingWindows5yr?.length ?? "..."}</p>
                <p className="text-sm text-muted-foreground">5-Year Rolling Windows</p>
              </div>
            </div>

            <div className="prose prose-invert max-w-none">
              <h3 className="text-lg font-semibold text-foreground">Data Sources</h3>
              <ul className="text-muted-foreground space-y-2">
                <li><strong>Financial Modeling Prep (FMP):</strong> Income statements (R&D expense, revenue) and daily adjusted prices</li>
                <li><strong>Ken French Data Library:</strong> Risk-free rate and factor series used in factor tests</li>
                <li>
                  <strong>S&amp;P 500 membership (Tier-1):</strong> Historical constituent spans (added/removed dates) used for point-in-time membership
                  at formation dates (where available). Exits are handled via return construction + sensitivity analysis rather than injecting proxy "delisting returns."
                </li>
              </ul>
            </div>

            <div className="prose prose-invert max-w-none">
              <h3 className="text-lg font-semibold text-foreground">Variable Definitions</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 text-foreground">Variable</th>
                    <th className="text-left py-2 text-foreground">Definition</th>
                  </tr>
                </thead>
                <tbody className="text-muted-foreground">
                  <tr className="border-b border-border/50"><td className="py-2">R&D Intensity</td><td>R&D Expenditure / Total Revenue × 100</td></tr>
                  <tr className="border-b border-border/50"><td className="py-2">Total Return</td><td>Price appreciation + dividends, annualized</td></tr>
                  <tr className="border-b border-border/50"><td className="py-2">Quintile</td><td>Ranked grouping (1-5) by R&D intensity</td></tr>
                  <tr className="border-b border-border/50"><td className="py-2">R&D Premium</td><td>Q5 return - Q1 return</td></tr>
                </tbody>
              </table>
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
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-6">
            <h3 className="text-lg font-semibold text-foreground">4.1 Data Extraction from SEC Filings</h3>
            <p className="text-muted-foreground leading-relaxed">
              We extract R&D expenditure directly from SEC 10-K annual reports using a systematic pipeline:
            </p>
            <div className="p-4 bg-muted/50 rounded-lg border border-border space-y-3">
              <div>
                <p className="text-sm font-semibold text-foreground">Step 1: SEC EDGAR Retrieval</p>
                <p className="text-sm text-muted-foreground">Download 10-K filings via SEC EDGAR API using CIK identifiers. Parse filing sections using SEC document structure.</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Step 2: Financial Data Extraction</p>
                <p className="text-sm text-muted-foreground">Extract from Income Statement: <code className="bg-muted px-1 rounded">Research and Development Expense</code> line item. This is the <strong>GAAP-mandated R&D expense</strong> that companies must disclose under ASC 730.</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Step 3: Revenue Extraction</p>
                <p className="text-sm text-muted-foreground">Extract <code className="bg-muted px-1 rounded">Total Revenue</code> or <code className="bg-muted px-1 rounded">Net Sales</code> from same period for intensity calculation.</p>
              </div>
            </div>

            <h3 className="text-lg font-semibold text-foreground">4.2 R&D Intensity Calculation</h3>
            <p className="text-muted-foreground leading-relaxed">
              We define R&D Intensity as the ratio of research and development expense to total revenue:
            </p>
            <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg overflow-hidden">
              <Formulas.RDIntensity />
              <p className="text-slate-500 dark:text-slate-400 text-sm px-4 pb-3 -mt-1">Example: Company with $5B R&D and $50B revenue = 10% R&D intensity</p>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              <strong className="text-foreground">Why this metric?</strong> R&D intensity captures a company's investment 
              commitment relative to its scale. A large company spending $1B on R&D may still have low intensity 
              (1% of $100B revenue), while a smaller company spending $500M could have high intensity (10% of $5B revenue). 
              This normalization allows fair comparison across companies of different sizes.
            </p>
            
            <h4 className="text-md font-semibold text-foreground mt-4">Data Quality Filters</h4>
            <p className="text-muted-foreground leading-relaxed">
              To ensure robust results, we apply the following quality filters:
            </p>
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg space-y-2">
              <div className="flex items-start gap-2">
                <span className="text-amber-600 dark:text-amber-400 font-semibold">1.</span>
                <span className="text-muted-foreground"><strong className="text-foreground">Minimum Revenue Threshold:</strong> $100M annual revenue required to prevent extreme ratios from pre-revenue companies.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-600 dark:text-amber-400 font-semibold">2.</span>
                <span className="text-muted-foreground"><strong className="text-foreground">Intensity Cap:</strong> R&D intensity capped at 100% to prevent outliers from dominating results.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-600 dark:text-amber-400 font-semibold">3.</span>
                <span className="text-muted-foreground"><strong className="text-foreground">Look-Ahead Bias Prevention:</strong> At start of year T, we use FY(T-1) data only. FY(T) data is not yet available and would introduce bias.</span>
              </div>
            </div>

            <h3 className="text-lg font-semibold text-foreground">4.3 Quintile Portfolio Construction</h3>
            <p className="text-muted-foreground leading-relaxed">
              At portfolio formation (July 1 each year, per the July-June convention), we:
            </p>
            <ol className="text-muted-foreground list-decimal list-inside space-y-2">
              <li>Collect R&D intensity for all S&P 500 companies using fiscal year t-1 data (most recent available)</li>
              <li>Rank companies from lowest to highest R&D intensity</li>
              <li>Sort into 5 equal-sized quintiles (each containing ~100 companies)</li>
              <li>Calculate equal-weighted portfolio returns for the subsequent July-June window for each quintile</li>
            </ol>
            <div className="p-4 bg-muted/50 rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2">Quintile</th>
                    <th className="text-left py-2">Percentile Range</th>
                    <th className="text-left py-2">Typical R&D Intensity</th>
                  </tr>
                </thead>
                <tbody className="text-muted-foreground">
                  <tr className="border-b border-border/50"><td className="py-1">Q1 (Low)</td><td>0-20th</td><td>0-2%</td></tr>
                  <tr className="border-b border-border/50"><td className="py-1">Q2</td><td>20-40th</td><td>2-5%</td></tr>
                  <tr className="border-b border-border/50"><td className="py-1">Q3</td><td>40-60th</td><td>5-8%</td></tr>
                  <tr className="border-b border-border/50"><td className="py-1">Q4</td><td>60-80th</td><td>8-12%</td></tr>
                  <tr><td className="py-1">Q5 (High)</td><td>80-100th</td><td>12%+</td></tr>
                </tbody>
              </table>
            </div>

            <h3 className="text-lg font-semibold text-foreground">4.4 Return Calculation (July-June Convention)</h3>
            <p className="text-muted-foreground leading-relaxed">
              Following the Fama-French methodology, we use <strong className="text-foreground">July-June returns</strong> to 
              eliminate look-ahead bias. This ensures all financial data is publicly available before portfolio formation:
            </p>
            <div className="p-4 bg-muted/50 rounded-lg border border-border space-y-3">
              <div className="flex items-start gap-2">
                <span className="text-primary font-semibold">Timeline:</span>
                <span className="text-muted-foreground">FY 2019 ends Dec 31 → 10-K filed by March 2020 → Portfolio formed July 1, 2020 → Returns measured July 2020 to June 2021</span>
              </div>
              <div className="font-mono text-sm mt-2">
                <p className="text-primary">TSR = (P_June_end + Dividends - P_July_start) / P_July_start</p>
                <p className="text-slate-500 dark:text-slate-400 mt-1">
                  where P = split-adjusted close and Dividends are ex-dividend cashflows (reinvested in the return stream)
                </p>
              </div>
            </div>
            <p className="text-muted-foreground leading-relaxed mt-3">
              For multi-year windows, we compound annual July-June returns geometrically and then annualize.
            </p>
            
            <h4 className="text-md font-semibold text-foreground mt-4">Survivorship Bias Mitigation</h4>
            <p className="text-muted-foreground leading-relaxed">
              To address survivorship bias, we:
            </p>
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg space-y-2">
              <div className="flex items-start gap-2">
                <span className="text-blue-600 dark:text-blue-400 font-semibold">1.</span>
                <span className="text-muted-foreground"><strong className="text-foreground">Historical Constituents:</strong> Use point-in-time S&P 500 membership data to form portfolios only with companies that were in the index at that time.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-600 dark:text-blue-400 font-semibold">2.</span>
                <span className="text-muted-foreground"><strong className="text-foreground">Exit Handling:</strong> When a firm exits mid-period (merger/delisting), we compute return to the last observed trading day and treat cash as earning 0% thereafter for the remainder of the July-June window (cash-after-exit). Delisting uncertainty is quantified via sensitivity analysis.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-600 dark:text-blue-400 font-semibold">3.</span>
                <span className="text-muted-foreground"><strong className="text-foreground">Documentation:</strong> See DATA_PROVENANCE.md for full details on our two-tier survivorship framework.</span>
              </div>
            </div>

            <h3 className="text-lg font-semibold text-foreground">4.5 Statistical Framework</h3>
            <p className="text-muted-foreground leading-relaxed">
              We employ Analysis of Variance (ANOVA) to test the null hypothesis that mean returns are 
              equal across all five quintiles. Our statistical tests:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Formulas.ANOVA />
              <Formulas.EtaSquared />
              <Formulas.CohensD />
              <Formulas.SharpeRatio />
            </div>
            <p className="text-muted-foreground leading-relaxed mt-4">
              <strong className="text-foreground">Interpretation benchmarks:</strong> η² {">"} 0.14 is "large effect"; 
              Cohen's d {">"} 0.8 is "large effect"; d {">"} 1.2 is "very large". Sharpe {">"} 1.0 indicates excellent risk-adjusted returns.
            </p>
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg mt-4">
              <p className="text-sm text-blue-600 dark:text-blue-400">
                <strong>Unit Convention:</strong> All returns are stored as decimals in our database (0.10 = 10%) 
                and converted to percentages for display. R&D intensity is stored and displayed as percentage (10 = 10%).
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground">4.6 Rolling Window Analysis</h3>
            <p className="text-muted-foreground leading-relaxed">
              To assess persistence and time variation, we compute overlapping rolling windows (5/10/20-year) across
              the available sample period.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              For each window, we calculate the R&D premium (Q5 - Q1 return) and statistical significance.
            </p>
            
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg mt-4">
              <p className="text-sm font-semibold text-amber-600 dark:text-amber-400 mb-2">⚠️ Methodology Note: July-June Portfolio Formation</p>
              <p className="text-sm text-muted-foreground mb-2">
                <strong>Current Implementation:</strong> We form portfolios annually using the <strong className="text-foreground">July-June return convention</strong>.
                Firms are sorted by fiscal-year R&D intensity, portfolios are formed at the end of June, and returns are measured from July to June.
                Portfolios are equal-weighted within quintile and rebalanced annually.
              </p>
              <p className="text-sm text-muted-foreground mb-2">
                <strong>Statistical Caveat:</strong> Rolling windows are overlapping and not independent observations. 
                For k-year overlapping windows, we apply <strong className="text-foreground">Newey-West (HAC) corrections</strong> with 
                lags = k-1 years to address autocorrelation. Standard t-tests would overstate significance.
              </p>
              <p className="text-sm text-muted-foreground">
                <strong>T-Test Methodology:</strong> We use <strong className="text-foreground">Welch's t-test</strong> (unequal variance) 
                for quintile comparisons, as quintiles may have different return volatilities.
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground">4.7 Controls and Robustness</h3>
            <p className="text-muted-foreground leading-relaxed">
              We conduct additional analyses to ensure the R&D premium is robust:
            </p>
            <ul className="text-muted-foreground space-y-2">
              <li>• <strong className="text-foreground">Survivorship mitigation:</strong> We use point-in-time membership where spans are available and handle exits via cash-after-exit, reporting delisting sensitivity rather than injecting a single proxy delisting return.</li>
              <li>• <strong className="text-foreground">Look-Ahead Bias Mitigation:</strong> We follow the Fama-French July-June convention, 
              forming portfolios at June-end to ensure financial data from the prior year is fully disseminated.</li>
              <li>• <strong className="text-foreground">Sector diagnostics:</strong> We report sector concentration explicitly and treat sector-neutral testing as a robustness extension (not the primary claim).</li>
            </ul>
            
            <h3 className="text-lg font-semibold text-foreground">4.8 Known Limitations & Caveats</h3>
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg space-y-3">
              <p className="text-sm font-semibold text-red-600 dark:text-red-400">Important: Interpret Results with Caution</p>
              
              <div className="text-sm text-muted-foreground space-y-2">
                <p><strong className="text-foreground">1. Survivorship Bias (Partially mitigated):</strong> We enforce point-in-time S&amp;P 500 membership where historical constituent spans are available. Exits are handled via cash-after-exit return construction, and delisting uncertainty is reported via sensitivity scenarios. Tier-1 still has coverage limitations versus CRSP/Compustat-grade data.</p>
                
                <p><strong className="text-foreground">2. Look-Ahead Bias (Addressed):</strong> We employ the Fama-French July-June return convention. 
                Portfolios are formed on June 30th using financial data from the prior fiscal year, ensuring all 10-K filings are public 
                before the first return is measured.</p>
                
                <p><strong className="text-foreground">3. Sector Concentration:</strong> High R&D quintiles are dominated by Technology and Healthcare. 
                The "R&amp;D premium" may partially reflect sector performance, not R&amp;D specifically. We report sector composition and treat sector-neutral testing as an extension.</p>
                
                <p><strong className="text-foreground">4. Zero-R&D Companies:</strong> Companies with zero reported R&D are included in Q1. 
                This may include companies that expense R&D differently or have missing data.</p>
                
                <p><strong className="text-foreground">5. Overlapping Windows:</strong> Rolling window observations are highly correlated. 
                Standard p-values are too optimistic. We apply HAC (Newey-West) corrections but results should still be interpreted conservatively.</p>
                
                <p><strong className="text-foreground">6. Transaction Costs:</strong> Trading frictions reduce implementable returns. The Main Paper reports a snapshot-pinned transaction-cost calibration and net-of-cost results for a rules-based implementation.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
