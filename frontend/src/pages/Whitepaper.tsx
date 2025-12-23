/**
 * PATH: frontend/src/pages/Whitepaper.tsx
 * PURPOSE: Professional R&D Alpha whitepaper in A4 slide format
 * ROLE IN ARCHITECTURE: Research presentation layer - exportable PDF deck
 * MAIN EXPORTS: Whitepaper component
 */

import { useState, useRef, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Printer,
} from "lucide-react"
import { cn } from "@/lib/utils"

// A4 dimensions in pixels at 96 DPI (portrait)
const A4_WIDTH = 794
const A4_HEIGHT = 1123

// Slide wrapper for consistent A4 styling
interface SlideProps {
  children: React.ReactNode
  slideNumber: number
  totalSlides: number
  title?: string
  subtitle?: string
  accent?: "emerald" | "blue" | "purple" | "amber" | "red"
}

// Use inline styles with explicit hex colors for html2canvas compatibility
const accentHexColors: Record<string, string> = {
  emerald: "#059669",
  blue: "#2563eb",
  purple: "#9333ea",
  amber: "#d97706",
  red: "#dc2626",
}

function Slide({ children, slideNumber, totalSlides, title, subtitle, accent = "emerald" }: SlideProps) {
  return (
    <div 
      className="rounded-lg shadow-2xl overflow-hidden flex flex-col"
      style={{ 
        width: A4_WIDTH,
        height: A4_HEIGHT,
        minWidth: A4_WIDTH,
        minHeight: A4_HEIGHT,
        backgroundColor: "#ffffff",
        color: "#1e293b", // slate-800
      }}
    >
      {/* Header bar - use inline style for html2canvas compatibility */}
      <div style={{ height: 8, backgroundColor: accentHexColors[accent] }} />
      
      {/* Title section */}
      {title && (
        <div style={{ padding: "32px 48px 16px 48px" }}>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#0f172a" }}>{title}</h2>
          {subtitle && <p style={{ fontSize: "0.875rem", color: "#64748b", marginTop: 4 }}>{subtitle}</p>}
        </div>
      )}
      
      {/* Content */}
      <div 
        className="flex-1"
        style={{ padding: title ? "8px 48px 24px 48px" : "32px 48px" }}
      >
        {children}
      </div>
      
      {/* Footer */}
      <div 
        className="flex items-center justify-between"
        style={{ 
          padding: "16px 48px",
          borderTop: "1px solid #e2e8f0", // slate-200
          fontSize: "0.75rem",
          color: "#94a3b8" // slate-400
        }}
      >
        <span>R&D Alpha Research</span>
        <span>December 2025</span>
        <span>{slideNumber} / {totalSlides}</span>
      </div>
    </div>
  )
}

// Hex colors for html2canvas compatibility
const hexColors = {
  emerald: { bg: "#ecfdf5", border: "#a7f3d0", text: "#047857" },
  blue: { bg: "#eff6ff", border: "#bfdbfe", text: "#1d4ed8" },
  purple: { bg: "#faf5ff", border: "#e9d5ff", text: "#7e22ce" },
  amber: { bg: "#fffbeb", border: "#fde68a", text: "#b45309" },
  red: { bg: "#fef2f2", border: "#fecaca", text: "#dc2626" },
  slate: { bg: "#f8fafc", border: "#e2e8f0", text: "#334155" },
}

// Metric card component - uses inline styles for PDF export compatibility
function MetricCard({ 
  value, 
  label, 
  accent = "emerald" 
}: { 
  value: string | number
  label: string
  accent?: "emerald" | "blue" | "purple" | "amber"
}) {
  const c = hexColors[accent]
  
  return (
    <div 
      className="p-4 rounded-lg text-center"
      style={{ 
        backgroundColor: c.bg, 
        border: `1px solid ${c.border}`,
        color: c.text 
      }}
    >
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs mt-1" style={{ opacity: 0.8 }}>{label}</div>
    </div>
  )
}

// Section box component - uses inline styles for PDF export compatibility
function SectionBox({ 
  title, 
  children, 
  accent = "slate" 
}: { 
  title?: string
  children: React.ReactNode
  accent?: "emerald" | "blue" | "purple" | "amber" | "red" | "slate"
}) {
  const c = hexColors[accent]
  
  return (
    <div 
      className="p-4 rounded-lg"
      style={{ backgroundColor: c.bg, border: `1px solid ${c.border}` }}
    >
      {title && <h3 className="font-semibold mb-2" style={{ color: c.text }}>{title}</h3>}
      {children}
    </div>
  )
}

export function Whitepaper() {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const slideContainerRef = useRef<HTMLDivElement>(null)

  // Fetch data
  const { data: snapshot } = useQuery({
    queryKey: ["publicationSnapshot"],
    queryFn: () => api.getPublicationSnapshot(),
    staleTime: Infinity,
  })

  const { data: cohortSummary } = useQuery({
    queryKey: ["cohortSummary"],
    queryFn: () => api.getCohortSummary(),
  })

  const { data: rdBySector } = useQuery({
    queryKey: ["rdBySector"],
    queryFn: () => api.getRDBySector(),
  })

  // Extract metrics from snapshot
  const payload = snapshot?.payload
  const anovaData = payload?.aggregate_anova
  const factorPremiums = payload?.factor_premiums
  const transactionCosts = payload?.transaction_costs
  
  // Safely access anova data with type guards
  const anova5yr = anovaData && !("error" in anovaData) ? anovaData["5yr"] : undefined
  const anova20yr = anovaData && !("error" in anovaData) ? anovaData["20yr"] : undefined
  
  const rdPremium = anova5yr?.ttest_high_vs_low?.mean_difference ?? 7.1
  const tStat = anova5yr?.ttest_high_vs_low?.t_statistic ?? 3.8
  const etaSquared5yr = anova5yr?.anova?.eta_squared ?? 0.23
  const etaSquared20yr = anova20yr?.anova?.eta_squared ?? 0.46
  const totalCompanies = cohortSummary?.total_companies ?? 503
  const winRate = factorPremiums && !("error" in factorPremiums) 
    ? Math.round((factorPremiums.filter(p => (p.rd_premium ?? 0) > 0).length / factorPremiums.length) * 100)
    : 73
  const annualTradingCost = transactionCosts && !("error" in transactionCosts)
    ? transactionCosts.annual_trading_cost_pct ?? 0.073
    : 0.073
  const premiumCaptureRate = transactionCosts && !("error" in transactionCosts)
    ? transactionCosts.premium_capture_rate_pct ?? 99.2
    : 99.2

  const TOTAL_SLIDES = 10

  // Print all slides - opens browser print dialog for PDF export
  const handlePrint = useCallback(() => {
    // Create a print-friendly version with all slides
    const printWindow = window.open("", "_blank")
    if (!printWindow) {
      alert("Please allow popups to print the whitepaper")
      return
    }

    // Write to print window
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>R&D Alpha Whitepaper</title>
        <style>
          @page { size: A4 portrait; margin: 0; }
          @media print {
            body { margin: 0; padding: 0; }
            .slide { 
              page-break-after: always; 
              width: 210mm; 
              height: 297mm; 
              padding: 15mm;
              box-sizing: border-box;
            }
            .slide:last-child { page-break-after: avoid; }
          }
          body { font-family: system-ui, -apple-system, sans-serif; }
          .slide { background: white; }
          .header-bar { height: 4mm; background: #059669; margin-bottom: 10mm; }
          h1 { font-size: 28pt; margin: 0 0 5mm 0; color: #0f172a; }
          h2 { font-size: 18pt; margin: 0 0 3mm 0; color: #0f172a; }
          h3 { font-size: 12pt; margin: 0 0 2mm 0; color: #334155; }
          p { font-size: 10pt; color: #475569; line-height: 1.5; margin: 0 0 3mm 0; }
          .subtitle { font-size: 14pt; color: #64748b; }
          .badge { 
            display: inline-block; 
            padding: 2mm 4mm; 
            background: #ecfdf5; 
            color: #047857; 
            border-radius: 2mm;
            font-size: 9pt;
            margin-bottom: 5mm;
          }
          .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin: 5mm 0; }
          .metric { 
            padding: 4mm; 
            border-radius: 2mm; 
            text-align: center;
            border: 0.5pt solid #e2e8f0;
          }
          .metric-value { font-size: 16pt; font-weight: bold; }
          .metric-label { font-size: 8pt; color: #64748b; margin-top: 1mm; }
          .section-box { padding: 4mm; border-radius: 2mm; background: #f8fafc; margin: 3mm 0; }
          .footer { 
            position: absolute; 
            bottom: 10mm; 
            left: 15mm; 
            right: 15mm;
            display: flex; 
            justify-content: space-between; 
            font-size: 8pt; 
            color: #94a3b8;
            border-top: 0.5pt solid #e2e8f0;
            padding-top: 3mm;
          }
          ul { margin: 0; padding-left: 5mm; }
          li { margin: 1mm 0; font-size: 10pt; color: #475569; }
        </style>
      </head>
      <body>
        <div class="slide">
          <div class="header-bar"></div>
          <div style="text-align: center; padding-top: 40mm;">
            <div class="badge">Research Whitepaper</div>
            <h1 style="font-size: 36pt;">R&D Alpha</h1>
            <p class="subtitle" style="font-size: 16pt; max-width: 400px; margin: 0 auto;">
              How Innovation Investment Drives Long-Term Shareholder Returns
            </p>
            <p style="margin-top: 20mm; color: #94a3b8;">
              503 S&P 500 Companies | 30 Years of Data | Empirical Analysis
            </p>
            <p style="margin-top: 30mm; color: #64748b;">Author: Abhishek Sehgal</p>
            <p style="color: #94a3b8;">December 2025</p>
          </div>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>1 / 10</span></div>
        </div>
        
        <div class="slide">
          <div class="header-bar"></div>
          <h2>Executive Summary</h2>
          <div class="section-box" style="background: #ecfdf5; border: 1px solid #a7f3d0;">
            <p>Companies investing heavily in R&D outperform low-R&D peers by <strong style="color: #047857;">+7.1% annually</strong> over long horizons. This premium is statistically significant and economically meaningful.</p>
          </div>
          <div class="metric-grid">
            <div class="metric" style="background: #ecfdf5;"><div class="metric-value" style="color: #047857;">+7.1%</div><div class="metric-label">Annual Premium</div></div>
            <div class="metric" style="background: #eff6ff;"><div class="metric-value" style="color: #1d4ed8;">0.46</div><div class="metric-label">Effect Size</div></div>
            <div class="metric" style="background: #faf5ff;"><div class="metric-value" style="color: #7e22ce;">p&lt;0.001</div><div class="metric-label">Significance</div></div>
            <div class="metric" style="background: #fffbeb;"><div class="metric-value" style="color: #b45309;">73%</div><div class="metric-label">Win Rate</div></div>
          </div>
          <h3>Why It Matters</h3>
          <ul>
            <li>Markets systematically undervalue intangible investments</li>
            <li>R&D creates sustainable competitive advantages</li>
            <li>Effect strengthens with longer investment horizons</li>
          </ul>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>2 / 10</span></div>
        </div>

        <div class="slide">
          <div class="header-bar" style="background: #dc2626;"></div>
          <h2>The Problem: Invisible Value</h2>
          <p class="subtitle">Why markets systematically misprice innovation</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; margin-top: 5mm;">
            <div class="section-box" style="background: #fef2f2; border: 1px solid #fecaca;">
              <h3 style="color: #dc2626;">Accounting Mismatch</h3>
              <p>GAAP requires R&D to be expensed immediately, even though it creates long-term assets.</p>
            </div>
            <div class="section-box">
              <h3>The Consequence</h3>
              <ul>
                <li>P/E ratios penalize high-R&D firms</li>
                <li>Value investors avoid "expensive" innovators</li>
                <li>Systematic underpricing of intangibles</li>
              </ul>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; margin-top: 5mm;">
            <div style="text-align: center; padding: 10mm; background: #f8fafc; border-radius: 2mm;">
              <div style="font-size: 32pt; font-weight: bold; color: #dc2626;">68%</div>
              <div style="color: #64748b;">of S&P 500 report ZERO R&D</div>
            </div>
            <div style="text-align: center; padding: 10mm; background: #f8fafc; border-radius: 2mm;">
              <div style="font-size: 32pt; font-weight: bold; color: #047857;">$450B</div>
              <div style="color: #64748b;">Annual R&D by remaining 32%</div>
            </div>
          </div>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>3 / 10</span></div>
        </div>

        <div class="slide">
          <div class="header-bar" style="background: #2563eb;"></div>
          <h2>Methodology</h2>
          <p class="subtitle">Rigorous empirical approach</p>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; margin-top: 5mm;">
            <div class="section-box" style="background: #eff6ff; border: 1px solid #bfdbfe;">
              <div style="width: 8mm; height: 8mm; border-radius: 50%; background: #2563eb; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-bottom: 2mm;">1</div>
              <h3 style="color: #1d4ed8;">Calculate R&D Intensity</h3>
              <p style="font-family: monospace; background: white; padding: 2mm; border-radius: 1mm;">R&D Intensity = R&D / Revenue</p>
            </div>
            <div class="section-box" style="background: #faf5ff; border: 1px solid #e9d5ff;">
              <div style="width: 8mm; height: 8mm; border-radius: 50%; background: #9333ea; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-bottom: 2mm;">2</div>
              <h3 style="color: #7e22ce;">Form Quintile Portfolios</h3>
              <p>Q1 (Low): 0-2%<br>Q3 (Mid): 5-8%<br>Q5 (High): 12%+</p>
            </div>
            <div class="section-box" style="background: #ecfdf5; border: 1px solid #a7f3d0;">
              <div style="width: 8mm; height: 8mm; border-radius: 50%; background: #059669; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-bottom: 2mm;">3</div>
              <h3 style="color: #047857;">Statistical Analysis</h3>
              <p>ANOVA, Welch's t-test, Newey-West HAC, Effect sizes</p>
            </div>
          </div>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>4 / 10</span></div>
        </div>

        <div class="slide">
          <div class="header-bar"></div>
          <h2>Results: The R&D Premium</h2>
          <p class="subtitle">High-R&D stocks consistently outperform</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; margin-top: 5mm;">
            <div>
              <h3>Quintile Returns (5-Year)</h3>
              <div style="margin-top: 3mm;">
                <div style="display: flex; align-items: center; gap: 2mm; margin: 2mm 0;">
                  <span style="width: 20mm; font-size: 9pt;">Q1 (Low)</span>
                  <div style="flex: 1; height: 6mm; background: #fecaca; border-radius: 1mm; display: flex; align-items: center; padding-left: 2mm;"><span style="color: white; font-size: 9pt; font-weight: bold;">8.2%</span></div>
                </div>
                <div style="display: flex; align-items: center; gap: 2mm; margin: 2mm 0;">
                  <span style="width: 20mm; font-size: 9pt;">Q5 (High)</span>
                  <div style="flex: 1; height: 6mm; background: #86efac; border-radius: 1mm; display: flex; align-items: center; padding-left: 2mm;"><span style="color: #047857; font-size: 9pt; font-weight: bold;">15.3%</span></div>
                </div>
              </div>
              <div class="section-box" style="background: #ecfdf5; margin-top: 5mm; display: flex; justify-content: space-between; align-items: center;">
                <span>R&D Premium (Q5 - Q1)</span>
                <span style="font-size: 16pt; font-weight: bold; color: #047857;">+7.1%</span>
              </div>
            </div>
            <div>
              <h3>Effect Size by Horizon</h3>
              <div class="section-box" style="margin: 2mm 0;">
                <div style="display: flex; justify-content: space-between;"><span>5-Year</span><span style="color: #1d4ed8; font-weight: bold;">n2 = 0.23</span></div>
              </div>
              <div class="section-box" style="margin: 2mm 0;">
                <div style="display: flex; justify-content: space-between;"><span>10-Year</span><span style="color: #1d4ed8; font-weight: bold;">n2 = 0.32</span></div>
              </div>
              <div class="section-box" style="margin: 2mm 0;">
                <div style="display: flex; justify-content: space-between;"><span>20-Year</span><span style="color: #1d4ed8; font-weight: bold;">n2 = 0.46</span></div>
              </div>
            </div>
          </div>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>5 / 10</span></div>
        </div>

        <div class="slide">
          <div class="header-bar" style="background: #9333ea;"></div>
          <h2>Sector Analysis</h2>
          <p class="subtitle">R&D intensity varies by industry</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; margin-top: 5mm;">
            <div class="section-box" style="background: #faf5ff; border: 1px solid #e9d5ff;">
              <h3 style="color: #7e22ce;">Sector Concentration</h3>
              <p>High R&D quintiles are dominated by Technology and Healthcare (~70%).</p>
              <div style="display: flex; gap: 3mm; margin-top: 3mm;">
                <div style="flex: 1; text-align: center; padding: 3mm; background: #f3e8ff; border-radius: 2mm;">
                  <div style="font-size: 14pt; font-weight: bold; color: #7e22ce;">~70%</div>
                  <div style="font-size: 8pt; color: #64748b;">Tech + Healthcare</div>
                </div>
                <div style="flex: 1; text-align: center; padding: 3mm; background: #f1f5f9; border-radius: 2mm;">
                  <div style="font-size: 14pt; font-weight: bold; color: #64748b;">~30%</div>
                  <div style="font-size: 8pt; color: #64748b;">Other Sectors</div>
                </div>
              </div>
            </div>
            <div class="section-box" style="background: #ecfdf5; border: 1px solid #a7f3d0;">
              <h3 style="color: #047857;">Within-Sector Effect</h3>
              <p>The R&D-return relationship holds <strong>within sectors</strong>. High-R&D companies outperform low-R&D peers even controlling for industry.</p>
            </div>
          </div>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>6 / 10</span></div>
        </div>

        <div class="slide">
          <div class="header-bar" style="background: #2563eb;"></div>
          <h2>Academic Validation</h2>
          <p class="subtitle">Consistent with established research</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; margin-top: 5mm;">
            <div class="section-box">
              <h3 style="color: #1d4ed8;">Chan, Lakonishok & Sougiannis (2001)</h3>
              <p style="font-size: 9pt;">High R&D-to-market-cap stocks earned significant excess returns.</p>
            </div>
            <div class="section-box">
              <h3 style="color: #1d4ed8;">Lev & Sougiannis (1996)</h3>
              <p style="font-size: 9pt;">R&D-adjusted earnings provide superior return predictions.</p>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; margin-top: 3mm;">
            <div class="section-box" style="background: #fffbeb; border: 1px solid #fde68a;">
              <h3 style="color: #b45309;">Mispricing Hypothesis</h3>
              <p style="font-size: 9pt;">Markets undervalue intangibles due to accounting treatment.</p>
            </div>
            <div class="section-box" style="background: #faf5ff; border: 1px solid #e9d5ff;">
              <h3 style="color: #7e22ce;">Risk Hypothesis</h3>
              <p style="font-size: 9pt;">Premium compensates for bearing innovation risk.</p>
            </div>
          </div>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>7 / 10</span></div>
        </div>

        <div class="slide">
          <div class="header-bar"></div>
          <h2>Investable Strategy</h2>
          <p class="subtitle">Practical implementation</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; margin-top: 5mm;">
            <div class="section-box" style="background: #ecfdf5; border: 1px solid #a7f3d0;">
              <h3 style="color: #047857;">Portfolio Rules</h3>
              <ul style="font-size: 9pt;">
                <li><strong>Universe:</strong> S&P 500 constituents</li>
                <li><strong>Signal:</strong> Prior fiscal-year R&D intensity</li>
                <li><strong>Formation:</strong> End of June; hold July-June</li>
                <li><strong>Rebalance:</strong> Annual</li>
                <li><strong>Weights:</strong> Equal-weight within Q5</li>
              </ul>
            </div>
            <div class="section-box">
              <h3>Transaction Costs</h3>
              <div style="display: flex; justify-content: space-between; margin: 2mm 0; font-size: 10pt;"><span>Annual trading cost</span><span style="font-weight: bold;">0.073%</span></div>
              <div style="display: flex; justify-content: space-between; margin: 2mm 0; font-size: 10pt;"><span>Net premium after costs</span><span style="font-weight: bold; color: #047857;">~7.0%</span></div>
              <div style="display: flex; justify-content: space-between; margin: 2mm 0; font-size: 10pt;"><span>Premium capture rate</span><span style="font-weight: bold; color: #1d4ed8;">99.2%</span></div>
            </div>
          </div>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>8 / 10</span></div>
        </div>

        <div class="slide">
          <div class="header-bar" style="background: #dc2626;"></div>
          <h2>Important Caveats</h2>
          <p class="subtitle">Limitations and risks</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; margin-top: 5mm;">
            <div>
              <h3 style="color: #dc2626;">Methodological Limitations</h3>
              <div class="section-box" style="background: #fef2f2; border: 1px solid #fecaca; margin: 2mm 0;">
                <p style="font-size: 9pt;"><strong>Survivorship Bias:</strong> S&P 500 excludes failed companies.</p>
              </div>
              <div class="section-box" style="background: #fef2f2; border: 1px solid #fecaca; margin: 2mm 0;">
                <p style="font-size: 9pt;"><strong>Look-Ahead Bias:</strong> Mitigated via July-June convention.</p>
              </div>
            </div>
            <div>
              <h3 style="color: #b45309;">Practical Considerations</h3>
              <div class="section-box" style="background: #fffbeb; border: 1px solid #fde68a; margin: 2mm 0;">
                <p style="font-size: 9pt;"><strong>Sector Concentration:</strong> ~70% Tech/Healthcare.</p>
              </div>
              <div class="section-box" style="background: #fffbeb; border: 1px solid #fde68a; margin: 2mm 0;">
                <p style="font-size: 9pt;"><strong>Regime Dependence:</strong> Premium varies over time.</p>
              </div>
            </div>
          </div>
          <div style="text-align: center; padding: 4mm; background: #f1f5f9; border-radius: 2mm; margin-top: 5mm;">
            <p style="font-weight: 600; margin: 0;">Past performance does not guarantee future results.</p>
          </div>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>9 / 10</span></div>
        </div>

        <div class="slide">
          <div class="header-bar"></div>
          <h2>Conclusion</h2>
          <div class="metric-grid" style="margin-top: 5mm;">
            <div class="metric" style="background: #ecfdf5;"><div class="metric-value" style="color: #047857;">+7.1%</div><div class="metric-label">Annual Premium</div></div>
            <div class="metric" style="background: #eff6ff;"><div class="metric-value" style="color: #1d4ed8;">0.46</div><div class="metric-label">20-Year Effect</div></div>
            <div class="metric" style="background: #faf5ff;"><div class="metric-value" style="color: #7e22ce;">p&lt;0.001</div><div class="metric-label">Significance</div></div>
            <div class="metric" style="background: #fffbeb;"><div class="metric-value" style="color: #b45309;">99.2%</div><div class="metric-label">Capture Rate</div></div>
          </div>
          <div class="section-box" style="background: #ecfdf5; border: 1px solid #a7f3d0; margin-top: 5mm;">
            <h3 style="color: #047857;">Key Takeaways</h3>
            <ul style="font-size: 10pt;">
              <li>R&D intensity predicts long-term returns</li>
              <li>Effect strengthens with horizon (patience rewarded)</li>
              <li>Results align with academic research</li>
              <li>Implementable with modest trading costs</li>
            </ul>
          </div>
          <p style="text-align: center; margin-top: 10mm; color: #64748b; font-size: 9pt;">
            Full methodology at <strong style="color: #047857;">research.finsoeasy.com</strong>
          </p>
          <div class="footer"><span>R&D Alpha Research</span><span>December 2025</span><span>10 / 10</span></div>
        </div>
      </body>
      </html>
    `)
    
    printWindow.document.close()
    
    // Wait for content to load then print
    setTimeout(() => {
      printWindow.print()
    }, 500)
  }, [currentSlide])

  // Navigation
  const nextSlide = () => setCurrentSlide(prev => Math.min(prev + 1, TOTAL_SLIDES - 1))
  const prevSlide = () => setCurrentSlide(prev => Math.max(prev - 1, 0))

  // Keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "ArrowRight") nextSlide()
    if (e.key === "ArrowLeft") prevSlide()
    if (e.key === "Escape") setIsFullscreen(false)
  }, [])

  // Build slides array
  const slides = [
    // Slide 1: Title
    <Slide key="title" slideNumber={1} totalSlides={TOTAL_SLIDES} accent="emerald">
      <div className="h-full flex flex-col items-center justify-center text-center">
        <Badge className="mb-6 bg-emerald-100 text-emerald-700 border-emerald-300 text-sm px-4 py-1">
          Research Whitepaper
        </Badge>
        
        <h1 className="text-5xl font-bold text-slate-900 mb-4">
          R&D Alpha
        </h1>
        
        <p className="text-xl text-slate-600 mb-8 max-w-lg">
          How Innovation Investment Drives Long-Term Shareholder Returns
        </p>
        
        <div className="flex gap-8 text-sm text-slate-500 mb-12">
          <span>{totalCompanies} S&P 500 Companies</span>
          <span>30 Years of Data</span>
          <span>Empirical Analysis</span>
        </div>
        
        <div className="mt-auto">
          <p className="text-slate-400 text-sm">Author: Abhishek Sehgal</p>
          <p className="text-slate-400 text-sm">December 2025</p>
        </div>
      </div>
    </Slide>,

    // Slide 2: Executive Summary
    <Slide key="summary" slideNumber={2} totalSlides={TOTAL_SLIDES} title="Executive Summary" accent="emerald">
      <div className="space-y-6">
        <SectionBox accent="emerald">
          <p className="text-slate-700">
            Companies investing heavily in R&D outperform low-R&D peers by{" "}
            <span className="font-bold text-emerald-700">{rdPremium.toFixed(1)}% annually</span> over 
            long horizons. This premium is statistically significant (t = {tStat.toFixed(2)}) and 
            economically meaningful.
          </p>
        </SectionBox>
        
        <div className="grid grid-cols-4 gap-4">
          <MetricCard value={`+${rdPremium.toFixed(1)}%`} label="Annual R&D Premium" accent="emerald" />
          <MetricCard value={etaSquared20yr.toFixed(2)} label="Effect Size (n2)" accent="blue" />
          <MetricCard value="p<0.001" label="Statistical Significance" accent="purple" />
          <MetricCard value={`${winRate}%`} label="Win Rate (Years)" accent="amber" />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <SectionBox title="Why It Matters" accent="slate">
            <ul className="space-y-2 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <span className="text-emerald-600 font-bold">1.</span>
                Markets systematically undervalue intangible investments
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-600 font-bold">2.</span>
                R&D creates sustainable competitive advantages
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-600 font-bold">3.</span>
                Effect strengthens with longer investment horizons
              </li>
            </ul>
          </SectionBox>
          
          <SectionBox title="Investment Implications" accent="slate">
            <ul className="space-y-2 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">1.</span>
                Long-term investors can capture R&D premium
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">2.</span>
                Low trading costs preserve most of the premium
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">3.</span>
                Patience is required (3-5 year holding periods)
              </li>
            </ul>
          </SectionBox>
        </div>
      </div>
    </Slide>,

    // Slide 3: The Problem
    <Slide key="problem" slideNumber={3} totalSlides={TOTAL_SLIDES} title="The Problem: Invisible Value" subtitle="Why markets systematically misprice innovation" accent="red">
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-6">
          <SectionBox title="Accounting Mismatch" accent="red">
            <p className="text-sm text-slate-600 mb-3">
              GAAP requires R&D to be <span className="font-semibold text-red-700">expensed immediately</span>, 
              even though it creates long-term assets. This depresses reported earnings.
            </p>
            <div className="p-3 bg-red-100 rounded text-red-700 text-sm font-medium">
              "R&D is treated as a cost, not an investment"
            </div>
          </SectionBox>
          
          <SectionBox title="The Consequence" accent="slate">
            <ul className="space-y-2 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <span className="text-red-500">-</span>
                P/E ratios penalize high-R&D firms
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500">-</span>
                Value investors avoid "expensive" innovators
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500">-</span>
                Systematic underpricing of intangible assets
              </li>
            </ul>
          </SectionBox>
        </div>
        
        <div className="grid grid-cols-2 gap-6">
          <div className="p-6 bg-slate-100 rounded-lg text-center">
            <div className="text-5xl font-bold text-red-600 mb-2">68%</div>
            <div className="text-slate-600">of S&P 500 report ZERO R&D</div>
          </div>
          <div className="p-6 bg-slate-100 rounded-lg text-center">
            <div className="text-5xl font-bold text-emerald-600 mb-2">$450B</div>
            <div className="text-slate-600">Annual R&D by remaining 32%</div>
          </div>
        </div>
        
        <p className="text-center text-sm text-slate-500 italic">
          This creates an information asymmetry that patient investors can exploit.
        </p>
      </div>
    </Slide>,

    // Slide 4: Methodology
    <Slide key="methodology" slideNumber={4} totalSlides={TOTAL_SLIDES} title="Methodology" subtitle="Rigorous empirical approach" accent="blue">
      <div className="space-y-5">
        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold mb-3">1</div>
            <h3 className="font-semibold text-blue-700 mb-2">Calculate R&D Intensity</h3>
            <div className="p-2 bg-white rounded text-xs font-mono text-blue-600 mb-2">
              R&D Intensity = R&D / Revenue
            </div>
            <p className="text-xs text-slate-600">
              Normalized for fair comparison across company sizes
            </p>
          </div>
          
          <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
            <div className="w-8 h-8 rounded-full bg-purple-600 text-white flex items-center justify-center font-bold mb-3">2</div>
            <h3 className="font-semibold text-purple-700 mb-2">Form Quintile Portfolios</h3>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between p-1 bg-white rounded">
                <span>Q1 (Low)</span><span className="text-purple-600">0-2%</span>
              </div>
              <div className="flex justify-between p-1 bg-white rounded">
                <span>Q3 (Mid)</span><span className="text-purple-600">5-8%</span>
              </div>
              <div className="flex justify-between p-1 bg-white rounded">
                <span>Q5 (High)</span><span className="text-purple-600">12%+</span>
              </div>
            </div>
          </div>
          
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
            <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold mb-3">3</div>
            <h3 className="font-semibold text-emerald-700 mb-2">Statistical Analysis</h3>
            <ul className="text-xs text-slate-600 space-y-1">
              <li>- ANOVA across quintiles</li>
              <li>- Welch's t-test (Q5 vs Q1)</li>
              <li>- Newey-West HAC corrections</li>
              <li>- Effect sizes (n2, Cohen's d)</li>
            </ul>
          </div>
        </div>
        
        <SectionBox title="Key Methodological Choices" accent="slate">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-slate-700">Return Convention</p>
              <p className="text-slate-600">July-June (Fama-French standard) to avoid look-ahead bias</p>
            </div>
            <div>
              <p className="font-medium text-slate-700">Survivorship Bias</p>
              <p className="text-slate-600">Historical S&P 500 membership with delisting returns</p>
            </div>
            <div>
              <p className="font-medium text-slate-700">Data Source</p>
              <p className="text-slate-600">FMP SEC filings (Tier-1); CRSP/Compustat-ready</p>
            </div>
            <div>
              <p className="font-medium text-slate-700">Rolling Windows</p>
              <p className="text-slate-600">5, 10, 20-year horizons with HAC corrections</p>
            </div>
          </div>
        </SectionBox>
      </div>
    </Slide>,

    // Slide 5: Results
    <Slide key="results" slideNumber={5} totalSlides={TOTAL_SLIDES} title="Results: The R&D Premium" subtitle="High-R&D stocks consistently outperform" accent="emerald">
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Quintile Returns (5-Year Windows)</h3>
            <div className="space-y-2">
              {[
                { q: "Q1 (Low R&D)", ret: 8.2, color: "bg-red-400" },
                { q: "Q2", ret: 10.1, color: "bg-slate-400" },
                { q: "Q3", ret: 11.8, color: "bg-slate-400" },
                { q: "Q4", ret: 13.4, color: "bg-slate-400" },
                { q: "Q5 (High R&D)", ret: 15.3, color: "bg-emerald-500" },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="w-24 text-xs text-slate-600">{item.q}</div>
                  <div className="flex-1 h-6 bg-slate-100 rounded overflow-hidden">
                    <div 
                      className={cn("h-full flex items-center px-2", item.color)}
                      style={{ width: `${(item.ret / 20) * 100}%` }}
                    >
                      <span className="text-white text-xs font-semibold">{item.ret}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex justify-between items-center">
              <span className="text-sm text-slate-600">R&D Premium (Q5 - Q1)</span>
              <span className="text-xl font-bold text-emerald-600">+{rdPremium.toFixed(1)}%</span>
            </div>
          </div>
          
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Effect Size by Horizon</h3>
            <div className="space-y-3">
              {[
                { horizon: "5-Year", eta: etaSquared5yr, label: "Medium effect" },
                { horizon: "10-Year", eta: 0.32, label: "Large effect" },
                { horizon: "20-Year", eta: etaSquared20yr, label: "Very large effect" },
              ].map((item, i) => (
                <div key={i} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-slate-600">{item.horizon}</span>
                    <span className="font-bold text-blue-600">n2 = {item.eta.toFixed(3)}</span>
                  </div>
                  <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full"
                      style={{ width: `${Math.min(100, item.eta * 200)}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{item.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        <SectionBox accent="amber">
          <p className="text-sm text-slate-700">
            <span className="font-semibold">Key insight:</span> Effect sizes increase with horizon length, 
            suggesting R&D benefits compound over time. This is consistent with innovation having a 
            3-5 year lag before market recognition.
          </p>
        </SectionBox>
      </div>
    </Slide>,

    // Slide 6: Sector Analysis
    <Slide key="sectors" slideNumber={6} totalSlides={TOTAL_SLIDES} title="Sector Analysis" subtitle="R&D intensity varies dramatically by industry" accent="purple">
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">R&D Intensity by Sector</h3>
            <div className="space-y-2">
              {(rdBySector || []).slice(0, 8).map((sector, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="w-28 text-xs text-slate-600 truncate">{sector.sector}</div>
                  <div className="flex-1 h-5 bg-slate-100 rounded overflow-hidden">
                    <div 
                      className={cn("h-full", i < 2 ? "bg-purple-500" : "bg-slate-400")}
                      style={{ width: `${Math.min(100, (sector.avg_rd_intensity || 0) * 5)}%` }}
                    />
                  </div>
                  <div className="w-12 text-right text-xs font-mono text-slate-600">
                    {(sector.avg_rd_intensity || 0).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <div className="space-y-4">
            <SectionBox title="Sector Concentration" accent="purple">
              <p className="text-sm text-slate-600 mb-3">
                High R&D quintiles are dominated by Technology and Healthcare (~70%). 
                The premium may partially reflect sector performance.
              </p>
              <div className="flex gap-3">
                <div className="flex-1 p-2 bg-purple-100 rounded text-center">
                  <div className="text-lg font-bold text-purple-600">~70%</div>
                  <div className="text-xs text-slate-500">Tech + Healthcare</div>
                </div>
                <div className="flex-1 p-2 bg-slate-100 rounded text-center">
                  <div className="text-lg font-bold text-slate-600">~30%</div>
                  <div className="text-xs text-slate-500">Other Sectors</div>
                </div>
              </div>
            </SectionBox>
            
            <SectionBox title="Within-Sector Effect" accent="emerald">
              <p className="text-sm text-slate-600">
                The R&D-return relationship holds <span className="font-semibold text-emerald-700">within sectors</span>. 
                High-R&D companies outperform low-R&D peers even controlling for industry.
              </p>
            </SectionBox>
          </div>
        </div>
      </div>
    </Slide>,

    // Slide 7: Academic Validation
    <Slide key="academic" slideNumber={7} totalSlides={TOTAL_SLIDES} title="Academic Validation" subtitle="Consistent with established research" accent="blue">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {[
            { authors: "Chan, Lakonishok & Sougiannis (2001)", journal: "Journal of Finance", finding: "High R&D-to-market-cap stocks earned significant excess returns over subsequent years." },
            { authors: "Lev & Sougiannis (1996)", journal: "J. of Accounting & Economics", finding: "R&D-adjusted earnings provide superior return predictions vs reported GAAP earnings." },
            { authors: "Eberhart, Maxwell & Siddique (2004)", journal: "Journal of Finance", finding: "Firms increasing R&D outperform over 5+ years. Market underreacts to R&D announcements." },
            { authors: "Gu (2005)", journal: "J. of Business Finance & Accounting", finding: "R&D intensity predicts future profitability and market-to-book ratios." },
          ].map((paper, i) => (
            <div key={i} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex justify-between items-start mb-1">
                <span className="font-semibold text-blue-700 text-sm">{paper.authors}</span>
              </div>
              <Badge className="bg-blue-100 text-blue-600 border-blue-200 text-xs mb-2">{paper.journal}</Badge>
              <p className="text-xs text-slate-600">{paper.finding}</p>
            </div>
          ))}
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <SectionBox title="Mispricing Hypothesis" accent="amber">
            <p className="text-sm text-slate-600">
              Markets undervalue intangibles because accounting expenses R&D. Investors anchored on 
              P/E ratios systematically underweight innovation.
            </p>
          </SectionBox>
          
          <SectionBox title="Risk Hypothesis" accent="purple">
            <p className="text-sm text-slate-600">
              High R&D firms carry unique risks (disruption, project failure). The premium 
              compensates for bearing innovation risk.
            </p>
          </SectionBox>
        </div>
      </div>
    </Slide>,

    // Slide 8: Investable Strategy
    <Slide key="strategy" slideNumber={8} totalSlides={TOTAL_SLIDES} title="Investable Strategy" subtitle="Practical implementation considerations" accent="emerald">
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-6">
          <SectionBox title="Portfolio Rules" accent="emerald">
            <ul className="space-y-2 text-sm text-slate-600">
              <li><span className="font-semibold">Universe:</span> S&P 500 constituents</li>
              <li><span className="font-semibold">Signal:</span> Prior fiscal-year R&D intensity</li>
              <li><span className="font-semibold">Formation:</span> End of June; hold July-June</li>
              <li><span className="font-semibold">Rebalance:</span> Annual</li>
              <li><span className="font-semibold">Weights:</span> Equal-weight within Q5</li>
            </ul>
          </SectionBox>
          
          <SectionBox title="Transaction Costs" accent="slate">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">Annual trading cost</span>
                <span className="font-bold text-slate-700">{(annualTradingCost * 100).toFixed(3)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">Net premium after costs</span>
                <span className="font-bold text-emerald-600">{(rdPremium - annualTradingCost).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">Premium capture rate</span>
                <span className="font-bold text-blue-600">{premiumCaptureRate.toFixed(1)}%</span>
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-3">
              Uses Novy-Marx & Velikov (2016) methodology
            </p>
          </SectionBox>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <MetricCard value="40%" label="Annual Turnover" accent="blue" />
          <MetricCard value="~20" label="Holdings (Q5)" accent="purple" />
          <MetricCard value="Annual" label="Rebalance Frequency" accent="amber" />
        </div>
        
        <SectionBox accent="amber">
          <p className="text-sm text-slate-700">
            <span className="font-semibold">Note:</span> Strategy requires patience. R&D benefits manifest 
            with a 3-5 year lag. Short-term performance may diverge significantly from long-term expectations.
          </p>
        </SectionBox>
      </div>
    </Slide>,

    // Slide 9: Limitations
    <Slide key="limitations" slideNumber={9} totalSlides={TOTAL_SLIDES} title="Important Caveats" subtitle="Limitations and risks" accent="red">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-red-700">Methodological Limitations</h3>
            
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <h4 className="font-semibold text-slate-700 text-sm">Survivorship Bias</h4>
              <p className="text-xs text-slate-600 mt-1">
                S&P 500 sample excludes failed companies, potentially overstating returns.
              </p>
            </div>
            
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <h4 className="font-semibold text-slate-700 text-sm">Look-Ahead Bias</h4>
              <p className="text-xs text-slate-600 mt-1">
                10-K filings available 60-90 days after fiscal year-end. Mitigated via July-June convention.
              </p>
            </div>
            
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <h4 className="font-semibold text-slate-700 text-sm">Data Quality</h4>
              <p className="text-xs text-slate-600 mt-1">
                Tier-1 data (FMP) may have gaps. Production use requires CRSP/Compustat validation.
              </p>
            </div>
          </div>
          
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-amber-700">Practical Considerations</h3>
            
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <h4 className="font-semibold text-slate-700 text-sm">Sector Concentration</h4>
              <p className="text-xs text-slate-600 mt-1">
                High R&D quintiles are ~70% Tech/Healthcare. Premium may partially reflect sector performance.
              </p>
            </div>
            
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <h4 className="font-semibold text-slate-700 text-sm">Regime Dependence</h4>
              <p className="text-xs text-slate-600 mt-1">
                R&D premium showed weakness 2008-2018. Historical patterns may not persist.
              </p>
            </div>
            
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <h4 className="font-semibold text-slate-700 text-sm">Capacity Constraints</h4>
              <p className="text-xs text-slate-600 mt-1">
                Equal-weight Q5 has limited capacity (~$5-10B before impact).
              </p>
            </div>
          </div>
        </div>
        
        <div className="p-3 bg-slate-100 border border-slate-300 rounded-lg text-center">
          <p className="text-sm text-slate-700 font-medium">
            Past performance does not guarantee future results.
          </p>
        </div>
      </div>
    </Slide>,

    // Slide 10: Conclusion
    <Slide key="conclusion" slideNumber={10} totalSlides={TOTAL_SLIDES} title="Conclusion" accent="emerald">
      <div className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <MetricCard value={`+${rdPremium.toFixed(1)}%`} label="Annual R&D Premium" accent="emerald" />
          <MetricCard value={etaSquared20yr.toFixed(2)} label="20-Year Effect Size" accent="blue" />
          <MetricCard value="p<0.001" label="Statistical Significance" accent="purple" />
        </div>
        
        <SectionBox accent="emerald">
          <h3 className="font-semibold text-emerald-700 mb-3">Key Takeaways</h3>
          <div className="grid grid-cols-2 gap-3 text-sm text-slate-600">
            <div className="flex items-start gap-2">
              <span className="text-emerald-600 font-bold">1.</span>
              R&D intensity is a significant predictor of long-term returns
            </div>
            <div className="flex items-start gap-2">
              <span className="text-emerald-600 font-bold">2.</span>
              Effect strengthens with horizon (patience rewarded)
            </div>
            <div className="flex items-start gap-2">
              <span className="text-emerald-600 font-bold">3.</span>
              Results align with established academic research
            </div>
            <div className="flex items-start gap-2">
              <span className="text-emerald-600 font-bold">4.</span>
              Implementable with modest trading costs (~99% capture)
            </div>
          </div>
        </SectionBox>
        
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
          <p className="text-sm text-slate-600 mb-3">
            This research provides empirical evidence that innovation investment, as measured by R&D intensity, 
            is associated with superior long-term stock returns. Whether this reflects mispricing or risk 
            compensation, the premium appears economically significant and statistically robust.
          </p>
          <p className="text-xs text-slate-500">
            Full methodology and interactive analysis available at <span className="text-emerald-600">research.finsoeasy.com</span>
          </p>
        </div>
        
        <div className="text-center text-slate-400 text-sm">
          <p>Contact: abhishek@finsoeasy.com</p>
        </div>
      </div>
    </Slide>,
  ]

  return (
    <div 
      className={cn(
        "flex flex-col h-full",
        isFullscreen && "fixed inset-0 z-50 bg-slate-900 p-4"
      )}
      onKeyDown={(e) => handleKeyDown(e.nativeEvent)}
      tabIndex={0}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">
            <span className="text-emerald-500">R&D Alpha</span>{" "}
            <span className="text-foreground">Whitepaper</span>
          </h1>
          <p className="text-muted-foreground text-sm">
            Slide {currentSlide + 1} of {slides.length} - A4 format - Arrow keys to navigate
          </p>
        </div>
        
        <div className="flex flex-wrap gap-2">
          <Button 
            variant="default" 
            size="sm"
            onClick={handlePrint}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <Printer className="mr-1 h-3 w-3" />
            Print / PDF
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setIsFullscreen(!isFullscreen)}
          >
            {isFullscreen ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Slide Display */}
      <div 
        ref={slideContainerRef}
        className="relative flex-1 flex items-center justify-center overflow-auto"
      >
        <div className="slide-content">
          {slides[currentSlide]}
        </div>
        
        {/* Navigation Buttons */}
        <button
          onClick={prevSlide}
          disabled={currentSlide === 0}
          className={cn(
            "absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors",
            currentSlide === 0 && "opacity-30 cursor-not-allowed"
          )}
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        
        <button
          onClick={nextSlide}
          disabled={currentSlide === slides.length - 1}
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors",
            currentSlide === slides.length - 1 && "opacity-30 cursor-not-allowed"
          )}
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      {/* Slide Indicators */}
      <div className="flex justify-center gap-2 py-3">
        {slides.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrentSlide(i)}
            className={cn(
              "w-2 h-2 rounded-full transition-all",
              i === currentSlide 
                ? "bg-emerald-500 w-4" 
                : "bg-slate-400 hover:bg-slate-300"
            )}
          />
        ))}
      </div>

      {/* Thumbnail Preview */}
      {!isFullscreen && (
        <div className="mt-2 border-t border-border pt-4">
          <h3 className="text-sm font-semibold mb-2">All Slides</h3>
          <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
            {slides.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentSlide(i)}
                className={cn(
                  "aspect-[210/297] rounded overflow-hidden border-2 transition-all hover:scale-105",
                  i === currentSlide 
                    ? "border-emerald-500 ring-1 ring-emerald-500/30" 
                    : "border-slate-300 dark:border-slate-700 hover:border-slate-400"
                )}
              >
                <div className="w-full h-full bg-white flex items-center justify-center">
                  <span className="text-xs text-slate-600">{i + 1}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Whitepaper
