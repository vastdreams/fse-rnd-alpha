/**
 * PATH: src/hooks/useMainPaperDerivedStrategy.ts
 * PURPOSE: Pure helper functions for strategy/investable derived computations
 * WHY: Split from useMainPaperDerived.ts to stay under 300-line limit.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

export function deriveDoubleSortTableRows(doubleSortData: any) {
  const matrix = doubleSortData?.matrix
  const spreads = doubleSortData?.rd_spreads_by_size
  if (!matrix || typeof matrix !== "object") return []

  const sizes: Array<"Large" | "Medium" | "Small"> = ["Large", "Medium", "Small"]
  const rds: Array<"Low" | "Medium" | "High"> = ["Low", "Medium", "High"]

  return sizes
    .map((size) => {
      const row = matrix?.[size] || {}
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
}

export function deriveFactorPremiumSeries(factorPremiums: any[]) {
  const currentYear = new Date().getFullYear()
  return (factorPremiums || [])
    .filter((f) => typeof f.year === "number" && f.year < currentYear)
    .map((f) => ({
      year: f.year,
      rdPremium: f.rd_premium ?? null,
      q1: f.q1_return ?? null,
      q5: f.q5_return ?? null,
    }))
}

export function deriveRegimePremiumTable(factorPremiumSeries: ReturnType<typeof deriveFactorPremiumSeries>) {
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
}

export function deriveSampleYearRange(snapshotPayload: any, factorPremiumSeries: ReturnType<typeof deriveFactorPremiumSeries>) {
  const annualHml = snapshotPayload?.annual_hml_premium
  if (annualHml && "annual_premiums" in annualHml && Array.isArray(annualHml.annual_premiums) && annualHml.annual_premiums.length > 0) {
    const years = annualHml.annual_premiums
      .map((p: any) => p.formation_year)
      .filter((y: unknown): y is number => typeof y === "number")
    if (years.length > 0) {
      const min = Math.min(...years)
      const max = Math.max(...years)
      return `Jul ${min + 1}-Jun ${max + 2}`
    }
  }
  const currentYear = new Date().getFullYear()
  const years = (factorPremiumSeries || [])
    .map((r) => r.year)
    .filter((y): y is number => typeof y === "number" && y < currentYear)
  if (years.length === 0) return undefined
  const min = Math.min(...years)
  const max = Math.max(...years)
  if (!Number.isFinite(min) || !Number.isFinite(max)) return undefined
  return `${min}-${max}`
}

export function deriveGrowthOf1(factorPremiumSeries: ReturnType<typeof deriveFactorPremiumSeries>) {
  const rows = factorPremiumSeries.filter((r) => typeof r.year === "number")
  let q5 = 1
  let q1 = 1
  return rows.map((r) => {
    q5 = q5 * (1 + (r.q5 || 0) / 100)
    q1 = q1 * (1 + (r.q1 || 0) / 100)
    return { year: r.year, q5Cumulative: q5, q1Cumulative: q1 }
  })
}

export function deriveInvestableGrowth(investableBacktest: any) {
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
}

export function deriveInvestableNetExcessVsSp500Pp(investableBacktest: any, transactionCosts: any) {
  const bt = investableBacktest as any
  const portfolioNetAnnualized = bt?.portfolio_performance_net?.annualized_return
  const sp500Annualized = bt?.sp500_performance?.annualized_return
  if (typeof portfolioNetAnnualized === "number" && typeof sp500Annualized === "number") {
    return portfolioNetAnnualized - sp500Annualized
  }
  const tx = transactionCosts as any
  const netPremiumFromCostsTable = tx?.net_rd_premium_pct
  if (typeof netPremiumFromCostsTable === "number") return netPremiumFromCostsTable
  return undefined
}

export function deriveInvestableTurnoverAvgPct(investableBacktest: any) {
  const bt = investableBacktest as any
  const v = bt?.turnover?.avg_turnover_pct
  return typeof v === "number" ? v : undefined
}

export function deriveInvestableUnderperformPct(investableBacktest: any) {
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
}
