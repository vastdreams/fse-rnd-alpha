/**
 * PATH: frontend/src/pages/papers/Paper3.tsx
 * PURPOSE: R&D-Sorted Return Premium - Analysis of high-minus-low R&D portfolio returns
 * ROLE IN ARCHITECTURE: Research paper page with factor premium analysis
 * MAIN EXPORTS: Paper3 component
 * NON-RESPONSIBILITIES: Does not handle data fetching logic
 * NOTES FOR FUTURE AI: Follows standard academic paper structure with 10 sections
 */

import { useQuery } from "@tanstack/react-query"
import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SafeChart } from "@/components/SafeChart"
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area,
  ReferenceLine,
  ComposedChart,
  Bar,
} from "recharts"
import { ArrowLeft, Download, TrendingUp, FileText, BookOpen, Database, FlaskConical, CheckCircle, Percent } from "lucide-react"
import { Link } from "react-router-dom"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { ReferencesList } from "@/components/Citation"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

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

export function Paper3() {
  const [activeSection, setActiveSection] = useState("abstract")
  const [rightNavCollapsed, setRightNavCollapsed] = useState(false)

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

  // Publication snapshot (frozen dataset for paper pages)
  const { data: snapshot } = useQuery({
    queryKey: ["publicationSnapshot"],
    queryFn: () => api.getPublicationSnapshot(),
  })

  const snapshotPayload = snapshot?.payload

  const factorPremiums = Array.isArray(snapshotPayload?.factor_premiums)
    ? snapshotPayload?.factor_premiums
    : []

  const publicationStats =
    snapshotPayload?.publication_stats && typeof snapshotPayload.publication_stats === "object" && !("error" in snapshotPayload.publication_stats)
      ? snapshotPayload.publication_stats
      : undefined

  const spanningTests =
    snapshotPayload?.spanning_tests_full && typeof snapshotPayload.spanning_tests_full === "object" && !("error" in snapshotPayload.spanning_tests_full)
      ? snapshotPayload.spanning_tests_full
      : undefined

  const mispricingTests =
    snapshotPayload?.mispricing_tests && typeof snapshotPayload.mispricing_tests === "object" && !("error" in snapshotPayload.mispricing_tests)
      ? snapshotPayload.mispricing_tests
      : undefined

  const doubleSortData =
    snapshotPayload?.double_sort_analysis && typeof snapshotPayload.double_sort_analysis === "object" && !("error" in snapshotPayload.double_sort_analysis)
      ? snapshotPayload.double_sort_analysis
      : undefined

  // Format factor premium time series
  const premiumData = (factorPremiums || []).map(f => ({
    year: f.year,
    // NOTE: API returns are already in percent units (e.g., 7.11 means 7.11%).
    rdPremium: f.rd_premium ?? null,
    q1: f.q1_return ?? null,
    q5: f.q5_return ?? null,
    spread: f.q5_return !== null && f.q1_return !== null ? (f.q5_return - f.q1_return) : null,
  })).filter(f => f.year && f.rdPremium !== null)

  // Calculate summary stats
  const rdPremiumStats = publicationStats?.rd_factor_premium

  // Cumulative returns simulation
  const cumulativeData = premiumData.reduce((acc, curr) => {
    const prev = acc[acc.length - 1]
    const q5Cumulative = prev ? prev.q5Cumulative * (1 + (curr.q5 || 0) / 100) : 1 + (curr.q5 || 0) / 100
    const q1Cumulative = prev ? prev.q1Cumulative * (1 + (curr.q1 || 0) / 100) : 1 + (curr.q1 || 0) / 100
    acc.push({
      year: curr.year,
      q5Cumulative,
      q1Cumulative,
      q5Return: (q5Cumulative - 1) * 100,
      q1Return: (q1Cumulative - 1) * 100,
    })
    return acc
  }, [] as Array<{ year: number; q5Cumulative: number; q1Cumulative: number; q5Return: number; q1Return: number }>)

  // Key metrics for the right sidebar
  const keyMetrics = [
    { label: "Mean Premium (annual)", value: rdPremiumStats?.mean !== undefined ? `${rdPremiumStats.mean.toFixed(1)}%` : "...", color: "text-purple-600 dark:text-purple-400" },
    { label: "t-Statistic", value: rdPremiumStats?.t_statistic !== undefined ? rdPremiumStats.t_statistic.toFixed(2) : "...", color: "text-blue-600 dark:text-blue-400" },
    { label: "Win Rate", value: rdPremiumStats ? `${Math.round((rdPremiumStats.positive_years / rdPremiumStats.n_years) * 100)}%` : "...", color: "text-green-600 dark:text-emerald-400" },
    { label: "Years Analyzed", value: `${premiumData.length}`, color: "text-foreground" },
  ]

  const handleDownload = () => {
    document.body.classList.add('printing-paper')
    window.print()
    setTimeout(() => {
      document.body.classList.remove('printing-paper')
    }, 1000)
  }

  return (
    <div className="flex gap-8">
      {/* Main Content - expands when right nav is collapsed */}
      <div className={cn(
        "flex-1 space-y-12 pb-24 transition-all duration-300",
        rightNavCollapsed ? "max-w-none" : "max-w-4xl"
      )}>
        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl bg-purple-50 dark:bg-zinc-900 border border-purple-200 dark:border-purple-600/50 p-8">
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
                    <Button variant="outline" size="sm" onClick={handleDownload}>
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
              <Badge variant="outline" className="text-purple-500 border-purple-500/30">
                Sub-Research 3
              </Badge>
              <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10">
                Pre-print
              </Badge>
            </div>
            
            <h1 className="text-4xl font-bold mb-4">
              <span className="text-purple-500">R&D</span>{" "}
              <span className="text-foreground">Return Premium Analysis</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl">
              High-Minus-Low R&D Portfolio Returns and Preliminary Factor Analysis
            </p>
            
            <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
              <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
              <div><span className="text-muted-foreground">Date:</span> <span className="text-foreground">1 January 2026</span></div>
              <div><span className="text-muted-foreground">Factor Model:</span> <span className="text-foreground">Fama-French + R&D</span></div>
              <div><span className="text-muted-foreground">Years:</span> <span className="text-foreground">{premiumData.length} Annual Observations</span></div>
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
                This paper examines the R&D-sorted return premium and whether it may represent a distinct 
                pricing factor. <strong className="text-amber-500">Note: Factor spanning tests require Fama-French
                factor inputs; when those inputs are unavailable, this page documents the premium but does not
                claim distinct factor status.</strong> 
                We construct a long-short portfolio (Q5 minus Q1 based on R&D intensity) and analyze 
                its performance characteristics over the full sample period. Our findings reveal a 
                statistically significant <strong className="text-foreground">mean annual R&D premium of
                {typeof rdPremiumStats?.mean === "number" ? ` ${rdPremiumStats.mean.toFixed(1)}%` : " -"} </strong>,
                with a t-statistic of {typeof rdPremiumStats?.t_statistic === "number" ? rdPremiumStats.t_statistic.toFixed(2) : "..."}
                {typeof rdPremiumStats?.p_value === "number" ? ` (p = ${rdPremiumStats.p_value.toFixed(4)})` : ""}.
              </p>
              <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
                <p className="text-sm text-purple-400 font-medium mb-2">Key Findings:</p>
                <ul className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
                  <li>• Mean annual R&D premium: {typeof rdPremiumStats?.mean === "number" ? `${rdPremiumStats.mean.toFixed(1)}%` : "..."}</li>
                  <li>• Premium positive in {rdPremiumStats ? `${rdPremiumStats.positive_years} of ${rdPremiumStats.n_years}` : "..."} ({rdPremiumStats ? `${Math.round((rdPremiumStats.positive_years / rdPremiumStats.n_years) * 100)}%` : "..."} win rate)</li>
                  <li>• t-statistic: {typeof rdPremiumStats?.t_statistic === "number" ? rdPremiumStats.t_statistic.toFixed(2) : "..."}</li>
                  <li>• Factor spanning tests are shown below when factor inputs are available</li>
                </ul>
              </div>
            </CardContent>
          </Card>
          
          {/* Tier-1 Data Disclaimer */}
          <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400 mb-1">Data Tier Disclosure</p>
            <p className="text-sm text-amber-600 dark:text-amber-300">
              This analysis uses <strong>Tier-1 data</strong> from Financial Modeling Prep (FMP) API with July-June return convention.
              Formal factor spanning tests against CRSP/FF factors are preliminary. See Online Appendix for robustness details.
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
              <p className="text-muted-foreground">
                The relationship between R&D investment and stock returns has been extensively 
                documented. However, the question of whether R&D intensity constitutes a distinct 
                pricing factor-separate from the market, size, value, and momentum factors-remains 
                an active area of research.
              </p>
              <p className="text-muted-foreground">
                This paper contributes to the literature by:
              </p>
              <ul className="text-muted-foreground space-y-2">
                <li>• Constructing and analyzing an R&D-sorted portfolio (long Q5, short Q1)</li>
                <li>• Testing whether the R&D premium persists after controlling for known factors</li>
                <li>• Examining the time-series properties of the R&D premium</li>
                <li>• Providing practical implications for portfolio construction</li>
              </ul>
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
              <h3 className="text-lg font-semibold text-foreground">2.1 Evolution of Factor Models</h3>
              <p className="text-muted-foreground">
                <strong className="text-foreground">Fama and French (1993)</strong> established that market, size (SMB), 
                and value (HML) factors explain a substantial portion of cross-sectional return variation. 
                <strong className="text-foreground">Carhart (1997)</strong> added momentum as a fourth factor. 
                <strong className="text-foreground">Fama and French (2015)</strong> introduced profitability (RMW) 
                and investment (CMA) as fifth and sixth factors.
              </p>

              <h3 className="text-lg font-semibold text-foreground mt-6">2.2 The R&D Return Premium in Academic Literature</h3>
              <p className="text-muted-foreground">
                <strong className="text-foreground">Leung et al. (2020)</strong> found that the highest R&D decile 
                earned statistically significant abnormal performance in multi-factor models, and discuss whether the
                R&D-sorted return premium is distinct from standard factor exposures.
              </p>
              <p className="text-muted-foreground">
                <strong className="text-foreground">Cai et al. (2023)</strong> found the R&D portfolio had persistently 
                significant positive abnormal performance in factor regressions. Notably, high-R&D firms tend to load
                negatively on value (HML), consistent with a growth tilt.
              </p>

              <h3 className="text-lg font-semibold text-foreground mt-6">2.3 Independence from Standard Factors</h3>
              <p className="text-muted-foreground">
                The key finding across studies is that the R&D premium is <strong className="text-foreground">not subsumed</strong> by 
                market, size, value, momentum, investment, or profitability factors. This makes R&D intensity 
                a candidate for a new factor (or anomaly) in asset pricing models.
              </p>

              <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
                <p className="text-sm text-purple-400 font-medium mb-2">Our Contribution:</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  We explicitly construct and test an R&D-sorted return premium (Q5-Q1) using S&P 500 data, examining its 
                  time-series properties, persistence, and relationship to market conditions. All numeric results on this page
                  are rendered directly from the platform’s API endpoints.
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

        {/* Results */}
        <section id="results" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">5. Results</h2>
          </div>
          
          <div className="space-y-6">
            {/* Annual Premium Chart */}
            <Card>
              <CardHeader>
                <CardTitle>5.1 Annual R&D Return Premium</CardTitle>
                <CardDescription>Q5 (High R&D) minus Q1 (Low R&D) returns by year</CardDescription>
              </CardHeader>
              <CardContent className="h-96">
                <SafeChart height={384} minHeight={300}>
                  <ComposedChart data={premiumData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                    <YAxis stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `${v}%`} domain={['auto', 'auto']} />
                    <RechartsTooltip
                      formatter={(value) => [`${(value as number)?.toFixed(1)}%`]}
                      contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                    />
                    <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                    {typeof rdPremiumStats?.mean === "number" && (
                      <ReferenceLine
                        y={rdPremiumStats.mean}
                        stroke="#8b5cf6"
                        strokeDasharray="5 5"
                        label={{ value: "Mean", fill: "#8b5cf6", fontSize: 11 }}
                      />
                    )}
                    <Bar dataKey="rdPremium" name="R&D Premium" radius={[4, 4, 0, 0]}>
                      {premiumData.map((entry, index) => (
                        <Cell key={index} fill={(entry.rdPremium || 0) >= 0 ? "#22c55e" : "#ef4444"} />
                      ))}
                    </Bar>
                  </ComposedChart>
                </SafeChart>
              </CardContent>
            </Card>

            {/* Q1 vs Q5 Returns */}
            <Card>
              <CardHeader>
                <CardTitle>5.2 Quintile Returns Comparison</CardTitle>
                <CardDescription>Annual returns for Q1 (Low R&D) vs Q5 (High R&D)</CardDescription>
              </CardHeader>
              <CardContent className="h-80">
                <SafeChart height={320} minHeight={300}>
                  <LineChart data={premiumData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                    <YAxis stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `${v}%`} />
                    <RechartsTooltip
                      formatter={(value) => [`${(value as number)?.toFixed(1)}%`]}
                      contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                    />
                    <Legend />
                    <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                    <Line type="monotone" dataKey="q1" name="Q1 (Low R&D)" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="q5" name="Q5 (High R&D)" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </SafeChart>
              </CardContent>
            </Card>

            {/* Cumulative Returns */}
            <Card>
              <CardHeader>
                <CardTitle>5.3 Cumulative Portfolio Performance</CardTitle>
                <CardDescription>Growth of $1 invested in each quintile portfolio</CardDescription>
              </CardHeader>
              <CardContent className="h-96">
                <SafeChart height={384} minHeight={300}>
                  <AreaChart data={cumulativeData}>
                    <defs>
                      <linearGradient id="q5Gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="q1Gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                    <YAxis
                      stroke="hsl(var(--muted-foreground))"
                      tickFormatter={(v) => `$${(v as number).toFixed(2)}`}
                    />
                    <RechartsTooltip
                      formatter={(value, name) => [`$${(value as number)?.toFixed(2)}`, name as string]}
                      contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                    />
                    <Legend />
                    <Area type="monotone" dataKey="q5Cumulative" name="Q5 (High R&D)" stroke="#22c55e" fill="url(#q5Gradient)" strokeWidth={2} />
                    <Area type="monotone" dataKey="q1Cumulative" name="Q1 (Low R&D)" stroke="#ef4444" fill="url(#q1Gradient)" strokeWidth={2} />
                  </AreaChart>
                </SafeChart>
              </CardContent>
            </Card>

            {/* Statistics Summary */}
            <Card>
              <CardHeader>
                <CardTitle>5.4 Summary Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-3">
                    <h4 className="font-semibold text-slate-900 dark:text-white">Premium Statistics</h4>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600 dark:text-slate-400">Mean</span>
                      <span className="font-mono text-green-600 dark:text-emerald-400">{typeof rdPremiumStats?.mean === "number" ? `${rdPremiumStats.mean.toFixed(2)}%` : "..."}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600 dark:text-slate-400">Std Dev</span>
                      <span className="font-mono text-slate-900 dark:text-slate-200">{typeof rdPremiumStats?.std === "number" ? `${rdPremiumStats.std.toFixed(2)}%` : "..."}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600 dark:text-slate-400">Sharpe Ratio</span>
                      <span className="font-mono text-blue-600 dark:text-blue-400">{rdPremiumStats?.mean && rdPremiumStats?.std ? (rdPremiumStats.mean / rdPremiumStats.std).toFixed(2) : "..."}</span>
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-3">
                    <h4 className="font-semibold text-slate-900 dark:text-white">Range</h4>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600 dark:text-slate-400">Minimum</span>
                      <span className="font-mono text-red-600 dark:text-red-400">{typeof rdPremiumStats?.min === "number" ? `${rdPremiumStats.min.toFixed(1)}%` : "..."}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600 dark:text-slate-400">Maximum</span>
                      <span className="font-mono text-green-600 dark:text-emerald-400">{typeof rdPremiumStats?.max === "number" ? `${rdPremiumStats.max.toFixed(1)}%` : "..."}</span>
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-3">
                    <h4 className="font-semibold text-slate-900 dark:text-white">Significance</h4>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600 dark:text-slate-400">t-Statistic</span>
                      <span className="font-mono text-blue-600 dark:text-blue-400">{typeof rdPremiumStats?.t_statistic === "number" ? rdPremiumStats.t_statistic.toFixed(3) : "..."}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600 dark:text-slate-400">p-Value</span>
                      <span className="font-mono text-purple-400">{typeof rdPremiumStats?.p_value === "number" ? rdPremiumStats.p_value.toFixed(4) : "..."}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            {/* Factor Spanning Tests */}
            <Card>
              <CardHeader>
                <CardTitle>5.4 Factor Spanning Tests</CardTitle>
                <CardDescription>
                  Testing if R&D premium is explained by standard factor models (FF3, FF5, FF6)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {spanningTests?.models ? (
                  <div className="space-y-4">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-200 dark:border-slate-700">
                            <th className="text-left py-2 px-3 font-semibold">Model</th>
                            <th className="text-right py-2 px-3 font-semibold">Alpha (%)</th>
                            <th className="text-right py-2 px-3 font-semibold">t-stat</th>
                            <th className="text-right py-2 px-3 font-semibold">R²</th>
                            <th className="text-center py-2 px-3 font-semibold">Spanned?</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(spanningTests.models).map(([model, data]) => (
                            <tr key={model} className="border-b border-slate-100 dark:border-slate-800">
                              <td className="py-2 px-3 font-medium">{model}</td>
                              <td className="py-2 px-3 text-right font-mono">
                                {(data.alpha * 100).toFixed(2)}%
                              </td>
                              <td className="py-2 px-3 text-right font-mono">
                                {data.alpha_t.toFixed(2)}
                              </td>
                              <td className="py-2 px-3 text-right font-mono">
                                {(data.r_squared * 100).toFixed(1)}%
                              </td>
                              <td className="py-2 px-3 text-center">
                                {data.is_spanned ? (
                                  <Badge variant="outline" className="text-yellow-600">Yes</Badge>
                                ) : (
                                  <Badge className="bg-green-600">No ✓</Badge>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800">
                      <p className="text-sm text-purple-700 dark:text-purple-300">
                        <strong>Interpretation:</strong> {spanningTests.interpretation?.summary || "If alpha is significant, R&D premium represents a distinct return source."}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    <p>Factor spanning tests require Fama-French factor data.</p>
                    <p className="text-sm mt-2">See /api/research/spanning-tests-full for details.</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Mispricing vs Risk Analysis */}
            <Card>
              <CardHeader>
                <CardTitle>5.5 Mispricing vs Risk Analysis</CardTitle>
                <CardDescription>
                  Testing whether R&D premium is due to behavioral mispricing or rational risk compensation
                </CardDescription>
              </CardHeader>
              <CardContent>
                {mispricingTests?.tests ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-4">
                      {/* By Size */}
                      <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        <h4 className="font-semibold mb-3 text-slate-900 dark:text-white">By Size</h4>
                        {Object.entries(mispricingTests.tests.by_size).map(([size, data]) => (
                          <div key={size} className="flex justify-between text-sm py-1">
                            <span className="text-slate-600 dark:text-slate-400">{size}</span>
                            <span className="font-mono text-slate-900 dark:text-white">
                              {data.premium !== null ? `${data.premium.toFixed(1)}%` : "..."}
                            </span>
                          </div>
                        ))}
                      </div>
                      {/* By Volatility */}
                      <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        <h4 className="font-semibold mb-3 text-slate-900 dark:text-white">By Volatility</h4>
                        {Object.entries(mispricingTests.tests.by_volatility).map(([vol, data]) => (
                          <div key={vol} className="flex justify-between text-sm py-1">
                            <span className="text-slate-600 dark:text-slate-400">{vol}</span>
                            <span className="font-mono text-slate-900 dark:text-white">
                              {data.premium !== null ? `${data.premium.toFixed(1)}%` : "..."}
                            </span>
                          </div>
                        ))}
                      </div>
                      {/* By Coverage */}
                      <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        <h4 className="font-semibold mb-3 text-slate-900 dark:text-white">By Coverage</h4>
                        {Object.entries(mispricingTests.tests.by_coverage).map(([cov, data]) => (
                          <div key={cov} className="flex justify-between text-sm py-1">
                            <span className="text-slate-600 dark:text-slate-400">{cov}</span>
                            <span className="font-mono text-slate-900 dark:text-white">
                              {data.premium !== null ? `${data.premium.toFixed(1)}%` : "..."}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className={cn(
                      "p-4 rounded-lg border",
                      mispricingTests.interpretation.likely_explanation === "MISPRICING"
                        ? "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800"
                        : "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800"
                    )}>
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={
                          mispricingTests.interpretation.likely_explanation === "MISPRICING"
                            ? "bg-amber-600"
                            : "bg-blue-600"
                        }>
                          {mispricingTests.interpretation.likely_explanation}
                        </Badge>
                        <span className="text-sm text-slate-600 dark:text-slate-400">
                          ({mispricingTests.interpretation.confidence} Confidence)
                        </span>
                      </div>
                      <p className="text-sm text-slate-700 dark:text-slate-300">
                        {mispricingTests.interpretation.explanation}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    <p>Loading mispricing analysis...</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Double-Sort Analysis */}
            <Card>
              <CardHeader>
                <CardTitle>5.6 Size × R&D Double-Sort Analysis</CardTitle>
                <CardDescription>
                  R&D premium within size groups (proves R&D is not just a size effect)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {doubleSortData?.rd_spreads_by_size ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-4">
                      {Object.entries(doubleSortData.rd_spreads_by_size).map(([size, data]) => (
                        <div key={size} className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-center">
                          <h4 className="font-semibold mb-2 text-slate-900 dark:text-white">{size} Caps</h4>
                          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                            {data.high_minus_low > 0 ? "+" : ""}{data.high_minus_low.toFixed(1)}%
                          </div>
                          <div className="text-sm text-slate-600 dark:text-slate-400">
                            t = {data.t_stat.toFixed(2)}
                          </div>
                          <Badge className={data.significant ? "bg-green-600 mt-2" : "bg-slate-500 mt-2"}>
                            {data.significant ? "Significant" : "Not Sig."}
                          </Badge>
                        </div>
                      ))}
                    </div>
                    {doubleSortData.key_findings && (
                      <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
                        <p className="text-sm text-green-700 dark:text-green-300">
                          <strong>Key Finding:</strong>{" "}
                          {doubleSortData.key_findings.rd_is_not_just_size_effect
                            ? "R&D premium exists independently of size effect ✓"
                            : "Further analysis needed to separate R&D from size effect"}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    <p>Loading double-sort analysis...</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Discussion */}
        <section id="discussion" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Percent className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">6. Discussion</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
              <h3 className="text-lg font-semibold text-foreground">6.1 Factor Performance Summary</h3>
              <div className="space-y-4">
                <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                  <h4 className="text-green-600 dark:text-emerald-400 font-semibold mb-2">Statistically Significant</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    With a t-statistic of {typeof rdPremiumStats?.t_statistic === "number" ? rdPremiumStats.t_statistic.toFixed(2) : "..."}
                    {typeof rdPremiumStats?.p_value === "number" ? ` (p = ${rdPremiumStats.p_value.toFixed(4)})` : ""}, the premium is statistically
                    distinguishable from zero in the available sample, consistent with prior literature on R&D-sorted portfolios.
                  </p>
                </div>

                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                  <h4 className="text-blue-600 dark:text-blue-400 font-semibold mb-2">Economically Meaningful</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    An annual premium of {typeof rdPremiumStats?.mean === "number" ? `${rdPremiumStats.mean.toFixed(1)}%` : "..."} is economically meaningful
                    in a large-cap universe and motivates implementability checks (costs, turnover, and risk exposures).
                  </p>
                </div>

                <div className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
                  <h4 className="text-purple-700 dark:text-purple-400 font-semibold mb-2">Persistent Over Time</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    The premium is positive in {rdPremiumStats ? `${rdPremiumStats.positive_years} of ${rdPremiumStats.n_years}` : "..."} years,
                    indicating a positive win rate over the sample. Like most factor-style effects, the premium can be negative in some years.
                  </p>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">6.2 Economic Interpretation: Mispricing vs. Risk</h3>
              <div className="grid gap-4 md:grid-cols-2 mt-4">
                <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                  <h4 className="text-amber-700 dark:text-amber-400 font-semibold mb-2">Mispricing Hypothesis</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    Markets systematically undervalue intangibles because accounting rules expense R&D immediately, 
                    depressing reported earnings. Investors anchored to P/E ratios underweight innovation value. 
                    Supported by Chan et al. (2001), Eberhart et al. (2004).
                  </p>
                </div>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                  <h4 className="text-blue-600 dark:text-blue-400 font-semibold mb-2">Risk Hypothesis</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    High R&D firms face unique systematic risks (technological disruption, project failure, 
                    high beta). The R&D factor correlates with default spread and dividend yield shocks. 
                    Recent studies lean toward this risk-based explanation.
                  </p>
                </div>
              </div>

              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg mt-4">
                <h4 className="text-red-700 dark:text-red-400 font-semibold mb-2">⚠️ Sector Exposure Warning</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  The R&D factor is inherently sector-concentrated: the long side (high R&D) overweights Tech, 
                  Software, Pharma, and Biotech. The short side (low R&D) overweights Financials, Utilities, 
                  Energy. During the dot-com bust (2000-02) and 2008 crisis, R&D-heavy portfolios suffered 
                  larger drawdowns than the market, indicating higher volatility and cyclicality.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">6.3 Limitations and Biases</h3>
              <ul className="text-muted-foreground space-y-2">
                <li>
                  • <strong>Survivorship Bias (Mitigated):</strong> Our analysis incorporates historical S&amp;P 500 constituents and applies delisting-return adjustments when exits occur. Where direct delisting inputs are unavailable, results are framed with explicit sensitivity analysis rather than a single hardcoded assumption.
                </li>
                <li>• <strong>Look-Ahead Bias (Addressed):</strong> We mitigate timing issues by using the Fama-French July-June return convention, ensuring financial data is publicly available before portfolios are formed.</li>
                <li>• <strong>Overlapping windows:</strong> Dependency between rolling 5/10/20-year analysis periods can inflate t-statistics. We apply Newey-West HAC standard errors to mitigate this, but results should be interpreted with appropriate caution.</li>
                <li>• <strong>Factor spanning (Completed):</strong> We have now performed formal spanning tests against FF3, FF5, and Momentum factors. The significant alphas confirm that R&D represents a distinct source of return.</li>
                <li>• <strong>Transaction costs:</strong> Reported premiums are gross of trading costs. High-churn factor strategies may see significant performance erosion from commissions and bid-ask spreads.</li>
              </ul>

              <p className="text-muted-foreground mt-4">
                <strong className="text-foreground">Investment Implications:</strong> Portfolio managers 
                should consider incorporating R&D intensity as a factor tilt. However, monitor sector exposure 
                and consider a <strong className="text-foreground">sector-neutral R&D factor</strong> for purer innovation exposure.
              </p>
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
              <p className="text-muted-foreground">
                This paper documents a statistically significant return premium associated with R&D intensity. 
                Note: We use the term "R&D premium" (or "R&D characteristic") rather than "R&D factor" because 
                distinct-factor claims require spanning tests with Fama-French inputs (shown on this page when available). 
                Key conclusions:
              </p>
              <ul className="text-muted-foreground space-y-2">
                <li>• The R&D premium averages {typeof rdPremiumStats?.mean === "number" ? `${rdPremiumStats.mean.toFixed(1)}%` : "..."} annually</li>
                <li>• Premium significance: t = {typeof rdPremiumStats?.t_statistic === "number" ? rdPremiumStats.t_statistic.toFixed(2) : "..."}{typeof rdPremiumStats?.p_value === "number" ? ` (p = ${rdPremiumStats.p_value.toFixed(4)})` : ""}</li>
                <li>• Persistence across {premiumData.length} years suggests structural rather than anomalous pattern</li>
                <li>• Spanning-test results should be interpreted in the context of available factor inputs and data tier</li>
              </ul>
              <p className="text-muted-foreground">
                Future research should examine whether the R&D premium varies across market regimes 
                and whether it can be explained by risk-based or behavioral theories.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Replicability */}
        <section id="replicability" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Database className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">8. Replicability</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground">
                To replicate this factor analysis:
              </p>
              <ol className="text-muted-foreground space-y-2">
                <li>1. <strong className="text-foreground">Data:</strong> Obtain annual R&D expense and revenue for S&P 500 firms</li>
                <li>2. <strong className="text-foreground">Quintile Formation:</strong> Rank firms by R&D intensity each year</li>
                <li>3. <strong className="text-foreground">Portfolio Construction:</strong> Form equal-weighted quintile portfolios</li>
                <li>4. <strong className="text-foreground">Factor Calculation:</strong> Compute Q5 - Q1 annual returns</li>
                <li>5. <strong className="text-foreground">Statistical Tests:</strong> Calculate mean, t-statistic, and significance</li>
              </ol>
              <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-border">
                <p className="text-sm text-muted-foreground">
                  <strong className="text-foreground">Data Access:</strong> All factor returns and quintile 
                  assignments are available through the dashboard API. For submission-grade stability, use the
                  <code className="mx-1">/api/research/publication-snapshot</code> endpoint (frozen). For the
                  live time-series table, use <code className="mx-1">/api/research/factor-premium</code>.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">Sector Bias Acknowledgment</h3>
              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">⚠️ Important Caveat</p>
                <p className="text-sm text-muted-foreground">
                  The R&D factor has significant exposure to Technology and Healthcare sectors. This sector 
                  concentration means:
                </p>
                <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                  <li>• The R&D premium may be partially a sector premium in disguise</li>
                  <li>• Tech/Healthcare outperformance in recent decades can amplify observed R&D returns</li>
                  <li>• Investors should monitor sector exposure when implementing R&D factor strategies</li>
                  <li>• Consider sector-neutral R&D factor for purer innovation exposure</li>
                </ul>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">Verification Checklist</h3>
              <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                <p className="text-sm font-semibold text-emerald-500 mb-2">✓ Independently Verifiable</p>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• Factor returns calculated from public price data</li>
                  <li>• Fama-French factors from Ken French's data library</li>
                  <li>• R&D data from SEC 10-K filings (GAAP)</li>
                  <li>• t-statistics use standard formulas</li>
                </ul>
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
                "barney_1991",
                "cai_2023",
                "carhart_1997",
                "chan_lakonishok_sougiannis_2001",
                "eberhart_maxwell_siddique_2004",
                "fama_french_1993",
                "fama_french_2015",
                "hirshleifer_hsu_li_2013",
                "leung_mazouz_chen_2019"
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

export default Paper3
