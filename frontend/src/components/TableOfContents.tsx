/**
 * PATH: frontend/src/components/TableOfContents.tsx
 * PURPOSE: Reusable table of contents component for page navigation
 * ROLE IN ARCHITECTURE: UI component for in-page navigation
 * MAIN EXPORTS:
 *   - TableOfContents: Main component
 *   - useTOC: Hook for tracking active sections
 * NON-RESPONSIBILITIES:
 *   - Does not handle scroll behavior (uses native scroll)
 * NOTES FOR FUTURE AI:
 *   - Add smooth scroll animation if needed
 *   - Extend with keyboard navigation (j/k keys)
 */

import { useState, useEffect, useCallback } from "react"
import { cn } from "@/lib/utils"
import { ChevronUp, ChevronDown, List } from "lucide-react"
import { Button } from "@/components/ui/button"
import { analytics } from "@/lib/analytics"

export interface TOCSection {
  id: string
  label: string
  level?: 1 | 2 | 3
}

interface TableOfContentsProps {
  sections: TOCSection[]
  title?: string
  className?: string
  sticky?: boolean
  showProgress?: boolean
}

export function TableOfContents({
  sections,
  title = "Contents",
  className,
  sticky = true,
  showProgress = true,
}: TableOfContentsProps) {
  const [activeSection, setActiveSection] = useState<string>(sections[0]?.id || "")
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [scrollProgress, setScrollProgress] = useState(0)

  // Track active section based on scroll position
  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 100 // Offset for header

      // Find the current section
      for (let i = sections.length - 1; i >= 0; i--) {
        const section = sections[i]
        const element = document.getElementById(section.id)
        if (element && element.offsetTop <= scrollPosition) {
          if (activeSection !== section.id) {
            setActiveSection(section.id)
          }
          break
        }
      }

      // Calculate scroll progress
      const windowHeight = window.innerHeight
      const documentHeight = document.documentElement.scrollHeight - windowHeight
      const progress = Math.min((window.scrollY / documentHeight) * 100, 100)
      setScrollProgress(progress)
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    handleScroll() // Initial check
    return () => window.removeEventListener("scroll", handleScroll)
  }, [sections, activeSection])

  const scrollToSection = useCallback((id: string) => {
    const element = document.getElementById(id)
    if (element) {
      analytics.trackClick("toc_navigation", { section: id })
      element.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [])

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  const scrollToBottom = () => {
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" })
  }

  if (sections.length === 0) return null

  return (
    <nav
      className={cn(
        "bg-card border border-border rounded-lg p-4",
        sticky && "sticky top-20",
        className
      )}
    >
      {/* Header with collapse toggle */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <List className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium text-sm">{title}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="h-6 w-6 p-0"
        >
          {isCollapsed ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronUp className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Progress bar */}
      {showProgress && !isCollapsed && (
        <div className="h-1 bg-muted rounded-full mb-3 overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-150"
            style={{ width: `${scrollProgress}%` }}
          />
        </div>
      )}

      {/* Section links */}
      {!isCollapsed && (
        <ul className="space-y-1">
          {sections.map((section) => (
            <li key={section.id}>
              <button
                onClick={() => scrollToSection(section.id)}
                className={cn(
                  "w-full text-left px-2 py-1.5 rounded text-sm transition-colors",
                  "hover:bg-muted cursor-pointer",
                  section.level === 2 && "pl-4",
                  section.level === 3 && "pl-6",
                  activeSection === section.id
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground"
                )}
              >
                {section.label}
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Quick navigation */}
      {!isCollapsed && (
        <div className="flex gap-2 mt-4 pt-3 border-t border-border">
          <Button
            variant="ghost"
            size="sm"
            onClick={scrollToTop}
            className="flex-1 text-xs"
          >
            <ChevronUp className="w-3 h-3 mr-1" />
            Top
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={scrollToBottom}
            className="flex-1 text-xs"
          >
            <ChevronDown className="w-3 h-3 mr-1" />
            Bottom
          </Button>
        </div>
      )}
    </nav>
  )
}

// Hook to get current active section
export function useTOC(sections: TOCSection[]) {
  const [activeSection, setActiveSection] = useState<string>(sections[0]?.id || "")

  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 100

      for (let i = sections.length - 1; i >= 0; i--) {
        const section = sections[i]
        const element = document.getElementById(section.id)
        if (element && element.offsetTop <= scrollPosition) {
          setActiveSection(section.id)
          break
        }
      }
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    handleScroll()
    return () => window.removeEventListener("scroll", handleScroll)
  }, [sections])

  return activeSection
}

