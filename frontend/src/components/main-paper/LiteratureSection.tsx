/**
 * PATH: frontend/src/components/main-paper/LiteratureSection.tsx
 * PURPOSE: Section 2 – Literature Review & Hypotheses.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - lucide-react BookOpen: section icon
 *  - ui/card: Card + CardContent wrappers
 *  - InfoTooltip: inline term definitions
 */

import { BookOpen } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { InfoTooltip } from "@/components/InfoTooltip"

export function LiteratureSection() {
  return (
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
  )
}
