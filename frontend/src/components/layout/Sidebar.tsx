/**
 * PATH: src/components/layout/Sidebar.tsx
 * PURPOSE: Sidebar shell — logo, collapse toggle, mobile overlay. Delegates nav and footer to sub-components.
 * WHY: Keeps orchestration in parent; nav + footer extracted to stay under 300 lines.
 */

import { useState } from "react"
import { useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import { BarChart3, ChevronLeft, ChevronRight } from "lucide-react"
import { useTheme } from "@/components/theme-provider"
import { useSidebar } from "@/components/sidebar-context"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { SidebarNav } from "./sidebar/SidebarNav"
import { SidebarFooter } from "./sidebar/SidebarFooter"

export function Sidebar() {
  const location = useLocation()
  const { collapsed, toggle, isMobile, mobileOpen, setMobileOpen } = useSidebar()
  const [papersExpanded, setPapersExpanded] = useState(true)
  const { theme, setTheme } = useTheme()

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark")
  }

  // On mobile, only show when mobileOpen is true
  if (isMobile && !mobileOpen) {
    return null
  }

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && mobileOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30"
          onClick={() => setMobileOpen(false)}
        />
      )}
    <aside 
      className={cn(
          "fixed left-0 top-0 z-40 h-screen bg-card border-r border-border transition-all duration-300 flex flex-col",
          isMobile ? "w-64" : (collapsed ? "w-16" : "w-64")
      )}
    >
      {/* Logo - fixed at top */}
      <div className={cn(
        "flex items-center gap-3 p-4 border-b border-border flex-shrink-0",
        collapsed && "justify-center"
      )}>
        <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
          <BarChart3 className="w-6 h-6 text-primary-foreground" />
        </div>
        {!collapsed && (
          <div>
            <h1 className="font-bold text-lg">R&D Alpha</h1>
            <p className="text-xs text-muted-foreground">Factor Analysis</p>
          </div>
        )}
      </div>

      {/* Collapse Toggle */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={toggle}
              className={cn(
                "absolute -right-4 top-20 z-50",
                "w-8 h-8 rounded-full",
                "bg-primary text-primary-foreground",
                "border-2 border-background",
                "shadow-lg",
                "flex items-center justify-center",
                "cursor-pointer",
                "transition-all duration-200",
                "hover:scale-110 hover:shadow-xl",
                "active:scale-95"
              )}
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {collapsed ? "Expand sidebar" : "Collapse sidebar"}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Navigation - scrollable middle section */}
      <TooltipProvider delayDuration={0}>
        <nav className="p-2 space-y-1 overflow-y-auto flex-1 min-h-0">
          <SidebarNav
            pathname={location.pathname}
            collapsed={collapsed}
            papersExpanded={papersExpanded}
            setPapersExpanded={setPapersExpanded}
          />
        </nav>
      </TooltipProvider>

      {/* Footer - fixed at bottom */}
      <SidebarFooter
        collapsed={collapsed}
        pathname={location.pathname}
        theme={theme}
        toggleTheme={toggleTheme}
      />
    </aside>
    </>
  )
}
