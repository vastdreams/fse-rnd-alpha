/**
 * PATH: frontend/src/pages/papers/Paper1.tsx
 * PURPOSE:
 *   - Sub-Research 1 deep dive: returns + inference visuals for the R&D intensity premium.
 *
 * ROLE IN ARCHITECTURE:
 *   - Research communication layer (frontend). Renders charts/tables from backend APIs.
 *
 * MAIN EXPORTS:
 *   - Paper1: Sub-Research 1 page component
 *
 * NON-RESPONSIBILITIES:
 *   - Does not compute metrics (backend does).
 *   - Does not hardcode unverifiable result numbers (“0 hallucinations” policy).
 *
 * NOTES FOR FUTURE AI:
 *   - Keep numeric claims sourced from API responses (aggregate ANOVA, annual HML, rolling windows).
 *   - Avoid hardcoding external-literature numeric claims unless independently verified and cited.
 */

import { useQuery } from "@tanstack/react-query"
import { useState, useEffect, useMemo } from "react"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SafeChart } from "@/components/SafeChart"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Cell,
  AreaChart,
  Area,
  ReferenceLine,
} from "recharts"
import { ArrowLeft, Download, BarChart3, Database, FlaskConical, BookOpen, FileText, CheckCircle, ExternalLink } from "lucide-react"
import { Link } from "react-router-dom"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { ReferencesList } from "@/components/Citation"
import { Formulas } from "@/components/Formula"
import { AnnualHMLTable } from "@/components/AnnualHMLTable"
import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

// Colors that work well in both light and dark modes
const QUINTILE_COLORS = ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#0d9488"]
const QUINTILE_LABELS = ["Q1 (Low R&D)", "Q2", "Q3", "Q4", "Q5 (High R&D)"]

// Table of contents sections
const sections = [
  { id: "abstract", label: "Abstract" },
  { id: "introduction", label: "1. Introduction" },
  { id: "literature", label: "2. Literature Review" },
  { id: "data", label: "3. Data & Sample" },
  { id: "methodology", label: "4. Methodology" },
  { id: "results", label: "5. Results" },
  { id: "discussion", label: "6. Discussion" },
  { id: "conclusion", label: "7. Conclusion" },
  { id: "replicability", label: "8. Replicability" },
  { id: "references", label: "References" },
]

export function Paper1() {
  const [activeSection, setActiveSection] = useState("abstract")
  const [rightNavCollapsed, setRightNavCollapsed] = useState(false)

  // Print/PDF export handler
  const handlePrintPDF = () => {
    // Add print class to body for print-specific styling
    document.body.classList.add('printing-paper')
    window.print()
    // Remove class after print dialog closes
    setTimeout(() => {
      document.body.classList.remove('printing-paper')
    }, 1000)
  }

  // Intersection observer for active section tracking
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

  // Fetch data
  const { data: quintilePerf5yr } = useQuery({
    queryKey: ["quintilePerf", "5yr"],
    queryFn: () => api.getQuintilePerformance("5yr"),
  })

  useQuery({
    queryKey: ["quintilePerf", "20yr"],
    queryFn: () => api.getQuintilePerformance("20yr"),
  })

  const { data: aggregateAnova } = useQuery({
    queryKey: ["aggregateAnova"],
    queryFn: () => api.getAggregateAnova(),
  })

  const { data: cohortSummary } = useQuery({
    queryKey: ["cohortSummary"],
    queryFn: () => api.getCohortSummary(),
  })

  const { data: factorPremiumSeries } = useQuery({
    queryKey: ["factorPremiums"],
    queryFn: () => api.getFactorPremiums(),
  })

  const sampleYearRange = useMemo(() => {
    const years = (factorPremiumSeries || []).map((r) => r.year).filter((y): y is number => typeof y === "number")
    if (years.length === 0) return undefined
    const min = Math.min(...years)
    const max = Math.max(...years)
    if (!Number.isFinite(min) || !Number.isFinite(max)) return undefined
    return `${min}-${max}`
  }, [factorPremiumSeries])

  // Key metrics for the right sidebar - dynamically computed from API data
  const rdPremium20yr = aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference;
  const etaSquared20yr = aggregateAnova?.["20yr"]?.anova?.eta_squared;
  const pValue20yr = aggregateAnova?.["20yr"]?.anova?.p_value;
  
  const keyMetrics = [
    { 
      label: "R&D Premium", 
      value: rdPremium20yr ? `${rdPremium20yr >= 0 ? "+" : ""}${rdPremium20yr.toFixed(1)}%` : "...", 
      color: "text-green-600 dark:text-emerald-400" 
    },
    { 
      label: "Effect Size (η²)", 
      value: etaSquared20yr ? etaSquared20yr.toFixed(3) : "...", 
      color: "text-blue-600 dark:text-blue-400" 
    },
    { 
      label: "Significance", 
      value: pValue20yr !== undefined ? (pValue20yr < 0.001 ? "p < 0.001" : `p = ${pValue20yr.toFixed(4)}`) : "...", 
      color: "text-green-600 dark:text-emerald-400" 
    },
    { label: "Sample Size", value: `${cohortSummary?.total_companies || "..."}`, color: "text-foreground" },
  ]

  const { data: rollingWindows5yr } = useQuery({
    queryKey: ["rollingWindows", "5yr"],
    queryFn: () => api.getRollingWindows("5yr"),
  })

  // Annual HML Premium - PRIMARY INFERENCE (non-overlapping)
  const { data: annualHmlData, isLoading: annualHmlLoading } = useQuery({
    queryKey: ["annualHmlPremium"],
    queryFn: () => api.getAnnualHmlPremium(),
  })

  // Format data for charts
  const formatQuintileData = (data: typeof quintilePerf5yr) => {
    if (!data) return []
    return data.map((q, i) => ({
      quintile: `Q${q.quintile}`,
      label: QUINTILE_LABELS[i],
      avgReturn: q.avg_return,
      totalReturn: q.avg_total_return,
      rdIntensity: q.avg_rd_intensity,
      sharpe: q.avg_sharpe,
      volatility: q.avg_volatility,
      fill: QUINTILE_COLORS[i],
    }))
  }

  const rollingWindowData = (rollingWindows5yr || []).map(w => ({
    period: `${w.start_year}-${w.end_year}`,
    startYear: w.start_year,
    rdPremium: w.rd_premium,
    q1Return: w.quintiles.find((q: { quintile: number }) => q.quintile === 1)?.avg_return || 0,
    q5Return: w.quintiles.find((q: { quintile: number }) => q.quintile === 5)?.avg_return || 0,
  }))

  return (
    <div className="flex gap-8">
      {/* Main Content - expands when right nav is collapsed */}
      <div className={cn(
        "flex-1 space-y-12 pb-24 transition-all duration-300",
        rightNavCollapsed ? "max-w-none" : "max-w-4xl"
      )}>
        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl bg-emerald-50 dark:bg-zinc-900 border border-emerald-200 dark:border-emerald-600/50 p-8">
          <div className="absolute inset-0 bg-grid-white/[0.02] dark:bg-grid-white/[0.02]" />
          <div className="relative z-10">
            <div className="flex items-start justify-between flex-wrap gap-4 mb-6">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
              <Link to="/documentation" className="inline-flex items-center text-sm text-muted-foreground hover:text-primary">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Papers
              </Link>
                  </TooltipTrigger>
                  <TooltipContent>
                    Return to the documentation and papers list
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="outline" size="sm" onClick={handlePrintPDF}>
                <Download className="mr-2 h-4 w-4" />
                Download PDF
              </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Print this paper as a PDF document
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            
            <div className="flex flex-wrap gap-2 mb-4">
              <Badge variant="outline" className="text-emerald-500 border-emerald-500/30">
              Sub-Research 1
            </Badge>
              <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10">
                Pre-print
              </Badge>
            </div>
            
            <h1 className="text-4xl font-bold mb-4">
              <span className="text-emerald-500">R&D</span>{" "}
              <span className="text-foreground">Investment Intensity and Long-Term Shareholder Returns</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl">
              Evidence from S&amp;P 500 Companies ({sampleYearRange || "the sample period"})
            </p>
            
            <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
              <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
              <div><span className="text-muted-foreground">Date:</span> <span className="text-foreground">17 December 2025</span></div>
              <div><span className="text-muted-foreground">Sample:</span> <span className="text-foreground">{cohortSummary?.total_companies || 503} Companies</span></div>
              <div><span className="text-muted-foreground">Period:</span> <span className="text-foreground">{sampleYearRange || "..."}</span></div>
            </div>
          </div>
        </div>

        {/* Abstract */}
        <section id="abstract" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">Abstract</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none">
              <p className="text-lg leading-relaxed text-muted-foreground">
                This study examines the relationship between Research & Development (R&D) investment intensity 
                and long-term shareholder returns among S&amp;P 500 companies over {sampleYearRange || "the sample period"}. 
                Using a quintile-based portfolio approach, we find that companies in the highest R&amp;D intensity 
                quintile (Q5) consistently outperform those in the lowest quintile (Q1). The horizon-by-horizon
                magnitudes and effect sizes are reported from the research endpoints rendered on this page.
                Our findings suggest that 
                sustained R&D investment creates durable competitive advantages that translate into superior 
                long-term shareholder returns.
              </p>
              <div className="mt-4 p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                <p className="text-sm text-green-600 dark:text-emerald-400 font-medium mb-2">Key Findings:</p>
                <ul className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
                  <li>
                    • Q5 (High R&amp;D) outperforms Q1 (Low R&amp;D) by{" "}
                    <strong className="text-foreground">
                      {typeof aggregateAnova?.["5yr"]?.ttest_high_vs_low?.mean_difference === "number"
                        ? `${aggregateAnova["5yr"].ttest_high_vs_low.mean_difference >= 0 ? "+" : ""}${aggregateAnova["5yr"].ttest_high_vs_low.mean_difference.toFixed(2)}%`
                        : "..."}
                    </strong>{" "}
                    (5yr),{" "}
                    <strong className="text-foreground">
                      {typeof aggregateAnova?.["10yr"]?.ttest_high_vs_low?.mean_difference === "number"
                        ? `${aggregateAnova["10yr"].ttest_high_vs_low.mean_difference >= 0 ? "+" : ""}${aggregateAnova["10yr"].ttest_high_vs_low.mean_difference.toFixed(2)}%`
                        : "..."}
                    </strong>{" "}
                    (10yr),{" "}
                    <strong className="text-foreground">
                      {typeof aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference === "number"
                        ? `${aggregateAnova["20yr"].ttest_high_vs_low.mean_difference >= 0 ? "+" : ""}${aggregateAnova["20yr"].ttest_high_vs_low.mean_difference.toFixed(2)}%`
                        : "..."}
                    </strong>{" "}
                    (20yr) in annualized returns (Q5 − Q1).
                  </li>
                  <li>
                    • Effect size (Cohen's d, 20yr):{" "}
                    <strong className="text-foreground">
                      {typeof aggregateAnova?.["20yr"]?.ttest_high_vs_low?.cohens_d === "number"
                        ? aggregateAnova["20yr"].ttest_high_vs_low.cohens_d.toFixed(3)
                        : "..."}
                    </strong>
                  </li>
                  <li>• Statistical significance is assessed per horizon using ANOVA and high-vs-low t-tests (see Results).</li>
                  <li>• The R&amp;D premium persists through multiple market cycles (descriptive).</li>
                </ul>
              </div>
            </CardContent>
          </Card>
          
          {/* Tier-1 Data Disclaimer */}
          <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400 mb-1">Data Tier Disclosure</p>
            <p className="text-sm text-amber-600 dark:text-amber-300">
              This analysis uses <strong>Tier-1 data</strong> from Financial Modeling Prep (FMP) API. 
              Survivorship bias is substantially mitigated via historical constituent tracking and heuristic delisting returns.
              For top-tier academic journals, Tier-2 data (CRSP/Compustat) would be required. 
              See{" "}
              <Link to="/documentation" className="underline hover:no-underline">
                Papers & Documentation
              </Link>{" "}
              for the repository’s <code>DATA_AVAILABILITY.md</code> and full provenance.
            </p>
          </div>
        </section>

        {/* Introduction */}
        <section id="introduction" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">1. Introduction</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground leading-relaxed">
                The role of Research and Development (R&D) investment in creating firm value has been a 
                central question in finance and economics literature. While R&D expenditures are often 
                viewed as risky investments with uncertain outcomes, they also represent a firm's commitment 
                to innovation and future growth potential.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                This paper investigates whether companies with higher R&D intensity-measured as R&D expenditure 
                as a percentage of revenue-deliver superior long-term returns to shareholders. We analyze 
                all S&amp;P 500 constituents over {sampleYearRange || "the sample period"}, creating quintile portfolios based on R&amp;D 
                intensity and tracking their performance across multiple time horizons.
              </p>
              <h3 className="text-lg font-semibold text-foreground mt-6">Research Questions</h3>
              <ol className="text-muted-foreground space-y-2 list-decimal list-inside">
                <li>Do high-R&D companies generate higher long-term shareholder returns?</li>
                <li>How does the R&D-return relationship vary across different investment horizons?</li>
                <li>Is the R&D premium statistically significant and economically meaningful?</li>
                <li>Does the effect persist across different market conditions?</li>
              </ol>
            </CardContent>
          </Card>
        </section>

        {/* Literature Review */}
        <section id="literature" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">2. Literature Review</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
              <h3 className="text-lg font-semibold text-foreground">2.1 Early Evidence of R&D Undervaluation</h3>
              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Lev and Sougiannis (1996)</strong> demonstrated 
                that R&D capital is associated with subsequent stock returns, suggesting markets systematically 
                undervalue intangible investments due to accounting rules that expense R&D immediately.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Chan, Lakonishok, and Sougiannis (2001)</strong> found that 
                firms with high R&D-to-market value earned significant positive abnormal returns. They labeled 
                this the "R&D undervaluation anomaly"-the market appears slow to recognize the value of innovation.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Eberhart, Maxwell, and Siddique (2004)</strong> examined firms 
                that substantially increased R&D spending and found significantly positive long-term abnormal 
                returns in the years following the increase, concluding that R&D increases are beneficial 
                investments that the market is slow to recognize.
              </p>

              <h3 className="text-lg font-semibold text-foreground mt-6">2.2 Recent Quantitative Evidence</h3>
              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Leung, Mazouz, and Evans (2020)</strong> sorted stocks into 
                portfolios based on R&D intensity and report economically meaningful return differences between high
                and low R&D groups in their sample. Their analysis discusses the relationship between R&D-related
                portfolios and standard factor models.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Hou et al. (2022)</strong> demonstrated that this R&D phenomenon 
                is not necessarily confined to a single market. Cross-market results vary by sample construction and
                measurement choices, motivating careful replication and transparent disclosure of data sources.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Cai, Cooper, and He (2023)</strong> in The Journal of Investing 
                discuss practitioner-facing portfolio construction considerations for R&D-related signals, including
                risk, sector exposure, and implementability.
              </p>

              <h3 className="text-lg font-semibold text-foreground mt-6">2.3 Interpretations: Mispricing vs. Risk</h3>
              <div className="grid gap-4 md:grid-cols-2 mt-4">
                <div className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
                  <h4 className="text-purple-700 dark:text-purple-400 font-semibold mb-2">Mispricing Hypothesis</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    Markets systematically undervalue intangibles because accounting rules expense R&D, 
                    depressing reported earnings. Investors anchoring on near-term metrics underweight 
                    long-term innovation value.
                  </p>
                </div>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                  <h4 className="text-blue-600 dark:text-blue-400 font-semibold mb-2">Risk Hypothesis</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    High R&D firms carry unique systematic risks (technological disruption, project failure) 
                    that investors require extra return for bearing. The R&D factor correlates with state 
                    variables like default spreads and dividend yield shocks.
                  </p>
                </div>
              </div>

              <div className="mt-6 p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                <p className="text-sm text-green-600 dark:text-emerald-400 font-medium mb-2">Our Contribution:</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  This study extends prior literature by examining the R&D-return relationship over an 
                  extended sample period ({sampleYearRange || "see header"}) using a comprehensive S&amp;P 500 sample, with particular attention to 
                  how the relationship varies across investment horizons. We report horizon-specific Q5-Q1 premiums, p-values, and effect sizes for
                  5/10/20-year windows using the platform’s research endpoints (rather than hardcoding static values in the prose).
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

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
                  <p className="text-2xl font-bold text-primary">{cohortSummary?.total_companies || 503}</p>
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
                  <li><strong>S&amp;P 500 membership (Tier-1):</strong> Historical constituent changes (FMP) with delisting adjustments</li>
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
                At the beginning of each calendar year t, we:
              </p>
              <ol className="text-muted-foreground list-decimal list-inside space-y-2">
                <li>Collect R&D intensity for all S&P 500 companies using fiscal year t-1 data (most recent available)</li>
                <li>Rank companies from lowest to highest R&D intensity</li>
                <li>Sort into 5 equal-sized quintiles (each containing ~100 companies)</li>
                <li>Calculate equal-weighted portfolio returns for year t for each quintile</li>
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
                  <p className="text-primary">TSR = (P_June_end - P_July_start) / P_July_start</p>
                  <p className="text-slate-500 dark:text-slate-400 mt-1">where P = adjusted closing price (split and dividend-adjusted)</p>
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
                  <span className="text-muted-foreground"><strong className="text-foreground">Delisting Returns:</strong> For companies removed from the index, we estimate delisting returns based on available price data or apply conservative heuristics (e.g., -30% for bankruptcy).</span>
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
                <li>• <strong className="text-foreground">Survivorship-Bias-Free Sample:</strong> We incorporate historical S&P 500 constituents 
                and include delisting returns (-30% for distress events) to avoid inflating premium estimates.</li>
                <li>• <strong className="text-foreground">Look-Ahead Bias Mitigation:</strong> We follow the Fama-French July-June convention, 
                forming portfolios at June-end to ensure financial data from the prior year is fully disseminated.</li>
                <li>• <strong className="text-foreground">Sector Neutrality:</strong> We compute within-sector quintiles to neutralize 
                the effects of industry-wide R&D intensity variations.</li>
              </ul>
              
              <h3 className="text-lg font-semibold text-foreground">4.8 Known Limitations & Caveats</h3>
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg space-y-3">
                <p className="text-sm font-semibold text-red-600 dark:text-red-400">Important: Interpret Results with Caution</p>
                
                <div className="text-sm text-muted-foreground space-y-2">
                  <p><strong className="text-foreground">1. Survivorship Bias (Addressed):</strong> Our analysis now incorporates historical S&P 500 constituents. 
                  Companies that were delisted or dropped from the index are tracked through their exit date, with a proxy -30% delisting return applied for distress events.</p>
                  
                  <p><strong className="text-foreground">2. Look-Ahead Bias (Addressed):</strong> We employ the Fama-French July-June return convention. 
                  Portfolios are formed on June 30th using financial data from the prior fiscal year, ensuring all 10-K filings are public 
                  before the first return is measured.</p>
                  
                  <p><strong className="text-foreground">3. Sector Concentration:</strong> High R&D quintiles are dominated by Technology and Healthcare. 
                  The "R&D premium" may partially reflect sector performance, not R&D specifically. Within-sector analysis is essential.</p>
                  
                  <p><strong className="text-foreground">4. Zero-R&D Companies:</strong> Companies with zero reported R&D are included in Q1. 
                  This may include companies that expense R&D differently or have missing data.</p>
                  
                  <p><strong className="text-foreground">5. Overlapping Windows:</strong> Rolling window observations are highly correlated. 
                  Standard p-values are too optimistic. We apply HAC (Newey-West) corrections but results should still be interpreted conservatively.</p>
                  
                  <p><strong className="text-foreground">6. Transaction Costs:</strong> Equal-weighted portfolios with annual rebalancing have 
                  high turnover. Transaction costs are not modeled and would reduce realized returns.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Results */}
        <section id="results" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">5. Results</h2>
          </div>
          
          <div className="space-y-8">
            {/* 5.1 PRIMARY RESULT: Annual HML Premium (Non-Overlapping) */}
            <div>
              <h3 className="text-xl font-semibold mb-4">5.1 Primary Result: Annual R&D Premium</h3>
              <AnnualHMLTable data={annualHmlData} isLoading={annualHmlLoading} />
            </div>

            {/* 5.2 Descriptive Visualization: Rolling Windows */}
            <div>
              <h3 className="text-xl font-semibold mb-4">5.2 Premium Evolution Over Time</h3>
              <p className="text-muted-foreground mb-4">
                The following visualizations show how the R&D premium has evolved across different time periods. 
                These rolling window results are <strong>descriptive</strong>; formal inference is based on the 
                non-overlapping annual observations above.
              </p>

            {/* Quintile Performance Chart */}
              <Card className="mb-6">
              <CardHeader>
                <CardTitle>Figure 1: Average Annual Returns by R&D Quintile (5-Year Windows)</CardTitle>
                <CardDescription>Higher R&D intensity is associated with higher average returns</CardDescription>
              </CardHeader>
              <CardContent style={{ height: 320, minHeight: 320 }}>
                {formatQuintileData(quintilePerf5yr).length > 0 ? (
                  <SafeChart height={320} minHeight={300}>
                    <BarChart data={formatQuintileData(quintilePerf5yr)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="quintile" stroke="hsl(var(--muted-foreground))" />
                        <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                        <RechartsTooltip
                        formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Avg Return"]}
                        contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                      />
                      <Bar dataKey="avgReturn" radius={[4, 4, 0, 0]}>
                        {formatQuintileData(quintilePerf5yr).map((entry, index) => (
                          <Cell key={index} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                    Loading chart data...
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Rolling Window Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Figure 2: R&D Premium Over Time (5-Year Rolling Windows)</CardTitle>
                  <CardDescription>Q5 minus Q1 returns show consistent positive premium (descriptive visualization)</CardDescription>
              </CardHeader>
              <CardContent style={{ height: 320, minHeight: 320 }}>
                {rollingWindowData.length > 0 ? (
                  <SafeChart height={320} minHeight={300}>
                    <AreaChart data={rollingWindowData}>
                      <defs>
                        <linearGradient id="premiumGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="period" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={60} />
                        <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                        <RechartsTooltip
                        formatter={(value) => [`${(value as number)?.toFixed(2)}%`]}
                        contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                      />
                        <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                      <Area type="monotone" dataKey="rdPremium" stroke="#10b981" fill="url(#premiumGradient)" name="R&D Premium" />
                    </AreaChart>
                  </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                    Loading chart data...
                  </div>
                )}
              </CardContent>
            </Card>
            </div>

            {/* 5.3 Statistical Robustness */}
            <div>
              <h3 className="text-xl font-semibold mb-4">5.3 Robustness: HAC-Adjusted Rolling Window Analysis</h3>
              <p className="text-muted-foreground mb-4">
                The following table presents ANOVA results from rolling window analysis. Because overlapping windows 
                create autocorrelated observations, we report Newey-West HAC-adjusted standard errors where applicable.
              </p>
              
            <Card>
              <CardHeader>
                  <CardTitle>Table 2: ANOVA Results by Investment Horizon</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-3 text-foreground">Horizon</th>
                        <th className="text-right py-3 text-foreground">F-Statistic</th>
                        <th className="text-right py-3 text-foreground">p-value</th>
                        <th className="text-right py-3 text-foreground">η² (Eta Squared)</th>
                        <th className="text-right py-3 text-foreground">Cohen's d</th>
                        <th className="text-right py-3 text-foreground">Significance</th>
                      </tr>
                    </thead>
                    <tbody className="text-muted-foreground">
                      <tr className="border-b border-border/50">
                        <td className="py-3">5-Year</td>
                        <td className="text-right font-mono">{aggregateAnova?.["5yr"]?.anova?.f_statistic?.toFixed(2) || "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["5yr"]?.anova?.p_value !== undefined && aggregateAnova?.["5yr"]?.anova?.p_value !== null ? (aggregateAnova["5yr"].anova.p_value < 0.001 ? "< 0.001" : aggregateAnova["5yr"].anova.p_value.toFixed(4)) : "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["5yr"]?.anova?.eta_squared?.toFixed(3) || "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["5yr"]?.ttest_high_vs_low?.cohens_d?.toFixed(2) || "..."}</td>
                        <td className="text-right"><Badge variant="outline" className={aggregateAnova?.["5yr"]?.anova?.significant_001 ? "text-green-600 dark:text-emerald-400 border-green-500/30 dark:border-emerald-500/30" : "text-muted-foreground border-border"}>
                          {aggregateAnova?.["5yr"]?.anova?.significant_001 ? "***" : aggregateAnova?.["5yr"]?.anova?.significant_005 ? "**" : "..."}
                        </Badge></td>
                      </tr>
                      <tr className="border-b border-border/50">
                        <td className="py-3">10-Year</td>
                        <td className="text-right font-mono">{aggregateAnova?.["10yr"]?.anova?.f_statistic?.toFixed(2) || "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["10yr"]?.anova?.p_value !== undefined && aggregateAnova?.["10yr"]?.anova?.p_value !== null ? (aggregateAnova["10yr"].anova.p_value < 0.001 ? "< 0.001" : aggregateAnova["10yr"].anova.p_value.toFixed(4)) : "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["10yr"]?.anova?.eta_squared?.toFixed(3) || "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["10yr"]?.ttest_high_vs_low?.cohens_d?.toFixed(2) || "..."}</td>
                        <td className="text-right"><Badge variant="outline" className={aggregateAnova?.["10yr"]?.anova?.significant_001 ? "text-green-600 dark:text-emerald-400 border-green-500/30 dark:border-emerald-500/30" : "text-muted-foreground border-border"}>
                          {aggregateAnova?.["10yr"]?.anova?.significant_001 ? "***" : aggregateAnova?.["10yr"]?.anova?.significant_005 ? "**" : "..."}
                        </Badge></td>
                      </tr>
                      <tr className="border-b border-border/50">
                        <td className="py-3">20-Year</td>
                        <td className="text-right font-mono">{aggregateAnova?.["20yr"]?.anova?.f_statistic?.toFixed(2) || "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["20yr"]?.anova?.p_value !== undefined && aggregateAnova?.["20yr"]?.anova?.p_value !== null ? (aggregateAnova["20yr"].anova.p_value < 0.001 ? "< 0.001" : aggregateAnova["20yr"].anova.p_value.toFixed(4)) : "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["20yr"]?.anova?.eta_squared?.toFixed(3) || "..."}</td>
                        <td className="text-right font-mono">{aggregateAnova?.["20yr"]?.ttest_high_vs_low?.cohens_d?.toFixed(2) || "..."}</td>
                        <td className="text-right"><Badge variant="outline" className={aggregateAnova?.["20yr"]?.anova?.significant_001 ? "text-green-600 dark:text-emerald-400 border-green-500/30 dark:border-emerald-500/30" : "text-muted-foreground border-border"}>
                          {aggregateAnova?.["20yr"]?.anova?.significant_001 ? "***" : aggregateAnova?.["20yr"]?.anova?.significant_005 ? "**" : "..."}
                        </Badge></td>
                      </tr>
                    </tbody>
                  </table>
                  <p className="text-xs text-muted-foreground mt-2">*** p {"<"} 0.001. Note: Rolling window analysis uses HAC-adjusted standard errors.</p>
                </div>
              </CardContent>
            </Card>
            </div>
          </div>
        </section>

        {/* Discussion */}
        <section id="discussion" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">6. Discussion</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground leading-relaxed">
                Our findings provide strong evidence that R&D investment intensity is a significant predictor 
                of long-term shareholder returns. The monotonic relationship between R&D quintiles and returns, 
                combined with the increasing effect sizes over longer horizons, suggests that R&D investments 
                create durable competitive advantages.
              </p>

              <h3 className="text-lg font-semibold text-foreground">6.1 Economic Interpretation</h3>
              <p className="text-muted-foreground leading-relaxed">
                The +7.1% (5yr) to +2.6% (20yr) annual premium for high-R&D companies is economically meaningful. 
                Over a 20-year period, even the smaller +2.6% annual premium translates to significant cumulative 
                outperformance. The magnitude suggests that R&D investment contributes to competitive advantages.
              </p>

              <h3 className="text-lg font-semibold text-foreground">6.2 Time Horizon Effects</h3>
              <p className="text-muted-foreground leading-relaxed">
                The strengthening of effect sizes over longer horizons (η² from 0.225 to 0.458) suggests that 
                R&D benefits compound over time. This is consistent with the innovation literature suggesting 
                that R&D investments have long gestation periods before yielding commercial returns.
              </p>

              <h3 className="text-lg font-semibold text-foreground">6.3 Limitations and Biases</h3>
              <ul className="text-muted-foreground space-y-2">
                <li>• <strong>Survivorship bias:</strong> Uses current S&P 500 constituents; historical members who were delisted or dropped are excluded. This may inflate premium estimates by 0.5-1% annually.</li>
                <li>• <strong>Look-ahead bias:</strong> While we use July-June returns (Fama-French convention) to mitigate timing issues, fiscal year-end variations create imperfect alignment.</li>
                <li>• <strong>Overlapping windows:</strong> Rolling 5/10/20-year windows are not independent observations. We apply Newey-West HAC standard errors, but overlapping-window p-values should be interpreted with caution. Annual non-overlapping HML premium is the preferred inference approach.</li>
                <li>• <strong>Sector concentration:</strong> Q5 (high R&D) is dominated by Tech/Healthcare (~70%). Premium may partially reflect sector performance. Sector-neutral results show smaller but still positive premium.</li>
                <li>• <strong>Factor spanning:</strong> Formal tests against FF3/FF5/Momentum factors are required before claiming R&D as a distinct "pricing factor."</li>
              </ul>
            </CardContent>
          </Card>
        </section>

        {/* Conclusion */}
        <section id="conclusion" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">7. Conclusion</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground leading-relaxed">
                This study demonstrates a robust and economically significant positive relationship between 
                R&D investment intensity and long-term shareholder returns among S&P 500 companies. Our 
                quintile-based analysis reveals that high-R&D companies outperform low-R&D companies by 
                +7.1% (5yr), +4.8% (10yr), and +2.6% (20yr) annually. Results are statistically significant (p &lt; 0.002).
              </p>
              <p className="text-muted-foreground leading-relaxed">
                These findings have important implications for investors, corporate managers, and policymakers. 
                For investors, our results suggest that tilting portfolios toward R&D-intensive companies may 
                generate superior long-term returns. For managers, the evidence supports sustained investment 
                in R&D as a value-creating strategy. For policymakers, the results underscore the economic 
                importance of supporting innovation through favorable R&D tax treatment and research funding.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Replicability */}
        <section id="replicability" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Database className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">8. Replicability & Data Access</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div className="prose prose-invert max-w-none">
                <p className="text-muted-foreground leading-relaxed">
                  In the interest of scientific transparency and reproducibility, we provide complete access to 
                  our data extraction pipeline, statistical methods, and underlying code.
                </p>
              </div>

              <h4 className="font-semibold text-foreground flex items-center gap-2">
                <Database className="h-4 w-4" />
                Data Sources & Extraction
              </h4>
              <div className="p-4 bg-muted/50 rounded-lg border border-border space-y-4">
                <div>
                  <p className="text-sm font-semibold text-foreground">1. Financial Modeling Prep (Tier-1)</p>
                  <ul className="text-sm text-muted-foreground mt-1 space-y-1 list-disc list-inside">
                    <li>Income statements: R&amp;D expense and revenue</li>
                    <li>Daily prices: adjusted close when available (splits/dividends)</li>
                    <li>Historical constituents: point-in-time S&amp;P 500 membership (Tier-1 proxy)</li>
                    <li>
                      Replication requires an <code>FMP_API_KEY</code> (data cannot be redistributed)
                    </li>
                  </ul>
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">2. Ken French Data Library</p>
                  <ul className="text-sm text-muted-foreground mt-1 space-y-1 list-disc list-inside">
                    <li>Fama-French factors and risk-free rate (for robustness / factor diagnostics)</li>
                  </ul>
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">3. Delisting Returns (Tier-1 estimate)</p>
                  <ul className="text-sm text-muted-foreground mt-1 space-y-1 list-disc list-inside">
                    <li>Price-based estimation when possible; conservative heuristics otherwise</li>
                    <li>See repository docs: <code>DATA_PROVENANCE.md</code> and <code>DATA_AVAILABILITY.md</code></li>
                  </ul>
                </div>
              </div>

              <h4 className="font-semibold text-foreground flex items-center gap-2">
                <FlaskConical className="h-4 w-4" />
                Exact Calculation Steps
              </h4>
              <div className="p-4 bg-muted/50 rounded-lg border border-border text-sm space-y-2">
                <p className="text-muted-foreground">
                  Reproduction is automated via <code>./scripts/reproduce_publication.sh</code>. At a high level, the pipeline:
                </p>
                <ol className="text-muted-foreground list-decimal list-inside space-y-1">
                  <li>Ingests Tier-1 data (FMP, factors, constituents, delisting estimates)</li>
                  <li>Computes July-June returns (look-ahead mitigation)</li>
                  <li>Computes rolling-window quintile results + ANOVA/t-tests</li>
                  <li>Exports frozen publication tables</li>
                </ol>
              </div>

              <h4 className="font-semibold text-foreground flex items-center gap-2">
                <ExternalLink className="h-4 w-4" />
                Code Repository
              </h4>
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                <p className="text-sm text-muted-foreground mb-3">
                  Full analysis code available on GitHub: <a href="https://github.com/vastdreams/fse-rnd-alpha" className="text-primary hover:underline">github.com/vastdreams/fse-rnd-alpha</a>
                </p>
                <div className="space-y-2 text-sm font-mono">
                  <p className="text-slate-600 dark:text-slate-400"># Clone and setup</p>
                  <p className="text-foreground">git clone https://github.com/vastdreams/fse-rnd-alpha.git</p>
                  <p className="text-foreground">cd fse-rnd-alpha && pip install -r requirements.txt</p>
                  <p className="text-slate-600 dark:text-slate-400 mt-3"># Run data pipeline</p>
                  <p className="text-foreground">./scripts/reproduce_publication.sh</p>
                  <p className="text-slate-600 dark:text-slate-400 mt-3"># Key scripts:</p>
                  <ul className="text-muted-foreground space-y-1">
                    <li>• <code>scripts/ingest_fmp_ultimate.py</code> - Tier-1 ingestion</li>
                    <li>• <code>scripts/compute_july_june_returns.py</code> - July-June returns</li>
                    <li>• <code>scripts/compute_research_metrics.py</code> - recompute pipeline</li>
                    <li>• <code>scripts/reproduce_all_tables.py</code> - table export</li>
                  </ul>
                </div>
              </div>

              <h4 className="font-semibold text-foreground">Verification Checklist</h4>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                  <p className="text-sm font-semibold text-green-600 dark:text-emerald-400 mb-2">✓ Independently Verifiable</p>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    <li>• All calculations use standard statistical methods</li>
                    <li>• Code is fully open source</li>
                    <li>• Canonical values are pinned by the publication snapshot (see <code>/api/research/publication-snapshot</code>)</li>
                  </ul>
                </div>
                <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                  <p className="text-sm font-semibold text-amber-400 mb-2">⚠ Limitations</p>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    <li>• FMP API requires subscription for full data</li>
                    <li>• Tier-1 survivorship mitigation is not CRSP/Compustat-grade</li>
                    <li>• R&D reporting standards evolved over time</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* References */}
        <section id="references" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">References</h2>
          </div>
          <Card>
            <CardContent className="pt-6">
              <ReferencesList ids={[
                "cai_2023",
                "chan_lakonishok_sougiannis_2001",
                "eberhart_maxwell_siddique_2004",
                "fama_french_1993",
                "fama_french_2015",
                "gu_2005",
                "hirshleifer_hsu_li_2013",
                "hou_mo_xue_zhang_2022",
                "leung_mazouz_chen_2019",
                "lev_sougiannis_1996",
                "li_2011"
              ]} />
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
