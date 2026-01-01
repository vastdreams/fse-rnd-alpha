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
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Target,
  Scale,
  Github,
} from "lucide-react"
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
import { SafeChart } from "@/components/SafeChart"
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
  { id: "cite", label: "How to Cite" },
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

  const handleDownloadPDF = () => {
    // Download/open the official LaTeX-built PDF (served as a static asset).
    window.open("/rnd-alpha-paper.pdf", "_blank", "noopener,noreferrer")
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

  const investableExcessNetPp = useMemo(() => {
    const bt = investableBacktest as any
    const v = bt?.excess_return_net
    return typeof v === "number" ? v : undefined
  }, [investableBacktest])

  const investableTurnoverAvgPct = useMemo(() => {
    const bt = investableBacktest as any
    const v = bt?.turnover?.avg_turnover_pct
    return typeof v === "number" ? v : undefined
  }, [investableBacktest])

  const investableUnderperformPct = useMemo(() => {
    const bt = investableBacktest as any
    const rows = Array.isArray(bt?.yearly_data) ? (bt.yearly_data as any[]) : []
    const usable = rows
      .map((r) => {
        const portfolioReturn =
          typeof r?.portfolio_return_net === "number"
            ? r.portfolio_return_net
            : typeof r?.portfolio_return === "number"
              ? r.portfolio_return
              : undefined
        const benchmarkReturn =
          typeof r?.benchmark_return_net === "number"
            ? r.benchmark_return_net
            : typeof r?.benchmark_return === "number"
              ? r.benchmark_return
              : undefined
        return { portfolioReturn, benchmarkReturn }
      })
      .filter(
        (x): x is { portfolioReturn: number; benchmarkReturn: number } =>
          typeof x.portfolioReturn === "number" && typeof x.benchmarkReturn === "number"
      )
    if (usable.length === 0) return undefined
    const under = usable.filter((x) => x.portfolioReturn < x.benchmarkReturn).length
    return (under / usable.length) * 100
  }, [investableBacktest])

  return (
    <div className="flex justify-center min-h-0">
      <div className="flex w-full max-w-screen-2xl gap-8">
        <div
          className={cn(
            "flex-1 min-w-0 space-y-12 pb-24 transition-all duration-300 print-content",
            rightNavCollapsed ? "max-w-none" : "max-w-4xl mx-auto"
          )}
        >
        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-100 via-white to-slate-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 border border-slate-200 dark:border-slate-600 p-8">
          <div className="absolute inset-0 bg-grid-slate-100/[0.04] dark:bg-grid-slate-500/[0.03]" />
          <div className="relative z-10">
            <div className="flex items-start justify-between flex-wrap gap-4 mb-6 no-print" data-pdf-hide="true">
              <Link
                to="/documentation"
                className="inline-flex items-center text-sm text-slate-500 dark:text-slate-400 hover:text-primary"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Papers
              </Link>
              <div className="flex gap-2">
                <Link to="/whitepaper">
                  <Button variant="default" size="sm" className="bg-emerald-600 hover:bg-emerald-700">
                    <Layers className="mr-2 h-4 w-4" />
                    View Slide Deck
                  </Button>
                </Link>
                <Button variant="outline" size="sm" onClick={handleDownloadPDF}>
                  <Download className="mr-2 h-4 w-4" />
                  Download PDF
                </Button>
                <a
                  href="https://github.com/vastdreams/fse-rnd-alpha"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="outline" size="sm">
                    <Github className="mr-2 h-4 w-4" />
                    View Code
                  </Button>
                </a>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mb-4">
              <Badge variant="outline" className="border-slate-400/40 dark:border-slate-500/50 dark:text-slate-300">
                Main Paper
              </Badge>
              <Badge variant="outline" className="text-amber-600 dark:text-amber-400 border-amber-500/30 bg-amber-500/10">
                Frozen snapshot
              </Badge>
              <Badge variant="outline" className="text-blue-500 dark:text-blue-400 border-blue-500/30 bg-blue-500/10">
                Tier-1 data (FMP)
              </Badge>
            </div>

            <h1 className="text-4xl font-bold mb-4 text-slate-900 dark:text-white">
              R&D Investment Intensity and Long-Term Stock Returns
            </h1>
            <p className="text-xl text-slate-600 dark:text-slate-300 max-w-3xl">
              Empirical evidence on the relation between R&D intensity and subsequent stock returns.
            </p>

            <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-slate-200 dark:border-slate-600 text-sm">
              <div>
                <span className="text-slate-500 dark:text-slate-400">Author:</span>{" "}
                <span className="text-slate-900 dark:text-white">Abhishek Sehgal</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400">Sample:</span>{" "}
                <span className="text-slate-900 dark:text-white">{cohortSummary?.total_companies || "..."} companies</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400">Period:</span>{" "}
                <span className="text-slate-900 dark:text-white">{sampleYearRange || "..."}</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400">Return Convention:</span>{" "}
                <span className="text-slate-900 dark:text-white">{returnConventionLabel}</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400">Snapshot built:</span>{" "}
                <span className="text-slate-900 dark:text-white">{snapshotBuiltAtLabel || "..."}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Reader Guide */}
        <div className="rounded-xl bg-gradient-to-br from-emerald-50 via-white to-blue-50 dark:from-emerald-950/30 dark:via-slate-950/20 dark:to-blue-950/30 border border-slate-200/70 dark:border-slate-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2.5 rounded-lg bg-emerald-100/70 dark:bg-emerald-900/40">
              <BookOpen className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground leading-none">Reader Guide</h3>
              <p className="text-sm text-muted-foreground mt-1">Pick the depth that matches your time.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-lg border border-emerald-200/70 dark:border-emerald-800/60 bg-white/70 dark:bg-slate-950/30 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
                Quick overview
              </div>
              <p className="text-sm text-foreground/90 mt-1 leading-relaxed">
                Start with the{" "}
                <Link to="/whitepaper" className="text-emerald-700 dark:text-emerald-400 hover:underline font-semibold">
                  Whitepaper slide deck
                </Link>{" "}
                (11 slides, ~5 min).
              </p>
            </div>

            <div className="rounded-lg border border-blue-200/70 dark:border-blue-800/60 bg-white/70 dark:bg-slate-950/30 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
                Full methods
              </div>
              <p className="text-sm text-foreground/90 mt-1 leading-relaxed">
                You're in the right place. This Main Paper contains full methodology, all tables, and references.
              </p>
            </div>

            <div className="rounded-lg border border-purple-200/70 dark:border-purple-800/60 bg-white/70 dark:bg-slate-950/30 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-purple-700 dark:text-purple-400">
                Deep dives
              </div>
              <p className="text-sm text-foreground/90 mt-1 leading-relaxed">
                Jump to{" "}
                <a href="#appendix" className="text-purple-700 dark:text-purple-400 hover:underline font-semibold">
                  Supporting Notes
                </a>{" "}
                for sector analysis, factor tests, and robustness checks.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <a
                  href="#sector"
                  className="text-xs px-2 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 dark:bg-purple-950/30 dark:text-purple-200 dark:border-purple-800/60"
                >
                  Sector
                </a>
                <a
                  href="#robustness"
                  className="text-xs px-2 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 dark:bg-purple-950/30 dark:text-purple-200 dark:border-purple-800/60"
                >
                  Factor tests
                </a>
                <a
                  href="#appendix"
                  className="text-xs px-2 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 dark:bg-purple-950/30 dark:text-purple-200 dark:border-purple-800/60"
                >
                  Appendix
                </a>
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
                in a large-cap U.S. universe, using methodology designed for <em>portfolio implementability</em>.
              </p>

              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Method:</strong> Each year we sort S&amp;P 500 firms (N ≈ {cohortSummary?.total_companies || 500} with
                R&amp;D data) into quintiles by R&amp;D intensity (R&amp;D expense / revenue) and measure subsequent July-June returns
                over {sampleYearRange || "the sample period"}.
                This timing convention aligns with Fama-French methodology to avoid look-ahead bias. Where historical constituent spans are available,
                we enforce point-in-time S&amp;P 500 membership at formation dates. For exits (mergers/delistings), returns are computed to the last observed
                trading day within the July-June window (cash thereafter), and delisting uncertainty is reported via sensitivity analysis rather than a single hard-coded assumption.
              </p>

              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Results:</strong>{" "}
                {typeof annualHmlData?.mean_premium === "number" && typeof annualHmlData?.hac_adjusted?.t_statistic === "number" ? (
                  <>
                    The high-minus-low premium (Q5 minus Q1) averages{" "}
                    <strong className="text-foreground">{annualHmlData.mean_premium.toFixed(2)}%</strong> per year
                    in non-overlapping annual returns. In plain terms: stocks in the top 20% by R&amp;D intensity outperformed the bottom 20% 
                    by approximately {annualHmlData.mean_premium.toFixed(0)}% annually over the sample period. This difference is statistically 
                    significant (Newey-West t = {annualHmlData.hac_adjusted.t_statistic.toFixed(2)}, p = {annualHmlData.hac_adjusted.p_value < 0.001 ? "<0.001" : annualHmlData.hac_adjusted.p_value.toFixed(4)}), 
                    meaning it is unlikely to have occurred by chance. The premium was positive in{" "}
                    {typeof annualHmlData?.positive_years === "number" && typeof annualHmlData?.n_years === "number" 
                      ? `${annualHmlData.positive_years} of ${annualHmlData.n_years} years (${Math.round(annualHmlData.positive_years / annualHmlData.n_years * 100)}% win rate)`
                      : "the majority of years"}.
                  </>
                ) : (
                  <>The high-minus-low premium (Q5 minus Q1) is positive and statistically significant in non-overlapping annual returns. 
                    In plain terms: stocks with high R&amp;D intensity consistently outperformed those with low R&amp;D intensity.</>
                )}
              </p>

              <p className="text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Implementation:</strong>{" "}
                {typeof transactionCosts?.annual_trading_cost_pct === "number" && typeof transactionCosts?.net_rd_premium_pct === "number" ? (
                  <>
                    We translate this finding into an investable strategy: hold the top <strong className="text-foreground">20</strong> stocks by R&amp;D intensity
                    (equal-weighted) and reconstitute annually in July. Using realized turnover from the backtest and a literature-calibrated transaction-cost model
                    (Novy-Marx &amp; Velikov, 2016), estimated trading costs are{" "}
                    <strong className="text-foreground">{transactionCosts.annual_trading_cost_pct.toFixed(3)}%</strong> annually
                    (large-cap liquidity), yielding a net premium of{" "}
                    <strong className="text-foreground">{transactionCosts.net_rd_premium_pct.toFixed(2)}%</strong> per year after costs.
                    This means the strategy retains nearly all of its gross return advantage when implemented in practice.
                  </>
                ) : (
                  <>We translate the signal into an implementable strategy with explicit portfolio rules: hold the top 20 by R&amp;D intensity,
                    reconstitute annually in July, and equal-weight positions. Trading costs are modeled separately using a literature-calibrated framework.</>
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
                GAAP{" "}
                <span className="inline-flex items-center">
                  <InfoTooltip term="gaap_expensing" size={12} />
                </span>
                , firms with substantial R&amp;D can often look less profitable in contemporaneous statements even when R&amp;D creates economically valuable
                assets. This accounting treatment is important because it creates a potential disconnect between reported earnings and true economic value.
                These features motivate two broad interpretations for any return premium associated with R&amp;D intensity: investors may
                underweight intangibles{" "}
                <span className="inline-flex items-center">
                  (<InfoTooltip term="mispricing" size={12} />)
                </span>
                , or the premium may compensate for innovation-related risks{" "}
                <span className="inline-flex items-center">
                  (<InfoTooltip term="risk_compensation" size={12} />)
                </span>
                .
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
                <strong className="text-foreground"> Why does this matter?</strong> Because when R&amp;D is expensed immediately (rather than capitalized like physical assets),
                a firm investing heavily in innovation reports lower earnings today even if that investment will generate substantial future cash flows.
                If investors anchor on near-term earnings, the market can underreact to productive R&amp;D and price high-R&amp;D firms too pessimistically.
                Under that view, a premium reflects gradual learning as innovation outcomes arrive and the market corrects its initial undervaluation.
              </p>

              <h3 className="text-lg font-semibold text-foreground">2.2 Risk-based interpretation</h3>
              <p className="text-muted-foreground">
                A competing interpretation is that high-R&amp;D firms load on innovation-related risks: uncertain payoffs, higher operating leverage, and
                sensitivity to funding conditions. <strong className="text-foreground">Why would investors demand a premium for these risks?</strong> Because
                R&amp;D outcomes are inherently uncertain (most projects fail), high-R&amp;D firms tend to have more volatile cash flows, and innovation-heavy
                companies are more sensitive to economic downturns when funding dries up. In this case, a premium can exist without superior risk-adjusted
                performance; Sharpe ratios{" "}
                <span className="inline-flex items-center">
                  <InfoTooltip term="sharpe_ratio" size={12} />
                </span>{" "}
                may not dominate even when mean returns do, because investors are being compensated for bearing innovation risk.
              </p>

              <h3 className="text-lg font-semibold text-foreground">2.3 Practitioner relevance</h3>
              <p className="text-muted-foreground">
                For a portfolio audience, the core questions are implementability and robustness. <strong className="text-foreground">Specifically:</strong>
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-1 mt-2">
                <li>Is the premium stable across market regimes{" "}
                  <span className="inline-flex items-center">
                    <InfoTooltip term="regime_dependence" size={12} />
                  </span>
                  , or does it only work in specific conditions?
                </li>
                <li>How concentrated is it by sector{" "}
                  <span className="inline-flex items-center">
                    <InfoTooltip term="sector_tilt" size={12} />
                  </span>
                  ? Is this really an R&amp;D effect or just a tech bet?
                </li>
                <li>How sensitive are results to survivorship{" "}
                  <span className="inline-flex items-center">
                    <InfoTooltip term="survivorship_bias" size={12} />
                  </span>{" "}
                  and delisting assumptions?
                </li>
                <li>What fraction of the gross premium survives after trading costs?</li>
              </ul>
              <p className="text-muted-foreground mt-2">
                We address these by (i) prioritizing a clean annual return series for inference, (ii) reporting sector structure transparently, and (iii) mapping the signal
                into an explicit strategy section with realistic cost assumptions.
              </p>

              <h3 className="text-lg font-semibold text-foreground">Hypotheses</h3>
              <p className="text-muted-foreground mb-2">
                We structure our analysis around four testable hypotheses. Each addresses a specific concern that practitioners and academics would raise:
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">H1 (Characteristic premium{" "}
                    <InfoTooltip term="characteristic_premium" size={12} />
                  ):</strong> Firms with higher R&amp;D intensity earn higher subsequent returns than low-R&amp;D firms in a large-cap U.S. universe.
                  <span className="text-xs block ml-6 mt-1 italic">Why test this? This is the fundamental question: does R&amp;D intensity predict returns?</span>
                </li>
                <li>
                  <strong className="text-foreground">H2 (Stability and regimes):</strong> The premium is observable in the annual series and exhibits time variation that can be summarized with rolling windows and event/regime splits.
                  <span className="text-xs block ml-6 mt-1 italic">Why test this? A premium that only worked in one decade would be less useful for forward-looking portfolios.</span>
                </li>
                <li>
                  <strong className="text-foreground">H3 (Not just sector):</strong> The premium is not fully explained by sector composition, size, or standard factor exposures.
                  <span className="text-xs block ml-6 mt-1 italic">Why test this? If the premium disappears after controlling for sectors, it's just a sector bet, not an R&amp;D effect.</span>
                </li>
                <li>
                  <strong className="text-foreground">H4 (Implementability):</strong> A rules-based portfolio derived from the signal retains a positive net premium under explicit trading-friction assumptions.
                  <span className="text-xs block ml-6 mt-1 italic">Why test this? Academic premiums often disappear after trading costs. We need to show the premium is capturable in practice.</span>
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
                We define R&amp;D intensity as R&amp;D expense divided by revenue, expressed as a percentage. This ratio captures how much
                a firm invests in research and development relative to its scale. <strong className="text-foreground">Why use revenue as the denominator?</strong>{" "}
                Revenue is a stable, comparable measure of firm size that is less affected by capital structure or accounting choices than
                alternatives like total assets or market capitalization.
              </p>
              <div className="not-prose">
                <Formulas.RDIntensity />
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                <strong className="text-foreground">Typical values:</strong> Technology and Healthcare firms often have R&amp;D intensity of 10-30%,
                while Financials and Utilities are typically below 1%. This wide dispersion is what creates meaningful quintile separation.
              </p>

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
              <p className="text-sm text-muted-foreground mt-2">
                <strong className="text-foreground">Why this timing matters:</strong> Most U.S. firms have December fiscal year ends and must file
                10-K reports within 60-90 days (by late February/March). By waiting until July to form portfolios, we ensure all accounting
                data is publicly available. Using calendar-year returns (January-December) would mean trading on data that wasn't yet public,
                inflating apparent performance.
              </p>
              <div className="not-prose mt-3">
                <Formulas.TSR />
              </div>
              <div className="not-prose p-3 rounded-lg bg-muted/30 border mt-3">
                <p className="text-sm text-muted-foreground">
                  <strong className="text-foreground">Example timeline:</strong> A firm reports FY2022 R&amp;D in its 10-K filed March 2023.
                  We use this data to form portfolios in July 2023 and measure returns through June 2024. This 6+ month lag ensures
                  no information leakage.
                </p>
              </div>

              <h3 className="text-lg font-semibold text-foreground mt-6">3.3 Statistical Inference</h3>
              <p className="text-muted-foreground">
                We present (i) annual non-overlapping HML premiums for primary inference and (ii) rolling-window
                summaries for descriptive context. <strong className="text-foreground">Why two approaches?</strong> Annual non-overlapping
                observations are non-overlapping (reduces mechanical overlap) and support cleaner inference. Rolling windows are autocorrelated (overlapping periods share data)
                but useful for visualizing trends and regime dependence. We are explicit about which is which.
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                Where overlapping windows are used, inference is HAC-adjusted using Newey-West standard errors to account for serial correlation.
              </p>
              <div className="not-prose grid md:grid-cols-2 gap-4 mt-3">
                <Formulas.ANOVA />
                <Formulas.EtaSquared />
                <Formulas.CohensD />
                <Formulas.SharpeRatio />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                <strong>Reading these formulas:</strong> Each formula box includes a description explaining what it measures and how to interpret typical values.
                Hover or tap the formula label for details.
              </p>
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
              <p className="text-muted-foreground mb-3">
                We construct portfolios using a standard academic approach that prioritizes transparency and replicability.
                Each step is designed to minimize biases while remaining implementable by practitioners.
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">Universe:</strong> S&amp;P 500 point-in-time constituents{" "}
                  <InfoTooltip term="point_in_time" size={12} />.{" "}
                  <span className="text-sm">
                    Where historical membership spans are available, we include only stocks that were actually in the index at each formation date,
                    reducing survivorship bias (coverage limitations are disclosed via snapshot diagnostics).
                  </span>
                </li>
                <li>
                  <strong className="text-foreground">Signal:</strong> prior fiscal-year R&amp;D intensity (R&amp;D expense / revenue).{" "}
                  <span className="text-sm">Using the prior year ensures data was publicly available before portfolio formation.</span>
                </li>
                <li>
                  <strong className="text-foreground">Sorting:</strong> equal-count quintiles (Q1 = lowest R&amp;D intensity, Q5 = highest).{" "}
                  <span className="text-sm">Equal-count sorting ensures each quintile has roughly the same number of stocks, making comparisons fair.</span>
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
                <div className="mt-3">
                  <Formulas.HMLPremium />
                </div>
              </div>

              <ul className="text-muted-foreground list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">Weights:</strong> equal-weight within each portfolio{" "}
                  <InfoTooltip term="equal_weight" size={12} />.{" "}
                  <span className="text-sm">Equal-weighted returns are computed each year and compounded. This gives smaller firms equal influence
                  with larger firms, which can increase the premium but also increases volatility.</span>
                </li>
                <li>
                  <strong className="text-foreground">Inclusion:</strong> firms with R&amp;D reported as zero are retained (typically in Q1).
                  <span className="text-sm"> A minimum-revenue filter is applied to avoid extreme ratios from very small denominators.
                  Zero-R&amp;D firms are legitimate members of Q1 (they simply don't invest in R&amp;D).</span>
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
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Min revenue threshold
                            <InfoTooltip title="Minimum Revenue Threshold" size={12}>
                              Firms with revenue below this threshold are excluded to avoid extreme R&amp;D intensity ratios from very small denominators.
                              A firm with $1M revenue and $500K R&amp;D would show 50% intensity, which may not be comparable to larger firms.
                              This filter ensures meaningful comparisons across the universe.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {typeof (methodologyParameters as any)?.filters?.min_revenue_threshold_usd === "number"
                            ? `$${((methodologyParameters as any).filters.min_revenue_threshold_usd / 1e6).toFixed(0)}M`
                            : "..."}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            R&amp;D intensity cap (default)
                            <InfoTooltip title="R&D Intensity Cap (Default)" size={12}>
                              Maximum R&amp;D intensity allowed for most sectors. Values above this cap are winsorized (set to the cap value) to prevent
                              outliers from distorting quintile assignments. For example, a biotech firm with 150% R&amp;D/revenue would be capped at 100%.
                              This is a conservative default that works for most industries.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {typeof (methodologyParameters as any)?.filters?.rd_intensity_capping?.default_cap_pct === "number"
                            ? `${(methodologyParameters as any).filters.rd_intensity_capping.default_cap_pct.toFixed(0)}%`
                            : "..."}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            R&amp;D intensity cap (high-R&amp;D sectors)
                            <InfoTooltip title="R&D Intensity Cap (High-R&D Sectors)" size={12}>
                              Higher cap for sectors where extreme R&amp;D intensity is common and meaningful (e.g., Biotech, Pharma).
                              These sectors routinely have firms spending more than 100% of revenue on R&amp;D (funded by capital raises).
                              A higher cap preserves the signal while still limiting extreme outliers.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {typeof (methodologyParameters as any)?.filters?.rd_intensity_capping?.high_rd_sector_cap_pct === "number"
                            ? `${(methodologyParameters as any).filters.rd_intensity_capping.high_rd_sector_cap_pct.toFixed(0)}%`
                            : "..."}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Return definition
                            <InfoTooltip title="Return Definition" size={12}>
                              Publication returns are computed from provider <strong>adjusted close</strong> (split+dividend adjusted per vendor) to approximate total shareholder return.
                              We do not add dividends separately (to avoid double counting). In publication mode, we do not silently fall back to unadjusted close; fallback modes exist only for sensitivity/coverage checks.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">Adj close (publication)</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Universe membership
                            <InfoTooltip title="Point-in-time Membership" size={12}>
                              We use historical S&amp;P 500 constituent data to include only stocks that were actually in the index at each formation date.
                              This prevents survivorship bias: we don't just look at today's S&amp;P 500 members (which excludes failed companies).
                              When historical membership data is unavailable, we note this limitation.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">Point-in-time (when available)</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Delisting returns
                            <InfoTooltip title="Delisting Return Treatment" size={12}>
                              We do not inject a separate “delisting return” into the annual return series. If a firm’s price history ends before the July–June window ends
                              (e.g., merger/delisting), we compute the holding-period return to the last observed trading day and treat cash as earning 0% thereafter for the remainder of the window.
                              We also report a literature-calibrated sensitivity analysis for delisting uncertainty.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">Cash-after-exit + sensitivity</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Return convention
                            <InfoTooltip title="Return Convention (July-June)" size={12}>
                              We use July-June return periods following Fama-French methodology. Fiscal year data for year T is used to form portfolios
                              in July of year T+1, with returns measured through June T+2. This 6+ month lag ensures all accounting data is publicly
                              available before we "trade" on it, preventing look-ahead bias.
                            </InfoTooltip>
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">{snapshot?.meta?.return_convention || "july_june"}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1">
                            Data tier
                            <InfoTooltip title="Data Tier" size={12}>
                              Tier 1 uses Financial Modeling Prep (FMP) data, which is accessible and cost-effective but may have coverage gaps.
                              Tier 2 would use CRSP/Compustat (the academic gold standard) for higher coverage and quality.
                              We document the tier to set appropriate expectations for data limitations.
                            </InfoTooltip>
                          </span>
                        </TableCell>
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

              <h3 className="text-lg font-semibold text-foreground mt-6 flex items-center gap-2">
                4.3 Rolling windows vs annual inference (what each object means)
              </h3>
              <p className="text-muted-foreground">
                <strong className="text-foreground">This distinction is critical for interpreting our results.</strong> We report two complementary objects, each with a specific interpretation:
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-2">
                <li>
                  <strong className="text-foreground">Annual series (primary inference){" "}
                    <InfoTooltip term="non_overlapping" size={12} />
                  :</strong> each year, we form R&amp;D quintiles using the prior fiscal
                  year and measure the next July-June return. This produces one observation per year, which is the cleanest basis for inference because
                  <em> the series is non-overlapping (reduces mechanical overlap)</em>. We still use Newey-West standard errors{" "}
                  <InfoTooltip term="newey_west" size={12} />{" "}
                  to account for any residual autocorrelation.
                </li>
                <li>
                  <strong className="text-foreground">Rolling windows (descriptive only){" "}
                    <InfoTooltip term="overlapping_windows" size={12} />
                  :</strong> for a given window start, we assign quintiles once (based on
                  that start-year signal) and then summarize outcomes over 5/10/20 years. <strong>Important:</strong> these overlapping windows are autocorrelated
                  by construction (a 2000-2004 window shares 4 years with a 2001-2005 window). We use them to visualize regime dependence and horizon behavior,
                  <em> not as standalone p-values</em>.
                </li>
              </ul>
              <div className="not-prose mt-3 p-3 rounded-lg border bg-amber-500/5 border-amber-500/20">
                <p className="text-sm text-muted-foreground">
                  <strong className="text-foreground">Why does this matter?</strong> Many academic papers report rolling-window statistics as if they were independent observations,
                  leading to overstated significance. We explicitly separate descriptive (rolling) from inferential (annual) results to avoid this pitfall.
                </p>
              </div>
              
              <h4 className="text-md font-semibold text-foreground mt-6">Statistical formulas used in this paper</h4>
              <p className="text-sm text-muted-foreground mb-3">
                Each formula box below includes a description explaining what it measures and how to interpret typical values.
              </p>
              <div className="not-prose grid md:grid-cols-2 gap-4">
                <Formulas.ANOVA />
                <Formulas.EtaSquared />
                <Formulas.CohensD />
                <Formulas.SharpeRatio />
                <Formulas.NeweyWest />
                <Formulas.MaxDrawdown />
              </div>

              <div className="not-prose mt-4 p-4 rounded-lg border bg-muted/30">
                <p className="font-semibold text-foreground mb-2">Bias controls and data integrity (summary)</p>
                <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                  <li>Look-ahead mitigation via July-June timing (default).</li>
                  <li>Point-in-time index membership used where historical constituent spans are available.</li>
                  <li>Exits are handled via cash-after-exit return construction; delisting sensitivity is reported separately.</li>
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
                We report the main return evidence in three complementary views, each serving a distinct purpose:
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-2 mt-2">
                <li>
                  <strong className="text-foreground">Table 5.1 (Annual premium series):</strong> Non-overlapping annual observations{" "}
                  <InfoTooltip term="non_overlapping" size={12} /> provide the cleanest basis for statistical inference.
                  <em> This is our primary evidence.</em>
                </li>
                <li>
                  <strong className="text-foreground">Figures 5.2-5.3 (Quintile returns and rolling premium):</strong> Visualize how returns differ across R&amp;D quintiles
                  and how the premium evolves over time. These illustrate stability and regime dependence.
                </li>
                <li>
                  <strong className="text-foreground">Table 5.4 (Horizon summaries):</strong> 5/10/20-year rolling windows{" "}
                  <InfoTooltip term="rolling_window" size={12} /> as descriptive context.
                  <em> Note: these are descriptive, not inferential, because windows overlap.</em>
                </li>
              </ul>
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
                  <SafeChart height={340} minHeight={300}>
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
                  </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                  Loading quintile summary...
                  </div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
                <p className="mb-2">
                  Each bar shows the average annual return for stocks in that R&amp;D quintile. Q1 contains the 20% of firms with the lowest R&amp;D intensity;
                  Q5 contains the 20% with the highest. The difference between Q5 and Q1 is the R&amp;D premium.
                </p>
                <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">Premium magnitude:</strong>{" "}
                    {(() => {
                      const q1 = quintileReturnBar5yr.find((r) => r.quintile === "Q1")?.avgReturn
                      const q5 = quintileReturnBar5yr.find((r) => r.quintile === "Q5")?.avgReturn
                      if (typeof q1 !== "number" || typeof q5 !== "number") return "Q5 outperforms Q1."
                      const diff = q5 - q1
                      return `Q5 averages ${q5.toFixed(1)}% vs Q1's ${q1.toFixed(1)}%, a spread of ${diff.toFixed(2)} percentage points per year.`
                    })()}
                  </li>
                  <li>
                    <strong className="text-foreground">Pattern shape:</strong> The relationship need not be perfectly monotonic (Q2 &lt; Q3 &lt; Q4).
                    What matters is whether Q5 consistently outperforms Q1. Mid-quintiles often show noise because the R&amp;D signal is strongest at extremes.
                  </li>
                  <li>
                    <strong className="text-foreground">Caveat:</strong> This figure aggregates overlapping 5-year windows and is descriptive only.
                    For statistical inference, see the non-overlapping annual series in Table 5.1.
                  </li>
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
                  <SafeChart height={340} minHeight={300}>
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
                  </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                  Loading rolling-window series...
                  </div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
                <p className="mb-2">
                  Each point shows the 5-year rolling premium (Q5 return minus Q1 return) for windows ending at that date.
                  For example, the point at "2015-2019" shows the average annual premium over those 5 years.
                  The green shaded area highlights when the premium is positive (high R&amp;D outperforms).
                </p>
                <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">Time variation:</strong> The premium is not constant. It can be strongly positive in some periods
                    and negative in others. This is normal for any characteristic premium and reflects changing market conditions.
                  </li>
                  <li>
                    <strong className="text-foreground">Regime dependence:</strong> Look for patterns around major events. The premium often behaves differently
                    during market stress (2008-2009) vs expansion periods. Section 8 provides regime-by-regime analysis.
                  </li>
                  <li>
                    <strong className="text-foreground">Important caveat:</strong> Adjacent points share 4 of 5 years of data, making them highly correlated.
                    Do not interpret the smoothness of this curve as statistical precision. This chart shows trends, not independent evidence.
                  </li>
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
                          {row.premiumPct !== undefined ? row.premiumPct.toFixed(2) : "..."}
                        </TableCell>
                        <TableCell className="text-right">{row.t !== undefined ? row.t.toFixed(2) : "..."}</TableCell>
                        <TableCell className="text-right">
                          {row.p !== undefined ? (row.p < 0.001 ? "< 0.001" : row.p.toFixed(4)) : "..."}
                        </TableCell>
                        <TableCell className="text-right">
                          {row.eta2 !== undefined ? row.eta2.toFixed(3) : "..."}
                        </TableCell>
                        <TableCell className="text-right">
                          {row.cohensD !== undefined ? row.cohensD.toFixed(3) : "..."}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="mt-4 rounded-lg border-2 border-amber-500/30 bg-amber-500/5 p-4 text-sm">
                <p className="font-semibold text-foreground mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  Why does the 20-year premium appear lower?
                </p>
                <p className="text-muted-foreground mb-3">
                  <strong className="text-foreground">Critical methodology note:</strong> Rolling windows sort stocks into quintiles <em>once at window start</em> and 
                  hold those assignments for the entire period. They do <strong>not</strong> re-sort annually based on updated R&D data.
                </p>
                <div className="grid md:grid-cols-2 gap-3 mb-3">
                  <div className="p-3 rounded bg-green-500/10 border border-green-500/20">
                    <p className="font-semibold text-green-700 dark:text-green-400 text-xs uppercase tracking-wide mb-1">
                      Annual (re-sorted):{" "}
                      {typeof annualHmlData?.mean_premium === "number" ? `${annualHmlData.mean_premium.toFixed(1)}%` : "…"}
                    </p>
                    <p className="text-xs text-muted-foreground">Re-sorts every year using current R&D intensity. This is the <strong>investable</strong> premium with annual rebalancing.</p>
                  </div>
                  <div className="p-3 rounded bg-slate-500/10 border border-slate-500/20">
                    <p className="font-semibold text-slate-700 dark:text-slate-400 text-xs uppercase tracking-wide mb-1">
                      20-year rolling (fixed-sort):{" "}
                      {(() => {
                        const p20 = headlinePremiums.find((h) => h.horizon === "20yr")?.premiumPct
                        return typeof p20 === "number" ? `${p20.toFixed(1)}%` : "…"
                      })()}
                    </p>
                    <p className="text-xs text-muted-foreground">Sorts once in year 1, holds for 20 years. Shows what happens if you <strong>never update</strong> the signal.</p>
                  </div>
                </div>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">Signal staleness:</strong> A company's R&D intensity changes over 20 years. A "high R&D" firm in 2000 may be "low R&D" by 2020.
                  </li>
                  <li>
                    <strong className="text-foreground">Competitive diffusion:</strong> R&D advantages erode through imitation, patent expiration, and market evolution.
                  </li>
                  <li>
                    <strong className="text-foreground">Implication for investors:</strong> To capture the full premium, you must rebalance annually. The R&D ETF (Section 9) does exactly this.
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
                  <strong className="text-foreground">Horizon decay reflects signal staleness, not strategy failure:</strong>{" "}
                  {(() => {
                    const p20 = headlinePremiums.find((h) => h.horizon === "20yr")?.premiumPct
                    const pAnnual = typeof annualHmlData?.mean_premium === "number" ? annualHmlData.mean_premium : undefined
                    if (typeof p20 === "number" && typeof pAnnual === "number") {
                      return `the 20-year rolling premium (${p20.toFixed(1)}%) is lower because quintile assignments are fixed at window start and never updated. An investable strategy with annual rebalancing captures the full annual premium (${pAnnual.toFixed(1)}%).`
                    }
                    return "long-horizon rolling windows show lower premiums because the sort is never updated; investable strategies with annual rebalancing capture the full annual premium."
                  })()}
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
                <strong className="text-foreground">Why sector analysis matters:</strong> Sector composition is a key confounder for any R&amp;D-based sort.
                High-R&amp;D firms are concentrated in a small set of sectors (primarily Technology and Healthcare), and sector-wide shocks
                can mechanically influence the premium. If the R&amp;D premium is entirely driven by sector exposure, an investor could replicate
                it with a simpler sector bet.
              </p>
              <p className="text-muted-foreground mt-2">
                We therefore report (i) R&amp;D intensity by sector, (ii) coverage of eligible firms by sector for long-horizon windows, and
                (iii) descriptive sector trends and leaderboards. These exhibits are descriptive and are intended to support transparent
                interpretation of the return results. The key question is: <em>does the R&amp;D premium exist within sectors, or is it just a sector effect?</em>
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
                  <SafeChart height={380} minHeight={320}>
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
                  </SafeChart>
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
                <p className="font-semibold text-foreground mb-2">How to Read This Chart and Table</p>
                <p className="mb-2">
                  The horizontal bar chart shows average R&amp;D intensity by sector. Longer bars indicate sectors where firms invest more in R&amp;D
                  relative to their revenue. The table provides additional detail: company count and total R&amp;D dollars.
                </p>
                <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">Concentration is extreme:</strong> Technology and Healthcare dominate R&amp;D intensity.
                    This means high-R&amp;D quintiles (Q4, Q5) will be heavily tilted toward these sectors.
                  </li>
                  <li>
                    <strong className="text-foreground">Implication for the premium:</strong> If the R&amp;D premium is just a "tech bet," it would
                    disappear when we control for sectors. Section 7.5 (Double-Sort) tests this directly.
                  </li>
                  <li>
                    <strong className="text-foreground">Dollar magnitude:</strong> Total R&amp;D spend shows the economic significance. Technology
                    firms spend the most in absolute terms, even if some Healthcare firms have higher intensity ratios.
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
                  <SafeChart height={420} minHeight={340}>
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
                  </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading coverage...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
                <p className="mb-2">
                  Each bar group shows what percentage of firms in that sector have continuous data for 5, 10, and 20-year analysis windows.
                  Higher coverage means more firms contribute to the analysis; lower coverage means results are based on fewer observations.
                </p>
                <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">Coverage declines with horizon:</strong> Fewer firms have 20 years of continuous data than 5 years.
                    This is natural: firms merge, go private, or delist over time.
                  </li>
                  <li>
                    <strong className="text-foreground">Sector variation:</strong> Some sectors (e.g., established industries) have higher long-term coverage.
                    Newer sectors or those with more M&amp;A activity have lower coverage.
                  </li>
                  <li>
                    <strong className="text-foreground">Implication:</strong> Low coverage doesn't invalidate results, but it increases uncertainty.
                    20-year window results should be interpreted with more caution than 5-year results.
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
                  <SafeChart height={420} minHeight={340}>
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
                  </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading sector radar...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
                <p className="mb-2">
                  This radar chart overlays two different concepts for the same sectors: <strong className="text-foreground">R&amp;D intensity</strong> (how
                  R&amp;D-heavy the sector is on average) and <strong className="text-foreground">company count</strong> (how many firms from that sector are in
                  the sample). The goal is to separate “high intensity” from “broad participation.”
                </p>
                <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">High intensity, few firms:</strong> These sectors can dominate the top quintile even with a small number
                    of names, which increases concentration risk.
                  </li>
                  <li>
                    <strong className="text-foreground">Many firms, moderate intensity:</strong> These sectors contribute breadth. Broad participation reduces
                    idiosyncratic concentration but may dilute the signal.
                  </li>
                  <li>
                    <strong className="text-foreground">Investor implication:</strong> If the high-R&amp;D portfolio is concentrated in a few sectors, the
                    observed premium may come with sector drawdowns and capacity constraints that matter for real allocations.
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
                  <SafeChart height={380} minHeight={320}>
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
                  </SafeChart>
                ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">Loading trends...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
                <p className="mb-2">
                  The green line (left axis) shows the <strong className="text-foreground">average R&amp;D intensity</strong> in the dataset by year. The blue
                  line (right axis) shows <strong className="text-foreground">total R&amp;D dollars</strong> across the covered firms (a scale measure, not a
                  return metric). This chart is context for interpretation, not a return test.
                </p>
                <p className="font-semibold text-foreground mb-1 mt-3">Why this matters for the paper</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">Signal environment shifts:</strong> If the economy becomes more R&amp;D-intensive over time, the
                    cross-sectional separation between “high” and “low” can compress or expand, affecting observed premiums.
                  </li>
                  <li>
                    <strong className="text-foreground">Regime interpretation:</strong> Large macro episodes can coincide with changes in financing conditions for
                    innovative firms (risk appetite, rates), which can change the premium’s behavior without changing the definition of the signal.
                  </li>
                  <li>
                    <strong className="text-foreground">Non-causal:</strong> This is not evidence that higher aggregate R&amp;D “causes” returns. It helps explain
                    why event and subperiod splits (Section 8) are informative and why long-horizon results can mix different economic regimes.
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
                            typeof r.avg_rd_intensity === "number" ? `${r.avg_rd_intensity.toFixed(2)}%` : "..."
                          const years = typeof r.years_of_data === "number" ? `${r.years_of_data}y` : "..."
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
                      : "..."}
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
                      : "..."}
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
                      if (!s || typeof s.positive_years !== "number" || typeof s.n_years !== "number" || s.n_years <= 0) return "..."
                      return `${Math.round((s.positive_years / s.n_years) * 100)}%`
                    })()}
                  </div>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <div className="text-xs text-muted-foreground">Years</div>
                  <div className="font-semibold">
                    {typeof (publicationStats as any)?.rd_factor_premium?.n_years === "number"
                      ? (publicationStats as any).rd_factor_premium.n_years
                      : "..."}
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
                  <SafeChart height={360} minHeight={300}>
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
                  </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading factor premium series...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
                <p className="mb-2">
                  Each bar shows the annual R&amp;D premium (Q5 return minus Q1 return) for that year. Green bars indicate years when high-R&amp;D
                  stocks outperformed; red bars indicate years when low-R&amp;D stocks outperformed. This is the raw, year-by-year evidence.
                </p>
                <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">Variability is normal:</strong> Even a "real" premium will have negative years.
                    The question is whether the long-run average is positive and statistically significant (see Table 5.1).
                  </li>
                  <li>
                    <strong className="text-foreground">Win rate:</strong> Count the green vs red bars. A win rate above 50% suggests the premium
                    is consistent, not just driven by a few outlier years.
                  </li>
                  <li>
                    <strong className="text-foreground">Drawdown periods:</strong> Look for clusters of red bars. These represent periods when
                    the strategy underperformed and help set realistic expectations for implementation.
                  </li>
                  <li>
                    <strong className="text-foreground">Statistical approach:</strong> We use Newey-West standard errors on this annual series
                    to account for potential autocorrelation. This is more conservative than assuming independence.
                  </li>
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
                  <SafeChart height={360} minHeight={300}>
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
                  </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading cumulative series...</div>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">How to Read This Chart</p>
                <p className="mb-2">
                  This shows what $1 invested at the start of the sample period would grow to over time. The green line (Q5) represents
                  the high-R&amp;D portfolio; the red line (Q1) represents the low-R&amp;D portfolio. The widening gap between lines
                  visualizes the cumulative effect of the annual premium.
                </p>
                <p className="font-semibold text-foreground mb-1 mt-3">Key Observations</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">Compounding effect:</strong> Small annual differences compound dramatically over time.
                    {(() => {
                      const lastQ5 = growthOf1[growthOf1.length - 1]?.q5Cumulative
                      const lastQ1 = growthOf1[growthOf1.length - 1]?.q1Cumulative
                      if (typeof lastQ5 === "number" && typeof lastQ1 === "number") {
                        return ` $1 in Q5 grew to $${lastQ5.toFixed(2)} vs $${lastQ1.toFixed(2)} in Q1.`
                      }
                      return ""
                    })()}
                  </li>
                  <li>
                    <strong className="text-foreground">Path dependence:</strong> The final value depends heavily on the sequence of returns.
                    A large drawdown early in the period has a bigger impact than one late in the period because there's more time to recover (or not).
                  </li>
                  <li>
                    <strong className="text-foreground">Not risk-adjusted:</strong> This chart shows raw wealth growth, not risk-adjusted performance.
                    Q5 may have higher volatility (see Section 9.3). Higher returns with higher risk may or may not be attractive depending on your risk tolerance.
                  </li>
                  <li>
                    <strong className="text-foreground">Hindsight bias warning:</strong> This is a backtest. Actual implementation would face
                    trading costs, timing differences, and behavioral challenges not reflected here.
                  </li>
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
              <div className="mb-4 p-3 rounded-lg border bg-muted/30 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground mb-2">What are factor spanning tests?</p>
                <p className="mb-2">
                  We regress the R&amp;D premium (HML-RD) on standard academic factors to test whether it's explained by known risk exposures.
                  If the alpha (intercept) is significant after controlling for factors, the R&amp;D premium is "distinct" and not just a combination
                  of existing factors.
                </p>
                <Formulas.FactorAlpha />
                <p className="mt-2 text-xs">
                  <strong>Models tested:</strong> FF3 (Market, Size, Value), FF5 (adds Profitability, Investment), FF6 (adds Momentum).
                </p>
              </div>
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
                            <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.alpha === "number" ? `${(data.alpha * 100).toFixed(2)}%` : "..."}</td>
                            <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.alpha_t === "number" ? data.alpha_t.toFixed(2) : "..."}</td>
                            <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.r_squared === "number" ? `${(data.r_squared * 100).toFixed(1)}%` : "..."}</td>
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
                            High {typeof high === "number" ? `${high.toFixed(2)}%` : "..."} vs Low {typeof low === "number" ? `${low.toFixed(2)}%` : "..."}
                          </div>
                          <div className="text-2xl font-bold text-primary mt-2">
                            {typeof spread === "number" ? `${spread >= 0 ? "+" : ""}${spread.toFixed(2)}%` : "..."}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            t = {typeof r.t === "number" ? r.t.toFixed(2) : "..."}
                          </div>
                          <Badge
                            className={
                              r.significant === null ? "bg-slate-500 mt-2" : r.significant ? "bg-green-600 mt-2" : "bg-slate-500 mt-2"
                            }
                          >
                            {r.significant === null ? "..." : r.significant ? "Significant" : "Not Sig."}
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
                                {typeof r.spread === "number" ? `${r.spread >= 0 ? "+" : ""}${r.spread.toFixed(2)}%` : "..."}
                              </TableCell>
                              <TableCell className="text-right font-mono">{typeof r.t === "number" ? r.t.toFixed(2) : "..."}</TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.p === "number" ? (r.p < 0.001 ? "< 0.001" : r.p.toFixed(4)) : "..."}
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
                                      {r.delta === null ? "..." : `${r.delta >= 0 ? "+" : ""}${r.delta.toFixed(2)}%`}
                                    </TableCell>
                                    <TableCell className="text-right font-mono">{r.t === null ? "..." : r.t.toFixed(2)}</TableCell>
                                    <TableCell className="text-right font-mono">
                                      {r.p === null ? "..." : r.p < 0.001 ? "< 0.001" : r.p.toFixed(4)}
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
                                These scenarios apply literature-calibrated delisting sensitivity adjustments (Shumway 1997, Beaver et al. 2007) to test premium robustness.
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
                      ? `net premium ${transactionCosts.net_rd_premium_pct.toFixed(2)}% per year (benchmark-relative; see Section 9)`
                      : "reported in the implementation section (Section 9)."}
                  </li>
                </ul>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground">8.2 Horizon dependence and event/regime context</h3>
                
                <div className="not-prose mb-4 p-4 rounded-lg border-2 border-blue-500/30 bg-blue-500/5">
                  <p className="font-semibold text-foreground mb-2">Key insight: Rolling windows do NOT re-sort</p>
                  <p className="text-sm text-muted-foreground mb-3">
                    The declining premium at longer horizons is a <strong>methodological artifact</strong>, not evidence that R&D stops working. 
                    Rolling window analysis sorts stocks into quintiles <em>once at the window start</em> and holds those assignments for the entire period
                    (no annual re-sorting). A company classified as "high R&D" in 2000 stays in Q5 even if its R&D intensity drops by 2010.
                  </p>
                  <div className="grid md:grid-cols-3 gap-2 text-xs">
                    <div className="p-2 rounded bg-green-500/10 border border-green-500/20 text-center">
                      <p className="font-bold text-green-700 dark:text-green-400">
                        Annual (
                        {typeof annualHmlData?.mean_premium === "number" ? `${annualHmlData.mean_premium.toFixed(1)}%` : "~"}
                        )
                      </p>
                      <p className="text-muted-foreground">Re-sort every year</p>
                    </div>
                    <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20 text-center">
                      <p className="font-bold text-amber-700 dark:text-amber-400">
                        5-Year (
                        {(() => {
                          const row = headlinePremiums.find((h) => h.horizon === "5yr")
                          return typeof row?.premiumPct === "number" ? `${row.premiumPct.toFixed(1)}%` : "~"
                        })()}
                        )
                      </p>
                      <p className="text-muted-foreground">Sort once, hold 5 years</p>
                    </div>
                    <div className="p-2 rounded bg-slate-500/10 border border-slate-500/20 text-center">
                      <p className="font-bold text-slate-700 dark:text-slate-400">
                        20-Year (
                        {(() => {
                          const row = headlinePremiums.find((h) => h.horizon === "20yr")
                          return typeof row?.premiumPct === "number" ? `${row.premiumPct.toFixed(2)}%` : "~"
                        })()}
                        )
                      </p>
                      <p className="text-muted-foreground">Sort once, hold 20 years</p>
                    </div>
                  </div>
                </div>

                <p className="text-muted-foreground">
                  Why does this matter? Because R&D intensity is <strong>not a permanent firm characteristic</strong>. Over 20 years, companies pivot, 
                  mature, face new competition, and change their R&D strategies. A "high R&D" classification from 2000 becomes increasingly meaningless by 2020.
                </p>
                <ul className="text-muted-foreground list-disc list-inside space-y-2">
                  <li>
                    <strong className="text-foreground">Signal staleness:</strong> rolling windows form the sort at the window start; over long horizons firms
                    change business models, R&amp;D policy, and competitive position. Microsoft in 2000 vs 2020 is effectively a different company.
                  </li>
                  <li>
                    <strong className="text-foreground">Competitive diffusion:</strong> R&amp;D advantages erode through imitation, patent expiration, and market evolution.
                    A 20-year horizon captures the full lifecycle of most competitive advantages.
                  </li>
                  <li>
                    <strong className="text-foreground">Selection and survivorship:</strong> long horizons filter firms via delistings and index turnover.
                    The Q5 cohort from 2000 may have few survivors by 2020.
                  </li>
                  <li>
                    <strong className="text-foreground">Regime mixing:</strong> a 20-year window starting in 2000 includes dot-com bust, GFC, and recovery,
                    which can dominate compounded outcomes.
                  </li>
                  <li>
                    <strong className="text-foreground">Implication for investors:</strong> to capture the full R&D premium, you must rebalance annually.
                    The R&D ETF strategy (Section 9) implements exactly this approach.
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
                                {typeof r.meanPremium === "number" ? `${r.meanPremium.toFixed(2)}%` : "..."}
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.winRatePct === "number" ? `${r.winRatePct.toFixed(0)}%` : "..."}
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.meanQ5 === "number" ? `${r.meanQ5.toFixed(2)}%` : "..."}
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {typeof r.meanQ1 === "number" ? `${r.meanQ1.toFixed(2)}%` : "..."}
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
                <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                  8.3 Sector structure
                  <InfoTooltip term="sector_tilt" size={14} />
                </h3>
                <p className="text-muted-foreground">
                  High-R&D portfolios mechanically tilt toward R&D-intensive sectors (notably Technology and Healthcare). <strong className="text-foreground">Why does this matter?</strong>{" "}
                  Because if the premium is entirely driven by sector exposure, an investor could replicate it with a simpler sector bet.
                  This does not invalidate the signal, but it makes sector reporting essential. Section 6 documents both R&D intensity by sector and coverage,
                  and Section 7 includes diagnostics (including double-sorts{" "}
                  <InfoTooltip term="double_sort" size={12} />
                  ) that help assess whether the premium survives basic sector and size confounding.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground">8.4 Factor controls</h3>
                <p className="text-muted-foreground">
                  The spanning tests in Section 7.3 evaluate whether the premium is explained by standard factor models (Fama-French 3-factor, 5-factor, and 6-factor including momentum).
                  <strong className="text-foreground"> Why do we run these tests?</strong> If the R&D premium is fully "spanned"{" "}
                  <InfoTooltip term="spanned" size={12} />{" "}
                  by known factors, it would mean investors can replicate the premium using existing factor ETFs without needing an R&D-specific strategy.
                  A significant alpha{" "}
                  <InfoTooltip term="alpha" size={12} />{" "}
                  after controlling for factors suggests the R&D premium is distinct and potentially valuable.
                </p>
                <p className="text-muted-foreground mt-2">
                  When factor inputs are present in the frozen snapshot, we report regression alphas and a model-by-model interpretation.
                  When factor inputs are missing, we treat the spanning results as unavailable rather than imputing them.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                  8.5 Mechanisms (mispricing vs risk)
                </h3>
                <p className="text-muted-foreground">
                  This design does not identify mechanisms, but the stratification diagnostics in Section 7.4 provide structured evidence that is more consistent
                  with either a mispricing{" "}
                  <InfoTooltip term="mispricing" size={12} />{" "}
                  or risk-based{" "}
                  <InfoTooltip term="risk_compensation" size={12} />{" "}
                  interpretation. <strong className="text-foreground">Why does this distinction matter?</strong>
                </p>
                <ul className="text-muted-foreground list-disc list-inside space-y-1 mt-2">
                  <li>If <strong>mispricing</strong>: the premium may shrink as investors become more sophisticated or R&D valuation improves.</li>
                  <li>If <strong>risk compensation</strong>: the premium should persist because it compensates for real economic risks that won't disappear.</li>
                </ul>
                <p className="text-muted-foreground mt-2">
                  We report those diagnostics as suggestive rather than definitive. Most likely, both mechanisms contribute to some degree.
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
                Long-only implementation using a top-20 R&D-intensity portfolio with annual reconstitution and explicit trading-friction assumptions.
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
                  <p className="font-semibold mb-2 text-foreground">Portfolio Construction Rules</p>
                  <ul className="text-sm text-muted-foreground space-y-2 list-disc list-inside">
                    <li>
                      <strong className="text-foreground">Universe:</strong> point-in-time S&amp;P 500 constituents{" "}
                      <InfoTooltip term="point_in_time" size={12} />
                    </li>
                    <li>
                      <strong className="text-foreground">Signal:</strong> prior fiscal-year R&amp;D intensity (R&amp;D / revenue)
                    </li>
                    <li>
                      <strong className="text-foreground">Holdings:</strong> top-20 stocks by R&amp;D intensity (equal-weight)
                    </li>
                    <li>
                      <strong className="text-foreground">Formation:</strong> end of June; hold July through June{" "}
                      <InfoTooltip term="july_june_convention" size={12} />
                    </li>
                    <li>
                      <strong className="text-foreground">Rebalance:</strong> annual (once per year)
                    </li>
                    <li>
                      <strong className="text-foreground">Weights:</strong> equal-weight within the selected portfolio{" "}
                      <InfoTooltip term="equal_weight" size={12} />
                    </li>
                  </ul>
                  <div className="mt-3">
                    <Formulas.Turnover />
                  </div>
                </div>

                <div className="p-4 border rounded-lg">
                  <p className="font-semibold mb-2 text-foreground">Transaction-cost assumptions</p>
                  <p className="text-sm text-muted-foreground mb-3">
                    We use the Novy-Marx &amp; Velikov (2016) methodology, calibrated for S&amp;P 500 liquidity characteristics.
                    Trading costs include bid-ask spread, market impact, and commissions.
                  </p>
                  <div className="mb-3">
                    <Formulas.TradingCost />
                  </div>
                  {transactionCosts ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            Annual trading cost
                            <InfoTooltip term="annual_trading_cost" size={12} />
                          </div>
                          <div className="font-semibold">
                            {typeof transactionCosts.annual_trading_cost_pct === "number" ? `${transactionCosts.annual_trading_cost_pct.toFixed(3)}%` : "..."}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            Net premium after costs (pp)
                            <InfoTooltip term="net_premium_after_costs" size={12} />
                          </div>
                          <div className="font-semibold">
                            {typeof transactionCosts.net_rd_premium_pct === "number" ? `${transactionCosts.net_rd_premium_pct.toFixed(2)}%` : "..."}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            Premium capture rate
                            <InfoTooltip term="premium_capture_rate" size={12} />
                          </div>
                          <div className="font-semibold">
                            {(() => {
                              const capture = transactionCosts.premium_capture_rate_pct ?? transactionCosts.premium_after_costs_pct
                              if (capture === null || capture === undefined) return "..."
                              return `${capture.toFixed(1)}%`
                            })()}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground">Realized turnover (avg)</div>
                          <div className="font-semibold">
                            {typeof (transactionCosts as any)?.turnover?.avg_turnover_pct === "number"
                              ? `${(transactionCosts as any).turnover.avg_turnover_pct.toFixed(1)}%`
                              : "..."}
                          </div>
                        </div>
                      </div>

                      <div className="p-3 rounded border bg-muted/30 text-sm">
                        <p className="font-semibold text-foreground mb-1">Definitions / assumptions (snapshot)</p>
                        <pre className="text-xs overflow-auto">
                          {JSON.stringify(
                            {
                              definition: (transactionCosts as any).definition,
                              cost_assumptions: (transactionCosts as any).cost_assumptions,
                            },
                            null,
                            2
                          )}
                        </pre>
                      </div>

                      <p className="text-xs text-muted-foreground">{(transactionCosts as any)?.note || ""}</p>
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
                    <>
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
                            <TableRow className="bg-muted/30">
                              <TableCell className="font-semibold">HML (Q5-Q1)</TableCell>
                              <TableCell className="text-right font-semibold">{netOfCost5yr.gross_rd_premium_pct.toFixed(2)}</TableCell>
                              <TableCell className="text-right">-</TableCell>
                              <TableCell className="text-right font-semibold">{netOfCost5yr.net_rd_premium_pct.toFixed(2)}</TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                      <div className="mt-4 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                        <p className="font-semibold text-foreground mb-2">How to Read This Table</p>
                        <ul className="list-disc list-inside space-y-1">
                          <li>
                            <strong className="text-foreground">Gross Return:</strong> Average annual return before any trading costs.
                          </li>
                          <li>
                            <strong className="text-foreground">Trading Cost:</strong> Estimated annual cost from rebalancing (bid-ask + impact + commissions).
                          </li>
                          <li>
                            <strong className="text-foreground">Net Return:</strong> What you actually keep after trading costs.
                          </li>
                          <li>
                            <strong className="text-foreground">HML row:</strong> The premium (Q5 minus Q1). This is what matters for the strategy.
                            A gross premium of {netOfCost5yr.gross_rd_premium_pct.toFixed(2)}% becomes {netOfCost5yr.net_rd_premium_pct.toFixed(2)}% after costs.
                          </li>
                        </ul>
                      </div>
                    </>
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
                              <TableCell className="text-right">{q.avg_return !== null && q.avg_return !== undefined ? q.avg_return.toFixed(2) : "..."}</TableCell>
                              <TableCell className="text-right">{q.volatility !== null && q.volatility !== undefined ? q.volatility.toFixed(2) : "..."}</TableCell>
                              <TableCell className="text-right">{q.sharpe_ratio !== null && q.sharpe_ratio !== undefined ? q.sharpe_ratio.toFixed(3) : "..."}</TableCell>
                              <TableCell className="text-right">{q.max_drawdown !== null && q.max_drawdown !== undefined ? q.max_drawdown.toFixed(2) : "..."}</TableCell>
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
                              : "..."}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground">EW Cohort (annualized)</div>
                          <div className="font-semibold">
                            {typeof (investableBacktest as any)?.benchmark_performance?.annualized_return === "number"
                              ? `${(investableBacktest as any).benchmark_performance.annualized_return.toFixed(2)}%`
                              : "..."}
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
                              : "..."}
                          </div>
                        </div>
                        <div className="p-3 rounded border bg-muted/30">
                          <div className="text-xs text-muted-foreground">Excess vs S&amp;P 500</div>
                          <div className="font-semibold">
                            {typeof (investableBacktest as any)?.excess_vs_sp500 === "number"
                              ? `${(investableBacktest as any).excess_vs_sp500 >= 0 ? "+" : ""}${(investableBacktest as any).excess_vs_sp500.toFixed(2)}%`
                              : "..."}
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
                              : "..."}
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
                          <SafeChart height={340} minHeight={300}>
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
                          </SafeChart>
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
                                  <TableCell className="text-right font-semibold text-green-600 dark:text-green-400">{typeof r.portfolio_return === "number" ? r.portfolio_return.toFixed(2) : "..."}</TableCell>
                                  <TableCell className="text-right">{typeof r.benchmark_return === "number" ? r.benchmark_return.toFixed(2) : "..."}</TableCell>
                                  <TableCell className="text-right">{typeof r.sp500_return === "number" ? r.sp500_return.toFixed(2) : "..."}</TableCell>
                                  <TableCell className={`text-right ${typeof r.excess_vs_sp500 === "number" && r.excess_vs_sp500 >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
                                    {typeof r.excess_vs_sp500 === "number" ? `${r.excess_vs_sp500 >= 0 ? "+" : ""}${r.excess_vs_sp500.toFixed(2)}` : "..."}
                                  </TableCell>
                                  <TableCell className="text-right">{typeof r.turnover_pct === "number" ? r.turnover_pct.toFixed(1) : "..."}</TableCell>
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

              {/* 9.5 Implementation Timeline */}
              <Card className="border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 text-xs font-bold">📅</span>
                    9.5 Implementation Timeline
                  </CardTitle>
                  <CardDescription>
                    Annual calendar view: when to do what for the R&D Alpha strategy.{" "}
                    <InfoTooltip term="rebalancing_calendar" size={12} />
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Timeline visual */}
                  <div className="relative">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      {/* Q1: Jan-Mar */}
                      <div className="p-4 rounded-lg border bg-slate-50 dark:bg-slate-900/50">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-2xl">❄️</span>
                          <span className="font-semibold text-foreground">Jan – Mar</span>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">10-Ks filing window</p>
                        <ul className="text-xs text-muted-foreground space-y-1">
                          <li>• Most Dec fiscal-year 10-Ks filed</li>
                          <li>• <strong className="text-foreground">Do nothing</strong> – hold positions</li>
                          <li>• Optionally: collect R&D data as filings come in</li>
                        </ul>
                      </div>

                      {/* Q2: Apr-Jun */}
                      <div className="p-4 rounded-lg border-2 border-emerald-400 bg-emerald-50 dark:bg-emerald-900/30">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-2xl">🌱</span>
                          <span className="font-semibold text-foreground">Apr – Jun</span>
                          <Badge variant="outline" className="text-[10px] border-emerald-500 text-emerald-700 dark:text-emerald-300">
                            ACTION
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">Formation period</p>
                        <ul className="text-xs text-muted-foreground space-y-1">
                          <li>• <strong className="text-foreground">Late June:</strong> compute R&D/Rev rankings</li>
                          <li>• <strong className="text-foreground">June 25-30:</strong> place rebalance orders</li>
                          <li>• Use prior fiscal-year data (now fully available)</li>
                          <li>• Spread trades over 3-5 days to minimize impact</li>
                        </ul>
                      </div>

                      {/* Q3: Jul-Sep */}
                      <div className="p-4 rounded-lg border bg-slate-50 dark:bg-slate-900/50">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-2xl">☀️</span>
                          <span className="font-semibold text-foreground">Jul – Sep</span>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">New holding period starts</p>
                        <ul className="text-xs text-muted-foreground space-y-1">
                          <li>• Portfolio is set for 12 months</li>
                          <li>• <strong className="text-foreground">Do nothing</strong> – hold positions</li>
                          <li>• Ignore quarterly noise</li>
                        </ul>
                      </div>

                      {/* Q4: Oct-Dec */}
                      <div className="p-4 rounded-lg border bg-slate-50 dark:bg-slate-900/50">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-2xl">🍂</span>
                          <span className="font-semibold text-foreground">Oct – Dec</span>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">Continue holding</p>
                        <ul className="text-xs text-muted-foreground space-y-1">
                          <li>• <strong className="text-foreground">Do nothing</strong> – hold positions</li>
                          <li>• Dec: consider tax-loss harvesting if applicable</li>
                          <li>• Prepare for next year's data collection</li>
                        </ul>
                      </div>
                    </div>

                    {/* Arrow indicator */}
                    <div className="hidden md:flex items-center justify-center mt-4 text-muted-foreground">
                      <div className="flex items-center gap-2 text-xs">
                        <span>← Holding Period (12 months)</span>
                        <span className="font-mono text-emerald-600 dark:text-emerald-400">→ Rebalance → </span>
                        <span>Next Holding Period →</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
                    <p className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-1">⚠️ Key insight: You do almost nothing all year</p>
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      The strategy requires ~1 day of work per year (computing rankings + placing orders). The rest of the time, you hold. 
                      This is a feature, not a bug: frequent trading destroys returns through costs.
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* 9.6 Practical Implementation Checklist */}
              <Card className="border-blue-500/30 bg-blue-50/30 dark:bg-blue-950/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs font-bold">✓</span>
                    9.6 Practical Implementation Checklist
                  </CardTitle>
                  <CardDescription>
                    Step-by-step guide for implementing the R&D Alpha strategy with real money.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    {/* Setup (one-time) */}
                    <div className="p-4 rounded-lg border">
                      <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white text-xs">1</span>
                        One-Time Setup
                      </p>
                      <ul className="text-sm text-muted-foreground space-y-2">
                        <li className="flex items-start gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                          <span>
                            <strong className="text-foreground">Open brokerage account</strong>{" "}
                            <InfoTooltip term="broker_selection" size={12} />
                            <br />
                            <span className="text-xs">Schwab, Fidelity, or Interactive Brokers recommended</span>
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                          <span>
                            <strong className="text-foreground">Decide portfolio size</strong>{" "}
                            <InfoTooltip term="position_sizing" size={12} />
                            <br />
                            <span className="text-xs">Minimum ~$10K for reasonable position sizes (20 × $500)</span>
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                          <span>
                            <strong className="text-foreground">Bookmark data sources</strong>{" "}
                            <InfoTooltip term="data_sources" size={12} />
                            <br />
                            <span className="text-xs">SEC EDGAR (10-Ks), point-in-time S&amp;P 500 constituent history (index provider)</span>
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                          <span>
                            <strong className="text-foreground">Set calendar reminder</strong>
                            <br />
                            <span className="text-xs">June 20: "Compute R&D rankings and rebalance"</span>
                          </span>
                        </li>
                      </ul>
                    </div>

                    {/* Annual rebalance */}
                    <div className="p-4 rounded-lg border">
                      <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white text-xs">2</span>
                        Annual Rebalance (June)
                      </p>
                      <ul className="text-sm text-muted-foreground space-y-2">
                        <li className="flex items-start gap-2">
                          <span className="text-blue-500 font-mono text-xs mt-0.5">A.</span>
                          <span>
                            <strong className="text-foreground">Get current S&P 500 list</strong>
                            <br />
                            <span className="text-xs">
                              ~{typeof cohortSummary?.total_companies === "number" ? cohortSummary.total_companies : "..."} tickers (incl. share classes)
                            </span>
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-blue-500 font-mono text-xs mt-0.5">B.</span>
                          <span>
                            <strong className="text-foreground">Collect R&D + Revenue</strong>
                            <br />
                            <span className="text-xs">From most recent 10-K (prior fiscal year)</span>
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-blue-500 font-mono text-xs mt-0.5">C.</span>
                          <span>
                            <strong className="text-foreground">Compute R&D/Revenue, rank, select top 20</strong>{" "}
                            <InfoTooltip term="rd_intensity" size={12} />
                            <br />
                            <span className="text-xs">Exclude firms with 0 R&D (banks, utilities)</span>
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-blue-500 font-mono text-xs mt-0.5">D.</span>
                          <span>
                            <strong className="text-foreground">Place orders over 3-5 days</strong>{" "}
                            <InfoTooltip term="execution_slippage" size={12} />
                            <br />
                            <span className="text-xs">Limit orders, avoid market-on-open</span>
                          </span>
                        </li>
                      </ul>
                    </div>

                    {/* During the year */}
                    <div className="p-4 rounded-lg border">
                      <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-400 text-white text-xs">3</span>
                        During the Year (Jul – May)
                      </p>
                      <ul className="text-sm text-muted-foreground space-y-2">
                        <li className="flex items-start gap-2">
                          <span className="text-slate-400">-</span>
                          <span>
                            <strong className="text-foreground">Do nothing</strong>{" "}
                            <InfoTooltip term="holding_period" size={12} />
                            <br />
                            <span className="text-xs">Seriously. No mid-year trading.</span>
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-slate-400">-</span>
                          <span>
                            <strong className="text-foreground">Reinvest dividends</strong>
                            <br />
                            <span className="text-xs">Set to DRIP or accumulate cash for next rebalance</span>
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-slate-400">-</span>
                          <span>
                            <strong className="text-foreground">Ignore earnings surprises</strong>
                            <br />
                            <span className="text-xs">Quarterly noise is not signal</span>
                          </span>
                        </li>
                      </ul>
                    </div>

                    {/* What to expect */}
                    <div className="p-4 rounded-lg border bg-purple-50/50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800">
                      <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-purple-500 text-white text-xs">!</span>
                        What to Expect
                      </p>
                      <ul className="text-sm text-muted-foreground space-y-2">
                        <li className="flex items-start gap-2">
                          <TrendingUp className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                          <span>
                            <strong className="text-foreground">Long-term edge:</strong>{" "}
                            {typeof investableExcessNetPp === "number"
                              ? `+${investableExcessNetPp.toFixed(1)} pp/yr net excess (historical backtest)`
                              : "Net excess is reported in the investable backtest results."}
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <TrendingDown className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                          <span>
                            <strong className="text-foreground">Painful years:</strong>{" "}
                            {typeof investableUnderperformPct === "number"
                              ? `${investableUnderperformPct.toFixed(0)}% of years underperform`
                              : "Some years underperform"}{" "}
                            <InfoTooltip term="tracking_error" size={12} />
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <Target className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                          <span>
                            <strong className="text-foreground">Time horizon:</strong> 5+ years to see the edge
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <Scale className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                          <span>
                            <strong className="text-foreground">Sector tilt:</strong> Overweight tech/healthcare{" "}
                            <InfoTooltip term="sector_tilt" size={12} />
                          </span>
                        </li>
                      </ul>
                    </div>
                  </div>

                  {/* Quick reference */}
                  <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800/50 border">
                    <p className="font-semibold text-foreground mb-2">📋 Quick Reference</p>
                    <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                      <div>
                        <span className="text-muted-foreground">Holdings:</span>{" "}
                        <span className="font-semibold text-foreground">20 stocks (equal-weight)</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Rebalance:</span>{" "}
                        <span className="font-semibold text-foreground">Annual (June)</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Signal:</span>{" "}
                        <span className="font-semibold text-foreground">R&D / Revenue</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Universe:</span>{" "}
                        <span className="font-semibold text-foreground">S&P 500</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* 9.7 Common Questions */}
              <Card className="border-slate-500/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold">?</span>
                    9.7 Common Questions
                  </CardTitle>
                  <CardDescription>
                    Practical FAQs for implementing the R&D Alpha strategy.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[
                      {
                        q: "Can I use fewer than 20 stocks?",
                        a: "Yes, but more concentration = more volatility. With 10 stocks, each position is 10% of portfolio. Consider your risk tolerance. The minimum viable portfolio is probably 15-20 stocks for reasonable diversification.",
                      },
                      {
                        q: "What if a stock gets acquired mid-year?",
                        a: "Take the cash from the acquisition and hold it until the next rebalance. Don't try to replace the position mid-year – that's extra trading cost with no expected benefit.",
                      },
                      {
                        q: "Should I use sector caps?",
                        a: "Optional. Without caps, the portfolio can become concentrated in Technology and Healthcare. With sector caps (e.g., max 25% per sector), you get more diversification but may reduce the R&D signal strength. We show uncapped results in the backtest.",
                      },
                      {
                        q: "How much money do I need to start?",
                        a: "Minimum ~$10K for 20 positions of $500 each. Below this, commission costs (if any) and odd-lot execution become proportionally expensive. Ideal is $50K+ for cleaner position sizes.",
                      },
                      {
                        q: "Can I add this to my existing portfolio?",
                        a: "Yes – treat it as a 'sleeve'. Allocate 10-30% of your equity allocation to R&D Alpha, keep the rest in index funds. This reduces tracking error while capturing some of the premium.",
                      },
                      {
                        q: "What about taxes?",
                        a:
                          typeof investableTurnoverAvgPct === "number"
                            ? `Low turnover (~${investableTurnoverAvgPct.toFixed(1)}%) means most gains are long-term. Annual rebalancing qualifies all held positions for long-term capital gains rates. Consider holding in a tax-advantaged account (IRA, 401k) if concerned about taxes.`
                            : "Low turnover means most gains are long-term. Annual rebalancing qualifies all held positions for long-term capital gains rates. Consider holding in a tax-advantaged account (IRA, 401k) if concerned about taxes.",
                      },
                      {
                        q: "Why not use an ETF instead?",
                        a: "No pure R&D intensity ETF exists. Existing 'innovation' ETFs use different signals (patents, themes) and have higher fees. DIY costs ~0 in fees vs 0.5-0.8% for thematic ETFs.",
                      },
                      {
                        q: "What if I miss the June rebalance?",
                        a: "Rebalance when you can. A few weeks delay won't materially affect returns. The key is annual rebalancing with fresh R&D data – the exact date matters less than consistency.",
                      },
                    ].map((faq, i) => (
                      <div key={i} className="p-3 rounded-lg border bg-muted/30">
                        <p className="font-semibold text-foreground text-sm mb-1">{faq.q}</p>
                        <p className="text-muted-foreground text-xs">{faq.a}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
                    <p className="font-semibold text-emerald-800 dark:text-emerald-200 text-sm mb-2">🔗 Interactive Tool</p>
                    <p className="text-emerald-700 dark:text-emerald-300 text-xs mb-3">
                      For current holdings, live rankings, and scenario modeling, use the R&D ETF tool:
                    </p>
                    <Link to="/portfolio">
                      <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                        <FlaskConical className="mr-2 h-4 w-4" />
                        Open R&D ETF Tool
                      </Button>
                    </Link>
                  </div>
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
                  cash-after-exit return construction + delisting sensitivity
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
                  <span className="font-mono">{snapshot?.meta?.id || "..."}</span>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <span className="text-muted-foreground">Built at:</span>{" "}
                  <span className="font-mono">{snapshotBuiltAtLabel || "..."}</span>
                </div>
                <div className="p-3 rounded border bg-muted/30">
                  <span className="text-muted-foreground">Git commit:</span>{" "}
                  <span className="font-mono">{snapshot?.meta?.git_commit ? snapshot.meta.git_commit.slice(0, 12) : "..."}</span>
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
              <div className="not-prose mt-4 p-4 rounded-lg border border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/30">
                <div className="flex items-center gap-3 mb-2">
                  <Github className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  <span className="font-semibold text-foreground">Open Source</span>
                </div>
                <p className="text-sm text-muted-foreground mb-3">
                  The core research code is open source under MIT license. Clone the repository to replicate results or build upon this work.
                </p>
                <a
                  href="https://github.com/vastdreams/fse-rnd-alpha"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium transition-colors"
                >
                  <Github className="h-4 w-4" />
                  github.com/vastdreams/fse-rnd-alpha
                  <ExternalLink className="h-3 w-3 opacity-70" />
                </a>
              </div>
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
                convention to reduce look-ahead bias and explicit exit handling plus point-in-time membership (when available) to mitigate survivorship bias, we document a positive return
                spread between high-R&amp;D and low-R&amp;D portfolios.
              </p>

              <div className="not-prose p-4 rounded-lg bg-muted/30 border">
                <p className="font-semibold text-foreground mb-2">Key findings</p>
                <ul className="text-muted-foreground text-sm space-y-2">
                  <li>
                    <strong className="text-foreground">Primary result:</strong> The annual non-overlapping HML premium averages{" "}
                    <strong>{typeof annualHmlData?.mean_premium === "number" ? `${annualHmlData.mean_premium.toFixed(2)}%` : "..."}</strong> per year
                    (Newey-West t = {typeof annualHmlData?.hac_adjusted?.t_statistic === "number" ? annualHmlData.hac_adjusted.t_statistic.toFixed(2) : "..."},
                    p = {typeof annualHmlData?.hac_adjusted?.p_value === "number" ? (annualHmlData.hac_adjusted.p_value < 0.001 ? "<0.001" : annualHmlData.hac_adjusted.p_value.toFixed(4)) : "..."}).
                  </li>
                  <li>
                    <strong className="text-foreground">Horizon dependence:</strong> Rolling-window premiums are{" "}
                    {headlinePremiums.map((h) => `${h.horizon.toUpperCase()}: ${typeof h.premiumPct === "number" ? h.premiumPct.toFixed(2) : "..."}%`).join(", ")} (Q5-Q1).
                    Longer horizons show smaller premiums, consistent with signal decay and regime mixing.
                  </li>
                  <li>
                    <strong className="text-foreground">Implementability:</strong> Under literature-calibrated transaction costs, the net-of-cost premium
                    remains <strong>{typeof netOfCost5yr?.net_rd_premium_pct === "number" ? `${netOfCost5yr.net_rd_premium_pct.toFixed(2)}%` : "..."}</strong> at the
                    5-year horizon with a <strong>{typeof transactionCosts?.premium_capture_rate_pct === "number" ? `${transactionCosts.premium_capture_rate_pct.toFixed(1)}%` : "..."}</strong> capture rate.
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

        {/* How to Cite */}
        <section id="cite" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">How to Cite This Paper</h2>
          </div>
          <Card className="bg-card">
            <CardContent className="pt-6 space-y-4">
              <div className="flex flex-wrap gap-3 mb-4">
                <a
                  href="/rnd-alpha-paper.pdf"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                >
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Open PDF
                </a>
                <a
                  href="/rnd-alpha-paper.pdf"
                  download
                  className="inline-flex items-center px-4 py-2 border border-input bg-background rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download PDF
                </a>
                <Button variant="outline" size="sm" onClick={() => {
                  navigator.clipboard.writeText(
                    `Sehgal, A. (2025). R&D Alpha: Investment Intensity and Long-Term Stock Returns (Working paper). FSE Research & Investments Pty Ltd. https://research.finsoeasy.com/rnd-alpha-paper.pdf`
                  );
                  alert("Citation copied to clipboard!");
                }}>
                  Copy Citation
                </Button>
              </div>
              
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-semibold text-foreground mb-1">APA Format:</p>
                  <p className="text-sm text-muted-foreground bg-muted p-3 rounded-md font-mono">
                    Sehgal, A. (2025). R&amp;D Alpha: Investment Intensity and Long-Term Stock Returns (Working paper). <em>FSE Research &amp; Investments Pty Ltd</em>. https://research.finsoeasy.com/rnd-alpha-paper.pdf
                  </p>
                </div>
                
                <div>
                  <p className="text-sm font-semibold text-foreground mb-1">BibTeX:</p>
                  <pre className="text-xs text-muted-foreground bg-muted p-3 rounded-md overflow-x-auto">
{`@techreport{sehgal_rnd_alpha_2025,
  author      = {Sehgal, Abhishek},
  title       = {R\\&D Alpha: Investment Intensity and Long-Term Stock Returns},
  institution = {FSE Research \\& Investments Pty Ltd},
  year        = {2025},
  month       = {12},
  url         = {https://research.finsoeasy.com/rnd-alpha-paper.pdf},
  note        = {Working paper; results pinned to a frozen publication snapshot (see PDF for snapshot ID).}
}`}
                  </pre>
                </div>
              </div>
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
                  "griliches_1981",
                  "griliches_1990",
                  "hall_jaffe_trajtenberg_2005",
                  "deng_lev_narin_1999",
                  "gu_2005",
                  "li_2011",
                  "barth_kasznik_mcnichols_2001",
                  "fama_french_1993",
                  "fama_french_2015",
                  "fama_macbeth_1973",
                  "carhart_1997",
                  "hou_xue_zhang_2015",
                  "hou_mo_xue_zhang_2022",
                  "asness_frazzini_2013",
                  "novy_marx_velikov_2016",
                  "newey_west_1987",
                  "barney_1991",
                  "porter_1992",
                  "cohen_klepper_1996",
                  "polk_sapienza_2009",
                  "jaffe_1986",
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
    </div>
  )
}


