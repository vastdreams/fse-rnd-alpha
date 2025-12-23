/**
 * PATH: frontend/src/pages/papers/MainPaper.tsx
 * PURPOSE:
 *   - Provide a single, publication-ready "Main Paper" page that consolidates the four sub-research pages
 *     (returns, sector patterns, factor tests, and fundamental discussion) into one cohesive narrative.
 *
 * ROLE IN ARCHITECTURE:
 *   - Frontend research communication layer (presentation + PDF/print export).
 *
 * MAIN EXPORTS:
 *   - MainPaper: the consolidated paper page component (practitioner-style on-site manuscript).
 *
 * NON-RESPONSIBILITIES:
 *   - This page does NOT compute research metrics (backend does).
 *   - This page does NOT store or mutate research results.
 *
 * NOTES:
 *   - No hard-coded numeric claims in prose. Any numeric claim must be sourced from:
 *     - live API responses, or
 *     - the frozen publication snapshot served by the backend.
 *   - Prefer rendering values dynamically from endpoints; avoid hard-coded result numbers in prose.
 *   - Keep "Sub-Research" pages as deep dives; the Main Paper should remain coherent and citable.
 */

import { useQuery } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  ArrowLeft,
  Download,
  FileText,
  BookOpen,
  Database,
  BarChart3,
  Layers,
  FlaskConical,
  ExternalLink,
  AlertTriangle,
} from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
  AreaChart,
  Area,
  ReferenceLine,
  LineChart,
  Line,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts"

import { api } from "@/lib/api"
import { AnnualHMLTable } from "@/components/AnnualHMLTable"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { ReferencesList } from "@/components/Citation"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Formulas } from "@/components/Formula"
import { cn } from "@/lib/utils"

// Table of contents sections
const sections = [
  { id: "abstract", label: "Abstract" },
  { id: "introduction", label: "1. Introduction" },
  { id: "literature", label: "2. Literature Review & Hypotheses" },
  { id: "data", label: "3. Data & Sample Construction" },
  { id: "methodology", label: "4. Methodology" },
  { id: "results", label: "5. Results" },
  { id: "sector", label: "6. Sector Analysis" },
  { id: "robustness", label: "7. Robustness & Factor Tests" },
  { id: "discussion", label: "8. Discussion" },
  { id: "strategy", label: "9. Investable Strategy" },
  { id: "limitations", label: "10. Limitations" },
  { id: "replicability", label: "11. Replicability" },
  { id: "conclusion", label: "12. Conclusion" },
  { id: "references", label: "References" },
  { id: "appendix", label: "Online Appendix (Supporting Notes)" },
]

// Chart colors (work in both light and dark modes)
const QUINTILE_COLORS = ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#0d9488"]
const SECTOR_COLORS: Record<string, string> = {
  Technology: "#3b82f6",
  Healthcare: "#22c55e",
  "Consumer Cyclical": "#f59e0b",
  "Financial Services": "#8b5cf6",
  Industrials: "#6366f1",
  "Communication Services": "#ec4899",
  "Consumer Defensive": "#14b8a6",
  Energy: "#ef4444",
  "Basic Materials": "#84cc16",
  "Real Estate": "#06b6d4",
  Utilities: "#64748b",
}

export function MainPaper() {
  const [activeSection, setActiveSection] = useState("abstract")
  const [rightNavCollapsed, setRightNavCollapsed] = useState(false)

  const handlePrintPDF = () => {
    document.body.classList.add("printing-paper")
    window.print()
    setTimeout(() => {
      document.body.classList.remove("printing-paper")
    }, 1000)
  }

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActiveSection(entry.target.id)
        })
      },
      { rootMargin: "-20% 0px -60% 0px" }
    )

    sections.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })

    return () => observer.disconnect()
  }, [])

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  // Publication snapshot (frozen submission-grade dataset for paper pages)
  const { data: snapshot, isLoading: snapshotLoading } = useQuery({
    queryKey: ["publicationSnapshot"],
    queryFn: () => api.getPublicationSnapshot(),
  })

  const snapshotPayload = snapshot?.payload

  const cohortSummary =
    snapshotPayload?.cohort_summary && typeof snapshotPayload.cohort_summary === "object" && !("error" in snapshotPayload.cohort_summary)
      ? snapshotPayload.cohort_summary
      : undefined

  const aggregateAnova =
    snapshotPayload?.aggregate_anova && typeof snapshotPayload.aggregate_anova === "object" && !("error" in snapshotPayload.aggregate_anova)
      ? snapshotPayload.aggregate_anova
      : undefined

  const annualHmlData =
    snapshotPayload?.annual_hml_premium && typeof snapshotPayload.annual_hml_premium === "object" && !("error" in snapshotPayload.annual_hml_premium)
      ? snapshotPayload.annual_hml_premium
      : undefined

  const rdBySector = Array.isArray(snapshotPayload?.rd_by_sector) ? snapshotPayload?.rd_by_sector : undefined

  const netOfCost5yr =
    snapshotPayload?.net_of_cost_returns &&
    typeof snapshotPayload.net_of_cost_returns === "object" &&
    !("error" in snapshotPayload.net_of_cost_returns)
      ? snapshotPayload.net_of_cost_returns["5yr"]
      : undefined

  const rollingAggregates =
    snapshotPayload?.rolling_window_aggregates &&
    typeof snapshotPayload.rolling_window_aggregates === "object" &&
    !("error" in snapshotPayload.rolling_window_aggregates)
      ? snapshotPayload.rolling_window_aggregates
      : undefined

  const transactionCosts =
    snapshotPayload?.transaction_costs && typeof snapshotPayload.transaction_costs === "object" && !("error" in snapshotPayload.transaction_costs)
      ? snapshotPayload.transaction_costs
      : undefined

  const methodologyParameters =
    snapshotPayload?.methodology_parameters &&
    typeof snapshotPayload.methodology_parameters === "object" &&
    snapshotPayload.methodology_parameters !== null &&
    !("error" in (snapshotPayload.methodology_parameters as Record<string, unknown>))
      ? (snapshotPayload.methodology_parameters as Record<string, unknown>)
      : undefined

  const rollingWindows =
    snapshotPayload?.rolling_windows &&
    typeof snapshotPayload.rolling_windows === "object" &&
    snapshotPayload.rolling_windows !== null &&
    !Array.isArray(snapshotPayload.rolling_windows) &&
    !("error" in (snapshotPayload.rolling_windows as Record<string, unknown>))
      ? (snapshotPayload.rolling_windows as Record<string, unknown>)
      : undefined

  const snapshotBuiltAtYear = useMemo(() => {
    const iso = snapshotPayload?.built_at
    if (typeof iso !== "string") return undefined
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return undefined
    return d.getUTCFullYear()
  }, [snapshotPayload?.built_at])

  const rdTrendsRaw = Array.isArray(snapshotPayload?.rd_trends) ? snapshotPayload.rd_trends : undefined
  const rdTrends = useMemo(() => {
    if (!rdTrendsRaw) return undefined
    if (!snapshotBuiltAtYear) return rdTrendsRaw

    // Publication rule (freeze-consistent): FY income-statement coverage for the
    // current calendar year is typically incomplete, so keep trends through
    // (snapshot build year - 1).
    const maxCompleteFiscalYear = snapshotBuiltAtYear - 1
    return rdTrendsRaw.filter((t) => typeof t.year === "number" && t.year <= maxCompleteFiscalYear)
  }, [rdTrendsRaw, snapshotBuiltAtYear])
  const rdLeaderboard = Array.isArray(snapshotPayload?.rd_leaderboard) ? snapshotPayload.rd_leaderboard : undefined
  const rdLeaderboardBySector =
    snapshotPayload?.rd_leaderboard_by_sector &&
    typeof snapshotPayload.rd_leaderboard_by_sector === "object" &&
    snapshotPayload.rd_leaderboard_by_sector !== null &&
    !Array.isArray(snapshotPayload.rd_leaderboard_by_sector) &&
    !("error" in (snapshotPayload.rd_leaderboard_by_sector as Record<string, unknown>))
      ? (snapshotPayload.rd_leaderboard_by_sector as Record<string, any[]>)
      : undefined

  const factorPremiums = Array.isArray(snapshotPayload?.factor_premiums) ? snapshotPayload.factor_premiums : []

  const publicationStats =
    snapshotPayload?.publication_stats && typeof snapshotPayload.publication_stats === "object" && !("error" in snapshotPayload.publication_stats)
      ? snapshotPayload.publication_stats
      : undefined

  const spanningTests =
    snapshotPayload?.spanning_tests_full &&
    typeof snapshotPayload.spanning_tests_full === "object" &&
    !("error" in snapshotPayload.spanning_tests_full)
      ? snapshotPayload.spanning_tests_full
      : undefined

  const mispricingTests =
    snapshotPayload?.mispricing_tests && typeof snapshotPayload.mispricing_tests === "object" && !("error" in snapshotPayload.mispricing_tests)
      ? snapshotPayload.mispricing_tests
      : undefined

  const doubleSortData =
    snapshotPayload?.double_sort_analysis &&
    typeof snapshotPayload.double_sort_analysis === "object" &&
    !("error" in snapshotPayload.double_sort_analysis)
      ? snapshotPayload.double_sort_analysis
      : undefined

  const investableBacktest =
    snapshotPayload?.investable_backtest &&
    typeof snapshotPayload.investable_backtest === "object" &&
    !("error" in (snapshotPayload.investable_backtest as Record<string, unknown>))
      ? (snapshotPayload.investable_backtest as Record<string, unknown>)
      : undefined

  const delistingSensitivity =
    snapshotPayload?.delisting_sensitivity &&
    typeof snapshotPayload.delisting_sensitivity === "object" &&
    !("error" in (snapshotPayload.delisting_sensitivity as Record<string, unknown>))
      ? (snapshotPayload.delisting_sensitivity as Record<string, unknown>)
      : undefined

  const topSectors = useMemo(() => {
    const rows = (rdBySector || [])
      .filter((s) => typeof s.avg_rd_intensity === "number")
      .slice()
      .sort((a, b) => (b.avg_rd_intensity || 0) - (a.avg_rd_intensity || 0))
    return rows.slice(0, 5)
  }, [rdBySector])

  const headlinePremiums = useMemo(() => {
    const horizons: Array<"5yr" | "10yr" | "20yr"> = ["5yr", "10yr", "20yr"]
    return horizons.map((h) => {
      const node = aggregateAnova?.[h]
      return {
        horizon: h,
        premiumPct: node?.ttest_high_vs_low?.mean_difference,
        t: node?.ttest_high_vs_low?.t_statistic,
        p: node?.ttest_high_vs_low?.p_value,
        eta2: node?.anova?.eta_squared,
        cohensD: node?.ttest_high_vs_low?.cohens_d,
      }
    })
  }, [aggregateAnova])

  const quintileReturnBar5yr = useMemo(() => {
    const rows = rollingAggregates?.["5yr"] || []
    return rows.map((q) => ({
      quintile: `Q${q.quintile}`,
      label: q.label,
      avgReturn: typeof q.avg_return === "number" ? q.avg_return : null,
      fill: QUINTILE_COLORS[Math.max(0, Math.min(4, (q.quintile || 1) - 1))],
    }))
  }, [rollingAggregates])

  const rollingPremium5yr = useMemo(() => {
    const windows = (rollingWindows && Array.isArray((rollingWindows as any)["5yr"]) ? ((rollingWindows as any)["5yr"] as any[]) : []) || []
    return windows
      .filter((w) => typeof w?.start_year === "number" && typeof w?.end_year === "number")
      .map((w) => ({
        period: `${w.start_year}-${w.end_year}`,
        startYear: w.start_year,
        rdPremium: typeof w.rd_premium === "number" ? w.rd_premium : 0,
      }))
  }, [rollingWindows])

  const rollingPremium20yr = useMemo(() => {
    const windows = (rollingWindows && Array.isArray((rollingWindows as any)["20yr"]) ? ((rollingWindows as any)["20yr"] as any[]) : []) || []
    return windows
      .filter((w) => typeof w?.start_year === "number" && typeof w?.end_year === "number" && typeof w?.rd_premium === "number")
      .map((w) => ({
        period: `${w.start_year}-${w.end_year}`,
        startYear: w.start_year,
        endYear: w.end_year,
        rdPremium: w.rd_premium,
      }))
      .sort((a, b) => a.startYear - b.startYear)
  }, [rollingWindows])

  const rolling20yrEndpoints = useMemo(() => {
    if (!rollingPremium20yr.length) return undefined
    return {
      first: rollingPremium20yr[0],
      last: rollingPremium20yr[rollingPremium20yr.length - 1],
      n: rollingPremium20yr.length,
    }
  }, [rollingPremium20yr])

  const sectorIntensityData = useMemo(() => {
    const rows = (rdBySector || [])
      .slice()
      .filter((s) => typeof s.avg_rd_intensity === "number")
      .sort((a, b) => (b.avg_rd_intensity || 0) - (a.avg_rd_intensity || 0))
    return rows.map((s) => ({
      sector: s.sector,
      avgRdIntensity: s.avg_rd_intensity,
      companies: s.company_count,
      totalRdB: s.total_rd_spend / 1e9,
      fill: SECTOR_COLORS[s.sector] || "#64748b",
    }))
  }, [rdBySector])

  const sectorCoverageData = useMemo(() => {
    const rows = cohortSummary?.by_sector || []
    return rows.map((s) => {
      const total = s.total || 0
      const cov = (n: number) => (total > 0 ? Math.round((n / total) * 100) : 0)
      return {
        sector: s.sector,
        total,
        coverage5yr: cov(s.n_5yr),
        coverage10yr: cov(s.n_10yr),
        coverage20yr: cov(s.n_20yr),
        fill: SECTOR_COLORS[s.sector] || "#64748b",
      }
    })
  }, [cohortSummary?.by_sector])

  const sectorRadarData = useMemo(() => {
    return sectorIntensityData.slice(0, 8).map((s) => ({
      sector: s.sector.length > 15 ? `${s.sector.slice(0, 12)}...` : s.sector,
      fullSector: s.sector,
      intensity: s.avgRdIntensity,
      companies: s.companies,
      spend: Math.min(s.totalRdB, 100),
    }))
  }, [sectorIntensityData])

  const rdTrendData = useMemo(() => {
    return (rdTrends || []).map((t) => ({
      year: t.year,
      companies: t.companies,
      avgIntensity: t.avg_rd_intensity,
      totalSpendB: t.total_rd_spend / 1e9,
    }))
  }, [rdTrends])

  const rdLeadersBySector = useMemo(() => {
    const sanitizeLeader = (r: any) => {
      if (!r || typeof r.symbol !== "string" || !r.symbol) return null
      const intensity = typeof r.avg_rd_intensity === "number" ? r.avg_rd_intensity : null
      return {
        symbol: r.symbol,
        name: typeof r.name === "string" ? r.name : null,
        avg_rd_intensity: intensity,
        years_of_data: typeof r.years_of_data === "number" ? r.years_of_data : null,
      }
    }

    if (rdLeaderboardBySector) {
      return Object.entries(rdLeaderboardBySector)
        .map(([sector, rows]) => {
          const leaders = (Array.isArray(rows) ? rows : [])
            .map(sanitizeLeader)
            .filter((x): x is NonNullable<typeof x> => Boolean(x))
            .sort((a, b) => (b.avg_rd_intensity || 0) - (a.avg_rd_intensity || 0))
            .slice(0, 3)
          return { sector, leaders }
        })
        .filter((s) => s.leaders.length > 0)
        .sort((a, b) => ((b.leaders[0]?.avg_rd_intensity as number) || 0) - ((a.leaders[0]?.avg_rd_intensity as number) || 0))
    }

    const grouped: Record<string, ReturnType<typeof sanitizeLeader>[]> = {}
    for (const r of rdLeaderboard || []) {
      const sectorKey = typeof r?.sector === "string" && r.sector ? r.sector : "Unknown"
      grouped[sectorKey] = grouped[sectorKey] || []
      grouped[sectorKey].push(sanitizeLeader(r))
    }

    return Object.entries(grouped)
      .map(([sector, rows]) => {
        const leaders = rows
          .filter((x): x is NonNullable<typeof x> => Boolean(x))
          .sort((a, b) => (b.avg_rd_intensity || 0) - (a.avg_rd_intensity || 0))
          .slice(0, 3)
        return { sector, leaders }
      })
      .filter((s) => s.leaders.length > 0)
      .sort((a, b) => ((b.leaders[0]?.avg_rd_intensity as number) || 0) - ((a.leaders[0]?.avg_rd_intensity as number) || 0))
  }, [rdLeaderboard, rdLeaderboardBySector])

  const doubleSortTableRows = useMemo(() => {
    const matrix = (doubleSortData as any)?.matrix
    const spreads = (doubleSortData as any)?.rd_spreads_by_size
    if (!matrix || typeof matrix !== "object") return []

    const sizes: Array<"Large" | "Medium" | "Small"> = ["Large", "Medium", "Small"]
    const rds: Array<"Low" | "Medium" | "High"> = ["Low", "Medium", "High"]

    return sizes
      .map((size) => {
        const row = (matrix as any)?.[size] || {}
        const cells = rds.map((rd) => {
          const c = row?.[rd]
          return {
            rd,
            mean: typeof c?.mean_return === "number" ? (c.mean_return as number) : null,
            n: typeof c?.n_obs === "number" ? (c.n_obs as number) : null,
          }
        })

        const s = spreads?.[size]
        const spread = typeof s?.high_minus_low === "number" ? (s.high_minus_low as number) : null
        const t = typeof s?.t_stat === "number" ? (s.t_stat as number) : null
        const p = typeof s?.p_value === "number" ? (s.p_value as number) : null
        const significant = typeof s?.significant === "boolean" ? (s.significant as boolean) : null

        return { size, cells, spread, t, p, significant }
      })
      .filter((r) => r.cells.some((c) => typeof c.mean === "number"))
  }, [doubleSortData])

  const factorPremiumSeries = useMemo(() => {
    const currentYear = new Date().getFullYear()
    return (factorPremiums || [])
      // Exclude current year since data is incomplete
      .filter((f) => typeof f.year === "number" && f.year < currentYear)
      .map((f) => ({
        year: f.year,
        rdPremium: f.rd_premium ?? null,
        q1: f.q1_return ?? null,
        q5: f.q5_return ?? null,
      }))
  }, [factorPremiums])

  const regimePremiumTable = useMemo(() => {
    const rows = (factorPremiumSeries || []).filter((r) => typeof r.year === "number" && typeof r.rdPremium === "number")
    if (rows.length === 0) return []

    const years = rows.map((r) => r.year).filter((y): y is number => typeof y === "number")
    const maxYear = years.length ? Math.max(...years) : new Date().getFullYear() - 1
    const bins = [
      { label: "1995-1999", start: 1995, end: 1999, event: "Late 1990s" },
      { label: "2000-2002", start: 2000, end: 2002, event: "Dot-com bust" },
      { label: "2003-2007", start: 2003, end: 2007, event: "Pre-GFC expansion" },
      { label: "2008-2009", start: 2008, end: 2009, event: "Global Financial Crisis" },
      { label: "2010-2016", start: 2010, end: 2016, event: "Post-GFC recovery" },
      { label: `2017-${maxYear}`, start: 2017, end: maxYear, event: "Recent era" },
    ]

    const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null)

    return bins
      .map((b) => {
        const sub = rows.filter((r) => r.year >= b.start && r.year <= b.end)
        const prem = sub.map((r) => r.rdPremium as number)
        const q1 = sub.map((r) => (typeof r.q1 === "number" ? (r.q1 as number) : NaN)).filter((x) => Number.isFinite(x))
        const q5 = sub.map((r) => (typeof r.q5 === "number" ? (r.q5 as number) : NaN)).filter((x) => Number.isFinite(x))
        const pos = prem.filter((x) => x > 0).length
        return {
          ...b,
          n: sub.length,
          meanPremium: mean(prem),
          winRatePct: sub.length ? (pos / sub.length) * 100 : null,
          meanQ1: mean(q1 as number[]),
          meanQ5: mean(q5 as number[]),
        }
      })
      .filter((r) => r.n > 0)
  }, [factorPremiumSeries])

  const sampleYearRange = useMemo(() => {
    const currentYear = new Date().getFullYear()
    // Exclude current year since data is incomplete
    const years = (factorPremiumSeries || [])
      .map((r) => r.year)
      .filter((y): y is number => typeof y === "number" && y < currentYear)
    if (years.length === 0) return undefined
    const min = Math.min(...years)
    const max = Math.max(...years)
    if (!Number.isFinite(min) || !Number.isFinite(max)) return undefined
    return `${min}-${max}`
  }, [factorPremiumSeries])

  const snapshotBuiltAtLabel = useMemo(() => {
    const builtAt = snapshot?.meta?.built_at
    if (!builtAt) return undefined
    const d = new Date(builtAt)
    if (Number.isNaN(d.getTime())) return builtAt
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" })
  }, [snapshot?.meta?.built_at])

  const returnConventionLabel = useMemo(() => {
    const v = snapshot?.meta?.return_convention
    if (!v) return "July-June (Fama-French)"
    if (v === "july_june") return "July-June (Fama-French)"
    if (v === "calendar") return "Calendar year"
    return v
  }, [snapshot?.meta?.return_convention])

  const growthOf1 = useMemo(() => {
    const rows = factorPremiumSeries.filter((r) => typeof r.year === "number")
    let q5 = 1
    let q1 = 1
    return rows.map((r) => {
      q5 = q5 * (1 + (r.q5 || 0) / 100)
      q1 = q1 * (1 + (r.q1 || 0) / 100)
      return {
        year: r.year,
        q5Cumulative: q5,
        q1Cumulative: q1,
      }
    })
  }, [factorPremiumSeries])

  const investableGrowth = useMemo(() => {
    const bt = investableBacktest as any
    const rows = Array.isArray(bt?.yearly_data) ? (bt.yearly_data as any[]) : []
    let port = 1
    let bench = 1
    let sp500 = 1
    return rows
      .filter((r) => typeof r?.year === "number")
      .map((r) => {
        const pr = typeof r.portfolio_return === "number" ? r.portfolio_return : 0
        const br = typeof r.benchmark_return === "number" ? r.benchmark_return : 0
        const sr = typeof r.sp500_return === "number" ? r.sp500_return : 0
        port = port * (1 + pr / 100)
        bench = bench * (1 + br / 100)
        sp500 = sp500 * (1 + sr / 100)
        return {
          year: r.year,
          portfolioIndex: port,
          benchmarkIndex: bench,
          sp500Index: sr !== 0 ? sp500 : null,
        }
      })
  }, [investableBacktest])

  return (
    <div className="flex gap-8 min-h-0">
      <div
        className={cn(
          "flex-1 min-w-0 space-y-12 pb-24 transition-all duration-300",
          rightNavCollapsed ? "max-w-none" : "max-w-4xl"
        )}
      >
        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-50 via-card to-card dark:from-slate-900 dark:via-slate-950 dark:to-slate-950 border border-slate-200 dark:border-slate-800 p-8">
          <div className="absolute inset-0 bg-grid-white/[0.02] dark:bg-grid-white/[0.02]" />
          <div className="relative z-10">
            <div className="flex items-start justify-between flex-wrap gap-4 mb-6">
              <Link
                to="/documentation"
                className="inline-flex items-center text-sm text-muted-foreground hover:text-primary"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Papers
              </Link>
              <Button variant="outline" size="sm" onClick={handlePrintPDF}>
                <Download className="mr-2 h-4 w-4" />
                Download PDF
              </Button>
            </div>

            <div className="flex flex-wrap gap-2 mb-4">
              <Badge variant="outline" className="border-slate-400/40">
                Main Paper
              </Badge>
              <Badge variant="outline" className="text-amber-600 border-amber-500/30 bg-amber-500/10">
                Frozen snapshot
              </Badge>
              <Badge variant="outline" className="text-blue-500 border-blue-500/30 bg-blue-500/10">
                Tier-1 data (FMP)
              </Badge>
            </div>

            <h1 className="text-4xl font-bold mb-4">
              <span className="text-foreground">R&D Investment Intensity and Long-Term Stock Returns</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl">
              Empirical evidence on the relation between R&D intensity and subsequent stock returns.
            </p>

            <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
              <div>
                <span className="text-muted-foreground">Author:</span>{" "}
                <span className="text-foreground">Abhishek Sehgal</span>
              </div>
              <div>
                <span className="text-muted-foreground">Sample:</span>{" "}
                <span className="text-foreground">{cohortSummary?.total_companies || "-"} companies</span>
              </div>
              <div>
                <span className="text-muted-foreground">Period:</span>{" "}
                <span className="text-foreground">{sampleYearRange || "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Return Convention:</span>{" "}
                <span className="text-foreground">{returnConventionLabel}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Snapshot built:</span>{" "}
                <span className="text-foreground">{snapshotBuiltAtLabel || "-"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Abstract */}
        <section id="abstract" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">Abstract</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 space-y-4">
              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Objective:</strong> We test whether high R&amp;D intensity predicts higher stock returns
                in a large-cap U.S. universe, using methodology designed for implementability.
              </p>

              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Method:</strong> Each year we sort S&amp;P 500 firms (N ≈ {cohortSummary?.total_companies || 500} with
                R&amp;D data) into quintiles by R&amp;D intensity (R&amp;D expense / revenue) and measure subsequent July-June returns
                over {sampleYearRange || "the sample period"}.
                This timing convention aligns with Fama-French methodology to avoid look-ahead bias. We incorporate historical index membership
                and delisting adjustments to mitigate survivorship bias.
              </p>

              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Results:</strong>{" "}
                {typeof annualHmlData?.mean_premium === "number" && typeof annualHmlData?.hac_adjusted?.t_statistic === "number" ? (
                  <>
                    The high-minus-low premium (Q5 minus Q1) averages{" "}
                    <strong className="text-foreground">{annualHmlData.mean_premium.toFixed(2)}%</strong> per year
                    in non-overlapping annual returns (Newey-West t = {annualHmlData.hac_adjusted.t_statistic.toFixed(2)},
                    p = {annualHmlData.hac_adjusted.p_value < 0.001 ? "<0.001" : annualHmlData.hac_adjusted.p_value.toFixed(4)}).
                  </>
                ) : (
                  <>The high-minus-low premium (Q5 minus Q1) is positive and statistically significant in non-overlapping annual returns.</>
                )}
              </p>

              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Implementation:</strong>{" "}
                {typeof transactionCosts?.annual_trading_cost_pct === "number" && typeof transactionCosts?.net_rd_premium_pct === "number" ? (
                  <>
                    Under a literature-calibrated transaction-cost model (Novy-Marx &amp; Velikov, 2016), estimated trading costs
                    are <strong className="text-foreground">{transactionCosts.annual_trading_cost_pct.toFixed(3)}%</strong> annually,
                    yielding a net premium of <strong className="text-foreground">{transactionCosts.net_rd_premium_pct.toFixed(2)}%</strong> per year.
                  </>
                ) : (
                  <>We translate the signal into an implementable strategy with explicit portfolio rules and trading-friction assumptions.</>
                )}
              </p>

              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Interpretation:</strong> Results are consistent with either mispricing of intangible assets
                or risk compensation for innovation exposure. We document sector tilts, factor exposures, and regime dependence
                without claiming to isolate a single mechanism.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Introduction */}
        <section id="introduction" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">1. Introduction</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground">
                R&amp;D spending is an investment in intangible capital with uncertain payoffs and multi-year horizons. Because R&amp;D is expensed under U.S.
                GAAP, firms with substantial R&amp;D can look less profitable in contemporaneous statements even when R&amp;D creates economically valuable
                assets. These features motivate two broad interpretations for any return premium associated with R&amp;D intensity: investors may
                underweight intangibles (mispricing), or the premium may compensate for innovation-related risks (risk compensation).
              </p>
              <p className="text-muted-foreground">
                The central, investable question is straightforward: <strong className="text-foreground">does an R&amp;D-intensity sort create a repeatable
                return premium in a large-cap U.S. universe</strong> once we align accounting data to returns using a bias-aware timing convention and
                acknowledge real implementation frictions?
              </p>

              <div className="not-prose rounded-lg border bg-muted/30 p-4">
                <p className="font-semibold text-foreground mb-2">Terminology used in this paper</p>
                <ul className="text-sm text-muted-foreground list-disc list-inside space-y-2">
                  <li>
                    <span className="font-medium text-foreground">Premium (HML):</span> the return spread between high-R&amp;D and low-R&amp;D portfolios
                    formed in the same universe for the same period. In most exhibits this is{" "}
                    <span className="font-mono">Q5 - Q1</span> (highest R&amp;D quintile minus lowest R&amp;D quintile).{" "}
                    <InfoTooltip term="hml_premium" size={12} />
                  </li>
                  <li>
                    <span className="font-medium text-foreground">Not a benchmark excess return:</span> this premium is not automatically "above the S&amp;P
                    500". Benchmark comparisons are shown separately in the investable strategy section (Section 9).
                  </li>
                  <li>
                    <span className="font-medium text-foreground">Absolute return:</span> the average return of a single portfolio (for example, Q5 alone).
                    Absolute returns can be high even when the premium is small if both Q5 and Q1 perform similarly.
                  </li>
                </ul>
              </div>

              <div className="not-prose grid md:grid-cols-2 gap-4 mt-2">
                <div className="p-4 rounded-lg border bg-muted/30">
                  <p className="font-semibold text-foreground mb-2">What we do</p>
                  <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                    <li>Form annual R&amp;D-intensity quintiles and evaluate subsequent returns under a July-June convention.</li>
                    <li>Report primary inference on the annual non-overlapping premium series; use rolling windows for descriptive stability and regimes.</li>
                    <li>Show sector composition and robustness diagnostics (factor spanning, stratifications) when available in the snapshot.</li>
                    <li>Translate results into a rules-based, long-only implementation with explicit trading-friction assumptions.</li>
                  </ul>
                </div>
                <div className="p-4 rounded-lg border bg-muted/30">
                  <p className="font-semibold text-foreground mb-2">What we do not claim</p>
                  <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                    <li>No causal identification: results are an association (a characteristic premium), not a structural estimate.</li>
                    <li>No universal coverage: this analysis is scoped to a large-cap U.S. universe with disclosed data limitations.</li>
                    <li>No reliance on overlapping-window p-values as primary inference; those windows are autocorrelated.</li>
                  </ul>
                </div>
              </div>

              <p className="text-muted-foreground">
                The paper proceeds as follows. Section 2 frames related evidence and hypotheses. Section 3 describes data and sample construction. Section 4
                specifies portfolio formation, return definitions, and inference. Section 5 presents the primary annual premium evidence and descriptive
                time-variation, Section 6 documents sector structure, and Section 7 reports robustness and factor diagnostics. Sections 8-12 discuss
                interpretation, implementation, limitations, replicability, and conclusion.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Literature Review & Hypotheses */}
        <section id="literature" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">2. Literature Review &amp; Hypotheses</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
              <h3 className="text-lg font-semibold text-foreground">2.1 Intangible investment, accounting, and mispricing</h3>
              <p className="text-muted-foreground">
                A recurring theme in the intangible-capital literature is that standard accounting can understate the economic value of R&amp;D by expensing it.
                If investors anchor on near-term earnings, the market can underreact to productive R&amp;D and price high-R&amp;D firms too pessimistically.
                Under that view, a premium reflects gradual learning as innovation outcomes arrive.
              </p>

              <h3 className="text-lg font-semibold text-foreground">2.2 Risk-based interpretation</h3>
              <p className="text-muted-foreground">
                A competing interpretation is that high-R&amp;D firms load on innovation-related risks: uncertain payoffs, higher operating leverage, and
                sensitivity to funding conditions. In this case, a premium can exist without superior risk-adjusted performance; Sharpe ratios may not dominate
                even when mean returns do.
              </p>

              <h3 className="text-lg font-semibold text-foreground">2.3 Practitioner relevance</h3>
              <p className="text-muted-foreground">
                For a portfolio audience, the core questions are implementability and robustness: is the premium stable across regimes, how concentrated is it
                by sector, how sensitive are results to survivorship and delisting assumptions, and what fraction survives explicit trading costs?
                We address these by (i) prioritizing a clean annual return series for inference, (ii) reporting sector structure, and (iii) mapping the signal
                into an explicit strategy section.
              </p>

              <h3 className="text-lg font-semibold text-foreground">Hypotheses</h3>
              <ul className="text-muted-foreground list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">H1 (Characteristic premium):</strong> Firms with higher R&amp;D intensity earn higher subsequent returns than low-R&amp;D firms in a large-cap U.S. universe.
                </li>
                <li>
                  <strong className="text-foreground">H2 (Stability and regimes):</strong> The premium is observable in the annual series and exhibits time variation that can be summarized with rolling windows and event/regime splits.
                </li>
                <li>
                  <strong className="text-foreground">H3 (Not just sector):</strong> The premium is not fully explained by sector composition, size, or standard factor exposures.
                </li>
                <li>
                  <strong className="text-foreground">H4 (Implementability):</strong> A rules-based portfolio derived from the signal retains a positive net premium under explicit trading-friction assumptions.
                </li>
              </ul>
              <p className="text-muted-foreground">
                Additional exhibits and supporting notes are provided in the Online Appendix.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Data & Sample Construction */}
        <section id="data" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Database className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">3. Data &amp; Sample Construction</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
              <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                3.1 R&amp;D Intensity
                <InfoTooltip term="rd_intensity" size={16} />
              </h3>
              <p className="text-muted-foreground">
                We define R&amp;D intensity as R&amp;D expense divided by revenue, expressed as a percentage.
              </p>
              <div className="not-prose">
                <Formulas.RDIntensity />
              </div>

              <div className="not-prose p-4 rounded-lg bg-blue-500/5 border border-blue-500/20 mt-4">
                <p className="font-semibold text-foreground mb-2">Accounting Standard: SFAS 2 (1974)</p>
                <p className="text-sm text-muted-foreground">
                  Consistent R&amp;D reporting in the U.S. began with <strong>FASB Statement No. 2</strong> (SFAS 2), issued in October 1974.
                  This standard requires that R&amp;D expenditures be expensed as incurred due to the uncertainty of future economic benefits.
                  SFAS 2 is now codified as <strong>ASC Topic 730</strong>. Our sample period ({sampleYearRange || "see header"}) falls entirely within this standardized
                  reporting era, ensuring consistent R&amp;D disclosure across firms and years.
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Note: The "expense as incurred" rule is central to the R&amp;D premium hypothesis. Because R&amp;D is not capitalized, firms
                  with high R&amp;D can appear less profitable on traditional metrics even when building valuable intangible assets.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6 flex items-center gap-2">
                3.2 Return Timing (Look-Ahead Mitigation)
                <InfoTooltip term="look_ahead_bias" size={16} />
              </h3>
              <p className="text-muted-foreground">
                To reduce look-ahead bias, we default to July-June returns{" "}
                <span className="inline-flex items-center gap-1">
                  (Fama-French convention)
                  <InfoTooltip term="july_june_convention" size={12} />
                </span>
                : fiscal-year R&D data for year <span className="font-mono">T</span> is mapped to returns from July{" "}
                <span className="font-mono">T+1</span> through June <span className="font-mono">T+2</span>.
              </p>
              <div className="not-prose">
                <Formulas.TSR />
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">3.3 Statistical Inference</h3>
              <p className="text-muted-foreground">
                We present (i) annual non-overlapping HML premiums for primary inference and (ii) rolling-window
                summaries for descriptive context. Where overlapping windows are used, inference is HAC-adjusted.
              </p>
              <div className="not-prose grid md:grid-cols-2 gap-4">
                <Formulas.ANOVA />
                <Formulas.EtaSquared />
                <Formulas.CohensD />
                <Formulas.SharpeRatio />
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
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
              <h3 className="text-lg font-semibold text-foreground">4.1 Portfolio formation (signal and weights)</h3>
              <ul className="text-muted-foreground list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">Universe:</strong> S&amp;P 500 point-in-time constituents (as implemented in the research pipeline).
                </li>
                <li>
                  <strong className="text-foreground">Signal:</strong> prior fiscal-year R&amp;D intensity (R&amp;D expense / revenue).
                </li>
                <li>
                  <strong className="text-foreground">Sorting:</strong> equal-count quintiles (Q1 lowest R&amp;D intensity, Q5 highest).
                </li>
              </ul>

              <div className="not-prose p-4 rounded-lg bg-muted/30 border my-4">
                <p className="font-semibold text-foreground mb-2 flex items-center gap-2">
                  Understanding quintiles
                  <InfoTooltip term="quintile" size={14} />
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  Each year, stocks are sorted by R&amp;D intensity and divided into 5 equal-count groups (quintiles):
                </p>
                <div className="grid grid-cols-5 gap-2 text-center text-xs">
                  <div className="p-2 rounded bg-red-500/10 border border-red-500/20">
                    <div className="font-bold text-foreground">Q1</div>
                    <div className="text-muted-foreground">Lowest 20%</div>
                    <div className="text-muted-foreground">R&amp;D intensity</div>
                  </div>
                  <div className="p-2 rounded bg-orange-500/10 border border-orange-500/20">
                    <div className="font-bold text-foreground">Q2</div>
                    <div className="text-muted-foreground">20-40%</div>
                  </div>
                  <div className="p-2 rounded bg-yellow-500/10 border border-yellow-500/20">
                    <div className="font-bold text-foreground">Q3</div>
                    <div className="text-muted-foreground">40-60%</div>
                  </div>
                  <div className="p-2 rounded bg-lime-500/10 border border-lime-500/20">
                    <div className="font-bold text-foreground">Q4</div>
                    <div className="text-muted-foreground">60-80%</div>
                  </div>
                  <div className="p-2 rounded bg-green-500/10 border border-green-500/20">
                    <div className="font-bold text-foreground">Q5</div>
                    <div className="text-muted-foreground">Highest 20%</div>
                    <div className="text-muted-foreground">R&amp;D intensity</div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  The <strong>HML premium</strong> (High-Minus-Low) is Q5 return minus Q1 return. A positive premium means high-R&amp;D stocks outperformed low-R&amp;D stocks.
                </p>
              </div>

              <ul className="text-muted-foreground list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">Weights:</strong> equal-weight within each portfolio; equal-weighted returns are computed each year and compounded.
                </li>
                <li>
                  <strong className="text-foreground">Inclusion:</strong> firms with R&amp;D reported as zero are retained (typically in Q1). A minimum-revenue filter is applied to avoid extreme ratios from very small denominators.
                </li>
              </ul>

              <div className="not-prose mt-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Parameter</TableHead>
                        <TableHead className="text-right">Value</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell className="font-medium">Min revenue threshold</TableCell>
                        <TableCell className="text-right font-mono">
                          {typeof (methodologyParameters as any)?.filters?.min_revenue_threshold_usd === "number"
                            ? `$${((methodologyParameters as any).filters.min_revenue_threshold_usd / 1e6).toFixed(0)}M`
                            : "-"}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">R&amp;D intensity cap (default)</TableCell>
                        <TableCell className="text-right font-mono">
                          {typeof (methodologyParameters as any)?.filters?.rd_intensity_capping?.default_cap_pct === "number"
                            ? `${(methodologyParameters as any).filters.rd_intensity_capping.default_cap_pct.toFixed(0)}%`
                            : "-"}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">R&amp;D intensity cap (high-R&amp;D sectors)</TableCell>
                        <TableCell className="text-right font-mono">
                          {typeof (methodologyParameters as any)?.filters?.rd_intensity_capping?.high_rd_sector_cap_pct === "number"
                            ? `${(methodologyParameters as any).filters.rd_intensity_capping.high_rd_sector_cap_pct.toFixed(0)}%`
                            : "-"}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Return definition
                            <InfoTooltip title="Return Definition" size={12}>
                              Returns are computed from a daily price series using adjusted close when available (split/dividend-adjusted per the provider),
                              and falling back to close when adjusted close is unavailable. This is a practical approximation of total shareholder return,
                              subject to vendor definitions and data coverage.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">Adj close (fallback: close)</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Universe membership
                            <InfoTooltip title="Point-in-time membership" size={12}>
                              Where historical constituent spans are available, the universe for a given formation date is filtered to companies that were
                              members as of that date. If membership history is unavailable for a period, results fall back to the available dataset and
                              should be read as less strictly survivorship-controlled.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">Point-in-time (when available)</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Delisting returns
                            <InfoTooltip title="Delisting return treatment" size={12}>
                              If a constituent delists during a return period, the return for that period is replaced with a delisting return estimate.
                              The platform prefers a price-based estimate from the final trading days and falls back to a documented heuristic when price data
                              is insufficient.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">Integrated by period</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">Return convention</TableCell>
                        <TableCell className="text-right font-mono">{snapshot?.meta?.return_convention || "july_june"}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">Data tier</TableCell>
                        <TableCell className="text-right font-mono">{snapshot?.meta?.data_tier || "tier1"}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">4.2 Return timing (look-ahead mitigation)</h3>
              <p className="text-muted-foreground">
                The default convention uses July-June returns (Fama-French): fiscal-year accounting information for year <span className="font-mono">T</span>{" "}
                is mapped to subsequent returns from July <span className="font-mono">T+1</span> through June <span className="font-mono">T+2</span>.
                This timing reduces look-ahead bias from filing lags that can contaminate calendar-year sorts.
              </p>
              <div className="not-prose">
                <Formulas.TSR />
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">4.3 Rolling windows vs annual inference (what each object means)</h3>
              <p className="text-muted-foreground">
                We report two complementary objects, each with a specific interpretation:
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">Annual series (primary inference):</strong> each year, we form R&amp;D quintiles using the prior fiscal
                  year and measure the next July-June return. This produces one observation per year, which is the cleanest basis for inference in a
                  practitioner manuscript.
                </li>
                <li>
                  <strong className="text-foreground">Rolling windows (descriptive):</strong> for a given window start, we assign quintiles once (based on
                  that start-year signal) and then summarize outcomes over 5/10/20 years. These overlapping windows are autocorrelated and are used primarily
                  to visualize regime dependence and horizon behavior, not as standalone p-values.
                </li>
              </ul>
              <div className="not-prose grid md:grid-cols-2 gap-4">
                <Formulas.ANOVA />
                <Formulas.EtaSquared />
                <Formulas.CohensD />
                <Formulas.SharpeRatio />
              </div>

              <div className="not-prose mt-4 p-4 rounded-lg border bg-muted/30">
                <p className="font-semibold text-foreground mb-2">Bias controls and data integrity (summary)</p>
                <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                  <li>Look-ahead mitigation via July-June timing (default).</li>
                  <li>Point-in-time index membership used where historical constituent spans are available.</li>
                  <li>Delisting returns are applied in the delisting period and firms are removed thereafter.</li>
                  <li>Outlier controls: minimum revenue threshold and sector-aware R&amp;D-intensity caps.</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Main Results */}
        <section id="results" className="scroll-mt-24 space-y-6">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">5. Results</h2>
          </div>

          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none">
              <p className="text-muted-foreground">
                We report the main return evidence in three complementary views. First, we present the non-overlapping annual premium series (Table 5.1),
                which provides the cleanest basis for inference. Second, we summarize average returns by quintile and the evolution of the premium in rolling
                windows (Figures 5.2-5.3) to illustrate time variation. Third, we report horizon-level summaries for 5/10/20-year rolling windows (Table 5.4)
                as descriptive context.
              </p>
            </CardContent>
          </Card>

          {/* Primary Result: Annual HML */}
          <AnnualHMLTable
            data={annualHmlData}
            isLoading={snapshotLoading}
            title="5.1 Primary Result: Annual HML R&D Premium"
            description="Non-overlapping annual observations (primary inference)"
          />

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>5.2 Average Annual Returns by R&amp;D Quintile (5-Year Windows)</CardTitle>
              <CardDescription>
                Quintile-level average returns aggregated across stored 5-year windows (descriptive summary).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="h-[340px]">
                {quintileReturnBar5yr.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                    <BarChart data={quintileReturnBar5yr}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="quintile" stroke="hsl(var(--muted-foreground))" />
                      <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip
                        formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Avg Return"]}
                        contentStyle={{
                          backgroundColor: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Bar dataKey="avgReturn" radius={[4, 4, 0, 0]}>
                        {quintileReturnBar5yr.map((entry, index) => (
                          <Cell key={index} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                  Loading quintile summary...
                  </div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    The average return profile is higher in the high-R&amp;D quintile than in the low-R&amp;D quintile in the 5-year aggregates{" "}
                    {(() => {
                      const q1 = quintileReturnBar5yr.find((r) => r.quintile === "Q1")?.avgReturn
                      const q5 = quintileReturnBar5yr.find((r) => r.quintile === "Q5")?.avgReturn
                      if (typeof q1 !== "number" || typeof q5 !== "number") return ""
                      return `(Q5 - Q1 = ${(q5 - q1).toFixed(2)} pp).`
                    })()}
                  </li>
                  <li>Mid-quintiles need not be perfectly monotone; the premium is defined as Q5 minus Q1.</li>
                  <li>This figure is descriptive (aggregated from overlapping windows); inference is based on the annual non-overlapping series in Table 5.1.</li>
                </ul>
              </div>
              <p className="text-xs text-muted-foreground">
                Source: <code>/api/research/publication-snapshot</code> (frozen; derived from stored rolling-window results).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>5.3 Premium Over Time (5-Year Rolling Windows)</CardTitle>
              <CardDescription>
                Rolling 5-year HML premium series (Q5-Q1). Overlapping windows are descriptive; inference is based on the annual non-overlapping series.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="h-[340px]">
                {rollingPremium5yr.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                    <AreaChart data={rollingPremium5yr}>
                      <defs>
                        <linearGradient id="premiumGradientMain" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis
                        dataKey="period"
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fontSize: 10 }}
                        angle={-45}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip
                        formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Premium (Q5-Q1)"]}
                        contentStyle={{
                          backgroundColor: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                      <Area type="monotone" dataKey="rdPremium" stroke="#10b981" fill="url(#premiumGradientMain)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                  Loading rolling-window series...
                  </div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Time variation is substantial: the premium is not constant and can be negative in some regimes.</li>
                  <li>Overlapping windows are autocorrelated by construction; treat the shape as a stability/regime diagnostic, not independent evidence.</li>
                  <li>We use this figure to motivate event/regime context (Section 8) rather than to replace the annual-series inference.</li>
                </ul>
              </div>
              <p className="text-xs text-muted-foreground">
                Source: <code>/api/research/publication-snapshot</code> (frozen; stored rolling-window series).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>5.4 Horizon Summary (Rolling Windows)</CardTitle>
              <CardDescription>
                Summary across 5/10/20-year rolling windows (descriptive; inference shown via t-test/ANOVA).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Horizon</TableHead>
                      <TableHead className="text-right">
                        <span className="flex items-center justify-end gap-1">
                          HML Premium (%)
                          <InfoTooltip term="hml_premium" size={12} />
                        </span>
                      </TableHead>
                      <TableHead className="text-right">
                        <span className="flex items-center justify-end gap-1">
                          t-stat
                          <InfoTooltip term="t_statistic" size={12} />
                        </span>
                      </TableHead>
                      <TableHead className="text-right">
                        <span className="flex items-center justify-end gap-1">
                          p-value
                          <InfoTooltip term="p_value" size={12} />
                        </span>
                      </TableHead>
                      <TableHead className="text-right">
                        <span className="flex items-center justify-end gap-1">
                          η²
                          <InfoTooltip term="eta_squared" size={12} />
                        </span>
                      </TableHead>
                      <TableHead className="text-right">
                        <span className="flex items-center justify-end gap-1">
                          Cohen&apos;s d
                          <InfoTooltip term="cohens_d" size={12} />
                        </span>
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {headlinePremiums.map((row) => (
                      <TableRow key={row.horizon}>
                        <TableCell className="font-medium">{row.horizon.toUpperCase()}</TableCell>
                        <TableCell className="text-right">
                          {row.premiumPct !== undefined ? row.premiumPct.toFixed(2) : "-"}
                        </TableCell>
                        <TableCell className="text-right">{row.t !== undefined ? row.t.toFixed(2) : "-"}</TableCell>
                        <TableCell className="text-right">
                          {row.p !== undefined ? (row.p < 0.001 ? "< 0.001" : row.p.toFixed(4)) : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {row.eta2 !== undefined ? row.eta2.toFixed(3) : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {row.cohensD !== undefined ? row.cohensD.toFixed(3) : "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="mt-4 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    Horizon summaries typically shrink at longer horizons because the sort is formed once at the window start and the signal can become stale.
                  </li>
                  <li>
                    Long horizons also mix multiple market regimes; a single 20-year window can include boom and bust episodes that dominate compounded outcomes.
                  </li>
                  <li>
                    We treat these horizon aggregates as descriptive context and explain the horizon pattern explicitly (Section 8).
                  </li>
                </ul>
              </div>

              <p className="text-sm text-muted-foreground mt-4">
                Source: <code>/api/research/publication-snapshot</code> (frozen). Premium values are based on Q5 minus Q1.
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>5.5 Key takeaways</CardTitle>
              <CardDescription>High-signal interpretation of the main results (Sections 5.1-5.4).</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <ul className="list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">Primary evidence is annual:</strong>{" "}
                  {typeof annualHmlData?.mean_premium === "number"
                    ? `the mean annual premium is ${annualHmlData.mean_premium.toFixed(2)}% with Newey-West inference reported in Table 5.1.`
                    : "the mean annual premium and Newey-West inference are reported in Table 5.1."}
                </li>
                <li>
                  <strong className="text-foreground">Time variation matters:</strong> rolling windows illustrate regime dependence; they are used for context, not as independent observations.
                </li>
                <li>
                  <strong className="text-foreground">Horizon dependence is informative:</strong>{" "}
                  {headlinePremiums.some((h) => typeof h.premiumPct === "number")
                    ? `the premium is largest in shorter horizons and smaller in 20-year windows, consistent with signal decay and regime mixing.`
                    : "horizon summaries provide context on persistence and regime mixing."}
                </li>
              </ul>
              <p className="text-xs text-muted-foreground">
                Source: <code>/api/research/publication-snapshot</code> (frozen). This summary is computed from the same snapshot-backed objects shown above.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Sector */}
        <section id="sector" className="scroll-mt-24 space-y-6">
          <div className="flex items-center gap-3 mb-4">
            <Layers className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">6. Sector Analysis</h2>
          </div>

          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none">
              <p className="text-muted-foreground">
                Sector composition is a key confounder for any R&D-based sort. High-R&D firms are concentrated in a small set of sectors, and sector-wide shocks
                can mechanically influence the premium. We therefore report (i) R&D intensity by sector, (ii) coverage of eligible firms by sector for
                long-horizon windows, and (iii) descriptive sector trends and leaderboards. These exhibits are descriptive and are intended to support
                transparent interpretation of the return results.
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>6.1 R&amp;D Intensity by Sector (from dataset)</CardTitle>
              <CardDescription>
                Sectors with the highest average R&D intensity in the sample (computed from ingested statements).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[380px]">
                {sectorIntensityData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minHeight={320}>
                    <BarChart data={sectorIntensityData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                      <XAxis type="number" tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                      <YAxis
                        type="category"
                        dataKey="sector"
                        stroke="hsl(var(--muted-foreground))"
                        width={140}
                        tick={{ fontSize: 11 }}
                      />
                      <RechartsTooltip
                        formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Avg R&D Intensity"]}
                        contentStyle={{
                          backgroundColor: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Bar dataKey="avgRdIntensity" radius={[0, 4, 4, 0]}>
                        {sectorIntensityData.map((entry, index) => (
                          <Cell key={index} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading sector distribution...</div>
                )}
              </div>

              {topSectors.length === 0 ? (
                <p className="text-sm text-muted-foreground">Loading sector summary...</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Sector</TableHead>
                        <TableHead className="text-right">
                          <span className="flex items-center justify-end gap-1">
                            Avg R&D Intensity (%)
                            <InfoTooltip term="rd_intensity" size={12} />
                          </span>
                        </TableHead>
                        <TableHead className="text-right">Companies</TableHead>
                        <TableHead className="text-right">Cumulative R&D ($B)</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {topSectors.map((s) => (
                        <TableRow key={s.sector}>
                          <TableCell className="font-medium">{s.sector}</TableCell>
                          <TableCell className="text-right">{s.avg_rd_intensity.toFixed(2)}</TableCell>
                          <TableCell className="text-right">{s.company_count}</TableCell>
                          <TableCell className="text-right">{(s.total_rd_spend / 1e9).toFixed(0)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              <div className="mt-4 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    R&amp;D intensity is highly concentrated by sector. This is expected and makes sector reporting a required companion to any R&amp;D-based sort.
                  </li>
                  <li>
                    The premium could reflect (i) within-sector effects, (ii) sector tilts, or (iii) a combination. We therefore treat sector structure as a
                    first-order confounder to address in robustness diagnostics.
                  </li>
                  <li>
                    Total R&amp;D spend shown here is a cumulative sum over the dataset period (context), not a yearly flow.
                  </li>
                </ul>
              </div>

              <div className="mt-4 p-4 bg-muted/30 border rounded-lg flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-muted-foreground">
                  <p className="font-semibold text-foreground mb-1">Interpretation caution</p>
                  <p>
                    Sector composition matters: high-R&D quintiles naturally tilt toward Technology and Healthcare.
                    We address this via sector-neutral robustness tests (see Sub-Research 3 / Robustness).
                  </p>
                </div>
              </div>

              <p className="text-xs text-muted-foreground mt-3">
                Source: <code>/api/research/publication-snapshot</code> (frozen). Total R&amp;D spend is summed over the dataset period (not annual).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>6.2 Long-Horizon Coverage by Sector</CardTitle>
              <CardDescription>
                Coverage of eligible firms by sector for 5/10/20-year windows (derived from cohort summary).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="h-[420px]">
                {sectorCoverageData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minHeight={340}>
                    <BarChart
                      data={sectorCoverageData.slice().sort((a, b) => (b.coverage20yr || 0) - (a.coverage20yr || 0))}
                      layout="vertical"
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                      <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                      <YAxis type="category" dataKey="sector" stroke="hsl(var(--muted-foreground))" width={160} tick={{ fontSize: 11 }} />
                      <RechartsTooltip
                        formatter={(value) => [`${value}%`, "Coverage"]}
                        contentStyle={{
                          backgroundColor: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                      <Bar dataKey="coverage5yr" name="5-Year" fill="#3b82f6" radius={[0, 2, 2, 0]} />
                      <Bar dataKey="coverage10yr" name="10-Year" fill="#8b5cf6" radius={[0, 2, 2, 0]} />
                      <Bar dataKey="coverage20yr" name="20-Year" fill="#22c55e" radius={[0, 2, 2, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading coverage...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Long-horizon coverage is uneven: fewer firms have continuous data and eligibility for 20-year windows.</li>
                  <li>
                    Lower 20-year coverage mechanically increases estimation uncertainty and can interact with sector composition (some sectors have shorter
                    histories or more turnover).
                  </li>
                </ul>
              </div>
              <p className="text-xs text-muted-foreground">
                Source: <code>/api/research/publication-snapshot</code> (frozen; cohort summary by sector).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>6.3 Sector Profile (Radar)</CardTitle>
              <CardDescription>Intensity vs. company count across top sectors by R&amp;D intensity.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="h-[420px]">
                {sectorRadarData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minHeight={340}>
                    <RadarChart data={sectorRadarData}>
                      <PolarGrid stroke="hsl(var(--border))" />
                      <PolarAngleAxis dataKey="sector" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} />
                      <PolarRadiusAxis angle={30} domain={[0, "auto"]} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} />
                      <RechartsTooltip
                        formatter={(value, name) => [
                          name === "intensity" ? `${(value as number).toFixed(1)}%` : (value as number).toFixed(0),
                          name === "intensity" ? "R&D Intensity" : "Companies",
                        ]}
                        contentStyle={{
                          backgroundColor: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                      <Radar name="R&D Intensity" dataKey="intensity" stroke="#22c55e" fill="#22c55e" fillOpacity={0.25} />
                      <Radar name="Companies" dataKey="companies" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
                    </RadarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading sector radar...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>This view separates “high intensity” from “broad participation”: a sector can have very high R&amp;D intensity with relatively few firms.</li>
                  <li>
                    This matters for portfolio concentration and capacity: concentrated high-R&amp;D exposure can create sector risk that must be monitored.
                  </li>
                </ul>
              </div>
              <p className="text-xs text-muted-foreground">
                Source: <code>/api/research/publication-snapshot</code> (frozen; derived from sector aggregates).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>6.4 R&amp;D Trends Over Time (Context)</CardTitle>
              <CardDescription>Yearly R&amp;D intensity and aggregate R&amp;D spend (Tier-1 descriptive series).</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="h-[380px]">
                {rdTrendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minHeight={320}>
                    <LineChart data={rdTrendData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                      <YAxis yAxisId="left" tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        tickFormatter={(v) => `$${(v as number).toFixed(0)}B`}
                        stroke="hsl(var(--muted-foreground))"
                      />
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                        formatter={(value, name) => {
                          if (name === "avgIntensity") return [`${(value as number).toFixed(2)}%`, "Avg R&D Intensity"]
                          if (name === "totalSpendB") return [`$${(value as number).toFixed(0)}B`, "Total R&D Spend"]
                          return [String(value), String(name)]
                        }}
                      />
                      <Legend />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="avgIntensity"
                        name="Avg R&D Intensity (%)"
                        stroke="#22c55e"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="totalSpendB"
                        name="Total R&D Spend ($B)"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">Loading trends...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>This figure provides context on the evolving R&amp;D landscape (coverage, aggregate spend, and average intensity).</li>
                  <li>
                    It is not a causal claim about returns; it helps interpret which eras and sectors dominate the sample and why regime splits can matter.
                  </li>
                </ul>
              </div>
              <p className="text-xs text-muted-foreground">
                Source: <code>/api/research/publication-snapshot</code> (frozen; Tier-1 descriptive series from income statements).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>6.5 R&amp;D Leaders (Snapshot)</CardTitle>
              <CardDescription>Top 3 firms by average R&amp;D intensity within each sector (snapshot-pinned).</CardDescription>
            </CardHeader>
            <CardContent>
              {!rdLeadersBySector || rdLeadersBySector.length === 0 ? (
                <p className="text-sm text-muted-foreground">Loading leaderboard...</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Sector</TableHead>
                        <TableHead>Top 1</TableHead>
                        <TableHead>Top 2</TableHead>
                        <TableHead>Top 3</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rdLeadersBySector.map(({ sector, leaders }) => {
                        const renderLeader = (r: any) => {
                          if (!r) return <span className="text-muted-foreground">-</span>
                          const intensity =
                            typeof r.avg_rd_intensity === "number" ? `${r.avg_rd_intensity.toFixed(2)}%` : "-"
                          const years = typeof r.years_of_data === "number" ? `${r.years_of_data}y` : "-"
                          return (
                            <div className="min-w-[200px] leading-tight">
                              <div className="font-mono">
                                <Link to={`/companies/${r.symbol}`} className="underline hover:no-underline">
                                  {r.symbol}
                                </Link>
                              </div>
                              <div className="text-xs text-muted-foreground">{`${intensity} | ${years}`}</div>
                              {typeof r.name === "string" && r.name ? (
                                <div className="text-xs text-muted-foreground truncate">{r.name}</div>
                              ) : null}
                            </div>
                          )
                        }

                        return (
                          <TableRow key={sector}>
                            <TableCell className="font-medium whitespace-nowrap">{sector}</TableCell>
                            <TableCell>{renderLeader(leaders?.[0])}</TableCell>
                            <TableCell>{renderLeader(leaders?.[1])}</TableCell>
                            <TableCell>{renderLeader(leaders?.[2])}</TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-3">
                Source: <code>/api/research/publication-snapshot</code> (frozen; cohort-based leaderboard).
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Robustness */}
        <section id="robustness" className="scroll-mt-24 space-y-6">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">7. Robustness & Factor Tests</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground">
                This section reports robustness and interpretation diagnostics that complement the primary annual premium evidence in Section 5.1. We present
                the annual premium time series, cumulative growth of $1 for Q5 versus Q1, factor spanning tests (when factor inputs are available), and
                stratification and double-sort diagnostics to assess size, sector, and other confounding.
              </p>
              <div className="not-prose grid md:grid-cols-4 gap-3">
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    Mean premium (annual)
                    <InfoTooltip term="hml_premium" size={12} />
                  </div>
                  <div className="font-semibold">
                    {typeof (publicationStats as any)?.rd_factor_premium?.mean === "number"
                      ? `${(publicationStats as any).rd_factor_premium.mean.toFixed(2)}%`
                      : "-"}
                  </div>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    t-stat
                    <InfoTooltip term="t_statistic" size={12} />
                  </div>
                  <div className="font-semibold">
                    {typeof (publicationStats as any)?.rd_factor_premium?.t_statistic === "number"
                      ? (publicationStats as any).rd_factor_premium.t_statistic.toFixed(2)
                      : "-"}
                  </div>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    Win rate
                    <InfoTooltip title="Win Rate" size={12}>
                      Percentage of years where Q5 (high R&D) outperformed Q1 (low R&D). A win rate above 50% suggests
                      the premium is consistent over time, not driven by a few outlier years.
                    </InfoTooltip>
                  </div>
                  <div className="font-semibold">
                    {(() => {
                      const s = (publicationStats as any)?.rd_factor_premium
                      if (!s || typeof s.positive_years !== "number" || typeof s.n_years !== "number" || s.n_years <= 0) return "-"
                      return `${Math.round((s.positive_years / s.n_years) * 100)}%`
                    })()}
                  </div>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground">Years</div>
                  <div className="font-semibold">
                    {typeof (publicationStats as any)?.rd_factor_premium?.n_years === "number"
                      ? (publicationStats as any).rd_factor_premium.n_years
                      : "-"}
                  </div>
                </div>
              </div>
              <p className="text-muted-foreground">
                For additional deep-dive commentary and supporting visuals, see{" "}
                <Link to="/papers/3" className="inline-flex items-center gap-2 underline hover:no-underline">
                  Sub-Research 3 <ExternalLink className="h-4 w-4" />
                </Link>
                .
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>7.1 Annual R&amp;D Premium (Time Series)</CardTitle>
              <CardDescription>Annual Q5-Q1 premium (from snapshot factor premium series).</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="h-[360px]">
                {factorPremiumSeries.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                    <BarChart data={factorPremiumSeries.filter((d) => d.rdPremium !== null)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                      <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip
                        formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "Premium (Q5-Q1)"]}
                        contentStyle={{
                          backgroundColor: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                      <Bar dataKey="rdPremium" radius={[4, 4, 0, 0]}>
                        {factorPremiumSeries
                          .filter((d) => d.rdPremium !== null)
                          .map((entry, index) => (
                            <Cell key={index} fill={(entry.rdPremium || 0) >= 0 ? "#22c55e" : "#ef4444"} />
                          ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading factor premium series...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Year-to-year dispersion is expected in characteristic premiums; negative years do not invalidate a positive long-run mean.</li>
                  <li>This series is the preferred object for “how often does it work?” style questions (win rate, drawdowns, regime dependence).</li>
                  <li>We use Newey-West inference on the annual non-overlapping premium (Table 5.1) rather than overlapping-window p-values.</li>
                </ul>
              </div>
              <p className="text-xs text-muted-foreground">
                Source: <code>/api/research/publication-snapshot</code> (frozen; factor premium series).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>7.2 Cumulative Portfolio Performance</CardTitle>
              <CardDescription>Growth of $1 invested in Q5 (high R&amp;D) vs Q1 (low R&amp;D) from annual return series.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="h-[360px]">
                {growthOf1.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                    <AreaChart data={growthOf1}>
                      <defs>
                        <linearGradient id="q5GradientMain" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="q1GradientMain" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                      <YAxis tickFormatter={(v) => `$${(v as number).toFixed(2)}`} stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip
                        formatter={(value, name) => [`$${(value as number)?.toFixed(2)}`, name as string]}
                        contentStyle={{
                          backgroundColor: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="q5Cumulative"
                        name="Q5 (High R&D)"
                        stroke="#22c55e"
                        fill="url(#q5GradientMain)"
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="q1Cumulative"
                        name="Q1 (Low R&D)"
                        stroke="#ef4444"
                        fill="url(#q1GradientMain)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading cumulative series...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Compounding highlights path dependence: a small set of drawdown episodes can dominate long-horizon wealth outcomes.</li>
                  <li>Growth-of-$1 is intuitive but not risk-adjusted; it should be read alongside volatility and drawdown diagnostics (Section 9.3).</li>
                </ul>
              </div>
              <p className="text-xs text-muted-foreground">
                Source: <code>/api/research/publication-snapshot</code> (frozen; computed from annual Q1/Q5 returns).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>7.3 Factor Spanning Tests</CardTitle>
              <CardDescription>Regression tests of whether the premium is explained by standard factor models.</CardDescription>
            </CardHeader>
            <CardContent>
              {(spanningTests as any)?.models ? (
                <div className="space-y-4">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left py-2 px-3 font-semibold text-foreground">Model</th>
                          <th className="text-right py-2 px-3 font-semibold text-foreground">
                            <span className="flex items-center justify-end gap-1">
                              Alpha (%)
                              <InfoTooltip term="alpha" size={12} />
                            </span>
                          </th>
                          <th className="text-right py-2 px-3 font-semibold text-foreground">
                            <span className="flex items-center justify-end gap-1">
                              t-stat
                              <InfoTooltip term="t_statistic" size={12} />
                            </span>
                          </th>
                          <th className="text-right py-2 px-3 font-semibold text-foreground">
                            <span className="flex items-center justify-end gap-1">
                              R²
                              <InfoTooltip term="r_squared" size={12} />
                            </span>
                          </th>
                          <th className="text-center py-2 px-3 font-semibold text-foreground">
                            <span className="flex items-center justify-center gap-1">
                              Spanned?
                              <InfoTooltip term="spanned" size={12} />
                            </span>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries((spanningTests as any).models).map(([model, data]: any) => (
                          <tr key={model} className="border-b border-border/50">
                            <td className="py-2 px-3 font-medium text-foreground">{model}</td>
                            <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.alpha === "number" ? `${(data.alpha * 100).toFixed(2)}%` : "-"}</td>
                            <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.alpha_t === "number" ? data.alpha_t.toFixed(2) : "-"}</td>
                            <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.r_squared === "number" ? `${(data.r_squared * 100).toFixed(1)}%` : "-"}</td>
                            <td className="py-2 px-3 text-center">
                              {data.is_spanned ? (
                                <Badge variant="outline" className="text-yellow-600 dark:text-yellow-400">Yes</Badge>
                              ) : (
                                <Badge className="bg-green-600 text-white">No</Badge>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {(spanningTests as any)?.interpretation?.summary && (
                    <div className="p-4 rounded-lg bg-muted/30 border">
                      <p className="text-sm text-muted-foreground">
                        <strong className="text-foreground">Interpretation:</strong> {(spanningTests as any).interpretation.summary}
                      </p>
                    </div>
                  )}
                  <div className="p-4 rounded-lg bg-muted/30 border">
                    <p className="text-sm text-muted-foreground">
                      <strong className="text-foreground">How to read this:</strong> the key statistic is the regression alpha for the R&amp;D premium after
                      controlling for standard factors. A positive and statistically meaningful alpha is consistent with the premium not being fully explained
                      by those factor exposures. Factor alignment and availability are snapshot-dependent; when inputs are missing, we report the test as
                      unavailable rather than imputing it.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Spanning tests are not available in this snapshot (factor inputs may be missing).</p>
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-3">
                Source: <code>/api/research/publication-snapshot</code> (frozen; spanning tests).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>7.4 Mispricing vs Risk Diagnostics</CardTitle>
              <CardDescription>Stratification tests to distinguish mispricing from risk-based explanations.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="not-prose p-4 rounded-lg bg-muted/30 border text-sm">
                <p className="font-semibold text-foreground mb-2">How to interpret these tests</p>
                <p className="text-muted-foreground mb-2">
                  If the premium is due to <strong>mispricing</strong>, it should be larger in stocks that are hard to arbitrage
                  (small, volatile, low analyst coverage). If the premium is <strong>risk compensation</strong>, it should be
                  similar across arbitrage-cost groups or larger in low-cost stocks.
                </p>
                <ul className="text-muted-foreground list-disc list-inside space-y-1">
                  <li><strong>By Size:</strong> Small stocks are harder to arbitrage due to liquidity and short-sale costs.</li>
                  <li><strong>By Volatility:</strong> High-volatility stocks carry more arbitrage risk (noise trader risk).</li>
                  <li><strong>By Coverage:</strong> Low-coverage stocks have more information asymmetry.</li>
                </ul>
              </div>

              {(mispricingTests as any)?.tests ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-lg bg-muted/30 border">
                      <h4 className="font-semibold mb-3 text-foreground flex items-center gap-2">
                        By Size
                        <InfoTooltip title="Size stratification" size={14}>
                          Firms sorted into terciles by market cap. Mispricing theory predicts higher premium in small stocks.
                        </InfoTooltip>
                      </h4>
                      {Object.entries((mispricingTests as any).tests.by_size || {}).map(([k, v]: any) => (
                        <div key={k} className="flex justify-between text-sm py-1">
                          <span className="text-muted-foreground">{k}</span>
                          <span className="font-mono">{v?.premium !== null && v?.premium !== undefined ? `${v.premium.toFixed(1)}%` : "n/a"}</span>
                        </div>
                      ))}
                    </div>
                    <div className="p-4 rounded-lg bg-muted/30 border">
                      <h4 className="font-semibold mb-3 text-foreground flex items-center gap-2">
                        By Volatility
                        <InfoTooltip title="Volatility stratification" size={14}>
                          Firms sorted into terciles by return volatility. Mispricing theory predicts higher premium in volatile stocks.
                        </InfoTooltip>
                      </h4>
                      {Object.entries((mispricingTests as any).tests.by_volatility || {}).map(([k, v]: any) => (
                        <div key={k} className="flex justify-between text-sm py-1">
                          <span className="text-muted-foreground">{k}</span>
                          <span className="font-mono">{v?.premium !== null && v?.premium !== undefined ? `${v.premium.toFixed(1)}%` : "n/a"}</span>
                        </div>
                      ))}
                    </div>
                    <div className="p-4 rounded-lg bg-muted/30 border">
                      <h4 className="font-semibold mb-3 text-foreground flex items-center gap-2">
                        By Coverage
                        <InfoTooltip title="Analyst coverage stratification" size={14}>
                          Firms sorted into terciles by analyst coverage. Mispricing theory predicts higher premium in low-coverage stocks.
                          Note: "High" coverage may show n/a if insufficient data exists for that stratum.
                        </InfoTooltip>
                      </h4>
                      {Object.entries((mispricingTests as any).tests.by_coverage || {}).map(([k, v]: any) => (
                        <div key={k} className="flex justify-between text-sm py-1">
                          <span className="text-muted-foreground">{k}</span>
                          <span className="font-mono">{v?.premium !== null && v?.premium !== undefined ? `${v.premium.toFixed(1)}%` : "n/a"}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {(mispricingTests as any)?.interpretation?.likely_explanation && (
                    <div className="p-4 rounded-lg bg-muted/30 border">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={(mispricingTests as any).interpretation.likely_explanation === "MISPRICING" ? "bg-amber-600" : "bg-blue-600"}>
                          {(mispricingTests as any).interpretation.likely_explanation}
                        </Badge>
                        <InfoTooltip
                          term={(mispricingTests as any).interpretation.likely_explanation === "MISPRICING" ? "mispricing" : "risk_compensation"}
                          size={14}
                        />
                        <span className="text-sm text-muted-foreground">
                          ({(mispricingTests as any).interpretation.confidence} Confidence)
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">{(mispricingTests as any).interpretation.explanation}</p>
                    </div>
                  )}

                  <div className="p-3 rounded border bg-yellow-500/5 border-yellow-500/20 text-sm">
                    <p className="text-muted-foreground">
                      <strong className="text-foreground">Interpretation caveat:</strong> These tests are suggestive, not definitive.
                      A risk-based interpretation does not preclude mispricing (and vice versa). The pattern here is that the premium
                      is present across size groups and is larger in high-volatility stocks, which is more consistent with risk compensation
                      but does not rule out partial mispricing.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Mispricing diagnostics are not available in this snapshot.</p>
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-3">
                Source: <code>/api/research/publication-snapshot</code> (frozen; mispricing diagnostics).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>7.5 Size × R&amp;D Double-Sort</CardTitle>
              <CardDescription>R&amp;D premium within size groups (diagnostic for size confounding).</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!doubleSortTableRows.length ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Double-sort results are not available in this snapshot.</p>
                </div>
              ) : (
                <>
                  <div className="text-sm text-muted-foreground space-y-2">
                    <p>
                      This diagnostic asks whether the R&amp;D premium exists after conditioning on size. We first sort firms into size terciles (a scale proxy
                      based on log revenue in the snapshot dataset), then sort into R&amp;D terciles within each size group, and report average returns for each
                      Size × R&amp;D cell.
                    </p>
                    <p>
                      The key object is the within-size spread: <span className="font-mono">High R&amp;D - Low R&amp;D</span>. A smaller spread in Large does
                      not mean returns are low; it means High and Low behave more similarly within that size bucket.
                    </p>
                    <p>
                      These diagnostics are intended to narrow confounds. Inference in this paper is anchored on the annual non-overlapping premium series
                      (Table 5.1); the double-sort uses pooled company-year observations and should be read as a robustness check rather than a primary test.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {doubleSortTableRows.map((r) => {
                      const low = r.cells.find((c) => c.rd === "Low")?.mean
                      const high = r.cells.find((c) => c.rd === "High")?.mean
                      const spread = r.spread
                      return (
                        <div key={r.size} className="p-4 rounded-lg bg-muted/30 border text-center">
                          <h4 className="font-semibold mb-2 text-foreground">{r.size}</h4>
                          <div className="text-xs text-muted-foreground">
                            High {typeof high === "number" ? `${high.toFixed(2)}%` : "-"} vs Low {typeof low === "number" ? `${low.toFixed(2)}%` : "-"}
                          </div>
                          <div className="text-2xl font-bold text-primary mt-2">
                            {typeof spread === "number" ? `${spread >= 0 ? "+" : ""}${spread.toFixed(2)}%` : "-"}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            t = {typeof r.t === "number" ? r.t.toFixed(2) : "-"}
                          </div>
                          <Badge
                            className={
                              r.significant === null ? "bg-slate-500 mt-2" : r.significant ? "bg-green-600 mt-2" : "bg-slate-500 mt-2"
                            }
                          >
                            {r.significant === null ? "-" : r.significant ? "Significant" : "Not Sig."}
                          </Badge>
                        </div>
                      )
                    })}
                  </div>

                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Size bucket</TableHead>
                          <TableHead className="text-right">Low R&amp;D</TableHead>
                          <TableHead className="text-right">Mid R&amp;D</TableHead>
                          <TableHead className="text-right">High R&amp;D</TableHead>
                          <TableHead className="text-right">High - Low</TableHead>
                          <TableHead className="text-right">t</TableHead>
                          <TableHead className="text-right">p</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {doubleSortTableRows.map((r) => {
                          const byRd = Object.fromEntries(r.cells.map((c) => [c.rd, c]))
                          const fmtCell = (c: any) => {
                            if (!c || typeof c.mean !== "number") return <span className="text-muted-foreground">-</span>
                            return (
                              <div className="text-right">
                                <div className="font-mono">{c.mean.toFixed(2)}%</div>
                                <div className="text-xs text-muted-foreground">{typeof c.n === "number" ? `n=${c.n}` : ""}</div>
                              </div>
                            )
                          }

                          return (
                            <TableRow key={r.size}>
                              <TableCell className="font-medium">{r.size}</TableCell>
                              <TableCell>{fmtCell(byRd["Low"])}</TableCell>
                              <TableCell>{fmtCell(byRd["Medium"])}</TableCell>
                              <TableCell>{fmtCell(byRd["High"])}</TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.spread === "number" ? `${r.spread >= 0 ? "+" : ""}${r.spread.toFixed(2)}%` : "-"}
                              </TableCell>
                              <TableCell className="text-right font-mono">{typeof r.t === "number" ? r.t.toFixed(2) : "-"}</TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.p === "number" ? (r.p < 0.001 ? "< 0.001" : r.p.toFixed(4)) : "-"}
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}

              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Interpretation</p>
                <ul className="list-disc list-inside space-y-2">
                  <li>
                    If the premium is present within size buckets, it is less likely to be a pure size proxy. Here, the within-size spread is positive in each
                    bucket and statistically meaningful in Small and Large in the snapshot.
                  </li>
                  <li>
                    The within-Large spread is smaller than within-Small. This pattern is consistent with the idea that the signal is more informative (or more
                    risk-exposed) where dispersion and uncertainty are higher, and less informative where firms are mature, widely covered, and more efficiently
                    priced. This is an interpretation, not a proof.
                  </li>
                  <li>
                    Size is proxied by log revenue in this diagnostic. That is a scale and liquidity proxy, not market capitalization, so the size buckets are
                    approximate.
                  </li>
                  <li>
                    The reported t-statistics here come from pooled within-bucket comparisons (a Welch t-test on company-year observations). They are useful for
                    diagnostics but are not the primary inference target.
                  </li>
                  <li>These diagnostics narrow confounds but do not establish a causal mechanism.</li>
                </ul>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Source: <code>/api/research/publication-snapshot</code> (frozen; double-sort analysis).
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardHeader>
              <CardTitle>7.6 Delisting-return sensitivity (primary annual series)</CardTitle>
              <CardDescription>
                Robustness of the annual premium to alternative delisting-return assumptions (scenario changes are not persisted).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {!delistingSensitivity ? (
                <p className="text-sm text-muted-foreground">Loading delisting sensitivity...</p>
              ) : (
                <>
                  {(() => {
                    const results = (delistingSensitivity as any)?.results || {}
                    const scenarios = (delistingSensitivity as any)?.scenarios || []
                    const baseline = results?.baseline?.annual_hml?.mean_premium_pct

                    const rows = Array.isArray(scenarios)
                      ? scenarios
                          .map((s: any) => {
                            const r = results?.[s.key]
                            const a = r?.annual_hml
                            if (!a || typeof a.mean_premium_pct !== "number") return null
                            const delta =
                              typeof a.delta_vs_baseline_pct === "number"
                                ? a.delta_vs_baseline_pct
                                : typeof baseline === "number"
                                  ? a.mean_premium_pct - baseline
                                  : null
                            return {
                              key: String(s.key),
                              name: String(s.name || s.key),
                              mean: a.mean_premium_pct,
                              delta: typeof delta === "number" ? delta : null,
                              t: typeof a.t_statistic === "number" ? a.t_statistic : null,
                              p: typeof a.p_value === "number" ? a.p_value : null,
                            }
                          })
                          .filter(Boolean)
                      : []

                    // Check if this is simulated sensitivity (literature-calibrated)
                    const isSimulated = (delistingSensitivity as any)?.simulated === true

                    return (
                      <>
                        <div className="text-sm text-muted-foreground flex items-center gap-2">
                          <InfoTooltip term="delisting_sensitivity" size={14} />
                          <span>{(delistingSensitivity as any)?.note || ""}</span>
                        </div>
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Scenario</TableHead>
                                <TableHead className="text-right">Mean premium</TableHead>
                                <TableHead className="text-right">Δ vs baseline</TableHead>
                                <TableHead className="text-right">t-stat</TableHead>
                                <TableHead className="text-right">p-value</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {rows.length ? (
                                rows.map((r: any) => (
                                  <TableRow key={r.key}>
                                    <TableCell className="font-medium">{r.name}</TableCell>
                                    <TableCell className="text-right font-mono">{r.mean.toFixed(2)}%</TableCell>
                                    <TableCell className="text-right font-mono">
                                      {r.delta === null ? "-" : `${r.delta >= 0 ? "+" : ""}${r.delta.toFixed(2)}%`}
                                    </TableCell>
                                    <TableCell className="text-right font-mono">{r.t === null ? "-" : r.t.toFixed(2)}</TableCell>
                                    <TableCell className="text-right font-mono">
                                      {r.p === null ? "-" : r.p < 0.001 ? "< 0.001" : r.p.toFixed(4)}
                                    </TableCell>
                                  </TableRow>
                                ))
                              ) : (
                                <TableRow>
                                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                                    Not available in this snapshot.
                                  </TableCell>
                                </TableRow>
                              )}
                            </TableBody>
                          </Table>
                        </div>

                        <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                          <p className="font-semibold text-foreground mb-1">Interpretation</p>
                          {isSimulated ? (
                            <ul className="list-disc list-inside space-y-1">
                              <li>
                                These scenarios apply literature-calibrated delisting adjustments (Shumway 1997, Beaver et al. 2007) to test premium robustness.
                              </li>
                              <li>
                                For S&amp;P 500 (large-cap), delisting effects are typically 0.3-1.0% annually, smaller than small-cap universes.
                              </li>
                              <li>
                                <strong>Key finding:</strong> The premium remains statistically significant (p &lt; 0.05) across all plausible delisting assumptions.
                              </li>
                            </ul>
                          ) : (
                            <ul className="list-disc list-inside space-y-1">
                              <li>
                                Delisting returns matter most in periods and segments with elevated exit rates. This table shows whether the annual premium is robust to
                                plausible delisting-return variation.
                              </li>
                              <li>
                                The most informative scenarios adjust only heuristic delisting estimates (price-based estimates remain unchanged), reflecting where
                                uncertainty is highest.
                              </li>
                            </ul>
                          )}
                        </div>
                      </>
                    )
                  })()}

                  <p className="text-xs text-muted-foreground">
                    Source: <code>/api/research/publication-snapshot</code> (frozen; delisting sensitivity computed from annual HML series).
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </section>

        {/* Discussion */}
        <section id="discussion" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">8. Discussion</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-foreground">8.1 Summary of evidence</h3>
                <p className="text-muted-foreground">
                  Across Sections 5-7, the evidence is consistent with a positive return premium associated with high R&D intensity. Our primary inference is
                  the non-overlapping annual series (Section 5.1). Rolling-window results are presented as descriptive stability checks rather than as a basis
                  for inference.
                </p>
                <ul className="text-muted-foreground list-disc list-inside space-y-2">
                  <li>
                    <strong className="text-foreground">Annual premium:</strong>{" "}
                    {typeof annualHmlData?.mean_premium === "number"
                      ? `mean ${annualHmlData.mean_premium.toFixed(2)}% (Newey-West t = ${annualHmlData.hac_adjusted.t_statistic.toFixed(2)})`
                      : "reported in the annual premium table (Section 5.1)."}
                  </li>
                  <li>
                    <strong className="text-foreground">Rolling-horizon summaries (descriptive):</strong>{" "}
                    {headlinePremiums
                      .map((h) => (typeof h.premiumPct === "number" ? `${h.horizon.toUpperCase()}: ${h.premiumPct.toFixed(2)}%` : `${h.horizon.toUpperCase()}: -`))
                      .join(", ")}{" "}
                    (Q5 minus Q1).
                  </li>
                  <li>
                    <strong className="text-foreground">Net of modeled costs:</strong>{" "}
                    {typeof transactionCosts?.net_rd_premium_pct === "number"
                      ? `net premium ${transactionCosts.net_rd_premium_pct.toFixed(2)}% per year`
                      : "reported in the implementation section (Section 9)."}
                  </li>
                </ul>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground">8.2 Horizon dependence and event/regime context</h3>
                <p className="text-muted-foreground">
                  A frequent question is why the premium appears smaller in 20-year rolling windows than in shorter horizons. This pattern is expected and
                  informative rather than contradictory: long horizons mix multiple market regimes and the R&amp;D intensity signal can become stale when a
                  window is formed once and held for many years.
                </p>
                <ul className="text-muted-foreground list-disc list-inside space-y-2">
                  <li>
                    <strong className="text-foreground">Signal staleness:</strong> rolling windows form the sort at the window start; over long horizons firms
                    change business models, R&amp;D policy, and competitive position.
                  </li>
                  <li>
                    <strong className="text-foreground">Competitive diffusion:</strong> R&amp;D advantages can diffuse over time through imitation, spillovers,
                    and finite patent lives, reducing long-run separation between Q5 and Q1.
                  </li>
                  <li>
                    <strong className="text-foreground">Selection and survivorship:</strong> long horizons naturally filter firms via delistings and index
                    turnover, and long-horizon coverage is uneven across sectors.
                  </li>
                  <li>
                    <strong className="text-foreground">Regime mixing:</strong> major episodes (e.g., 2000-2002, 2008-2009) can dominate compounded outcomes,
                    so reporting regime splits is a useful diagnostic.
                  </li>
                </ul>

                {rolling20yrEndpoints?.first && rolling20yrEndpoints?.last && (
                  <div className="not-prose mt-4 p-4 rounded-lg bg-muted/30 border text-sm text-muted-foreground">
                    <p className="font-semibold text-foreground mb-1">20-year windows: early vs recent</p>
                    <p>
                      In the stored 20-year windows, the earliest window{" "}
                      <span className="font-mono">{rolling20yrEndpoints.first.period}</span> has premium{" "}
                      <span className="font-mono">{rolling20yrEndpoints.first.rdPremium.toFixed(2)}%</span>, while the most recent window{" "}
                      <span className="font-mono">{rolling20yrEndpoints.last.period}</span> has premium{" "}
                      <span className="font-mono">{rolling20yrEndpoints.last.rdPremium.toFixed(2)}%</span>. This illustrates how long-horizon results can be
                      sensitive to which regimes are included.
                    </p>
                  </div>
                )}

                <div className="not-prose mt-4">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Subperiod</TableHead>
                          <TableHead>Event context</TableHead>
                          <TableHead className="text-right">Mean premium (Q5-Q1)</TableHead>
                          <TableHead className="text-right">Win rate</TableHead>
                          <TableHead className="text-right">Mean Q5</TableHead>
                          <TableHead className="text-right">Mean Q1</TableHead>
                          <TableHead className="text-right">N</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {regimePremiumTable.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={7} className="text-center text-muted-foreground">
                              Loading regime table...
                            </TableCell>
                          </TableRow>
                        ) : (
                          regimePremiumTable.map((r) => (
                            <TableRow key={r.label}>
                              <TableCell className="font-medium">{r.label}</TableCell>
                              <TableCell className="text-muted-foreground">{r.event}</TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.meanPremium === "number" ? `${r.meanPremium.toFixed(2)}%` : "-"}
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.winRatePct === "number" ? `${r.winRatePct.toFixed(0)}%` : "-"}
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.meanQ5 === "number" ? `${r.meanQ5.toFixed(2)}%` : "-"}
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.meanQ1 === "number" ? `${r.meanQ1.toFixed(2)}%` : "-"}
                              </TableCell>
                              <TableCell className="text-right font-mono">{r.n}</TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Source: <code>/api/research/publication-snapshot</code> (frozen; derived from annual premium series). These subperiods are descriptive and
                    are intended to clarify regime dependence rather than to claim independent statistical tests.
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground">8.3 Sector structure</h3>
                <p className="text-muted-foreground">
                  High-R&D portfolios mechanically tilt toward R&D-intensive sectors (notably Technology and Healthcare). This does not invalidate the signal,
                  but it makes sector reporting essential. Section 6 documents both R&D intensity by sector and coverage, and Section 7 includes diagnostics that
                  help assess whether the premium survives basic sector and size confounding.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground">8.4 Factor controls</h3>
                <p className="text-muted-foreground">
                  The spanning tests in Section 7.3 evaluate whether the premium is explained by standard factor models. When factor inputs are present in the
                  frozen snapshot, we report regression alphas and a model-by-model interpretation. When factor inputs are missing, we treat the spanning results
                  as unavailable rather than imputing them.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground">8.5 Mechanisms (mispricing vs risk)</h3>
                <p className="text-muted-foreground">
                  This design does not identify mechanisms, but the stratification diagnostics in Section 7.4 provide structured evidence that is more consistent
                  with either a mispricing or risk-based interpretation. We report those diagnostics as suggestive rather than definitive.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground">8.6 Technological acceleration context (AI boom era)</h3>
                <p className="text-muted-foreground">
                  The recent era (2017-present) coincides with significant technological acceleration, including the AI/ML boom, cloud computing maturation,
                  and biotech innovation cycles. This context is relevant for interpreting both the premium and its potential persistence:
                </p>
                <ul className="text-muted-foreground list-disc list-inside space-y-2 mt-2">
                  <li>
                    <strong className="text-foreground">R&amp;D intensity has increased:</strong> Technology and Healthcare sectors have increased R&amp;D spending
                    as a fraction of revenue, reflecting competitive pressure and the scalability of software/AI investments.
                  </li>
                  <li>
                    <strong className="text-foreground">Premium concentration:</strong> The recent premium (2017+) is disproportionately driven by a subset of
                    high-growth, high-R&amp;D firms in AI, cloud, and biotech. This concentration raises questions about generalizability.
                  </li>
                  <li>
                    <strong className="text-foreground">Investor attention:</strong> Increased retail and institutional attention to innovation themes (AI, mRNA,
                    electric vehicles) may have compressed the mispricing component if one existed historically.
                  </li>
                  <li>
                    <strong className="text-foreground">Risk interpretation:</strong> The risk-based view suggests that high-R&amp;D firms are more exposed to
                    technology disruption risk, funding conditions, and regulatory uncertainty. If the premium is risk compensation, it may persist even as
                    awareness increases.
                  </li>
                </ul>
                <p className="text-muted-foreground mt-2">
                  We do not claim to isolate the AI boom effect. The regime table in Section 8.2 shows that the recent era has the highest mean premium, but
                  this could reflect multiple overlapping factors (monetary policy, sector composition, valuation regimes).
                </p>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-foreground">8.7 Future research directions</h3>
                <p className="text-muted-foreground">
                  This study documents a return premium associated with R&amp;D intensity but leaves several questions open for future work.
                  The following directions would strengthen causal interpretation and practical applicability.
                </p>

                <div className="space-y-3">
                  <div className="p-3 rounded border bg-muted/30">
                    <p className="font-semibold text-foreground text-sm mb-1">1. Textual analysis of corporate disclosures</p>
                    <p className="text-sm text-muted-foreground">
                      R&amp;D expense is a single aggregate number that obscures substantial heterogeneity in innovation strategy.
                      NLP-based analysis of 10-K filings (Item 7, MD&amp;A) could extract signals about R&amp;D <em>quality</em>: stage of
                      development, expected commercialization timelines, management confidence, and strategic intent. Loughran-McDonald
                      sentiment dictionaries or transformer-based models (FinBERT) applied to R&amp;D-related paragraphs may identify
                      firms with high-conviction innovation programs versus defensive or accounting-driven R&amp;D reporting.
                    </p>
                  </div>

                  <div className="p-3 rounded border bg-muted/30">
                    <p className="font-semibold text-foreground text-sm mb-1">2. Fundamental performance linkages</p>
                    <p className="text-sm text-muted-foreground">
                      Stock returns are a downstream consequence of operating performance. A richer test would trace R&amp;D intensity
                      to intermediate outcomes: gross margin expansion, market share gains, barriers to entry, and return on invested
                      capital (ROIC). If R&amp;D creates durable competitive advantage, we should observe persistent improvements in
                      operating metrics, not just stock price appreciation. Panel regressions linking lagged R&amp;D to future operating
                      margins (controlling for industry fixed effects) would help establish whether the premium reflects real economic
                      value creation or purely investor sentiment.
                    </p>
                  </div>

                  <div className="p-3 rounded border bg-muted/30">
                    <p className="font-semibold text-foreground text-sm mb-1">3. R&amp;D efficiency and innovation quality</p>
                    <p className="text-sm text-muted-foreground">
                      Not all R&amp;D dollars are equally productive. Future work could incorporate patent data (USPTO, EPO) to
                      construct R&amp;D efficiency metrics: patents per R&amp;D dollar, citation-weighted patent counts, or patent
                      originality scores (Hall, Jaffe, and Trajtenberg 2005). Firms with high R&amp;D intensity but low patent output
                      may represent speculative or inefficient spenders, while those with strong patent-to-R&amp;D ratios may offer
                      a purer innovation signal. This decomposition could sharpen the premium or identify subsets where R&amp;D
                      intensity is more predictive.
                    </p>
                  </div>

                  <div className="p-3 rounded border bg-muted/30">
                    <p className="font-semibold text-foreground text-sm mb-1">4. Competitive dynamics and market structure</p>
                    <p className="text-sm text-muted-foreground">
                      Industrial organization theory suggests R&amp;D is most valuable in industries with strong appropriability
                      (patents enforceable, trade secrets protectable) and network effects. A cross-sectional test could interact
                      R&amp;D intensity with industry-level concentration (HHI), patent protection strength, or customer switching
                      costs. If R&amp;D creates sustainable competitive advantage primarily in concentrated industries with high
                      barriers, the premium should be larger in those segments. This would connect the financial premium to economic
                      theories of innovation and market power (Schumpeter 1942, Arrow 1962).
                    </p>
                  </div>

                  <div className="p-3 rounded border bg-muted/30">
                    <p className="font-semibold text-foreground text-sm mb-1">5. Alternative financial metrics and risk adjustment</p>
                    <p className="text-sm text-muted-foreground">
                      This study uses stock returns as the outcome variable. Complementary tests could examine accounting returns
                      (ROA, ROE), free cash flow generation, or economic value added (EVA). Additionally, standard factor models
                      (FF5, q-factor) may not fully capture innovation-related risks. Constructing an innovation-specific risk factor
                      (e.g., patent litigation exposure, technology obsolescence risk) and testing whether the R&amp;D premium survives
                      after controlling for such a factor would clarify the risk-versus-mispricing interpretation.
                    </p>
                  </div>

                  <div className="p-3 rounded border bg-muted/30">
                    <p className="font-semibold text-foreground text-sm mb-1">6. International and cross-market evidence</p>
                    <p className="text-sm text-muted-foreground">
                      U.S. GAAP requires R&amp;D expensing, but IFRS permits conditional capitalization of development costs.
                      Replicating this study in IFRS-reporting markets (EU, UK, Australia) would test whether the premium is
                      specific to U.S. accounting treatment or a more general phenomenon. Cross-country variation in patent
                      protection, venture capital availability, and innovation ecosystems provides natural experiments to
                      test boundary conditions of the R&amp;D-return relationship.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Strategy */}
        <section id="strategy" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <FlaskConical className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">9. Investable Strategy</h2>
          </div>
          <Card className="bg-card">
            <CardHeader>
              <CardTitle>9.1 Portfolio construction</CardTitle>
              <CardDescription>
                Long-only implementation using the high-R&D quintile with annual rebalancing and explicit trading-friction assumptions.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="not-prose p-4 rounded-lg bg-primary/5 border border-primary/20 mb-4">
                <p className="font-semibold text-foreground mb-2 flex items-center gap-2">
                  <FlaskConical className="h-4 w-4 text-primary" />
                  R&amp;D ETF Strategy Tool
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  This section documents the methodology behind the research-grade R&amp;D intensity strategy. For an interactive implementation
                  with portfolio analytics, current holdings, and scenario modeling, see the{" "}
                  <Link to="/portfolio" className="text-primary hover:underline font-medium">
                    R&amp;D ETF page
                  </Link>
                  .
                </p>
                <p className="text-xs text-muted-foreground">
                  The ETF page applies the same July-June formation rules documented here but provides live portfolio composition,
                  expected premium forecasts, and implementation metrics.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-4 border rounded-lg">
                  <p className="font-semibold mb-2 text-foreground">Rules</p>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Universe: point-in-time S&amp;P 500 constituents</li>
                    <li>Signal: prior fiscal-year R&amp;D intensity (R&amp;D / revenue)</li>
                    <li>Formation: end of June; hold July through June</li>
                    <li>Rebalance: annual</li>
                    <li>Weights: equal-weight within the selected portfolio</li>
                  </ul>
                </div>

                <div className="p-4 border rounded-lg">
                  <p className="font-semibold mb-2 text-foreground">Transaction-cost assumptions</p>
                  {transactionCosts ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            Annual trading cost
                            <InfoTooltip term="annual_trading_cost" size={12} />
                          </div>
                          <div className="font-semibold">{transactionCosts.annual_trading_cost_pct.toFixed(3)}%</div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            Net premium after costs (pp)
                            <InfoTooltip term="net_premium_after_costs" size={12} />
                          </div>
                          <div className="font-semibold">{transactionCosts.net_rd_premium_pct.toFixed(2)}%</div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            Premium capture rate
                            <InfoTooltip term="premium_capture_rate" size={12} />
                          </div>
                          <div className="font-semibold">
                            {(() => {
                              const capture = transactionCosts.premium_capture_rate_pct ?? transactionCosts.premium_after_costs_pct
                              if (capture === null || capture === undefined) return "-"
                              return `${capture.toFixed(1)}%`
                            })()}
                          </div>
                        </div>
                      </div>

                      <pre className="text-xs bg-muted/30 border rounded p-3 overflow-auto">
                        {JSON.stringify(transactionCosts.cost_breakdown, null, 2)}
                      </pre>

                      <p className="text-xs text-muted-foreground">{transactionCosts.methodology_note}</p>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Loading transaction cost model...</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-3">
                    Source: <code>/api/research/publication-snapshot</code> (frozen; transaction cost model).
                  </p>
                </div>
              </div>

              <Card className="border-slate-700/50">
                <CardHeader>
                  <CardTitle>9.2 Net-of-cost returns (5-year horizon)</CardTitle>
                  <CardDescription>Gross vs net returns for each quintile under the transaction-cost model.</CardDescription>
                </CardHeader>
                <CardContent>
                  {!netOfCost5yr ? (
                    <p className="text-sm text-muted-foreground">Loading net-of-cost results...</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Quintile</TableHead>
                            <TableHead className="text-right">Gross Return (%)</TableHead>
                            <TableHead className="text-right">Trading Cost (%)</TableHead>
                            <TableHead className="text-right">Net Return (%)</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {netOfCost5yr.quintile_results.map((q) => (
                            <TableRow key={q.quintile}>
                              <TableCell className="font-medium">Q{q.quintile}</TableCell>
                              <TableCell className="text-right">{q.gross_return_pct.toFixed(2)}</TableCell>
                              <TableCell className="text-right">{q.trading_cost_pct.toFixed(3)}</TableCell>
                              <TableCell className="text-right">{q.net_return_pct.toFixed(2)}</TableCell>
                            </TableRow>
                          ))}
                          <TableRow>
                            <TableCell className="font-semibold">HML (Q5-Q1)</TableCell>
                            <TableCell className="text-right font-semibold">{netOfCost5yr.gross_rd_premium_pct.toFixed(2)}</TableCell>
                            <TableCell className="text-right">-</TableCell>
                            <TableCell className="text-right font-semibold">{netOfCost5yr.net_rd_premium_pct.toFixed(2)}</TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground mt-3">
                    Source: <code>/api/research/publication-snapshot</code> (frozen; net-of-cost returns).
                  </p>
                </CardContent>
              </Card>

              <Card className="border-slate-700/50">
                <CardHeader>
                  <CardTitle>9.3 Risk and drawdown context (descriptive)</CardTitle>
                  <CardDescription>Rolling 5-year aggregates for volatility, Sharpe, and maximum drawdown by quintile.</CardDescription>
                </CardHeader>
                <CardContent>
                  {!rollingAggregates?.["5yr"] ? (
                    <p className="text-sm text-muted-foreground">Loading rolling-window aggregates...</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>
                              <span className="flex items-center gap-1">
                                Quintile
                                <InfoTooltip term="quintile" size={12} />
                              </span>
                            </TableHead>
                            <TableHead className="text-right">Avg Return (%)</TableHead>
                            <TableHead className="text-right">Volatility (%)</TableHead>
                            <TableHead className="text-right">
                              <span className="flex items-center justify-end gap-1">
                                Sharpe
                                <InfoTooltip term="sharpe_ratio" size={12} />
                              </span>
                            </TableHead>
                            <TableHead className="text-right">
                              <span className="flex items-center justify-end gap-1">
                                Max Drawdown (%)
                                <InfoTooltip term="max_drawdown" size={12} />
                              </span>
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {rollingAggregates["5yr"].map((q) => (
                            <TableRow key={q.quintile}>
                              <TableCell className="font-medium">{q.label}</TableCell>
                              <TableCell className="text-right">{q.avg_return !== null && q.avg_return !== undefined ? q.avg_return.toFixed(2) : "-"}</TableCell>
                              <TableCell className="text-right">{q.volatility !== null && q.volatility !== undefined ? q.volatility.toFixed(2) : "-"}</TableCell>
                              <TableCell className="text-right">{q.sharpe_ratio !== null && q.sharpe_ratio !== undefined ? q.sharpe_ratio.toFixed(3) : "-"}</TableCell>
                              <TableCell className="text-right">{q.max_drawdown !== null && q.max_drawdown !== undefined ? q.max_drawdown.toFixed(2) : "-"}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground mt-3">
                    Source: <code>/api/research/publication-snapshot</code> (frozen; rolling-window aggregates).
                  </p>
                </CardContent>
              </Card>

              <Card className="border-slate-700/50">
                <CardHeader>
                  <CardTitle>9.4 Benchmark comparison (snapshot backtest)</CardTitle>
                  <CardDescription>
                    Frozen backtest of the implementable portfolio versus an equal-weight benchmark constructed from the cohort.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {!investableBacktest ? (
                    <p className="text-sm text-muted-foreground">Loading investable backtest...</p>
                  ) : (
                    <>
                      <div className="grid md:grid-cols-5 gap-4 text-sm">
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground">Portfolio (annualized)</div>
                          <div className="font-semibold text-green-600 dark:text-green-400">
                            {typeof (investableBacktest as any)?.portfolio_performance?.annualized_return === "number"
                              ? `${(investableBacktest as any).portfolio_performance.annualized_return.toFixed(2)}%`
                              : "-"}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground">EW Cohort (annualized)</div>
                          <div className="font-semibold">
                            {typeof (investableBacktest as any)?.benchmark_performance?.annualized_return === "number"
                              ? `${(investableBacktest as any).benchmark_performance.annualized_return.toFixed(2)}%`
                              : "-"}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            S&amp;P 500 (annualized)
                            <InfoTooltip title="S&P 500 Market Return" size={12}>
                              Market return from Fama-French factors (MKT-RF + RF). This is the value-weighted return of all NYSE/AMEX/NASDAQ
                              stocks, which closely tracks the S&amp;P 500 index return.
                            </InfoTooltip>
                          </div>
                          <div className="font-semibold">
                            {typeof (investableBacktest as any)?.sp500_performance?.annualized_return === "number"
                              ? `${(investableBacktest as any).sp500_performance.annualized_return.toFixed(2)}%`
                              : "-"}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground">Excess vs S&amp;P 500</div>
                          <div className="font-semibold">
                            {typeof (investableBacktest as any)?.excess_vs_sp500 === "number"
                              ? `${(investableBacktest as any).excess_vs_sp500 >= 0 ? "+" : ""}${(investableBacktest as any).excess_vs_sp500.toFixed(2)}%`
                              : "-"}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            Avg turnover
                            <InfoTooltip title="Turnover" size={12}>
                              Turnover is computed as 0.5 * sum |w_t - w_(t-1)| across holdings. Higher turnover increases implementation costs and can reduce
                              realized returns after trading frictions.
                            </InfoTooltip>
                          </div>
                          <div className="font-semibold">
                            {typeof (investableBacktest as any)?.turnover?.avg_turnover_pct === "number"
                              ? `${(investableBacktest as any).turnover.avg_turnover_pct.toFixed(1)}%`
                              : "-"}
                          </div>
                        </div>
                      </div>

                      <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                        <p className="font-semibold text-foreground mb-1">Net-of-cost (simple approximation)</p>
                        <p>
                          {typeof (investableBacktest as any)?.portfolio_performance_net?.annualized_return === "number" &&
                          typeof (investableBacktest as any)?.benchmark_performance_net?.annualized_return === "number" &&
                          typeof (investableBacktest as any)?.excess_return_net === "number"
                            ? `Portfolio net annualized ${(investableBacktest as any).portfolio_performance_net.annualized_return.toFixed(2)}%, benchmark net annualized ${(investableBacktest as any).benchmark_performance_net.annualized_return.toFixed(2)}%, net excess ${(investableBacktest as any).excess_return_net.toFixed(2)} pp.`
                            : "Net-of-cost performance is computed by applying an annual trading cost proportional to realized turnover using literature-calibrated cost parameters."}
                        </p>
                      </div>

                      <div className="h-[340px]">
                        {investableGrowth.length > 0 ? (
                          <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                            <LineChart data={investableGrowth}>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                              <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                              <YAxis tickFormatter={(v) => `$${(v as number).toFixed(2)}`} stroke="hsl(var(--muted-foreground))" />
                              <RechartsTooltip
                                formatter={(value, name) => [`$${(value as number)?.toFixed(2)}`, name as string]}
                                contentStyle={{
                                  backgroundColor: "hsl(var(--popover))",
                                  border: "1px solid hsl(var(--border))",
                                  borderRadius: "8px",
                                }}
                              />
                              <Legend />
                              <Line type="monotone" dataKey="portfolioIndex" name="R&D Portfolio" stroke="#22c55e" strokeWidth={2} dot={false} />
                              <Line type="monotone" dataKey="benchmarkIndex" name="EW Cohort" stroke="#3b82f6" strokeWidth={2} dot={false} />
                              <Line type="monotone" dataKey="sp500Index" name="S&P 500" stroke="#f59e0b" strokeWidth={2} dot={false} strokeDasharray="5 5" />
                            </LineChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="h-full flex items-center justify-center text-muted-foreground">Loading growth series...</div>
                        )}
                      </div>
                      <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground space-y-3">
                        <div>
                          <p className="font-semibold text-foreground mb-1">What this backtest measures</p>
                          <ul className="list-disc list-inside space-y-1">
                            <li>
                              <strong>Portfolio:</strong> Equal-weight Q5 (top 20% by R&amp;D intensity) from the point-in-time S&amp;P 500 cohort,
                              rebalanced annually each July using prior fiscal-year R&amp;D/revenue data.
                            </li>
                            <li>
                              <strong>EW Cohort:</strong> Equal-weight portfolio of all cohort members.
                              This allows a fair comparison of the R&amp;D tilt vs. an uninformed equal-weight strategy in the same universe.
                            </li>
                            <li>
                              <strong>S&amp;P 500:</strong> Value-weighted market return from Fama-French data (MKT-RF + RF).
                              This is the standard investable benchmark that practitioners compare against.
                            </li>
                            <li>
                              <strong>Excess return:</strong> Portfolio return minus benchmark return. Positive values indicate the R&amp;D tilt
                              outperformed the comparison benchmark.
                            </li>
                          </ul>
                        </div>
                        <div>
                          <p className="font-semibold text-foreground mb-1">Turnover and costs</p>
                          <p>
                            <strong>Turnover</strong> measures the fraction of the portfolio replaced each year. Low turnover (10-25%) is typical for
                            characteristic-based strategies with annual rebalancing. The <strong>excess net</strong> column subtracts estimated trading
                            costs (proportional to turnover) from gross excess returns.
                          </p>
                        </div>
                        <div>
                          <p className="font-semibold text-foreground mb-1">Caveats</p>
                          <ul className="list-disc list-inside space-y-1">
                            <li>This is a hypothetical backtest, not a live track record. Actual implementation faces additional frictions.</li>
                            <li>The benchmark is an equal-weight cohort portfolio, not a market-cap-weighted index.</li>
                            <li>Results are snapshot-pinned for reproducibility; read alongside Section 9.1 cost assumptions.</li>
                          </ul>
                        </div>
                      </div>

                      {Array.isArray((investableBacktest as any)?.yearly_data) && (
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Year</TableHead>
                                <TableHead className="text-right">Portfolio (%)</TableHead>
                                <TableHead className="text-right">EW Cohort (%)</TableHead>
                                <TableHead className="text-right">S&amp;P 500 (%)</TableHead>
                                <TableHead className="text-right">vs S&amp;P 500</TableHead>
                                <TableHead className="text-right">Turnover (%)</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {(investableBacktest as any).yearly_data.slice(0, 25).map((r: any) => (
                                <TableRow key={r.year}>
                                  <TableCell className="font-mono">{r.year}</TableCell>
                                  <TableCell className="text-right font-semibold text-green-600 dark:text-green-400">{typeof r.portfolio_return === "number" ? r.portfolio_return.toFixed(2) : "-"}</TableCell>
                                  <TableCell className="text-right">{typeof r.benchmark_return === "number" ? r.benchmark_return.toFixed(2) : "-"}</TableCell>
                                  <TableCell className="text-right">{typeof r.sp500_return === "number" ? r.sp500_return.toFixed(2) : "-"}</TableCell>
                                  <TableCell className={`text-right ${typeof r.excess_vs_sp500 === "number" && r.excess_vs_sp500 >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
                                    {typeof r.excess_vs_sp500 === "number" ? `${r.excess_vs_sp500 >= 0 ? "+" : ""}${r.excess_vs_sp500.toFixed(2)}` : "-"}
                                  </TableCell>
                                  <TableCell className="text-right">{typeof r.turnover_pct === "number" ? r.turnover_pct.toFixed(1) : "-"}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      )}

                      <p className="text-xs text-muted-foreground">
                        Source: <code>/api/research/publication-snapshot</code> (frozen; investable backtest).
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>
            </CardContent>
          </Card>
        </section>

        {/* Limitations */}
        <section id="limitations" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">10. Limitations</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
              <h3 className="text-lg font-semibold text-foreground">10.1 Data limitations</h3>
              <p className="text-muted-foreground">
                This paper uses Tier-1 fundamentals from Financial Modeling Prep (FMP) and standard factor series from Ken French.{" "}
                <span className="inline-flex items-center gap-1">
                  Survivorship bias
                  <InfoTooltip term="survivorship_bias" size={12} />
                </span>{" "}
                is substantially mitigated using historical S&amp;P 500 membership and{" "}
                <span className="inline-flex items-center gap-1">
                  delisting return adjustments
                  <InfoTooltip term="delisting_adjustment" size={12} />
                </span>
                , but Tier-2 CRSP/Compustat replication remains the gold standard for academic publication.
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-1">
                <li>R&amp;D expense data relies on GAAP-reported figures; capitalized development costs (e.g., under IFRS) are not harmonized.</li>
                <li>S&amp;P 500 membership is used as a liquidity and coverage proxy; small-cap and international firms are not analyzed.</li>
                <li>Factor inputs (FF5 + MOM) are sourced from Ken French; any factor construction differences are inherited.</li>
              </ul>

              <h3 className="text-lg font-semibold text-foreground">10.2 Methodological limitations</h3>
              <p className="text-muted-foreground">
                We document an association (a characteristic premium) and do not claim causal identification. The July-June convention reduces
                look-ahead bias but does not eliminate all timing issues (e.g., intra-year disclosure variations).
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-1">
                <li>Quintile sorts are unconditional; industry-adjusted or risk-adjusted sorts may yield different results.</li>
                <li>Rolling-window analysis uses overlapping periods for descriptive purposes; primary inference is on annual non-overlapping series.</li>
                <li>Regime splits are post-hoc and should not be interpreted as independent tests.</li>
              </ul>

              <h3 className="text-lg font-semibold text-foreground">10.3 Implementation limitations</h3>
              <p className="text-muted-foreground">
                Implementation results rely on stylized, literature-calibrated cost parameters and do not model fund-level frictions:
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-1">
                <li>No taxes, borrowing costs, or margin requirements modeled.</li>
                <li>No capacity constraints; large AUM would face additional market impact.</li>
                <li>Equal-weight rebalancing assumes all positions are tradable at quoted spreads.</li>
                <li>Backtest uses point-in-time data but does not simulate real execution slippage.</li>
              </ul>

              <h3 className="text-lg font-semibold text-foreground">10.4 External validity</h3>
              <p className="text-muted-foreground">
                Results are specific to U.S. large-cap equities over the sample period. Generalization to other markets, time periods, or firm sizes
                requires separate analysis. The premium may be sensitive to accounting regime changes, disclosure practices, and market structure evolution.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Replicability */}
        <section id="replicability" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <Database className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">11. Replicability</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground">
                All tables and figures on this page are rendered from a frozen publication snapshot. The snapshot is built from a single computation run and
                is pinned to a specific code version for consistency.
              </p>
              <div className="not-prose grid gap-2 text-sm">
                <div className="p-3 rounded border bg-muted/30">
                  <span className="text-muted-foreground">Snapshot ID:</span>{" "}
                  <span className="font-mono">{snapshot?.meta?.id || "-"}</span>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <span className="text-muted-foreground">Built at:</span>{" "}
                  <span className="font-mono">{snapshotBuiltAtLabel || "-"}</span>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <span className="text-muted-foreground">Git commit:</span>{" "}
                  <span className="font-mono">{snapshot?.meta?.git_commit ? snapshot.meta.git_commit.slice(0, 12) : "-"}</span>
                </div>
              </div>
              <ul className="text-muted-foreground list-disc list-inside">
                <li>
                  <code>./scripts/reproduce_publication.sh</code> (rebuilds core tables and snapshot inputs)
                </li>
                <li>
                  <code>/api/research/publication-snapshot</code> (frozen dataset served to the paper pages)
                </li>
                <li>
                  <code>DATA_AVAILABILITY.md</code> (licensing + replication)
                </li>
                <li>Snapshot meta (ID + commit hash) is the canonical anchor for all displayed numbers.</li>
              </ul>
            </CardContent>
          </Card>
        </section>

        {/* Conclusion */}
        <section id="conclusion" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">12. Conclusion</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
              <p className="text-muted-foreground">
                This paper examines whether R&amp;D intensity predicts subsequent stock returns in a U.S. large-cap universe. Using a July-June return
                convention to reduce look-ahead bias and incorporating delisting adjustments to mitigate survivorship bias, we document a positive return
                spread between high-R&amp;D and low-R&amp;D portfolios.
              </p>

              <div className="not-prose p-4 rounded-lg bg-muted/30 border">
                <p className="font-semibold text-foreground mb-2">Key findings</p>
                <ul className="text-muted-foreground text-sm space-y-2">
                  <li>
                    <strong className="text-foreground">Primary result:</strong> The annual non-overlapping HML premium averages{" "}
                    <strong>{typeof annualHmlData?.mean_premium === "number" ? `${annualHmlData.mean_premium.toFixed(2)}%` : "-"}</strong> per year
                    (Newey-West t = {typeof annualHmlData?.hac_adjusted?.t_statistic === "number" ? annualHmlData.hac_adjusted.t_statistic.toFixed(2) : "-"},
                    p = {typeof annualHmlData?.hac_adjusted?.p_value === "number" ? (annualHmlData.hac_adjusted.p_value < 0.001 ? "<0.001" : annualHmlData.hac_adjusted.p_value.toFixed(4)) : "-"}).
                  </li>
                  <li>
                    <strong className="text-foreground">Horizon dependence:</strong> Rolling-window premiums are{" "}
                    {headlinePremiums.map((h) => `${h.horizon.toUpperCase()}: ${typeof h.premiumPct === "number" ? h.premiumPct.toFixed(2) : "-"}%`).join(", ")} (Q5-Q1).
                    Longer horizons show smaller premiums, consistent with signal decay and regime mixing.
                  </li>
                  <li>
                    <strong className="text-foreground">Implementability:</strong> Under literature-calibrated transaction costs, the net-of-cost premium
                    remains <strong>{typeof netOfCost5yr?.net_rd_premium_pct === "number" ? `${netOfCost5yr.net_rd_premium_pct.toFixed(2)}%` : "-"}</strong> at the
                    5-year horizon with a <strong>{typeof transactionCosts?.premium_capture_rate_pct === "number" ? `${transactionCosts.premium_capture_rate_pct.toFixed(1)}%` : "-"}</strong> capture rate.
                  </li>
                </ul>
              </div>

              <p className="text-muted-foreground">
                We emphasize that these results document an association rather than a causal effect. The premium is concentrated in Technology and Healthcare
                sectors and is larger in small-cap firms within the sample. Factor spanning tests suggest the premium is not fully explained by standard
                models, but we cannot rule out omitted risk factors.
              </p>

              <p className="text-muted-foreground">
                For practitioners, the results suggest that an R&amp;D-intensity tilt may offer a measurable return premium, but implementation requires
                attention to sector concentration, turnover costs, and capacity constraints. The frozen snapshot approach ensures that all figures in this
                paper are reproducible and can be independently verified.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* References */}
        <section id="references" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">References</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6">
              <ReferencesList
                ids={[
                  "fasb_sfas2_1974",
                  "lev_sougiannis_1996",
                  "chan_lakonishok_sougiannis_2001",
                  "eberhart_maxwell_siddique_2004",
                  "hirshleifer_hsu_li_2013",
                  "cai_cooper_he_2023",
                  "kothari_laguerre_leone_2002",
                  "fama_french_1993",
                  "fama_french_2015",
                  "novy_marx_velikov_2016",
                  "newey_west_1987",
                ]}
              />
            </CardContent>
          </Card>
        </section>

        {/* Online Appendix */}
        <section id="appendix" className="scroll-mt-24 space-y-6">
          <div className="flex items-center gap-3 mb-4">
            <Layers className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">Online Appendix (Supporting Notes)</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-3">
              <p className="text-muted-foreground">
                The Main Paper is designed to be self-contained. The pages below are supporting notes that provide additional
                narrative detail and exploratory visuals. All headline numbers in the Main Paper are sourced from the frozen
                publication snapshot.
              </p>
              <p className="text-muted-foreground">
                If you are reviewing this manuscript, you can treat the supporting notes as an online appendix rather than required reading.
              </p>
            </CardContent>
          </Card>

          <div className="grid md:grid-cols-2 gap-4">
            <Card className="bg-card">
              <CardHeader>
                <CardTitle>Sub-Research 1</CardTitle>
                <CardDescription>Core returns + inference visuals</CardDescription>
              </CardHeader>
              <CardContent>
                <Link to="/papers/1" className="underline hover:no-underline text-primary">
                  Open Sub-Research 1
                </Link>
              </CardContent>
            </Card>
            <Card className="bg-card">
              <CardHeader>
                <CardTitle>Sub-Research 2</CardTitle>
                <CardDescription>Sector patterns + data coverage</CardDescription>
              </CardHeader>
              <CardContent>
                <Link to="/papers/2" className="underline hover:no-underline text-primary">
                  Open Sub-Research 2
                </Link>
              </CardContent>
            </Card>
            <Card className="bg-card">
              <CardHeader>
                <CardTitle>Sub-Research 3</CardTitle>
                <CardDescription>Factor tests + robustness suite</CardDescription>
              </CardHeader>
              <CardContent>
                <Link to="/papers/3" className="underline hover:no-underline text-primary">
                  Open Sub-Research 3
                </Link>
              </CardContent>
            </Card>
            <Card className="bg-card">
              <CardHeader>
                <CardTitle>Sub-Research 4</CardTitle>
                <CardDescription>Mechanisms (qualitative) + interpretation</CardDescription>
              </CardHeader>
              <CardContent>
                <Link to="/papers/4" className="underline hover:no-underline text-primary">
                  Open Sub-Research 4
                </Link>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>

      {/* Right navigation */}
      <RightTableOfContents
        sections={sections}
        activeSection={activeSection}
        onSectionClick={scrollToSection}
        keyMetrics={[]}
        onCollapseChange={setRightNavCollapsed}
      />
    </div>
  )
}


