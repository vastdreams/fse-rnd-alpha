/** PATH: main-paper/DiscussionSectionAnalysis.tsx — Sections 8.4-8.7 (Factors, Mechanisms, AI era, Future) */
import { InfoTooltip } from "@/components/InfoTooltip"

export function DiscussionSectionAnalysis() {
  return (
    <>
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
          This design does not identify mechanisms, but the stratification diagnostics in Section 7.5 provide structured evidence that is more consistent
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
    </>
  )
}
