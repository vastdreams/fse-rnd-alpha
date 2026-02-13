/**
 * PATH: frontend/src/pages/Whitepaper.tsx
 * PURPOSE: Professional R&D Alpha whitepaper in A4 slide format
 * WHY: Research presentation layer - exportable PDF deck
 * MAIN EXPORTS: Whitepaper component
 * DEPENDENCIES:
 *  - useWhitepaperData: all data fetching and derived metrics
 *  - components/whitepaper: Slide components and shared helpers
 */

import { useState, useRef, useCallback, useEffect } from "react"
import { createPortal } from "react-dom"
import { Button } from "@/components/ui/button"
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Printer,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useWhitepaperData } from "@/hooks/useWhitepaperData"
import {
  TitleSlide,
  ExecSummarySlide,
  ImplementationSlide,
  MethodologySlide,
  ResultsSlide,
  VisualEvidenceSlide,
  SectorSlide,
  AcademicSlide,
  StrategySlide,
  LimitationsSlide,
  ConclusionSlide,
} from "@/components/whitepaper"

const TOTAL_SLIDES = 11

export function Whitepaper() {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const slideContainerRef = useRef<HTMLDivElement>(null)

  const data = useWhitepaperData()

  // Scroll slide viewport into view on navigation
  useEffect(() => {
    requestAnimationFrame(() => {
      slideContainerRef.current?.scrollTo({ top: 0 })
      slideContainerRef.current?.scrollIntoView({ block: "start", behavior: "smooth" })
    })
  }, [currentSlide])

  // Print handler - opens browser print dialog for PDF export
  const handlePrint = useCallback(() => {
    document.body.classList.add("printing-whitepaper")
    window.print()
    setTimeout(() => {
      document.body.classList.remove("printing-whitepaper")
    }, 500)
  }, [])

  const nextSlide = useCallback(() => {
    setCurrentSlide((s) => Math.min(s + 1, TOTAL_SLIDES - 1))
  }, [])

  const prevSlide = useCallback(() => {
    setCurrentSlide((s) => Math.max(s - 1, 0))
  }, [])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "PageDown") { e.preventDefault(); nextSlide(); return }
      if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); prevSlide(); return }
      if (e.key === "Home") { e.preventDefault(); setCurrentSlide(0); return }
      if (e.key === "End") { e.preventDefault(); setCurrentSlide(TOTAL_SLIDES - 1); return }
      if (e.key === "Escape" && isFullscreen) { e.preventDefault(); setIsFullscreen(false) }
    },
    [isFullscreen, nextSlide, prevSlide]
  )

  const slides = [
    <TitleSlide key="title" data={data} totalSlides={TOTAL_SLIDES} />,
    <ExecSummarySlide key="exec" data={data} totalSlides={TOTAL_SLIDES} />,
    <ImplementationSlide key="impl" data={data} totalSlides={TOTAL_SLIDES} />,
    <MethodologySlide key="method" data={data} totalSlides={TOTAL_SLIDES} />,
    <ResultsSlide key="results" data={data} totalSlides={TOTAL_SLIDES} />,
    <VisualEvidenceSlide key="visual" data={data} totalSlides={TOTAL_SLIDES} />,
    <SectorSlide key="sector" data={data} totalSlides={TOTAL_SLIDES} />,
    <AcademicSlide key="academic" totalSlides={TOTAL_SLIDES} />,
    <StrategySlide key="strategy" data={data} totalSlides={TOTAL_SLIDES} />,
    <LimitationsSlide key="limitations" totalSlides={TOTAL_SLIDES} />,
    <ConclusionSlide key="conclusion" data={data} totalSlides={TOTAL_SLIDES} />,
  ]

  return (
    <div
      className={cn("flex flex-col h-full", isFullscreen && "fixed inset-0 z-50 bg-slate-900 p-4")}
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
          <Button variant="default" size="sm" onClick={handlePrint} className="bg-emerald-600 hover:bg-emerald-700">
            <Printer className="mr-1 h-3 w-3" />
            Print / PDF
          </Button>
          <Button variant="outline" size="sm" onClick={() => setIsFullscreen(!isFullscreen)}>
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Slide Display */}
      <div ref={slideContainerRef} className="relative flex-1 flex items-start justify-center overflow-auto bg-slate-100 dark:bg-slate-900 py-4">
        <div className="slide-content">{slides[currentSlide]}</div>
        <button
          onClick={prevSlide}
          disabled={currentSlide === 0}
          className={cn("absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors", currentSlide === 0 && "opacity-30 cursor-not-allowed")}
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <button
          onClick={nextSlide}
          disabled={currentSlide === slides.length - 1}
          className={cn("absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors", currentSlide === slides.length - 1 && "opacity-30 cursor-not-allowed")}
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
            className={cn("w-2 h-2 rounded-full transition-all", i === currentSlide ? "bg-emerald-500 w-4" : "bg-slate-400 hover:bg-slate-300")}
          />
        ))}
      </div>

      {/* Thumbnail Preview */}
      {!isFullscreen && (
        <div className="mt-2 border-t border-border pt-4 no-print">
          <h3 className="text-sm font-semibold mb-2">All Slides</h3>
          <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
            {slides.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentSlide(i)}
                className={cn(
                  "aspect-[210/297] rounded overflow-hidden border-2 transition-all hover:scale-105",
                  i === currentSlide ? "border-emerald-500 ring-1 ring-emerald-500/30" : "border-slate-300 dark:border-slate-700 hover:border-slate-400"
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

      {/* Print View - rendered via portal to body for clean print isolation */}
      {createPortal(
        <div className="whitepaper-print-container">
          {slides.map((slide, i) => (
            <div key={i} className="whitepaper-print-slide">{slide}</div>
          ))}
        </div>,
        document.body
      )}
    </div>
  )
}

export default Whitepaper
