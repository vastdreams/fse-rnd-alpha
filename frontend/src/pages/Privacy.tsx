/**
 * PATH: src/pages/Privacy.tsx
 * PURPOSE: Privacy Policy page for R&D Alpha
 * 
 * Covers:
 * - Data collection and usage
 * - Cookie policy
 * - Third-party services
 * - User rights (GDPR, CCPA)
 */

import { Link } from "react-router-dom"
import { Shield, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

export function Privacy() {
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
          <div className="p-2 rounded-lg bg-emerald-500/10">
            <Shield className="h-6 w-6 text-emerald-500" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Privacy Policy</h1>
            <p className="text-muted-foreground">Last updated: December 28, 2025</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="prose prose-slate dark:prose-invert max-w-none space-y-8">
        
        <section>
          <h2 className="text-xl font-semibold border-b pb-2">1. Introduction</h2>
          <p className="text-muted-foreground leading-relaxed">
            FSE Research and Investments ("we", "us", or "our") operates the R&D Alpha platform at research.finsoeasy.com. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website or subscribe to our services.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-4">
            We respect your privacy and are committed to protecting your personal data. Please read this policy carefully.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">2. Information We Collect</h2>
          
          <h3 className="text-lg font-medium mt-4">Personal Information</h3>
          <p className="text-muted-foreground leading-relaxed">
            When you subscribe to our newsletter or make a donation, we may collect:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>Email address (required)</li>
            <li>First and last name (optional)</li>
            <li>Profession (optional)</li>
            <li>Payment information (processed securely by Stripe)</li>
          </ul>

          <h3 className="text-lg font-medium mt-4">Automatically Collected Information</h3>
          <p className="text-muted-foreground leading-relaxed">
            When you visit our website, we automatically collect:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>IP address and approximate location</li>
            <li>Browser type and version</li>
            <li>Device type (desktop, mobile, tablet)</li>
            <li>Operating system</li>
            <li>Pages visited and time spent</li>
            <li>Referral source</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">3. How We Use Your Information</h2>
          <p className="text-muted-foreground leading-relaxed">
            We use your information for the following purposes:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li><strong>Newsletter delivery:</strong> To send you research updates, market insights, and announcements</li>
            <li><strong>Service improvement:</strong> To understand how users interact with our platform and improve the experience</li>
            <li><strong>Donation processing:</strong> To process your contributions and send receipts</li>
            <li><strong>Communication:</strong> To respond to inquiries and provide support</li>
            <li><strong>Analytics:</strong> To analyze trends and optimize our content</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">4. Data Sharing and Disclosure</h2>
          <p className="text-muted-foreground leading-relaxed">
            We do not sell, trade, or rent your personal information to third parties. We may share your data with:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li><strong>Stripe:</strong> For secure payment processing (donations)</li>
            <li><strong>Resend:</strong> For email delivery services</li>
            <li><strong>Cloud hosting providers:</strong> For infrastructure (data stored securely)</li>
            <li><strong>Legal authorities:</strong> If required by law or to protect our rights</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">5. Cookies and Tracking</h2>
          <p className="text-muted-foreground leading-relaxed">
            We use minimal cookies and local storage for:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li><strong>Essential functionality:</strong> Remembering your preferences (dark mode, subscribed status)</li>
            <li><strong>Session tracking:</strong> Understanding page visits for analytics</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-4">
            We do not use third-party advertising cookies or sell data to advertisers.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">6. Data Security</h2>
          <p className="text-muted-foreground leading-relaxed">
            We implement appropriate security measures to protect your personal information:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>HTTPS encryption for all data transmission</li>
            <li>Secure password hashing for administrative access</li>
            <li>Database encryption at rest</li>
            <li>Regular security audits</li>
            <li>Access controls and authentication</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-4">
            However, no method of transmission over the Internet is 100% secure. While we strive to protect your data, we cannot guarantee absolute security.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">7. Data Retention</h2>
          <p className="text-muted-foreground leading-relaxed">
            We retain your personal information for as long as necessary to provide our services:
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li><strong>Subscriber data:</strong> Until you unsubscribe (then marked inactive but retained for re-subscription)</li>
            <li><strong>Donation records:</strong> As required by tax and financial regulations</li>
            <li><strong>Analytics data:</strong> Aggregated and anonymized after 12 months</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">8. Your Rights</h2>
          <p className="text-muted-foreground leading-relaxed">
            Depending on your location, you may have the following rights:
          </p>
          
          <h3 className="text-lg font-medium mt-4">For All Users</h3>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li><strong>Unsubscribe:</strong> You can unsubscribe from our newsletter at any time via the link in emails</li>
            <li><strong>Access:</strong> Request a copy of your personal data</li>
            <li><strong>Correction:</strong> Request correction of inaccurate data</li>
            <li><strong>Deletion:</strong> Request deletion of your data (subject to legal requirements)</li>
          </ul>

          <h3 className="text-lg font-medium mt-4">For EU/EEA Residents (GDPR)</h3>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>Right to data portability</li>
            <li>Right to restrict processing</li>
            <li>Right to object to processing</li>
            <li>Right to lodge a complaint with a supervisory authority</li>
          </ul>

          <h3 className="text-lg font-medium mt-4">For California Residents (CCPA)</h3>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>Right to know what personal information is collected</li>
            <li>Right to know if personal information is sold or disclosed</li>
            <li>Right to say no to the sale of personal information (we do not sell data)</li>
            <li>Right to non-discrimination for exercising privacy rights</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">9. Children's Privacy</h2>
          <p className="text-muted-foreground leading-relaxed">
            Our Service is not intended for individuals under the age of 18. We do not knowingly collect personal information from children. If you believe we have collected information from a child, please contact us immediately.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">10. International Data Transfers</h2>
          <p className="text-muted-foreground leading-relaxed">
            Your information may be transferred to and processed in countries other than your own. We ensure appropriate safeguards are in place for such transfers in compliance with applicable data protection laws.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">11. Changes to This Policy</h2>
          <p className="text-muted-foreground leading-relaxed">
            We may update this Privacy Policy from time to time. We will notify you of any material changes by posting the new policy on this page and updating the "Last updated" date. We encourage you to review this policy periodically.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold border-b pb-2">12. Contact Us</h2>
          <p className="text-muted-foreground leading-relaxed">
            If you have questions about this Privacy Policy or wish to exercise your rights, please contact us:
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
          <Link to="/terms" className="text-sm text-muted-foreground hover:text-foreground">
            Terms of Service
          </Link>
        </div>
      </div>
    </div>
  )
}

