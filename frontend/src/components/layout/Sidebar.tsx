import { useState } from "react"
import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import { 
  LayoutDashboard, 
  Building2, 
  BarChart3,
  GraduationCap,
  Briefcase,
  BookOpen,
  FileText,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Sun,
  Moon,
  FlaskConical,
  ScrollText,
  Presentation,
  ExternalLink,
  Heart,
  Mail
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTheme } from "@/components/theme-provider"
import { useSidebar } from "@/components/sidebar-context"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

// Navigation structure: Research Papers at top, then ETF, then data exploration
const navItems = [
  // Primary: Main Paper (landing page)
  { path: "/", label: "Main Paper", icon: Presentation },
  // Products
  { path: "/portfolio", label: "R&D ETF", icon: Briefcase },
  { path: "/whitepaper", label: "Whitepaper", icon: ScrollText },
  // Data exploration
  { path: "/overview", label: "Overview", icon: LayoutDashboard },
  { path: "/companies", label: "Companies", icon: Building2 },
  { path: "/research", label: "Analysis", icon: GraduationCap },
]

// Sub-research papers (under collapsible section)
const paperItems = [
  { path: "/papers/1", label: "Sub: Returns", icon: FileText },
  { path: "/papers/2", label: "Sub: Sectors", icon: FileText },
  { path: "/papers/3", label: "Sub: Factors", icon: FileText },
  { path: "/papers/4", label: "Sub: Mechanisms", icon: FileText },
]

// Keep for backward compatibility
const mainPaperItem = { path: "/", label: "Main Paper", icon: Presentation }

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
          {/* Main Nav Items */}
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            const Icon = item.icon
            
            const linkContent = (
              <Link
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 relative group",
                  isActive 
                    ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 shadow-sm border border-emerald-300 dark:border-emerald-700" 
                    : "text-muted-foreground hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-foreground hover:shadow-sm",
                  collapsed && "justify-center px-2"
                )}
              >
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-emerald-500 rounded-r-full" />
                )}
                <Icon className={cn(
                  "w-5 h-5 flex-shrink-0 transition-transform duration-200",
                  !isActive && "group-hover:scale-110"
                )} />
                {!collapsed && <span className="font-medium text-sm">{item.label}</span>}
              </Link>
            )

            if (collapsed) {
              return (
                <Tooltip key={item.path}>
                  <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                  <TooltipContent side="right" className="font-medium">
                    {item.label}
                  </TooltipContent>
                </Tooltip>
              )
            }

            return <div key={item.path}>{linkContent}</div>
          })}

        {/* Divider */}
        <div className="my-3 border-t border-border" />

        {/* Research Papers Section */}
        {!collapsed && (
          <button
            onClick={() => setPapersExpanded(!papersExpanded)}
            className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-all duration-200"
          >
            <div className="flex items-center gap-2">
              <ScrollText className="w-4 h-4" />
              <span>Research Papers</span>
            </div>
            <ChevronDown className={cn("w-4 h-4 transition-transform duration-300", papersExpanded && "rotate-180")} />
          </button>
        )}
        
        {collapsed && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Link
                to="/papers/1"
                className={cn(
                  "flex items-center justify-center py-2.5 px-2 rounded-xl transition-all duration-200 group",
                  location.pathname.startsWith("/papers")
                    ? "bg-blue-500/20 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-400/50 dark:border-blue-500/40" 
                    : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
                )}
              >
                <ScrollText className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right">Research Papers</TooltipContent>
          </Tooltip>
        )}

        {!collapsed && papersExpanded && (
          <div className="ml-2 space-y-1">
            {/* Main Paper - Prominent */}
            <Link
              to={mainPaperItem.path}
              className={cn(
                "flex items-center gap-2 px-3 py-2.5 rounded-xl transition-all duration-200 text-sm relative group font-medium border",
                location.pathname === mainPaperItem.path
                  ? "bg-emerald-500/20 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-400 dark:border-emerald-600 shadow-sm" 
                  : "bg-transparent text-muted-foreground border-slate-300 dark:border-slate-600 hover:bg-emerald-500/10 dark:hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400 hover:border-emerald-400 dark:hover:border-emerald-600"
              )}
            >
              {location.pathname === mainPaperItem.path && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-emerald-500 rounded-r-full" />
              )}
              <Presentation className={cn(
                "w-4 h-4 transition-transform duration-200",
                location.pathname !== mainPaperItem.path && "group-hover:scale-110"
              )} />
              <span>Main Paper</span>
            </Link>
            
            {/* Sub-research papers */}
            <div className="pt-1 space-y-0.5">
              <span className="px-3 text-[10px] uppercase tracking-wider text-muted-foreground/60">Sub-Research</span>
            {paperItems.map((item) => {
              const isActive = location.pathname === item.path
              const Icon = item.icon
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                      "flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-200 text-xs relative group",
                    isActive 
                        ? "bg-blue-500/20 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-400/50 dark:border-blue-500/40" 
                        : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
                    )}
                  >
                    {isActive && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-blue-500 rounded-r-full" />
                    )}
                    <Icon className={cn(
                      "w-3.5 h-3.5 transition-transform duration-200",
                      !isActive && "group-hover:scale-110"
                    )} />
                  <span className="truncate">{item.label}</span>
                </Link>
              )
            })}
            </div>
          </div>
        )}

        {/* Divider */}
        <div className="my-3 border-t border-border" />

        {/* Documentation */}
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Link
                to="/documentation"
                className={cn(
                  "flex items-center justify-center px-2 py-2.5 rounded-xl transition-all duration-200 group",
                  location.pathname === "/documentation"
                    ? "bg-amber-500/20 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-400/50 dark:border-amber-500/40" 
                    : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
                )}
              >
                <BookOpen className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right">Documentation</TooltipContent>
          </Tooltip>
        ) : (
          <Link
            to="/documentation"
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 relative group",
              location.pathname === "/documentation"
                ? "bg-amber-500/20 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-400/50 dark:border-amber-500/40" 
                : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
            )}
          >
            {location.pathname === "/documentation" && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-amber-500 rounded-r-full" />
            )}
            <BookOpen className={cn(
              "w-5 h-5 flex-shrink-0 transition-transform duration-200",
              location.pathname !== "/documentation" && "group-hover:scale-110"
            )} />
            <span className="font-medium text-sm">Documentation</span>
          </Link>
        )}

        {/* Methodology */}
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Link
                to="/methodology"
                className={cn(
                  "flex items-center justify-center px-2 py-2.5 rounded-xl transition-all duration-200 group",
                  location.pathname === "/methodology"
                    ? "bg-purple-500/20 dark:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-400/50 dark:border-purple-500/40" 
                    : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
                )}
              >
                <FlaskConical className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right">Methodology</TooltipContent>
          </Tooltip>
        ) : (
          <Link
            to="/methodology"
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 relative group",
              location.pathname === "/methodology"
                ? "bg-purple-500/20 dark:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-400/50 dark:border-purple-500/40" 
                : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
            )}
          >
            {location.pathname === "/methodology" && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-purple-500 rounded-r-full" />
            )}
            <FlaskConical className={cn(
              "w-5 h-5 flex-shrink-0 transition-transform duration-200",
              location.pathname !== "/methodology" && "group-hover:scale-110"
            )} />
            <span className="font-medium text-sm">Methodology</span>
          </Link>
        )}

        {/* Whitepaper */}
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Link
                to="/whitepaper"
                className={cn(
                  "flex items-center justify-center px-2 py-2.5 rounded-xl transition-all duration-200 group",
                  location.pathname === "/whitepaper"
                    ? "bg-teal-500/20 dark:bg-teal-500/20 text-teal-600 dark:text-teal-400 border border-teal-400/50 dark:border-teal-500/40" 
                    : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
                )}
              >
                <Presentation className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right">Whitepaper</TooltipContent>
          </Tooltip>
        ) : (
          <Link
            to="/whitepaper"
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 relative group",
              location.pathname === "/whitepaper"
                ? "bg-teal-500/20 dark:bg-teal-500/20 text-teal-600 dark:text-teal-400 border border-teal-400/50 dark:border-teal-500/40" 
                : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
            )}
          >
            {location.pathname === "/whitepaper" && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-teal-500 rounded-r-full" />
            )}
            <Presentation className={cn(
              "w-5 h-5 flex-shrink-0 transition-transform duration-200",
              location.pathname !== "/whitepaper" && "group-hover:scale-110"
            )} />
            <span className="font-medium text-sm">Whitepaper</span>
          </Link>
        )}
        </nav>
      </TooltipProvider>

      {/* Footer - fixed at bottom */}
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
              to={`/subscribe?from=${encodeURIComponent(location.pathname)}`}
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
                  <Link to={`/subscribe?from=${encodeURIComponent(location.pathname)}`} className="flex items-center justify-center p-2 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400">
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
            <p>S&P 500 • 25 Year Lookback</p>
          </div>
        )}
      </div>
    </aside>
    </>
  )
}
