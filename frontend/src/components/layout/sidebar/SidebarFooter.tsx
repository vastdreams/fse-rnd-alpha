/**
 * PATH: src/components/layout/sidebar/SidebarFooter.tsx
 * PURPOSE: Sidebar footer with "Back to Finsoeasy", subscribe/donate links, theme toggle, and info text.
 * WHY: Extracted from Sidebar.tsx to keep files under 300 lines.
 */

import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"
import { Sun, Moon, ExternalLink, Heart, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface SidebarFooterProps {
  collapsed: boolean
  pathname: string
  theme: string
  toggleTheme: () => void
}

export function SidebarFooter({ collapsed, pathname, theme, toggleTheme }: SidebarFooterProps) {
  return (
    <div className="p-3 border-t border-border space-y-2 flex-shrink-0">
      {/* Back to Finsoeasy.com */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <a
              href="https://finsoeasy.com"
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium transition-all",
                "bg-gradient-to-r from-emerald-500/10 to-teal-500/10 hover:from-emerald-500/20 hover:to-teal-500/20",
                "text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
                collapsed && "px-0 justify-center"
              )}
            >
              <ExternalLink className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span>Back to Finsoeasy.com</span>}
            </a>
          </TooltipTrigger>
          <TooltipContent side={collapsed ? "right" : "top"}>
            Return to Finsoeasy.com
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Subscribe & Donate Row */}
      {!collapsed && (
        <div className="flex gap-2">
          <Link
            to={`/subscribe?from=${encodeURIComponent(pathname)}`}
            className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-all bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/20"
          >
            <Mail className="w-3.5 h-3.5" />
            Subscribe
          </Link>
          <Link
            to="/donate"
            className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-all bg-pink-500/10 hover:bg-pink-500/20 text-pink-600 dark:text-pink-400 border border-pink-500/20"
          >
            <Heart className="w-3.5 h-3.5" />
            Donate
          </Link>
        </div>
      )}
      
      {collapsed && (
        <div className="flex flex-col gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Link to={`/subscribe?from=${encodeURIComponent(pathname)}`} className="flex items-center justify-center p-2 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400">
                  <Mail className="w-4 h-4" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">Subscribe to Research</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Link to="/donate" className="flex items-center justify-center p-2 rounded-lg bg-pink-500/10 hover:bg-pink-500/20 text-pink-600 dark:text-pink-400">
                  <Heart className="w-4 h-4" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">Support Our Research</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      )}

      {/* Theme Toggle */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleTheme}
              className={cn(
                "w-full justify-start cursor-pointer",
                collapsed && "px-0 justify-center"
              )}
            >
              {theme === "dark" ? (
                <>
                  <Sun className="w-4 h-4" />
                  {!collapsed && <span className="ml-2">Light Mode</span>}
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4" />
                  {!collapsed && <span className="ml-2">Dark Mode</span>}
                </>
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent side={collapsed ? "right" : "top"}>
            {theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      
      {!collapsed && (
        <div className="text-xs text-muted-foreground">
          <p>SEC Filing Analysis</p>
          <p>S&P 500 • Point-in-Time</p>
        </div>
      )}
    </div>
  )
}
