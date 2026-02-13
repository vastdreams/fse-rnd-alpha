/** PATH: main-paper/DiscussionSectionEvidence.tsx — Sections 8.1 (Summary), 8.2 (Horizon/Regime), 8.3 (Sector) */
import { InfoTooltip } from "@/components/InfoTooltip"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function DiscussionSectionEvidence({ snapshotPayload, annualHmlData, headlinePremiums, transactionCosts, rolling20yrEndpoints, regimePremiumTable }: { snapshotPayload: any; annualHmlData: any; headlinePremiums: any[]; transactionCosts: any; rolling20yrEndpoints: any; regimePremiumTable: any[] }) {
  return (
    <>
      <div>
        <h3 className="text-lg font-semibold text-foreground">8.1 Summary of evidence</h3>
        <p className="text-muted-foreground">
          Across Sections 5-7, the evidence is consistent with a positive return premium associated with high R&D intensity. Primary statistical inference
          uses monthly Fama-MacBeth cross-sectional regressions (Section 7.4) and factor spanning tests (Section 7.3), which provide sufficient observations
          for reliable hypothesis testing. The annual non-overlapping series (Section 5.1) provides economic intuition.
        </p>
        <ul className="text-muted-foreground list-disc list-inside space-y-2">
          <li>
            <strong className="text-foreground">Fama-MacBeth (primary):</strong>{" "}
            {(() => {
              const fm = (snapshotPayload as any)?.fama_macbeth_monthly;
              if (fm?.rd_intensity?.significant_005) {
                return `R&D predicts returns (t = ${fm.rd_intensity.t_stat_hac?.toFixed(2)}, p = ${fm.rd_intensity.p_value_hac?.toFixed(4)}) across ${fm.n_months} months.`;
              }
              return "reported in Section 7.4.";
            })()}
          </li>
          <li>
            <strong className="text-foreground">Annual premium (descriptive):</strong>{" "}
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
              ? `net premium ${transactionCosts.net_rd_premium_pct.toFixed(2)}% pp/yr vs SPY (${transactionCosts.period_label || "N/A"}); see Section 9`
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
    </>
  )
}
