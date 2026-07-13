/**
 * PATH: frontend/src/components/research/StanceTab.tsx
 * PURPOSE: Close-call waterfall → ROI runs → research BUY/HOLD with flowchart.
 * Fail-closed: UNKNOWN when catalyst/MoS missing; never invents news.
 */
import type { CloseCallWaterfall } from "@/lib/api/universe"

const stanceTone: Record<string, string> = {
  BUY: "border-emerald-400 bg-emerald-50 text-emerald-950",
  HOLD: "border-amber-300 bg-amber-50 text-amber-950",
  WATCH: "border-sky-300 bg-sky-50 text-sky-950",
  OUT: "border-rose-300 bg-rose-50 text-rose-950",
  UNKNOWN: "border-neutral-300 bg-neutral-50 text-neutral-800",
}

const resultTone: Record<string, string> = {
  PASS: "bg-emerald-600 text-white",
  FAIL: "bg-rose-600 text-white",
  UNKNOWN: "bg-neutral-500 text-white",
  BUY: "bg-emerald-700 text-white",
  HOLD: "bg-amber-600 text-white",
  WATCH: "bg-sky-600 text-white",
  OUT: "bg-rose-700 text-white",
}

export function StanceTab({
  waterfall,
  dataMode,
}: {
  waterfall: CloseCallWaterfall | null | undefined
  dataMode?: "current_overlay" | "frozen_universe"
}) {
  if (!waterfall) {
    return (
      <div className="rounded-xl border border-border bg-white p-6 text-sm text-neutral-600">
        Close-call waterfall unavailable for this ticker.
      </div>
    )
  }

  const a = waterfall.aggregate
  const tone = stanceTone[a.stance] || stanceTone.UNKNOWN

  return (
    <div className="space-y-4">
      {dataMode === "current_overlay" && (
        <p className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-950">
          Current price/tape overlay: the frozen universe metrics and bound evidence stay pinned, while
          this view uses the latest available price history.
        </p>
      )}
      {/* Verdict */}
      <div className={`rounded-xl border-2 p-4 sm:p-5 ${tone}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wide opacity-70">
              Research stance
            </div>
            <div className="mt-0.5 text-3xl font-bold tracking-tight">{a.stance}</div>
            <div className="mt-1 text-sm">
              Confidence <b>{a.confidence}</b>
              {a.score != null && (
                <>
                  {" "}
                  · Score <b>{a.score}</b>/100
                </>
              )}
              {a.horizon_years != null && (
                <>
                  {" "}
                  · Horizon <b>{a.horizon_years}y</b>
                  {a.implied_ann_return != null && (
                    <>
                      {" "}
                      (≈{(a.implied_ann_return * 100).toFixed(1)}%/yr if gap closes)
                    </>
                  )}
                </>
              )}
            </div>
          </div>
          <div className="max-w-sm text-[11px] leading-snug opacity-80">{a.watermark}</div>
        </div>
        {a.horizon_note && <p className="mt-3 text-xs leading-relaxed opacity-90">{a.horizon_note}</p>}
        {a.blockers.length > 0 && (
          <ul className="mt-3 list-disc space-y-0.5 pl-4 text-xs">
            {a.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        )}
        {a.stance === "UNKNOWN" && (
          <p className="mt-3 rounded-lg border border-neutral-200 bg-white/70 px-3 py-2 text-xs leading-relaxed">
            L4 UNKNOWN is fail-closed: usually no ≥25% drawdown window (L0) for a named catalyst, or no
            anchors inside the peak−30d…trough+45d window. We do not invent catalysts or loosen the
            drawdown gate. Missing filings are a separate completeness issue.
          </p>
        )}
      </div>

      {/* Flowchart */}
      <div className="rounded-xl border border-border bg-white p-4 sm:p-5">
        <h3 className="text-sm font-semibold text-black">How this decision was formed</h3>
        <p className="mt-0.5 text-[11px] text-neutral-600">
          Sequential gates — any UNKNOWN or FAIL blocks BUY. Same spirit as the stats-engine waterfall.
        </p>
        <ol className="mt-4 space-y-0">
          {a.flowchart.map((n, i) => (
            <li key={n.id} className="relative flex gap-3 pb-4 last:pb-0">
              {i < a.flowchart.length - 1 && (
                <span className="absolute left-[15px] top-8 bottom-0 w-px bg-neutral-200" aria-hidden />
              )}
              <span
                className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                  resultTone[n.result] || "bg-neutral-400 text-white"
                }`}
              >
                {i + 1}
              </span>
              <div className="min-w-0 flex-1 rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-sm font-semibold text-black">{n.label}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                      resultTone[n.result] || "bg-neutral-400 text-white"
                    }`}
                  >
                    {n.result}
                  </span>
                </div>
                <p className="mt-0.5 text-xs leading-relaxed text-neutral-700">{n.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Stages */}
      <div className="rounded-xl border border-border bg-white p-4 sm:p-5">
        <h3 className="text-sm font-semibold text-black">Close-call waterfall</h3>
        <div className="mt-3 space-y-3">
          {waterfall.stages.map((s) => (
            <div key={s.id} className="rounded-lg border border-neutral-100 p-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="text-sm font-semibold text-black">
                  {s.id} · {s.title}
                </div>
                <div className="flex items-center gap-2 text-[11px]">
                  <span
                    className={`rounded px-1.5 py-0.5 font-medium uppercase ${
                      s.status === "known"
                        ? "bg-emerald-100 text-emerald-900"
                        : s.status === "partial"
                          ? "bg-amber-100 text-amber-900"
                          : "bg-neutral-200 text-neutral-700"
                    }`}
                  >
                    {s.status}
                  </span>
                  <span className="tabular-nums text-neutral-600">
                    {s.score == null ? "score —" : `score ${s.score.toFixed(1)}/10`}
                  </span>
                </div>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-neutral-700">{s.summary}</p>
              {s.unknown_reason && (
                <p className="mt-1 text-xs font-medium text-amber-800">Unknown: {s.unknown_reason}</p>
              )}
              {s.claims.length > 0 && (
                <ul className="mt-2 space-y-1 border-t border-neutral-100 pt-2 text-[11px] text-neutral-700">
                  {s.claims.map((c) => (
                    <li key={c.claim_id} className="flex flex-wrap gap-x-2">
                      <span className="font-mono text-neutral-500">{c.field}</span>
                      <span>{c.value_text}</span>
                      {c.locator &&
                        (c.locator.startsWith("http") ? (
                          <a
                            href={c.locator}
                            target="_blank"
                            rel="noreferrer"
                            className="text-sky-700 hover:underline"
                          >
                            source
                          </a>
                        ) : (
                          <span className="text-neutral-400">{c.locator}</span>
                        ))}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ROI runs */}
      <div className="rounded-xl border border-border bg-white p-4 sm:p-5">
        <h3 className="text-sm font-semibold text-black">ROI runs (weighted)</h3>
        <p className="mt-0.5 text-[11px] text-neutral-600">
          Missing axes stay null — never imputed. Aggregate only averages scored runs, then penalizes
          coverage.
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-[10px] uppercase tracking-wide text-neutral-500">
                <th className="py-2 pr-3 font-medium">Run</th>
                <th className="py-2 pr-3 font-medium">Weight</th>
                <th className="py-2 pr-3 font-medium">Score</th>
                <th className="py-2 font-medium">Unknown axes</th>
              </tr>
            </thead>
            <tbody>
              {waterfall.roi_runs.map((r) => (
                <tr key={r.id} className="border-b border-neutral-100">
                  <td className="py-2 pr-3">
                    <div className="font-medium text-black">{r.label}</div>
                    <div className="text-[10px] text-neutral-500">{r.note}</div>
                  </td>
                  <td className="py-2 pr-3 tabular-nums">{(r.weight * 100).toFixed(0)}%</td>
                  <td className="py-2 pr-3 tabular-nums font-semibold">
                    {r.score == null ? (
                      <span className="text-amber-700">unknown</span>
                    ) : (
                      `${r.score.toFixed(1)}/10`
                    )}
                  </td>
                  <td className="py-2 text-[11px] text-neutral-600">
                    {r.unknown_axes.length ? r.unknown_axes.join(", ") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Precedence */}
      <div className="rounded-xl border border-border bg-white p-4 sm:p-5">
        <h3 className="text-sm font-semibold text-black">Precedence examples</h3>
        <p className="mt-0.5 text-[11px] text-neutral-600">
          Paper / desk rules this stance must clear (or fail explicitly).
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {a.precedence_examples.map((p) => (
            <div key={p.id} className="rounded-lg border border-neutral-100 px-3 py-2">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-medium text-black">{p.label}</span>
                <span
                  className={`text-[10px] font-bold uppercase ${
                    p.matched === true
                      ? "text-emerald-700"
                      : p.matched === false
                        ? "text-rose-700"
                        : "text-amber-700"
                  }`}
                >
                  {p.matched === true ? "match" : p.matched === false ? "fail" : "unknown"}
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-neutral-600">{p.rule}</p>
              <p className="mt-0.5 font-mono text-[10px] text-neutral-500">{p.evidence}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
