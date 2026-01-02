/**
 * PATH: frontend/src/pages/Methodology.tsx
 * PURPOSE: Standalone methodology page with rigorous, first-principles documentation
 * ROLE IN ARCHITECTURE: Documentation layer - explains research methodology in detail
 * MAIN EXPORTS:
 *   - Methodology: React component for methodology page
 * NON-RESPONSIBILITIES:
 *   - Does not contain research results (see Papers)
 *   - Does not contain interactive tools (see Portfolio, Research pages)
 * NOTES FOR FUTURE AI:
 *   - Keep methodology updated when data sources or calculations change
 *   - This should be the single source of truth for how analysis is performed
 */

import { useState, useEffect, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  Database, 
  FlaskConical, 
  Calculator, 
  CheckCircle, 
  AlertTriangle,
  FileText,
  Download,
  ExternalLink,
  Code,
  Scale,
  GitBranch,
  Boxes
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { Sub, Sup, Var, Greek, Formulas } from "@/components/Formula"

const sections = [
  { id: "overview", label: "Overview" },
  { id: "data-sources", label: "1. Data Sources" },
  { id: "rd-intensity", label: "2. R&D Intensity" },
  { id: "quintile-construction", label: "3. Quintile Construction" },
  { id: "return-calculation", label: "4. Return Calculation" },
  { id: "statistical-tests", label: "5. Statistical Tests" },
  { id: "fiscal-year-handling", label: "6. Fiscal Year Handling" },
  { id: "sector-bias", label: "7. Sector Bias" },
  { id: "limitations", label: "8. Limitations" },
  { id: "replication", label: "9. Replication Guide" },
  { id: "verification", label: "10. Verification Checklist" },
]

export function Methodology() {
  const [activeSection, setActiveSection] = useState("overview")
  const [rightNavCollapsed, setRightNavCollapsed] = useState(false)

  // “0 hallucinations” policy: any displayed counts/ranges should come from snapshot-backed API.
  const { data: publicationSnapshot } = useQuery({
    queryKey: ["publicationSnapshot", "methodology"],
    queryFn: () => api.getPublicationSnapshot(),
  })

  const companiesLabel = useMemo(() => {
    const cohort = publicationSnapshot?.payload?.cohort_summary as any
    const totalCompanies = cohort && typeof cohort === "object" && !("error" in cohort) ? cohort.total_companies : undefined
    return typeof totalCompanies === "number" ? String(totalCompanies) : "..."
  }, [publicationSnapshot])

  const timePeriodLabel = useMemo(() => {
    const annual = publicationSnapshot?.payload?.annual_hml_premium as any
    if (!annual || typeof annual !== "object" || ("error" in annual)) return "..."
    const rows = annual.annual_premiums
    const nYears = annual.n_years
    if (!Array.isArray(rows) || rows.length === 0) return "..."
    const first = rows[0]?.year
    const last = rows[rows.length - 1]?.year
    if (typeof first !== "string" || typeof last !== "string") return "..."
    const range = `${first} to ${last}`
    return typeof nYears === "number" ? `${range} (${nYears} yrs)` : range
  }, [publicationSnapshot])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id)
          }
        })
      },
      { rootMargin: "-20% 0px -60% 0px" }
    )

    sections.forEach(({ id }) => {
      const element = document.getElementById(id)
      if (element) observer.observe(element)
    })

    return () => observer.disconnect()
  }, [])

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  const keyMetrics = [
    { label: "Data Sources", value: "3", color: "text-blue-500" },
    { label: "Companies", value: companiesLabel, color: "text-emerald-500" },
    { label: "Time Period", value: timePeriodLabel, color: "text-purple-500" },
    { label: "Quintiles", value: "5", color: "text-foreground" },
  ]

  return (
    <div className="flex gap-8">
      {/* Main Content */}
      <div className={cn(
        "flex-1 space-y-12 pb-24 transition-all duration-300",
        rightNavCollapsed ? "max-w-none" : "max-w-4xl"
      )}>
        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 via-card to-card border border-blue-500/20 p-8">
          <div className="absolute inset-0 bg-grid-white/[0.02] dark:bg-grid-white/[0.02]" />
          <div className="relative z-10">
            <div className="flex items-start justify-between flex-wrap gap-4 mb-6">
              <Badge variant="outline" className="text-blue-500 border-blue-500/30">
                Methodology Documentation
              </Badge>
              <Button variant="outline" size="sm" asChild>
                <a href="/rnd-alpha-paper.pdf" target="_blank" rel="noopener noreferrer">
                <Download className="mr-2 h-4 w-4" />
                Download PDF
                </a>
              </Button>
            </div>
            
            <h1 className="text-4xl font-bold mb-4">
              <span className="text-blue-500">Research</span>{" "}
              <span className="text-foreground">Methodology</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl">
              First-Principles Documentation of R&D Factor Analysis
            </p>
            
            <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
              <div><span className="text-muted-foreground">Version:</span> <span className="text-foreground">2.0</span></div>
              <div><span className="text-muted-foreground">Last Updated:</span> <span className="text-foreground">January 2026</span></div>
              <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
            </div>
          </div>
        </div>

        {/* Overview */}
        <section id="overview" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Boxes className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">Overview</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground leading-relaxed">
                This document provides a rigorous, first-principles explanation of how we analyze the relationship 
                between R&D investment intensity and long-term shareholder returns. Every calculation, data source, 
                and methodological choice is documented to enable independent verification and replication.
              </p>
              
              <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <p className="text-sm font-semibold text-blue-500 mb-2">Core Hypothesis</p>
                <p className="text-sm text-muted-foreground">
                  Companies that invest more heavily in R&D (as a percentage of revenue) generate higher 
                  long-term shareholder returns than companies with lower R&D investment. This effect 
                  strengthens over longer time horizons.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground">Analysis Pipeline</h3>
              <div className="grid md:grid-cols-4 gap-4">
                <div className="p-3 bg-muted/50 rounded-lg border border-border text-center">
                  <Database className="h-6 w-6 text-blue-500 mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">1. Data Collection</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg border border-border text-center">
                  <Calculator className="h-6 w-6 text-emerald-500 mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">2. R&D Intensity Calculation</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg border border-border text-center">
                  <Scale className="h-6 w-6 text-purple-500 mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">3. Quintile Assignment</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg border border-border text-center">
                  <FlaskConical className="h-6 w-6 text-amber-500 mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">4. Statistical Analysis</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Data Sources */}
        <section id="data-sources" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Database className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">1. Data Sources</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-6">
              <p className="text-muted-foreground leading-relaxed">
                We use three primary data sources, each serving a specific purpose in the analysis:
              </p>

              <div className="space-y-4">
                <div className="p-4 bg-muted/50 rounded-lg border border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="text-blue-500 border-blue-500/30">Primary</Badge>
                    <h4 className="font-semibold text-foreground">SEC EDGAR</h4>
                  </div>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• <strong>What:</strong> 10-K annual reports (official SEC filings)</li>
                    <li>• <strong>Why:</strong> Authoritative source for R&D expenses under GAAP (ASC 730)</li>
                    <li>• <strong>API:</strong> <code className="bg-muted px-1 rounded">{"https://data.sec.gov/submissions/CIK{cik}.json"}</code></li>
                    <li>• <strong>Fields:</strong> R&D Expense, Total Revenue, Filing Date, Fiscal Year End</li>
                  </ul>
                </div>

                <div className="p-4 bg-muted/50 rounded-lg border border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="text-emerald-500 border-emerald-500/30">Secondary</Badge>
                    <h4 className="font-semibold text-foreground">Financial Modeling Prep (FMP)</h4>
                  </div>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• <strong>What:</strong> Standardized financial data API</li>
                    <li>• <strong>Why:</strong> Provides clean, normalized financial statements and price data</li>
                    <li>• <strong>Endpoints:</strong></li>
                    <li className="ml-4"><code className="bg-muted px-1 rounded text-xs">/api/v3/income-statement/{"{"}ticker{"}"}</code> → R&D, Revenue</li>
                    <li className="ml-4"><code className="bg-muted px-1 rounded text-xs">/api/v3/historical-price-full/{"{"}ticker{"}"}</code> → Prices</li>
                  </ul>
                </div>

                <div className="p-4 bg-muted/50 rounded-lg border border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="text-purple-500 border-purple-500/30">Reference</Badge>
                    <h4 className="font-semibold text-foreground">S&P 500 Historical Constituents</h4>
                  </div>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• <strong>What:</strong> List of companies in the S&P 500 over time</li>
                    <li>• <strong>Why:</strong> Enables point-in-time membership (include only names actually in the index at formation dates)</li>
                    <li>• <strong>Source:</strong> Historical membership spans (added/removed dates) ingested into our database</li>
                    <li>
                      • <strong>Caveat:</strong> Coverage can be incomplete in Tier-1; when spans are missing, some analyses fall back to an
                      “available-data” universe and we disclose this via diagnostics in the publication snapshot.
                    </li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* R&D Intensity Calculation */}
        <section id="rd-intensity" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Calculator className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">2. R&D Intensity Calculation</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div className="flex flex-wrap items-center gap-4">
                <h3 className="text-lg font-semibold text-foreground">Definition:</h3>
                <Formulas.RDIntensity />
              </div>

              <h3 className="text-lg font-semibold text-foreground">Why This Formula?</h3>
              <p className="text-muted-foreground leading-relaxed">
                <strong>First-principles reasoning:</strong> We want to measure a company's commitment to innovation 
                relative to its scale. Using absolute R&D dollars would favor large companies (Apple's $30B vs. a 
                biotech's $500M). Normalizing by revenue creates a fair comparison:
              </p>
              <ul className="text-muted-foreground space-y-2">
                <li>• <strong>Apple:</strong> $30B R&D / $394B revenue = 7.6% intensity</li>
                <li>• <strong>Biotech Co:</strong> $500M R&D / $2B revenue = 25% intensity</li>
              </ul>
              <p className="text-muted-foreground leading-relaxed">
                The biotech is making a larger proportional bet on R&D-our hypothesis is this matters for returns.
              </p>

              <h3 className="text-lg font-semibold text-foreground">Data Extraction</h3>
              <div className="p-4 bg-muted/50 rounded-lg border border-border font-mono text-sm space-y-2">
                <p className="text-muted-foreground"># From SEC 10-K or FMP API:</p>
                <p className="text-emerald-500">rd_expense = income_statement['researchAndDevelopmentExpenses']</p>
                <p className="text-emerald-500">revenue = income_statement['revenue']  # or 'totalRevenue'</p>
                <p className="text-muted-foreground mt-3"># Calculate intensity:</p>
                <p className="text-emerald-500">rd_intensity = (rd_expense / revenue) * 100</p>
              </div>

              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">⚠️ Edge Cases</p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• <strong>Zero R&D:</strong> Many companies (utilities, REITs) report $0 R&D. These are assigned to Q1 (lowest quintile).</li>
                  <li>• <strong>Negative Revenue:</strong> Excluded from analysis (rare, usually data errors).</li>
                  <li>• <strong>R&D {">"} Revenue:</strong> Valid for pre-revenue biotechs; intensity capped at 100% for quintile assignment.</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </section>

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

        {/* Fiscal Year Handling */}
        <section id="fiscal-year-handling" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">6. Fiscal Year Handling</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">Critical Consideration</p>
                <p className="text-sm text-muted-foreground">
                  U.S. companies have different fiscal year end dates. This affects data availability and timing.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground">Common Fiscal Year Ends</h3>
              <ul className="text-muted-foreground space-y-2">
                <li>• <strong>December 31:</strong> ~65% of S&P 500 (e.g., Alphabet, JPMorgan)</li>
                <li>• <strong>January 31:</strong> Retail (e.g., Walmart, Costco)</li>
                <li>• <strong>June 30:</strong> Microsoft, Nike</li>
                <li>• <strong>September 30:</strong> Apple (until 2020)</li>
              </ul>

              <h3 className="text-lg font-semibold text-foreground">Our Approach</h3>
              <p className="text-muted-foreground leading-relaxed">
                When constructing portfolios for calendar year t, we use the most recent available 
                fiscal year data. For a company with a December fiscal year end, this means:
              </p>
              <div className="p-4 bg-muted/50 rounded-lg border border-border font-mono text-sm">
                <p className="text-muted-foreground"># For calendar year 2024 portfolio:</p>
                <p className="text-emerald-500">fiscal_data = get_most_recent_fy(company, before='2024-01-01')</p>
                <p className="text-emerald-500"># → Returns FY2023 data (filed in Q1 2024)</p>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">July-June Returns (Fama-French Convention)</h3>
              <p className="text-muted-foreground leading-relaxed">
                To eliminate look-ahead bias, we implement the Fama-French July-June return convention:
              </p>
              <ul className="text-muted-foreground space-y-2">
                <li>• <strong>Portfolio Formation:</strong> July 1 each year (after 10-K filings are public)</li>
                <li>• <strong>Holding Period:</strong> July 1 to June 30 of the following year</li>
                <li>• <strong>Example:</strong> FY 2022 data (filed by March 2023) → portfolio formed July 2023 → returns measured July 2023 to June 2024</li>
              </ul>
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <p className="text-sm font-semibold text-emerald-500 mb-2">✓ Implementation Status</p>
                <p className="text-sm text-muted-foreground">
                  July-June returns are implemented via the <code>JulyJuneReturn</code> table and 
                  <code>JulyJuneReturnCalculator</code> service. The <code>RollingWindowAnalyzer</code> uses 
                  <code>use_july_june=True</code> by default for research-grade analysis.
                </p>
              </div>

              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">⚠️ Current Year ({new Date().getFullYear()}) Data</p>
                <p className="text-sm text-muted-foreground">
                  Data for the current calendar year is always incomplete because many companies 
                  haven't filed yet. We mark current year data as "Preliminary" in all visualizations.
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Sector Bias */}
        <section id="sector-bias" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <h2 className="text-2xl font-bold">7. Sector Bias Acknowledgment</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">Important Caveat</p>
                <p className="text-sm text-muted-foreground">
                  High R&D intensity is concentrated in specific sectors. Our results may partially 
                  reflect sector performance rather than R&D alone.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground">Sector Distribution by Quintile</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 text-foreground">Quintile</th>
                      <th className="text-left py-3 text-foreground">Dominant Sectors</th>
                      <th className="text-left py-3 text-foreground">% of Quintile</th>
                    </tr>
                  </thead>
                  <tbody className="text-muted-foreground">
                    <tr className="border-b border-border/50"><td className="py-2">Q5 (High R&D)</td><td>Technology, Healthcare/Biotech</td><td>~70%</td></tr>
                    <tr className="border-b border-border/50"><td className="py-2">Q4</td><td>Tech Hardware, Pharma</td><td>~55%</td></tr>
                    <tr className="border-b border-border/50"><td className="py-2">Q1-Q2 (Low R&D)</td><td>Financials, Utilities, REITs</td><td>~60%</td></tr>
                  </tbody>
                </table>
              </div>

              <h3 className="text-lg font-semibold text-foreground">Mitigation Approaches</h3>
              <ul className="text-muted-foreground space-y-2">
                <li>• <strong>Within-sector quintiles:</strong> We provide sector-neutral analysis in Paper 2</li>
                <li>• <strong>Sector controls:</strong> Regression analysis with sector dummy variables</li>
                <li>• <strong>Transparency:</strong> We always report sector composition of each quintile</li>
              </ul>
            </CardContent>
          </Card>
        </section>

        {/* Limitations */}
        <section id="limitations" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">8. Limitations</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-4">
              <h3 className="text-lg font-semibold text-foreground">Key Limitations (what reviewers should focus on)</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <p className="text-sm font-semibold text-red-500 mb-2">Membership coverage (survivorship risk)</p>
                  <p className="text-xs text-muted-foreground">
                    Where historical constituent spans are available, we enforce point-in-time S&amp;P 500 membership at formation dates.
                    In Tier-1, membership coverage can still be incomplete, and we disclose coverage diagnostics in the frozen publication snapshot.
                  </p>
                </div>
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <p className="text-sm font-semibold text-red-500 mb-2">Look-ahead bias (calendar-year risk)</p>
                  <p className="text-xs text-muted-foreground">
                    Calendar-year (Jan-Dec) sorts can inadvertently use accounting data that wasn’t public at the start of the return window.
                    Our primary analysis uses the July-June convention to mitigate this.
                  </p>
                </div>
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <p className="text-sm font-semibold text-red-500 mb-2">Overlapping Windows</p>
                  <p className="text-xs text-muted-foreground">
                    Rolling k-year windows overlap by k-1 years, violating the independence assumption of 
                    standard statistical tests. We treat rolling windows as descriptive context; primary inference uses monthly spanning tests and
                    cross-sectional regressions, with the annual non-overlapping series reported for economic context (Newey-West adjusted).
                  </p>
                </div>
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  <p className="text-sm font-semibold text-amber-500 mb-2">Sector Concentration</p>
                  <p className="text-xs text-muted-foreground">
                    High R&D quintiles (Q4, Q5) are ~70% Tech/Healthcare. The "R&D premium" may partially 
                    reflect sector performance, not R&D specifically. We provide within-sector analysis 
                    to address this, but it remains a key caveat.
                  </p>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">Other Methodological Notes</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  <p className="text-sm font-semibold text-amber-500 mb-2">R&D Accounting Differences</p>
                  <p className="text-xs text-muted-foreground">
                    GAAP requires R&D to be expensed, but definitions vary. Software capitalization 
                    rules changed in 2018, affecting comparability. Some companies may expense R&D 
                    differently or have missing data (assigned to Q1).
                  </p>
                </div>
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  <p className="text-sm font-semibold text-amber-500 mb-2">Transaction costs are modeled (but model-based)</p>
                  <p className="text-xs text-muted-foreground">
                    We report net-of-cost results using literature-calibrated cost parameters and realized turnover from the investable backtest.
                    These are still estimates (not an execution simulation), so cost results should be interpreted as approximations.
                  </p>
                </div>
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  <p className="text-sm font-semibold text-amber-500 mb-2">No Guarantee of Future Returns</p>
                  <p className="text-xs text-muted-foreground">
                    Historical patterns may not persist. The R&D premium has shown weakness in certain 
                    periods (e.g., 2008-2018 per Cai et al. 2023). Market conditions, interest rates, 
                    and sector dynamics all affect future R&D premium.
                  </p>
                </div>
                <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                  <p className="text-sm font-semibold text-blue-500 mb-2">Rebalancing Assumption</p>
                  <p className="text-xs text-muted-foreground">
                    We use <strong>annual formation/reconstitution in July</strong> (Fama-French convention) with equal-weight portfolios.
                    Rolling windows are reported as descriptive and do not re-sort annually by design.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Replication Guide */}
        <section id="replication" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <GitBranch className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">9. Replication Guide</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-6">
              <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <Code className="h-4 w-4" />
                Code Repository
              </h3>
              <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <p className="text-sm text-muted-foreground mb-3">
                  Full analysis code available on GitHub:
                </p>
                <a href="https://github.com/vastdreams/fse-rnd-alpha" className="text-primary hover:underline flex items-center gap-2">
                  github.com/vastdreams/fse-rnd-alpha
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>

              <h3 className="text-lg font-semibold text-foreground">Quick Start</h3>
              <div className="p-4 bg-muted/50 rounded-lg border border-border font-mono text-xs space-y-2">
                <p className="text-muted-foreground"># Clone repository</p>
                <p className="text-foreground">git clone https://github.com/vastdreams/fse-rnd-alpha.git</p>
                <p className="text-foreground">cd fse-rnd-alpha</p>
                <p className="text-muted-foreground mt-2"># Install dependencies</p>
                <p className="text-foreground">pip install -r requirements.txt</p>
                <p className="text-muted-foreground mt-2"># Run full pipeline</p>
                <p className="text-foreground">python scripts/run_full_pipeline.py</p>
              </div>

              <h3 className="text-lg font-semibold text-foreground">Key Scripts</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• <code className="bg-muted px-1 rounded">scripts/ingest_fmp_data.py</code> - Data collection from FMP API</li>
                <li>• <code className="bg-muted px-1 rounded">scripts/compute_rd_factors.py</code> - R&D intensity calculation</li>
                <li>• <code className="bg-muted px-1 rounded">src/factors/quintile_analysis.py</code> - Quintile portfolio construction</li>
                <li>• <code className="bg-muted px-1 rounded">src/factors/anova_analysis.py</code> - Statistical tests</li>
              </ul>
            </CardContent>
          </Card>
        </section>

        {/* Verification Checklist */}
        <section id="verification" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle className="h-5 w-5 text-emerald-500" />
            <h2 className="text-2xl font-bold">10. Verification Checklist</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-6">
              <p className="text-muted-foreground leading-relaxed">
                Use this checklist to verify results independently:
              </p>

              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Data Sources Accessible</p>
                    <p className="text-xs text-muted-foreground">SEC EDGAR is free; FMP requires API key (free tier available)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">R&D Intensity Formula Correct</p>
                    <p className="text-xs text-muted-foreground">rd_expense / revenue × 100 matches GAAP reporting</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Quintile Assignment Uses pd.qcut</p>
                    <p className="text-xs text-muted-foreground">Equal-sized groups (not equal-spaced bins)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Returns Are Total Shareholder Return</p>
                    <p className="text-xs text-muted-foreground">Approximated via split-adjusted close + dividend events (reinvested)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Statistical Tests Use scipy.stats</p>
                    <p className="text-xs text-muted-foreground">f_oneway for ANOVA; standard effect size formulas</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Sector Bias Acknowledged</p>
                    <p className="text-xs text-muted-foreground">Results may partly reflect Tech/Healthcare performance</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Survivorship Bias Acknowledged</p>
                    <p className="text-xs text-muted-foreground">Point-in-time membership is enforced where spans exist; remaining coverage gaps are disclosed</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>

      {/* Right Sidebar - Table of Contents */}
      <RightTableOfContents
        sections={sections}
        activeSection={activeSection}
        onSectionClick={scrollToSection}
        keyMetrics={keyMetrics}
        onCollapseChange={setRightNavCollapsed}
      />
    </div>
  )
}

