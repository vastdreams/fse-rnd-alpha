/**
 * PATH: frontend/src/lib/paperAudit.ts
 * PURPOSE: Strict Paper-2 Table-20 gate replay + 2026-07-12 AI-audit verdicts.
 *
 * The bundle's `core_thesis_path` flag ANDs only 6 of the paper's 12 Table-20
 * conditions. `paperStrictReplay` re-runs the full filter from raw fields so
 * the UI never has to trust the relaxed flag. `MODEL10_AUDIT` carries the
 * per-name verdicts from the 2026-07-12 audit (filings checked verbatim for
 * FRSH/DOCU/PCTY/WDAY; valuation engine replayed for all ten).
 */

import type { SaasCompany } from "@/lib/api/saasPortfolio"
import { mosLive } from "@/lib/portfolioReturns"

/** Named carve-out in the paper's core-portfolio code (payments/float economics). */
const CORE_PORTFOLIO_EXCLUSIONS = new Set(["BILL"])

export type StrictReplay = {
  pass: boolean
  /** Human-readable failures, empty when pass. */
  failures: string[]
  /** Conditions that could not be evaluated (missing data → paper treats as fail). */
  notEvaluable: string[]
}

/**
 * Replay the paper's Table-20 filter from raw bundle fields.
 * Omitted here (never binding on this Top-100 panel): the net-debt leverage check.
 */
export function paperStrictReplay(c: SaasCompany): StrictReplay {
  const failures: string[] = []
  const notEvaluable: string[] = []
  const mf = (c.mgmt_factors || {}) as Record<string, unknown>

  if (c.cohort !== "exposed_incumbent") failures.push("Not in the exposed-incumbent cohort")
  if (!((c.fcfm_sbc_l ?? -1) > 0)) failures.push("SBC-adjusted FCF not positive")
  if (!((c.mos ?? -1) > 0)) failures.push("Base margin of safety not positive at paper date")
  const mcap = c.live_marketcap_usd ?? c.marketcap_usd
  if (!(mcap != null && mcap >= 1e9)) failures.push("Below $1B investable size")

  const qual = mf.filing_qual_flag
  if (typeof qual !== "number") notEvaluable.push("No filing-quality flag (no 10-K overlay)")
  else if (qual < 0) failures.push("Filing text flag negative (AI framed as displacement risk)")

  if (c.d_fcfm_sbc == null) notEvaluable.push("Margin-trend field missing")
  else if (!(c.d_fcfm_sbc > 0))
    failures.push(`SBC-adjusted FCF margin deteriorating (${(c.d_fcfm_sbc * 100).toFixed(1)}pp)`)

  if (c.dilution_ann != null && c.dilution_ann > 0.15) failures.push("Dilution above 15%/yr")
  if (!((c.rev_cagr ?? -1) >= 0.05))
    failures.push(`Revenue growth below 5% (${(((c.rev_cagr ?? 0) as number) * 100).toFixed(1)}%)`)

  const moat = (c.rd_prod ?? -1) >= 0.25 || (c.rule40_sbc_l ?? -1) >= 0.2
  if (!moat) failures.push("Fails moat gate (R&D prod < 0.25 and Rule-of-40 < 20%)")

  if (CORE_PORTFOLIO_EXCLUSIONS.has(c.ticker.toUpperCase()))
    failures.push("Excluded by name in the paper's core-portfolio code (payments/float carve-out)")

  // Paper semantics: a condition that cannot be evaluated does not pass.
  return { pass: failures.length === 0 && notEvaluable.length === 0, failures, notEvaluable }
}

export type AuditVerdict = "paper_core" | "kill_triggered" | "watchlist_fails_paper"

export type Model10Audit = {
  verdict: AuditVerdict
  /** One-line verdict a non-specialist can act on. */
  headline: string
  /** The single paper gate (or event) that decides the verdict. */
  decidingGate: string
  /** Honest caveats and data bugs found by the audit. */
  flags: string[]
}

export const AUDIT_DATE = "2026-07-12"

/** 2026-07-12 audit results. Static by design: verdicts cite the audit, not a live recompute. */
export const MODEL10_AUDIT: Record<string, Model10Audit> = {
  FRSH: {
    verdict: "paper_core",
    headline: "Passes all 12 paper gates with the widest margin of safety. Strongest name in the ten.",
    decidingGate: "Full Table-20 pass",
    flags: [
      "NDR 108% is FX-flattered — constant-currency is 104%.",
      "GAAP operating income was only $13.2M; net income was inflated by a one-off SBC forfeiture reversal.",
    ],
  },
  DOCU: {
    verdict: "paper_core",
    headline: "Passes the full paper filter, but the cushion is thin (+6%) and the low valuation band is unverified.",
    decidingGate: "Full Table-20 pass",
    flags: [
      "Data bug: two of the three valuation models are duplicated in the bundle, so the low band equals the median and is unverified pending a rebuild.",
      "Retention is genuinely not disclosed, and billings guidance ends FY2027 — filing visibility is shrinking.",
    ],
  },
  PCTY: {
    verdict: "paper_core",
    headline: "Passes the full paper filter at snapshot and live prices.",
    decidingGate: "Full Table-20 pass",
    flags: [
      "About a third of reported FCF is interest on client-held funds (rate-sensitive float, not software economics).",
      "The low valuation lens sits 17% below the live price — the peer-multiple model disagrees with both DCFs.",
    ],
  },
  WDAY: {
    verdict: "kill_triggered",
    headline:
      "Its own kill criterion has fired: the margin of safety at live prices is negative. Paper protocol says hold off / trim, not buy.",
    decidingGate: "Live MoS < 0 (kill criterion: base MoS → negative)",
    flags: [
      "CEO churn (Bhusri back Feb 2026) plus a new FY2027 restructuring announced the same month.",
      "The '97% retention' is gross retention, not NRR.",
    ],
  },
  MNDY: {
    verdict: "watchlist_fails_paper",
    headline:
      "Fails the paper's improving-margin gate: SBC-adjusted FCF margin is deteriorating (−4.5pp). The big headline upside leans on a margin glide the trend contradicts.",
    decidingGate: "Improving SBC-FCF margin (−4.5pp)",
    flags: [
      "No 10-K overlay, no management note, no kill criterion — quantitative screens only.",
      "Fair value is set by the peer multiple; the high lens assumes margins rise toward 40% against the observed trend.",
    ],
  },
  PAYC: {
    verdict: "watchlist_fails_paper",
    headline: "Fails the paper's filing-quality gate (negative AI text stance in the 10-K).",
    decidingGate: "Filing text flag −1",
    flags: [
      "Share-count inconsistency between snapshot and live market caps (+14.6%) adds error bars to the live MoS.",
      "NRR 91% is the lowest disclosed retention in the ten. The DCF gives no credit for its heavy buybacks (conservative).",
    ],
  },
  NICE: {
    verdict: "watchlist_fails_paper",
    headline:
      "Closest miss of the six: fails the improving-margin gate by only −0.4pp, but has no filing overlay at all.",
    decidingGate: "Improving SBC-FCF margin (−0.4pp) + no 10-K overlay",
    flags: [
      "Tightest valuation band of the ten — all three models agree it is cheap; the open question is the CCaaS AI-displacement fear.",
      "No management note or kill criterion in the dataset.",
    ],
  },
  DBX: {
    verdict: "watchlist_fails_paper",
    headline:
      "Fails the paper's growth gate outright (0.4% revenue CAGR vs ≥5%). A harvest/buyback story, not the paper's compounder thesis.",
    decidingGate: "Revenue growth ≥ 5% (0.4%)",
    flags: [
      "R&D productivity is negative; the moat gate passes only via a Rule-of-40 that is 98% margin.",
      "Median upside is +1% — no margin of safety even on the model's own terms.",
    ],
  },
  APPF: {
    verdict: "watchlist_fails_paper",
    headline:
      "Fails the filing-quality gate, and the price has run above the model's median fair value (live MoS −10%).",
    decidingGate: "Filing text flag −1 + live MoS < 0",
    flags: [
      "The business screens well (23% growth, improving margins) — the problem is the price, not the company.",
      "The valuation models disagree 2.4x; the −51% low lens is real model output, not a typo.",
    ],
  },
  BILL: {
    verdict: "watchlist_fails_paper",
    headline:
      "Excluded BY NAME in the paper's own core-portfolio code: payments-float economics break the SaaS valuation engine.",
    decidingGate: "Named payments/float carve-out",
    flags: [
      "The $11.68 low band is the owner-earnings DCF choking on a ~5.6% SBC-adjusted FCF margin — unreliable in both directions.",
      "Only name where implied growth (21%) exceeds realised growth (14%).",
    ],
  },
}

export function model10Audit(ticker: string): Model10Audit | null {
  return MODEL10_AUDIT[ticker.toUpperCase()] ?? null
}

export function auditVerdictLabel(v: AuditVerdict): string {
  if (v === "paper_core") return "Audit: paper core"
  if (v === "kill_triggered") return "Audit: kill criterion triggered"
  return "Audit: watchlist — fails a paper gate"
}

export function auditVerdictTone(v: AuditVerdict): string {
  if (v === "paper_core") return "border-emerald-700 bg-emerald-50 text-emerald-950"
  if (v === "kill_triggered") return "border-rose-700 bg-rose-50 text-rose-950"
  return "border-amber-700 bg-amber-50 text-amber-950"
}

/** Live-price sanity check that pairs with the static verdicts. */
export function killTriggeredLive(c: SaasCompany): boolean {
  const m = mosLive(c)
  return m != null && m <= 0 && !!c.paper_tier
}
