/**
 * PATH: frontend/src/components/research/ThesisCard.tsx
 * PURPOSE: The per-name thesis object — disagreement, cause, repayment engine,
 * survivability floors, payoff skew, p* break-even, resolution and sizing.
 * Every value is sealed data or arithmetic; UNKNOWN renders as UNKNOWN.
 */
import type { ThesisObject } from "@/lib/api/universe"
import { formatPercent4, formatUsd4 } from "@/lib/formatMetrics"

function fmtPct(v: number | null | undefined): string {
  return v === null || v === undefined ? "Unknown" : formatPercent4(v)
}

function fmtUsd(v: number | null | undefined): string {
  return v === null || v === undefined ? "Unknown" : formatUsd4(v)
}

function TriBadge({ state, yes, no, unknown }: { state: boolean | null | undefined; yes: string; no: string; unknown: string }) {
  const label = state === true ? yes : state === false ? no : unknown
  const tone =
    state === true
      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
      : state === false
        ? "border-rose-300 bg-rose-50 text-rose-900"
        : "border-neutral-300 bg-neutral-100 text-neutral-700"
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold ${tone}`}>
      {label}
    </span>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-neutral-200 pt-2 first:border-t-0 first:pt-0">
      <h4 className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">{title}</h4>
      <div className="mt-1">{children}</div>
    </section>
  )
}

export function ThesisCard({ thesis }: { thesis: ThesisObject }) {
  const d = thesis.disagreement
  const spine = thesis.repayment_engine
  const surv = thesis.survivability
  const skew = thesis.skew
  const pstar = thesis.p_star
  const size = thesis.size
  const tape = thesis.cause.tape_event as
    | { peak_px?: number; peak_date?: string; trough_px?: number; trough_date?: string; drawdown?: number }
    | null

  const skewText =
    skew.payoff_skew_label === "below_band"
      ? "Below band — price at/under the low lens; downside-to-band ≤ 0"
      : skew.payoff_skew === null
        ? "Unknown"
        : `${skew.payoff_skew.toFixed(1)} : 1 (gate floor ${skew.min_ratio.toFixed(0)}:1)`

  return (
    <div className="space-y-2 rounded-lg border border-neutral-200 bg-white p-3" data-testid="thesis-card">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-950">Thesis · Repriced × R&D-validated × Survivable</h3>
        <span className="text-[10px] text-neutral-500">{thesis.engine_version} · sealed data + arithmetic only</span>
      </div>

      <Section title="Disagreement — what the price says vs the sealed band">
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[12px] tabular-nums sm:grid-cols-4">
          <div>Live {fmtUsd(d.price_live)}{d.price_stale ? " (stale)" : ""}</div>
          <div>Band {fmtUsd(d.fair_px_lo)} – {fmtUsd(d.fair_px_hi)}</div>
          <div>Sealed MoS {fmtPct(d.mos_live_sealed)}</div>
          <div>Live gap {fmtPct(d.gap_to_median)}</div>
        </div>
        <p className="mt-1 text-[10px] text-neutral-500">{d.note}</p>
      </Section>

      <Section title="Cause — the measured dislocation">
        {tape ? (
          <p className="text-[12px] text-neutral-800 tabular-nums">
            Peak {fmtUsd(tape.peak_px ?? null)} ({tape.peak_date}) → trough {fmtUsd(tape.trough_px ?? null)} ({tape.trough_date}),{" "}
            {tape.drawdown !== undefined ? formatPercent4(tape.drawdown) : "?"} drawdown.
          </p>
        ) : (
          <p className="text-[12px] text-neutral-600">{thesis.cause.note}</p>
        )}
      </Section>

      <Section title="Repayment engine — the validated factor spine">
        <div className="flex flex-wrap items-center gap-2 text-[12px]">
          <TriBadge state={spine.rd_elig} yes="RD cohort: eligible" no="RD cohort: outside" unknown="RD cohort: UNKNOWN" />
          <span className="tabular-nums text-neutral-800">
            composite {spine.rd_composite === null ? "Unknown" : spine.rd_composite.toFixed(2)}σ
          </span>
        </div>
        <ul className="mt-1 space-y-0.5 text-[10px] text-neutral-600">
          {Object.entries(spine.premium_series).map(([key, s]) => (
            <li key={key} className="tabular-nums">
              {s.label}: {s.mean_pct_per_year.toFixed(2)}%/yr (t={s.t_statistic.toFixed(2)}) — {s.role}
            </li>
          ))}
        </ul>
        <p className="mt-1 text-[10px] text-neutral-500">{spine.note}</p>
      </Section>

      <Section title="Survivability — hard floors, not scores">
        <div className="mb-1">
          <TriBadge state={surv.survivable} yes="All floors clear" no="Floor failed" unknown="Floors UNKNOWN — blocks BUY" />
        </div>
        <table className="w-full text-[11px]">
          <tbody>
            {surv.floors.map((f) => (
              <tr key={f.field} className="border-t border-neutral-100">
                <td className="py-0.5 pr-2 text-neutral-700">{f.label}</td>
                <td className="py-0.5 pr-2 tabular-nums text-neutral-900">
                  {f.value === null ? "Unknown" : f.value.toFixed(f.field === "runway_yrs" ? 1 : 3)}
                </td>
                <td className="py-0.5 text-[10px] text-neutral-500">{f.threshold}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Payoff skew — shape of the bet, never its size">
        <p className="text-[12px] tabular-nums text-neutral-800">{skewText}</p>
      </Section>

      <Section title="p* — what the market charges for the repricing">
        <p className="text-[12px] tabular-nums text-neutral-800">
          {pstar.p_star === null ? "—" : formatPercent4(pstar.p_star)}
        </p>
        <p className="mt-0.5 text-[10px] text-neutral-500">{pstar.reading} Display only — never gates, never sizes.</p>
      </Section>

      <Section title="Resolution — dated catalyst">
        {thesis.resolution.dated_anchors.length ? (
          <ul className="space-y-0.5 text-[11px] text-neutral-800">
            {thesis.resolution.dated_anchors.slice(0, 4).map((a, i) => (
              <li key={i}>
                <span className="tabular-nums text-neutral-500">{String(a.date ?? "")}</span>{" "}
                {String(a.title ?? a.kind ?? "anchor")}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[11px] text-neutral-600">{thesis.resolution.note}</p>
        )}
      </Section>

      <Section title="Size — validated evidence only">
        <p className="text-[12px] font-semibold tabular-nums text-neutral-950">
          Bound: {formatPercent4(size.f_max_fraction)} of capital
        </p>
        <p className="mt-0.5 text-[11px] text-neutral-700">{size.verdict}</p>
        {size.why_zero ? (
          <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[10px] text-neutral-500">
            {size.why_zero.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        ) : null}
      </Section>
    </div>
  )
}
