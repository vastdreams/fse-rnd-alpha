/**
 * PATH: src/components/layout/sidebar/SidebarNav.tsx
 * PURPOSE: Main nav items, research papers section, and extra links.
 * WHY: Extracted from Sidebar.tsx to keep files under 300 lines.
 */
import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"
import { LayoutDashboard, Building2, GraduationCap, Briefcase, BookOpen, FileText, ChevronDown, FlaskConical, ScrollText, Presentation } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const navItems = [
  { path: "/", label: "Main Paper", icon: Presentation },
  { path: "/portfolio", label: "R&D ETF", icon: Briefcase },
  { path: "/whitepaper", label: "Whitepaper", icon: ScrollText },
  { path: "/overview", label: "Overview", icon: LayoutDashboard },
  { path: "/companies", label: "Companies", icon: Building2 },
  { path: "/research", label: "Analysis", icon: GraduationCap },
]

const paperItems = [
  { path: "/papers/1", label: "Sub: Returns", icon: FileText },
  { path: "/papers/2", label: "Sub: Sectors", icon: FileText },
  { path: "/papers/3", label: "Sub: Factors", icon: FileText },
  { path: "/papers/4", label: "Sub: Mechanisms", icon: FileText },
]

const mainPaperItem = { path: "/", label: "Main Paper", icon: Presentation }

const extraLinks = [
  { path: "/documentation", label: "Documentation", icon: BookOpen, activeClasses: "bg-amber-500/20 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-400/50 dark:border-amber-500/40", indicatorColor: "bg-amber-500" },
  { path: "/methodology", label: "Methodology", icon: FlaskConical, activeClasses: "bg-purple-500/20 dark:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-400/50 dark:border-purple-500/40", indicatorColor: "bg-purple-500" },
  { path: "/whitepaper", label: "Whitepaper", icon: Presentation, activeClasses: "bg-teal-500/20 dark:bg-teal-500/20 text-teal-600 dark:text-teal-400 border border-teal-400/50 dark:border-teal-500/40", indicatorColor: "bg-teal-500" },
]

interface SidebarNavProps {
  pathname: string
  collapsed: boolean
  papersExpanded: boolean
  setPapersExpanded: (v: boolean) => void
}

export function SidebarNav({ pathname, collapsed, papersExpanded, setPapersExpanded }: SidebarNavProps) {
  return (
    <>
      {/* Main Nav Items */}
      {navItems.map((item) => {
        const isActive = pathname === item.path
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
                pathname.startsWith("/papers")
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
              pathname === mainPaperItem.path
                ? "bg-emerald-500/20 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-400 dark:border-emerald-600 shadow-sm" 
                : "bg-transparent text-muted-foreground border-slate-300 dark:border-slate-600 hover:bg-emerald-500/10 dark:hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400 hover:border-emerald-400 dark:hover:border-emerald-600"
            )}
          >
            {pathname === mainPaperItem.path && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-emerald-500 rounded-r-full" />
            )}
            <Presentation className={cn(
              "w-4 h-4 transition-transform duration-200",
              pathname !== mainPaperItem.path && "group-hover:scale-110"
            )} />
            <span>Main Paper</span>
          </Link>
          
          {/* Sub-research papers */}
          <div className="pt-1 space-y-0.5">
            <span className="px-3 text-[10px] uppercase tracking-wider text-muted-foreground/60">Sub-Research</span>
            {paperItems.map((item) => {
              const isActive = pathname === item.path
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

      {/* Extra links: Documentation, Methodology, Whitepaper */}
      {extraLinks.map((link) => {
        const isActive = pathname === link.path
        const Icon = link.icon
        if (collapsed) {
          return (
            <Tooltip key={link.path}>
              <TooltipTrigger asChild>
                <Link to={link.path} className={cn(
                  "flex items-center justify-center px-2 py-2.5 rounded-xl transition-all duration-200 group",
                  isActive
                    ? `${link.activeClasses}` 
                    : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
                )}>
                  <Icon className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">{link.label}</TooltipContent>
            </Tooltip>
          )
        }
        return (
          <Link key={link.path} to={link.path} className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 relative group",
            isActive ? `${link.activeClasses}` : "text-muted-foreground hover:bg-slate-200/50 dark:hover:bg-slate-700/50 hover:text-foreground"
          )}>
            {isActive && <div className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 ${link.indicatorColor} rounded-r-full`} />}
            <Icon className={cn("w-5 h-5 flex-shrink-0 transition-transform duration-200", !isActive && "group-hover:scale-110")} />
            <span className="font-medium text-sm">{link.label}</span>
          </Link>
        )
      })}
    </>
  )
}
