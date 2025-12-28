/**
 * PATH: src/pages/Terms.tsx
 * PURPOSE: Terms of Service / Terms & Conditions page for R&D Alpha
 * 
 * Legal terms covering:
 * - Service usage terms
 * - Investment disclaimers
 * - Intellectual property
 * - Limitation of liability
 */

import { Link } from "react-router-dom"
import { FileText, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

export function Terms() {
  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <Button variant="ghost" size="sm" asChild className="mb-4">
          <Link to="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Research
          </Link>
        </Button>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-primary/10">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Terms of Service</h1>
            <p className="text-muted-foreground">Last updated: December 28, 2025</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="prose prose-slate dark:prose-invert max-w-none space-y-8">
        
        <section>
          <h2 className="text-xl font-semibold border-b pb-2">1. Acceptance of Terms</h2>
          <p className="text-muted-foreground leading-relaxed">
            By accessing and using the R&D Alpha platform ("Service") operated by FSE Research and Investments ("we", "us", or "our"), you accept and agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our Service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">2. Description of Service</h2>
          <p className="text-muted-foreground leading-relaxed">
            R&D Alpha provides investment research, analysis, and data visualization tools focused on R&D-intensive companies and factor-based investment strategies. Our Service includes:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>Research papers and whitepapers</li>
            <li>Company analysis and factor screening tools</li>
            <li>Portfolio construction and backtesting visualizations</li>
            <li>Newsletter and email communications</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">3. Investment Disclaimer</h2>
          <div className="bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500 p-4 rounded-r-lg">
            <p className="text-amber-800 dark:text-amber-200 font-medium mb-2">Important Notice</p>
            <p className="text-muted-foreground leading-relaxed">
              <strong>The content provided on R&D Alpha is for informational and educational purposes only.</strong> It does not constitute investment advice, financial advice, trading advice, or any other form of professional advice.
            </p>
          </div>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2 mt-4">
            <li>Past performance does not guarantee future results</li>
            <li>All investments involve risk, including potential loss of principal</li>
            <li>We do not provide personalized investment recommendations</li>
            <li>You should consult with qualified financial professionals before making investment decisions</li>
            <li>Backtested performance is hypothetical and has inherent limitations</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">4. User Responsibilities</h2>
          <p className="text-muted-foreground leading-relaxed">
            When using our Service, you agree to:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>Provide accurate information when subscribing or registering</li>
            <li>Not redistribute or republish our research without permission</li>
            <li>Not attempt to reverse-engineer our data or systems</li>
            <li>Use the Service only for lawful purposes</li>
            <li>Not use automated systems to access our Service without permission</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">5. Intellectual Property</h2>
          <p className="text-muted-foreground leading-relaxed">
            All content on R&D Alpha, including but not limited to research papers, analysis, data visualizations, code, graphics, and trademarks, is owned by FSE Research and Investments or its licensors and is protected by intellectual property laws.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-4">
            You may view and download content for personal, non-commercial use only. Any other use requires our written permission.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">6. Data Sources and Accuracy</h2>
          <p className="text-muted-foreground leading-relaxed">
            While we strive to provide accurate and up-to-date information, we cannot guarantee the accuracy, completeness, or timeliness of all data. Our data sources include:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>SEC EDGAR filings (10-K, 10-Q reports)</li>
            <li>Third-party financial data providers</li>
            <li>Public market data</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-4">
            You should verify any information before relying on it for investment decisions.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">7. Limitation of Liability</h2>
          <p className="text-muted-foreground leading-relaxed">
            To the maximum extent permitted by law, FSE Research and Investments shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to loss of profits, data, or investment losses, arising from your use of the Service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">8. Donations</h2>
          <p className="text-muted-foreground leading-relaxed">
            Donations made through our platform are voluntary contributions to support our research. Donations are non-refundable unless required by law. Recurring donations can be cancelled at any time through your Stripe account or by contacting us.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">9. Modifications to Terms</h2>
          <p className="text-muted-foreground leading-relaxed">
            We reserve the right to modify these Terms at any time. We will notify subscribers of material changes via email. Your continued use of the Service after changes constitutes acceptance of the new Terms.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">10. Governing Law</h2>
          <p className="text-muted-foreground leading-relaxed">
            These Terms shall be governed by and construed in accordance with the laws of Australia, without regard to its conflict of law provisions.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">11. Contact Information</h2>
          <p className="text-muted-foreground leading-relaxed">
            For questions about these Terms, please contact us at:
          </p>
          <div className="bg-muted/50 p-4 rounded-lg mt-4">
            <p className="font-medium">FSE Research and Investments</p>
            <p className="text-muted-foreground">Email: abhishek@finsoeasy.com</p>
            <p className="text-muted-foreground">Website: finsoeasy.com</p>
          </div>
        </section>

      </div>

      {/* Footer Navigation */}
      <div className="mt-12 pt-8 border-t flex flex-wrap gap-4 justify-between items-center">
        <Button variant="outline" asChild>
          <Link to="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Research
          </Link>
        </Button>
        <div className="flex gap-4">
          <Link to="/privacy" className="text-sm text-muted-foreground hover:text-foreground">
            Privacy Policy
          </Link>
        </div>
      </div>
    </div>
  )
}

