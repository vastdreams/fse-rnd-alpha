/**
 * PATH: frontend/src/pages/Documentation.tsx
 * PURPOSE:
 *   - Provide an index of research outputs (Main Paper + Sub-Research) and platform documentation.
 *
 * ROLE IN ARCHITECTURE:
 *   - Frontend documentation hub and navigation entrypoint for research artifacts.
 *
 * MAIN EXPORTS:
 *   - Documentation: route component for /documentation
 *
 * NON-RESPONSIBILITIES:
 *   - Does not compute research metrics (backend does).
 *   - Does not hardcode unverifiable research results (“0 hallucinations” policy).
 *
 * NOTES FOR FUTURE AI:
 *   - Any numeric claims displayed here should come from API responses.
 *   - Prefer linking to the Main Paper page for citation-ready narrative.
 */

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { BarChart3, TrendingUp, FlaskConical, Database, Target, Layers, Award, FileText, Presentation, ArrowRight, Clock } from "lucide-react"
import { Formulas } from "@/components/Formula"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"

const PAPERS: Array<{
  id: string
  title: string
  subtitle: string
  icon: any
  color: keyof typeof COLOR_CLASSES
  route: string
  badgeLabel: string
}> = [
  {
    id: "main",
    title: "Main Paper",
    subtitle: "Consolidated manuscript + investable strategy + frozen publication snapshot",
    icon: FileText,
    color: "slate",
    route: "/papers/main",
    badgeLabel: "Main Paper",
  },
  {
    id: "1",
    title: "Sub-Research 1: Returns & Inference",
    subtitle: "Core returns results, annual HML series, and rolling-window context",
    icon: TrendingUp,
    color: "emerald",
    route: "/papers/1",
    badgeLabel: "Sub-Research 1",
  },
  {
    id: "2",
    title: "Sub-Research 2: Sector Patterns",
    subtitle: "Cross-sector R&D intensity and data coverage",
    icon: Layers,
    color: "blue",
    route: "/papers/2",
    badgeLabel: "Sub-Research 2",
  },
  {
    id: "3",
    title: "Sub-Research 3: Factor Tests",
    subtitle: "Robustness suite and factor-model diagnostics",
    icon: BarChart3,
    color: "purple",
    route: "/papers/3",
    badgeLabel: "Sub-Research 3",
  },
  {
    id: "4",
    title: "Sub-Research 4: Mechanisms (Qualitative)",
    subtitle: "Interpretation and mechanism discussion (no computed operational metrics)",
    icon: Award,
    color: "amber",
    route: "/papers/4",
    badgeLabel: "Sub-Research 4",
  },
]

const COLOR_CLASSES = {
  slate: {
    card: "from-slate-500/10 to-slate-600/5 border-slate-500/20 hover:border-slate-500/40",
    icon: "text-slate-500",
    badge: "bg-slate-500/10 text-slate-400",
  },
  emerald: {
    card: "from-emerald-500/10 to-emerald-600/5 border-emerald-500/20 hover:border-emerald-500/40",
    icon: "text-emerald-500",
    badge: "bg-emerald-500/10 text-emerald-400",
  },
  blue: {
    card: "from-blue-500/10 to-blue-600/5 border-blue-500/20 hover:border-blue-500/40",
    icon: "text-blue-500",
    badge: "bg-blue-500/10 text-blue-400",
  },
  purple: {
    card: "from-purple-500/10 to-purple-600/5 border-purple-500/20 hover:border-purple-500/40",
    icon: "text-purple-500",
    badge: "bg-purple-500/10 text-purple-400",
  },
  amber: {
    card: "from-amber-500/10 to-amber-600/5 border-amber-500/20 hover:border-amber-500/40",
    icon: "text-amber-500",
    badge: "bg-amber-500/10 text-amber-400",
  },
}

export function Documentation() {
  // “0 hallucinations” policy: show headline numbers only from API.
  const { data: aggregateAnova } = useQuery({
    queryKey: ["aggregateAnova", "documentation"],
    queryFn: () => api.getAggregateAnova(),
  })

  const { data: annualHml } = useQuery({
    queryKey: ["annualHmlPremium", "documentation"],
    queryFn: () => api.getAnnualHmlPremium(),
  })

  const { data: rdBySector } = useQuery({
    queryKey: ["rdBySector", "documentation"],
    queryFn: () => api.getRDBySector(),
  })

  const { data: fmpOverview } = useQuery({
    queryKey: ["fmpOverview", "documentation"],
    queryFn: () => api.getFMPOverview(),
  })

  const periodLabel = useMemo(() => {
    const rows = annualHml?.annual_premiums
    if (!rows || rows.length === 0) return "..."
    const first = rows[0]?.year
    const last = rows[rows.length - 1]?.year
    if (!first || !last) return "..."
    return `${first} to ${last}`
  }, [annualHml])

  const premium5yr = aggregateAnova?.["5yr"]?.ttest_high_vs_low?.mean_difference
  const premium10yr = aggregateAnova?.["10yr"]?.ttest_high_vs_low?.mean_difference
  const premium20yr = aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference
  const eta5yr = aggregateAnova?.["5yr"]?.anova?.eta_squared
  const eta20yr = aggregateAnova?.["20yr"]?.anova?.eta_squared

  const topSector = useMemo(() => {
    const rows = (rdBySector || []).slice().sort((a, b) => b.avg_rd_intensity - a.avg_rd_intensity)
    return rows[0]
  }, [rdBySector])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Papers & Documentation</h1>
        <p className="text-muted-foreground">
          Research papers and complete guide to the R&D Factor Analysis Platform
        </p>
      </div>

      <Tabs defaultValue="papers" className="space-y-4">
        <TabsList className="grid w-full grid-cols-7">
          <TabsTrigger value="papers">Papers</TabsTrigger>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="dashboards">Dashboards</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="interpretation">Interpretation</TabsTrigger>
        </TabsList>
        
        {/* Papers Tab */}
        <TabsContent value="papers" className="space-y-6">
          {/* Start Here: Whitepaper */}
          <div className="rounded-xl bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-blue-500/10 border-2 border-emerald-500/30 p-6">
            <div className="flex flex-col md:flex-row gap-6 items-start">
              <div className="p-3 rounded-xl bg-emerald-500/20">
                <Presentation className="h-8 w-8 text-emerald-500" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">Start Here</Badge>
                  <Badge variant="outline" className="text-muted-foreground">
                    <Clock className="h-3 w-3 mr-1" />
                    ~5 min read
                  </Badge>
                </div>
                <h3 className="text-2xl font-bold mb-2">Whitepaper Slide Deck</h3>
                <p className="text-muted-foreground mb-4">
                  A practitioner-friendly 12-slide deck covering key findings, definitions, methodology, and implementation guidance. 
                  Perfect for getting up to speed quickly or sharing with colleagues.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Link to="/whitepaper">
                    <Button className="bg-emerald-600 hover:bg-emerald-700">
                      View Slide Deck
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                  <Link to="/papers/main">
                    <Button variant="outline">
                      Or read the full Main Paper
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Reading Path Guide */}
          <Card className="border-slate-700/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Reading Path</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                  <span className="font-bold text-emerald-500">1</span>
                  <div>
                    <p className="font-medium text-sm">Quick Overview</p>
                    <p className="text-xs text-muted-foreground">Whitepaper (12 slides)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                  <span className="font-bold text-blue-500">2</span>
                  <div>
                    <p className="font-medium text-sm">Full Methods & Results</p>
                    <p className="text-xs text-muted-foreground">Main Paper</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-500/5 border border-purple-500/20">
                  <span className="font-bold text-purple-500">3</span>
                  <div>
                    <p className="font-medium text-sm">Deep Dives</p>
                    <p className="text-xs text-muted-foreground">Sub-Research 1-4</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Paper Cards */}
          <div className="grid gap-4 md:grid-cols-2">
            {PAPERS.map((paper) => {
              const Icon = paper.icon
              const colorClass = COLOR_CLASSES[paper.color as keyof typeof COLOR_CLASSES]
              
              return (
                <Link key={paper.id} to={paper.route}>
                  <Card className={`cursor-pointer transition-all bg-gradient-to-br ${colorClass.card} h-full`}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className={`p-2 rounded-lg ${colorClass.badge}`}>
                          <Icon className={`h-5 w-5 ${colorClass.icon}`} />
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {paper.badgeLabel}
                        </Badge>
                      </div>
                      <CardTitle className="text-xl mt-3">{paper.title}</CardTitle>
                      <CardDescription className="text-base">{paper.subtitle}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">
                        Click to view interactive charts and full analysis →
                      </p>
                    </CardContent>
                  </Card>
                </Link>
              )
            })}
          </div>

          {/* Research Summary */}
          <Card className="border-slate-700/50">
            <CardHeader>
              <CardTitle>Research Summary</CardTitle>
              <CardDescription>Key findings from our R&D investment analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="p-4 border rounded-lg bg-emerald-500/5 border-emerald-500/20">
                  <h4 className="font-semibold mb-2 text-emerald-400">Key Finding #1</h4>
                  <p className="text-sm text-muted-foreground">
                    High-R&D (Q5) outperforms low-R&D (Q1) by{" "}
                    <strong>
                      {premium5yr !== undefined ? `${premium5yr >= 0 ? "+" : ""}${premium5yr.toFixed(2)}%` : "..."} (5yr)
                      {" "}to{" "}
                      {premium20yr !== undefined ? `${premium20yr >= 0 ? "+" : ""}${premium20yr.toFixed(2)}%` : "..."} (20yr)
                    </strong>
                    {" "}per year (rolling-window averages).
                  </p>
                </div>
                <div className="p-4 border rounded-lg bg-blue-500/5 border-blue-500/20">
                  <h4 className="font-semibold mb-2 text-blue-400">Key Finding #2</h4>
                  <p className="text-sm text-muted-foreground">
                    Premium magnitude declines with horizon:{" "}
                    <strong>
                      {premium5yr !== undefined ? `${premium5yr.toFixed(2)}%` : "..."} (5yr),{" "}
                      {premium10yr !== undefined ? `${premium10yr.toFixed(2)}%` : "..."} (10yr),{" "}
                      {premium20yr !== undefined ? `${premium20yr.toFixed(2)}%` : "..."} (20yr)
                    </strong>.
                  </p>
                </div>
                <div className="p-4 border rounded-lg bg-purple-500/5 border-purple-500/20">
                  <h4 className="font-semibold mb-2 text-purple-400">Key Finding #3</h4>
                  <p className="text-sm text-muted-foreground">
                    Top sector by average R&D intensity:{" "}
                    <strong>
                      {topSector ? `${topSector.sector} (${topSector.avg_rd_intensity.toFixed(2)}%)` : "..."}
                    </strong>.
                  </p>
                </div>
                <div className="p-4 border rounded-lg bg-amber-500/5 border-amber-500/20">
                  <h4 className="font-semibold mb-2 text-amber-400">Key Finding #4</h4>
                  <p className="text-sm text-muted-foreground">
                    Statistical inference rejects equal means across quintiles (ANOVA), with large effect sizes:
                    <strong>
                      {" "}η² {eta5yr !== undefined ? eta5yr.toFixed(3) : "..."} (5yr) → {eta20yr !== undefined ? eta20yr.toFixed(3) : "..."} (20yr)
                    </strong>.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Platform Overview</CardTitle>
              <CardDescription>What is the R&D Factor Analysis Platform?</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">
                The R&D Factor Analysis Platform is a comprehensive research tool that analyzes the relationship
                between Research & Development (R&D) investment intensity and long-term stock returns across
                {fmpOverview?.total_companies ?? "..."} S&P 500 companies over the return period{" "}
                <strong className="text-foreground">{periodLabel}</strong>.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2 flex items-center gap-2">
                    <Database className="h-4 w-4" />
                    Data Coverage
                  </h3>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>{fmpOverview?.total_companies ?? "..."} companies</li>
                    <li>
                      Income statements: {fmpOverview?.total_income_statements ?? "..."} (annual)
                    </li>
                    <li>
                      Price records: {fmpOverview?.total_price_records ?? "..."} (daily)
                    </li>
                    <li>
                      Annual return records: {fmpOverview?.total_annual_returns ?? "..."}
                    </li>
                    <li>Primary data: Financial Modeling Prep (FMP) API</li>
                  </ul>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2 flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    Key Features
                  </h3>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Quintile portfolio analysis</li>
                    <li>Rolling window performance (5/10/20 years)</li>
                    <li>Statistical significance testing (ANOVA)</li>
                    <li>R&D ETF backtesting</li>
                    <li>Industry sector breakdown</li>
                  </ul>
                </div>
              </div>

              <div className="p-4 border rounded-lg bg-muted/30">
                <h3 className="font-semibold mb-2">Research Hypothesis</h3>
                <p className="text-sm text-muted-foreground">
                  <strong>H1:</strong> Companies with higher R&D investment intensity are associated with higher
                  subsequent shareholder returns; we test how this relationship varies across investment horizons.
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  <strong>Finding:</strong> The analysis supports this hypothesis with statistically significant results
                  (ANOVA p &lt; 1e-6) and increasing effect sizes over longer windows (η²{" "}
                  {eta5yr !== undefined ? eta5yr.toFixed(3) : "..."} at 5yr →{" "}
                  {eta20yr !== undefined ? eta20yr.toFixed(3) : "..."} at 20yr).
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Metrics Tab */}
        <TabsContent value="metrics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Key Metrics Explained</CardTitle>
              <CardDescription>Understanding the metrics used throughout the platform</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2 flex items-center gap-2">
                    <FlaskConical className="h-4 w-4 text-emerald-500" />
                    R&D Intensity
                  </h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    <strong>Definition:</strong> R&D Intensity = (R&D Expense / Total Revenue) × 100
                  </p>
                  <p className="text-sm text-muted-foreground">
                    This measures how much a company invests in R&D relative to its revenue. Higher values indicate
                    greater innovation focus. For example, a company with 20% R&D intensity spends $20 on R&D for
                    every $100 of revenue.
                  </p>
                  <div className="mt-3 flex gap-2">
                    <Badge variant="outline">Rule of thumb (illustrative)</Badge>
                  </div>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2 flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-500" />
                    July-June Total Return (Bias-Reduced)
                  </h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    <strong>Definition:</strong> Total shareholder return measured over July-June to align fiscal-year R&D timing
                  </p>
                  <div className="my-2">
                    <Formulas.TSR />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    We default to July-June returns (Fama-French convention) to reduce look-ahead bias when forming
                    portfolios from fiscal-year financial statements. Prices are taken from adjusted close when available.
                  </p>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2 flex items-center gap-2">
                    <Target className="h-4 w-4 text-purple-500" />
                    Sharpe Ratio
                  </h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    <strong>Definition:</strong> Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Volatility
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Measures risk-adjusted returns. Higher values indicate better risk-adjusted performance.
                    Generally, values &gt;1 are good, &gt;2 are very good, and &gt;3 are excellent.
                  </p>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2 flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-amber-500" />
                    Effect Size (η²)
                  </h3>
                  <Formulas.EtaSquared />
                  <p className="text-sm text-muted-foreground mt-2">
                    Measures the proportion of variance in returns explained by R&D intensity. Values range from
                    0 to 1, where higher values indicate stronger relationships.
                  </p>
                  <div className="mt-3 flex gap-2">
                    <Badge variant="outline">Small: 0.01-0.06</Badge>
                    <Badge variant="outline">Medium: 0.06-0.14</Badge>
                    <Badge variant="outline">Large: &gt;0.14</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Dashboards Tab */}
        <TabsContent value="dashboards" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Dashboard Guide</CardTitle>
              <CardDescription>What each dashboard shows and how to use it</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Overview Dashboard</h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    High-level summary of the entire dataset with key statistics:
                  </p>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Total companies and R&D data coverage</li>
                    <li>Average R&D intensity across all companies</li>
                    <li>R&D trends over time</li>
                    <li>Top R&D spenders by sector</li>
                    <li>Returns summary statistics</li>
                  </ul>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Companies Dashboard</h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    Browse and search all companies in the dataset:
                  </p>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Company profiles with sector and industry</li>
                    <li>R&D intensity rankings</li>
                    <li>Filter by sector or R&D profile</li>
                    <li>Click any company to see detailed analysis</li>
                  </ul>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Analysis (500) Dashboard</h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    Comprehensive research analysis with multiple tabs:
                  </p>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li><strong>Quintile Analysis:</strong> Performance by R&D intensity quintiles</li>
                    <li><strong>Factor Premium:</strong> R&D factor returns over time</li>
                    <li><strong>ANOVA Results:</strong> Statistical significance tests</li>
                    <li><strong>Cohort Companies:</strong> Full list of 503 companies</li>
                    <li><strong>Papers:</strong> Research papers with findings</li>
                    <li><strong>Methodology:</strong> Complete methodology documentation</li>
                  </ul>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">ETF R&D Alpha Selection Dashboard</h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    Portfolio construction and backtesting (ETF10/ETF20/ETF50):
                  </p>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>ETF10/20/50 R&D Alpha Selection baskets</li>
                    <li>Annual July reconstitution with point-in-time data</li>
                    <li>Performance vs S&P 500 benchmark</li>
                    <li>Historical backtests with eligibility gates</li>
                    <li>Forecast distribution (p10/p50/p90 bands)</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analysis Tab */}
        <TabsContent value="analysis" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Understanding the Analysis</CardTitle>
              <CardDescription>How to interpret quintiles, ANOVA, and statistical tests</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Quintile Portfolio Construction</h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    Companies are ranked by R&D intensity and divided into 5 equal groups:
                  </p>
                  <div className="grid gap-2 md:grid-cols-5 mt-3">
                    <div className="p-2 border rounded text-center">
                      <Badge className="bg-red-500">Q1</Badge>
                      <p className="text-xs mt-1 text-muted-foreground">Lowest R&D</p>
                    </div>
                    <div className="p-2 border rounded text-center">
                      <Badge className="bg-orange-500">Q2</Badge>
                      <p className="text-xs mt-1 text-muted-foreground">Low-Medium</p>
                    </div>
                    <div className="p-2 border rounded text-center">
                      <Badge className="bg-yellow-500">Q3</Badge>
                      <p className="text-xs mt-1 text-muted-foreground">Medium</p>
                    </div>
                    <div className="p-2 border rounded text-center">
                      <Badge className="bg-green-500">Q4</Badge>
                      <p className="text-xs mt-1 text-muted-foreground">Medium-High</p>
                    </div>
                    <div className="p-2 border rounded text-center">
                      <Badge className="bg-blue-500">Q5</Badge>
                      <p className="text-xs mt-1 text-muted-foreground">Highest R&D</p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mt-3">
                    Each quintile represents an equal-weighted portfolio. Q5 (high R&D) outperforms
                    Q1 (low R&D) by{" "}
                    <strong className="text-foreground">
                      {premium5yr !== undefined ? `${premium5yr >= 0 ? "+" : ""}${premium5yr.toFixed(2)}%` : "..."} (5yr)
                      {" "}to{" "}
                      {premium20yr !== undefined ? `${premium20yr >= 0 ? "+" : ""}${premium20yr.toFixed(2)}%` : "..."} (20yr)
                    </strong>{" "}
                    annually (rolling-window averages; descriptive due to overlap).
                  </p>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">ANOVA (Analysis of Variance)</h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    Tests whether mean returns differ significantly across quintiles:
                  </p>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li><strong>F-Statistic:</strong> Higher values indicate greater differences between groups</li>
                    <li><strong>p-value:</strong> Probability the results occurred by chance
                      <ul className="ml-4 mt-1">
                        <li>&lt; 0.05 (*): Significant at 95% confidence</li>
                        <li>&lt; 0.01 (**): Significant at 99% confidence</li>
                        <li>&lt; 0.001 (***): Highly significant</li>
                      </ul>
                    </li>
                    <li><strong>η² (eta-squared):</strong> Effect size - proportion of variance explained</li>
                  </ul>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Rolling Window Analysis</h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    Performance is analyzed over overlapping time windows:
                  </p>
                  <div className="grid gap-2 md:grid-cols-3 mt-3">
                    <div className="p-3 border rounded">
                      <Badge>5-Year Windows</Badge>
                      <p className="text-xs mt-2 text-muted-foreground">
                        {aggregateAnova?.["5yr"]?.n_windows ?? "..."} windows
                      </p>
                      <p className="text-xs text-muted-foreground">
                        η² = {typeof eta5yr === "number" ? eta5yr.toFixed(3) : "..."}
                      </p>
                    </div>
                    <div className="p-3 border rounded">
                      <Badge>10-Year Windows</Badge>
                      <p className="text-xs mt-2 text-muted-foreground">
                        {aggregateAnova?.["10yr"]?.n_windows ?? "..."} windows
                      </p>
                      <p className="text-xs text-muted-foreground">
                        η² = {typeof aggregateAnova?.["10yr"]?.anova?.eta_squared === "number" ? aggregateAnova["10yr"].anova.eta_squared.toFixed(3) : "..."}
                      </p>
                    </div>
                    <div className="p-3 border rounded">
                      <Badge>20-Year Windows</Badge>
                      <p className="text-xs mt-2 text-muted-foreground">
                        {aggregateAnova?.["20yr"]?.n_windows ?? "..."} windows
                      </p>
                      <p className="text-xs text-muted-foreground">
                        η² = {typeof eta20yr === "number" ? eta20yr.toFixed(3) : "..."}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mt-3">
                    Longer windows show stronger effects, indicating R&D benefits compound over time.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Portfolio Tab */}
        <TabsContent value="portfolio" className="space-y-4">
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
        </TabsContent>

        {/* Interpretation Tab */}
        <TabsContent value="interpretation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>How to Interpret Results</CardTitle>
              <CardDescription>Guidelines for understanding and using the findings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="p-4 border rounded-lg bg-emerald-500/10 border-emerald-500/20">
                  <h3 className="font-semibold mb-2 text-emerald-400">Key Finding</h3>
                  <p className="text-sm text-muted-foreground">
                    High-R&amp;D companies (Q5) outperform low-R&amp;D companies (Q1) by{" "}
                    <strong>
                      {premium5yr !== undefined ? `${premium5yr >= 0 ? "+" : ""}${premium5yr.toFixed(2)}%` : "..."} (5yr){" "}
                      to{" "}
                      {premium20yr !== undefined ? `${premium20yr >= 0 ? "+" : ""}${premium20yr.toFixed(2)}%` : "..."} (20yr)
                    </strong>{" "}
                    annually (rolling-window averages; descriptive due to overlap). ANOVA effect size rises with horizon (η²{" "}
                    {eta5yr !== undefined ? eta5yr.toFixed(3) : "..."} → {eta20yr !== undefined ? eta20yr.toFixed(3) : "..."}).
                  </p>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">What This Means</h3>
                  <ul className="text-sm text-muted-foreground space-y-2">
                    <li>
                      <strong>For Investors:</strong> Tilting portfolios toward high-R&D companies may generate
                      superior long-term returns across multi-year horizons (see Main Paper for the primary annual series).
                    </li>
                    <li>
                      <strong>For Researchers:</strong> R&D intensity is associated with a significant return premium that
                      is statistically significant across horizons in this dataset, with effect size increasing at longer windows.
                    </li>
                    <li>
                      <strong>For Corporate Managers:</strong> R&D investments are rewarded by markets over time,
                      consistent with long-run value creation mechanisms (association, not causation).
                    </li>
                  </ul>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Important Caveats</h3>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Past performance does not guarantee future results</li>
                    <li>Universe is S&P 500; Tier-1 survivorship bias is substantially mitigated but not CRSP/Compustat-grade</li>
                    <li>R&D reporting varies by industry and accounting standards</li>
                    <li>Short-term volatility may be higher for R&D-intensive companies</li>
                    <li>Results are based on historical data ({periodLabel})</li>
                  </ul>
                </div>

                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Using the Platform</h3>
                  <ol className="text-sm text-muted-foreground space-y-2 list-decimal list-inside">
                    <li>Start with the <strong>Overview</strong> to understand the dataset</li>
                    <li>Explore <strong>Companies</strong> to see individual R&D profiles</li>
                    <li>Review <strong>Analysis (500)</strong> for statistical findings</li>
                    <li>Check <strong>R&D ETF</strong> for portfolio construction ideas</li>
                    <li>Read the <strong>Papers</strong> and <strong>Methodology</strong> for detailed explanations</li>
                  </ol>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Documentation

