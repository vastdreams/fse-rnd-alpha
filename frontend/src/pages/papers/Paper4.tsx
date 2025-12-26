/**
 * PATH: frontend/src/pages/papers/Paper4.tsx
 * PURPOSE: Fundamental Value Creation Through R&D - Academic paper on operational value
 * ROLE IN ARCHITECTURE: Research paper page with fundamental analysis
 * MAIN EXPORTS: Paper4 component
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
  LineChart,
  Line,
  Legend,
  AreaChart,
  Area,
} from "recharts"
import { ArrowLeft, Download, FileText, TrendingUp, BookOpen, Database, FlaskConical, CheckCircle, Building2 } from "lucide-react"
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

export function Paper4() {
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

  const { data: rdTrends } = useQuery({
    queryKey: ["rdTrends"],
    queryFn: () => api.getRDTrends(),
  })

  const { data: rdBySector } = useQuery({
    queryKey: ["rdBySector"],
    queryFn: () => api.getRDBySector(),
  })

  const { data: cohortSummary } = useQuery({
    queryKey: ["cohortSummary"],
    queryFn: () => api.getCohortSummary(),
  })

  const { data: rdLeaders } = useQuery({
    queryKey: ["rdLeaders"],
    queryFn: () => api.getRDLeaderboard(20),
  })

  // R&D trends over time
  const trendData = (rdTrends || []).map(t => ({
    year: t.year,
    companies: t.companies,
    avgIntensity: t.avg_rd_intensity,
    totalSpendB: t.total_rd_spend / 1e9,
  }))

  // Calculate aggregate metrics
  const totalRdSpend = rdBySector?.reduce((acc, s) => acc + s.total_rd_spend, 0) || 0
  const avgIntensity = cohortSummary?.avg_rd_intensity || 0

  // Key metrics for the right sidebar
  const keyMetrics = [
    { label: "Total R&D", value: `$${(totalRdSpend / 1e12).toFixed(1)}T`, color: "text-amber-600 dark:text-amber-400" },
    { label: "Avg Intensity", value: `${avgIntensity.toFixed(1)}%`, color: "text-green-600 dark:text-emerald-400" },
    { label: "Companies", value: `${cohortSummary?.total_companies || 503}`, color: "text-foreground" },
    { label: "Years", value: `${trendData.length}`, color: "text-foreground" },
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
        <div className="relative overflow-hidden rounded-2xl bg-amber-50 dark:bg-zinc-900 border border-amber-200 dark:border-amber-600/50 p-8">
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
              <Badge variant="outline" className="text-amber-500 border-amber-500/30">
              Sub-Research 4
            </Badge>
              <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10">
                Pre-print
              </Badge>
            </div>
            
            <h1 className="text-4xl font-bold mb-4">
              <span className="text-amber-500">Fundamental</span>{" "}
              <span className="text-foreground">Value Creation Through R&D</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl">
              R&D Investment Beyond Stock Price Returns: Operational Performance and Competitive Position
            </p>
            
            <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
              <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
              <div><span className="text-muted-foreground">Date:</span> <span className="text-foreground">17 December 2025</span></div>
              <div><span className="text-muted-foreground">Focus:</span> <span className="text-foreground">Operational Metrics</span></div>
              <div><span className="text-muted-foreground">Total R&D:</span> <span className="text-foreground">${(totalRdSpend / 1e12).toFixed(1)}T Analyzed</span></div>
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
                While previous papers in this series focus on stock price returns, this paper examines 
                the <strong className="text-foreground">fundamental value creation</strong> aspect of R&D investment. 
                We analyze how R&D intensity relates to operational performance metrics including revenue 
                growth, profit margins, and competitive positioning. Our analysis covers 
                ${(totalRdSpend / 1e12).toFixed(1)} trillion in cumulative R&D spending across 
                {cohortSummary?.total_companies || 503} S&P 500 companies over {trendData.length} years.
              </p>
              <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                <p className="text-sm text-amber-400 font-medium mb-2">Key Findings:</p>
                <ul className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
                  <li>• R&D creates intangible assets that manifest in improved operational performance</li>
                  <li>• Payoffs from R&D often arrive with multi-year lags (varying by industry and project type)</li>
                  <li>• Effect size strengthens with investment horizon (η² = 0.23 at 5yr → 0.46 at 20yr)</li>
                  <li>• R&D investments satisfy the VRIN framework for sustainable competitive advantage</li>
                </ul>
              </div>
            </CardContent>
          </Card>
          
          {/* Tier-1 Data Disclaimer */}
          <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400 mb-1">Data Tier Disclosure</p>
            <p className="text-sm text-amber-600 dark:text-amber-300">
              This analysis uses <strong>Tier-1 data</strong> from Financial Modeling Prep (FMP) API.
              <strong> Operational metrics</strong> (revenue growth, margins, FCF) are <strong>illustrative</strong> based on literature estimates-
              not directly computed from this dataset. R&D spend totals are computed from the sample.
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
                Corporate R&D investment represents a commitment to future value creation. Unlike 
                capital expenditures that create tangible assets, R&D spending generates intangible 
                assets-knowledge, patents, processes-that are difficult to measure but critical for 
                long-term competitive advantage.
              </p>
              <p className="text-muted-foreground">
                This paper examines the fundamental mechanisms through which R&D investment is associated with value creation:
              </p>
              <ul className="text-muted-foreground space-y-2">
                <li>• <strong className="text-foreground">Innovation Pipeline:</strong> How R&D translates to new products and services</li>
                <li>• <strong className="text-foreground">Competitive Moat:</strong> The role of patents and proprietary knowledge</li>
                <li>• <strong className="text-foreground">Operational Efficiency:</strong> Process improvements and cost reduction</li>
                <li>• <strong className="text-foreground">Time Lag Effects:</strong> The delay between R&D spending and returns</li>
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
              <h3 className="text-lg font-semibold text-foreground">2.1 R&D Time Lags</h3>
              <p className="text-muted-foreground">
                <strong className="text-foreground">Griliches (1981)</strong> established that R&D investments have significant 
                lags before generating measurable productivity gains. Many empirical studies emphasize that these payoff
                horizons are multi-year and vary materially by sector and project type.
              </p>
              <p className="text-muted-foreground">
                This lag structure motivates long-horizon return tests. Consistent with that intuition, our return-sort
                effect sizes strengthen over longer horizons (η² from 0.23 at 5-year to 0.46 at 20-year).
              </p>

              <h3 className="text-lg font-semibold text-foreground mt-6">2.2 The VRIN Framework for Sustainable Advantage</h3>
              <p className="text-muted-foreground">
                <strong className="text-foreground">Barney (1991)</strong> introduced the VRIN framework (also called VRIO) for 
                evaluating resources that create sustainable competitive advantage. R&D-generated assets 
                often fulfill these criteria:
              </p>
              <div className="grid gap-3 md:grid-cols-2 mt-4">
                <div className="p-3 bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <span className="font-semibold text-blue-700 dark:text-blue-400">Valuable:</span>
                  <p className="text-slate-600 dark:text-slate-300 text-sm mt-1">
                    R&D leads to new products, cost reductions, or differentiation advantages. Successful 
                    drugs or patented technology directly add value.
                  </p>
                </div>
                <div className="p-3 bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-800 rounded-lg">
                  <span className="font-semibold text-purple-700 dark:text-purple-400">Rare:</span>
                  <p className="text-slate-600 dark:text-slate-300 text-sm mt-1">
                    Cutting-edge research output (patents, trade secrets) is unique to the firm. Not every 
                    firm can develop a given innovation-successful R&D outcomes are relatively rare.
                  </p>
                </div>
                <div className="p-3 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                  <span className="font-semibold text-emerald-700 dark:text-emerald-400">Inimitable:</span>
                  <p className="text-slate-600 dark:text-slate-300 text-sm mt-1">
                    Intangible know-how, protected IP, and tacit knowledge are difficult to replicate. 
                    Rivals may take years and substantial expense to reverse-engineer complex products.
                  </p>
                </div>
                <div className="p-3 bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 rounded-lg">
                  <span className="font-semibold text-amber-700 dark:text-amber-400">Non-substitutable:</span>
                  <p className="text-slate-600 dark:text-slate-300 text-sm mt-1">
                    Proprietary platforms, network effects, and ecosystem advantages are not easily 
                    replaced by alternative approaches.
                  </p>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">2.3 Strategic Implications</h3>
              <p className="text-muted-foreground">
                <strong className="text-foreground">Porter (1992)</strong> emphasized the strategic importance of sustained R&D 
                investment. Companies that underinvest in R&D during downturns often lose market position 
                permanently. <strong className="text-foreground">Lev and Sougiannis (1996)</strong> documented that capitalizing R&D 
                (treating it as an asset) resulted in significant explanatory power for future earnings and 
                stock prices, confirming that R&D builds economic assets not reflected in traditional accounting.
              </p>
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
                  Our sample comprises {cohortSummary?.total_companies || 503} S&P 500 companies with 
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
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{cohortSummary?.total_companies || 503}</div>
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

        {/* Results */}
        <section id="results" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">5. Results</h2>
          </div>
          
          <div className="space-y-6">
            {/* R&D Trends Over Time */}
            <Card>
              <CardHeader>
                <CardTitle>5.1 R&D Investment Trends</CardTitle>
                <CardDescription>Evolution of R&D spending and intensity across the S&P 500</CardDescription>
              </CardHeader>
              <CardContent className="h-80">
                {trendData.length > 0 ? (
                <SafeChart height={320} minHeight={250}>
                  <LineChart data={trendData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(v) => `${v}%`} />
                      <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(v) => `$${v}B`} />
                      <RechartsTooltip contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="avgIntensity" name="Avg R&D Intensity (%)" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
                    <Line yAxisId="right" type="monotone" dataKey="totalSpendB" name="Total R&D Spend ($B)" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </SafeChart>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">Loading chart data...</div>
                )}
              </CardContent>
            </Card>

            {/* Company Count */}
            <Card>
              <CardHeader>
                <CardTitle>5.2 R&D Reporting Coverage</CardTitle>
                <CardDescription>Number of companies reporting R&D expenses by year</CardDescription>
              </CardHeader>
              <CardContent className="h-64">
                {trendData.length > 0 ? (
                <SafeChart height={256} minHeight={250}>
                  <AreaChart data={trendData}>
                    <defs>
                      <linearGradient id="companyGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <RechartsTooltip formatter={(value) => [value as number, "Companies"]} contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                    <Area type="monotone" dataKey="companies" fill="url(#companyGradient)" stroke="#8b5cf6" strokeWidth={2} />
                  </AreaChart>
                </SafeChart>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">Loading chart data...</div>
                )}
              </CardContent>
            </Card>

            {/* Top R&D Leaders */}
            <Card>
              <CardHeader>
                <CardTitle>5.3 Top R&D Innovators</CardTitle>
                <CardDescription>Companies with highest R&D intensity</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2">
                  {(rdLeaders || []).slice(0, 10).map((company, i) => (
                    <div 
                      key={company.symbol}
                      className="flex items-center justify-between p-4 rounded-lg bg-slate-800 hover:bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-500/20 to-amber-600/10 flex items-center justify-center text-sm font-bold text-amber-400">
                          {i + 1}
                        </div>
                        <div>
                          <Link to={`/companies/${company.symbol}`} className="font-mono font-bold text-primary hover:underline">
                            {company.symbol}
                          </Link>
                          <p className="text-xs text-slate-600 dark:text-slate-400 truncate max-w-32">{company.name || company.symbol}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-green-600 dark:text-emerald-400">{company.avg_rd_intensity?.toFixed(1)}%</div>
                        <div className="text-xs text-slate-500">${(company.total_rd_spend / 1e9).toFixed(1)}B total</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Discussion */}
        <section id="discussion" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Building2 className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">6. Discussion</h2>
          </div>
          <Card>
            <CardContent className="pt-6 prose prose-invert max-w-none space-y-6">
              <p className="text-muted-foreground">
                Our analysis reveals that R&D investment is associated with value creation through multiple channels:
              </p>
              
              <div className="grid gap-6 md:grid-cols-3">
                <div className="p-6 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700">
                  <h4 className="text-blue-700 dark:text-blue-400 font-semibold mb-3">Innovation Pipeline</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    R&D spending funds new product development, process improvements, and 
                    intellectual property creation.
                  </p>
                </div>
                
                <div className="p-6 rounded-xl bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700">
                  <h4 className="text-purple-700 dark:text-purple-400 font-semibold mb-3">Competitive Moat</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    Patents, proprietary technology, and know-how create barriers to entry 
                    and pricing power.
                  </p>
                </div>
                
                <div className="p-6 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700">
                  <h4 className="text-emerald-700 dark:text-emerald-400 font-semibold mb-3">Financial Returns</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    Superior products lead to revenue growth, margin expansion, and 
                    ultimately stock price appreciation.
                  </p>
                </div>
              </div>

              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                <h4 className="text-amber-700 dark:text-amber-400 font-semibold mb-2">Time Lag Effect</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Long-horizon measurement matters. In our return-sort results, the effect size (η²) increases from
                  0.23 at 5-year windows to 0.46 at 20-year windows. This pattern is consistent with the intuition
                  that R&D payoffs can be multi-year, but we do not estimate causal lag lengths directly in this dataset.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">6.2 Intangible Capital and Market Value</h3>
              <p className="text-muted-foreground">
                There is growing recognition that intangible assets now drive a large share of corporate value. 
                Practitioner and academic work often notes that capitalizing R&D can materially change reported earnings
                and valuation multiples for R&D-intensive firms versus standard accounting (which expenses R&D).
              </p>
              <p className="text-muted-foreground">
                This indicates that high-R&D firms are creating real economic assets not immediately reflected 
                on financial statements. Investors who appreciate this "invisible capital" can benefit from the 
                eventual recognition of innovation value in earnings and stock prices.
              </p>

              <h3 className="text-lg font-semibold text-foreground mt-6">6.3 Limitations and Caveats</h3>
              <ul className="text-muted-foreground space-y-2">
                <li>• <strong>Survivorship Bias (Tier-1 mitigation):</strong> Historical S&P 500 constituents and delisting adjustments substantially reduce survivorship bias, but Tier-1 is not CRSP/Compustat-grade.</li>
                <li>• <strong>Look-Ahead Bias (Mitigated):</strong> We utilize the Fama-French July-June return convention to align fiscal-year R&D data with subsequent returns.</li>
                <li>• <strong>Overlapping windows:</strong> Dependency between rolling 5/10/20-year analysis periods requires caution when interpreting the strengthening of effect sizes over time.</li>
                <li>• <strong>Causation vs. Correlation:</strong> While R&D correlates with long-term performance, successful firms may simply have more excess cash to invest in R&D (reverse causality).</li>
                <li>• <strong>Qualitative Framework:</strong> The VRIN analysis is a qualitative strategic framework and has not been empirically mapped to specific patent or IP metrics in this study.</li>
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
              <p className="text-muted-foreground">
                This sub-research note complements the Main Paper by discussing plausible mechanisms for why
                R&D intensity can be associated with long-run returns. Key takeaways:
              </p>
              
              <div className="grid gap-4 md:grid-cols-2">
                <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700">
                  <h4 className="text-emerald-700 dark:text-emerald-700 dark:text-emerald-400 font-semibold">Finding 1</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-700 dark:text-slate-200 mt-2">High-R&D companies outperform low-R&D by +7.1% (5yr) to +2.6% (20yr) annually</p>
                </div>
                <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700">
                  <h4 className="text-blue-700 dark:text-blue-700 dark:text-blue-400 font-semibold">Finding 2</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-700 dark:text-slate-200 mt-2">
                    Effect size increases with horizon (η² rises), even as premium magnitude declines
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700">
                  <h4 className="text-purple-700 dark:text-purple-700 dark:text-purple-400 font-semibold">Finding 3</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-700 dark:text-slate-200 mt-2">R&D premium is statistically significant</p>
                </div>
                <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
                  <h4 className="text-amber-700 dark:text-amber-700 dark:text-amber-400 font-semibold">Finding 4</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-700 dark:text-slate-200 mt-2">R&D satisfies VRIN framework criteria</p>
                </div>
              </div>

              <p className="text-muted-foreground mt-4">
                <strong className="text-foreground">Investment Implications:</strong> Incorporating R&D 
                intensity into portfolio construction can enhance long-term returns. The R&D Alpha ETF 
                strategy provides a practical implementation of these insights.
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
                To replicate this fundamental analysis:
              </p>
              <ol className="text-muted-foreground space-y-2">
                <li>1. <strong className="text-foreground">Data Collection:</strong> Obtain annual R&D expense and revenue from 10-K filings</li>
                <li>2. <strong className="text-foreground">Intensity Calculation:</strong> Compute R&D/Revenue for each firm-year</li>
                <li>3. <strong className="text-foreground">Trend Analysis:</strong> Aggregate by year and sector</li>
                <li>4. <strong className="text-foreground">VRIN Evaluation:</strong> Assess qualitative factors for competitive advantage</li>
                <li>5. <strong className="text-foreground">Time Lag Testing:</strong> Correlate R&D with returns at various horizons</li>
              </ol>
              <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-border">
                <p className="text-sm text-muted-foreground">
                  <strong className="text-foreground">Data Access:</strong> All R&D data and calculated 
                  metrics are available through the dashboard API. Use the /api/research/rd-trends 
                  endpoint for time-series data.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">Sector Bias Acknowledgment</h3>
              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                <p className="text-sm font-semibold text-amber-600 dark:text-amber-400 mb-2">⚠️ Sector Concentration</p>
                <p className="text-sm text-muted-foreground">
                  R&D-intensive companies are heavily concentrated in Technology, Healthcare, and Biotech sectors. 
                  This concentration affects our findings:
                </p>
                <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                  <li>• Top R&D spenders are predominantly tech giants (Apple, Alphabet, Meta, Microsoft)</li>
                  <li>• R&D intensity trends partly reflect tech sector growth</li>
                  <li>• VRIN framework may apply differently across industries</li>
                  <li>• Value creation mechanisms vary (software IP vs. pharma patents)</li>
                </ul>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">Verification Checklist</h3>
              <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-2">✓ Independently Verifiable</p>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    <li>• R&D expense from SEC 10-K (GAAP-mandated)</li>
                    <li>• Revenue figures are audited</li>
                    <li>• All calculations use standard formulas</li>
                    <li>• Time-series data is publicly accessible</li>
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
                "griliches_1981",
                "gu_2005",
                "hall_jaffe_trajtenberg_2005",
                "lev_sougiannis_1996",
                "porter_1992"
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

export default Paper4
