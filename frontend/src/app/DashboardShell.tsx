/**
 * PATH: frontend/src/app/DashboardShell.tsx
 * PURPOSE: Light-only Finsoeasy Portfolio shell (no dark mode).
 */
import type { ReactNode } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import {
  Briefcase,
  LogOut,
  BookOpen,
  Search,
  Library,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react"
import { useAuthStore } from "@/stores/authStore"
import { useEffect, useState } from "react"
import { useServerBookCount } from "@/hooks/useServerBookCount"
import { useTheme } from "@/components/theme-provider"
import { getBuyPerformanceBook, type BuyPerformanceBook } from "@/lib/api/universe"

const NAV_COLLAPSED_KEY = "fse_portfolio_nav_collapsed"

export function DashboardShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { token, user, logout, hydrate, hydrated } = useAuthStore()
  const isAuthPage = ["/login", "/register", "/verify-email", "/reset-password"].includes(location.pathname)
  const {
    count: bookCount,
    error: bookError,
    refresh: refreshBookCount,
  } = useServerBookCount(Boolean(token && user && hydrated && !isAuthPage))
  const { setTheme } = useTheme()
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(NAV_COLLAPSED_KEY) === "1"
    } catch {
      return false
    }
  })
  const [engineStatus, setEngineStatus] = useState<BuyPerformanceBook | null>(null)

  // Thesis-engine trust chip: engine version, sealed universe, armed
  // falsification rules. Informational only — failure to load renders nothing.
  useEffect(() => {
    if (!token || !user || !hydrated || isAuthPage) return
    let cancelled = false
    getBuyPerformanceBook()
      .then((b) => {
        if (!cancelled) setEngineStatus(b)
      })
      .catch(() => {
        if (!cancelled) setEngineStatus(null)
      })
    return () => {
      cancelled = true
    }
  }, [token, user, hydrated, isAuthPage])

  useEffect(() => {
    if (!hydrated) hydrate()
  }, [hydrated, hydrate])

  // Portfolio product is white-only. Ignore research-site dark preference.
  useEffect(() => {
    setTheme("light")
    const root = document.documentElement
    root.classList.remove("dark")
    root.classList.add("light")
    root.style.colorScheme = "light"
  }, [setTheme])

  // Model-10 auto-seed removed (ship rule: books start empty; loading the
  // model is only ever an explicit user action on the legacy pages).

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem(NAV_COLLAPSED_KEY, next ? "1" : "0")
      } catch {
        // ignore
      }
      return next
    })
  }

  const onUniverse =
    location.pathname === "/app" ||
    location.pathname === "/app/universe" ||
    location.pathname === "/app/investigate"
  const onBook = location.pathname === "/app/book"
  const onCompany = location.pathname.startsWith("/app/company/")

  if (isAuthPage) {
    return (
      <div className="flex min-h-screen flex-col bg-[#f7f7f5] text-neutral-900">
        <div className="flex flex-1 items-center justify-center p-4">{children}</div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-[#f7f7f5] text-neutral-900">
      <aside
        className={`hidden flex-col border-r border-neutral-200 bg-white transition-[width] duration-200 md:flex ${
          collapsed ? "w-14" : "w-56"
        }`}
      >
        <div
          className={`flex h-14 items-center border-b border-neutral-200 ${
            collapsed ? "justify-center px-1" : "gap-2 px-3"
          }`}
        >
          <Link
            to="/app"
            className={`flex min-w-0 items-center gap-2.5 ${collapsed ? "justify-center" : ""}`}
            title="Finsoeasy Portfolio"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-900 text-white">
              <Briefcase className="h-4 w-4" />
            </div>
            {!collapsed && (
              <div className="min-w-0 leading-tight">
                <div className="truncate text-sm font-semibold text-neutral-900">Finsoeasy</div>
                <div className="text-[10px] text-neutral-500">Portfolio</div>
              </div>
            )}
          </Link>
          {!collapsed && (
            <button
              type="button"
              onClick={toggleCollapsed}
              className="ml-auto rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
              title="Collapse navigation"
              aria-label="Collapse navigation"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
        </div>

        <nav className={`flex-1 space-y-1 ${collapsed ? "p-1.5" : "p-3"}`}>
          <NavItem
            to="/app/universe"
            active={onUniverse && !onCompany}
            icon={<Search className="h-4 w-4" />}
            label="Universe"
            hint="What to Buy · ETF · All"
            collapsed={collapsed}
          />
          <NavItem
            to="/app/book"
            active={onBook}
            icon={<Library className="h-4 w-4" />}
            label="My Book"
            hint={bookError ? "Book unavailable" : `${bookCount} holdings`}
            badge={bookError ? "!" : bookCount || undefined}
            collapsed={collapsed}
          />
          {bookError && !collapsed && (
            <button
              type="button"
              onClick={refreshBookCount}
              className="w-full rounded-md px-2 py-1 text-left text-[10px] text-rose-700 hover:bg-rose-50"
            >
              Book count unavailable — retry
            </button>
          )}
          {onCompany && !collapsed && (
            <div className="mt-2 border-t border-neutral-200 pt-3">
              <div className="mb-1 px-2 text-[10px] uppercase tracking-wide text-neutral-500">
                Open company
              </div>
              <div className="px-2 py-1.5 text-sm font-semibold text-neutral-900">
                {location.pathname.split("/").pop()}
              </div>
            </div>
          )}
        </nav>

        {engineStatus && !collapsed && (
          <div
            className="mx-3 mb-2 rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-2"
            data-testid="thesis-engine-chip"
            title="The thesis engine behind every stance on this platform. Falsification rules are pre-registered — decaying evidence retires claims publicly."
          >
            <div className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
              Thesis engine
            </div>
            <div className="mt-0.5 text-[11px] font-medium text-neutral-800">{engineStatus.engine}</div>
            <div className="text-[10px] text-neutral-500">
              {engineStatus.universe_version
                ? `universe ${engineStatus.universe_version.slice(0, 18)}`
                : "no sealed universe"}
            </div>
            {engineStatus.falsification && engineStatus.falsification.length > 0 && (
              <div className="text-[10px] text-neutral-500">
                {engineStatus.falsification.length} falsification rules armed
              </div>
            )}
          </div>
        )}

        <div className={`space-y-1 border-t border-neutral-200 ${collapsed ? "p-1.5" : "p-3"}`}>
          {collapsed ? (
            <button
              type="button"
              onClick={toggleCollapsed}
              className="flex w-full items-center justify-center rounded-lg p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
              title="Expand navigation"
              aria-label="Expand navigation"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          ) : null}
          <a
            href="https://research.finsoeasy.com/"
            className={`flex items-center rounded-lg text-xs text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 ${
              collapsed ? "justify-center p-2" : "gap-2 px-2 py-2"
            }`}
            title="Research papers"
          >
            <BookOpen className="h-3.5 w-3.5 shrink-0" />
            {!collapsed && "Research papers"}
          </a>
          {token && user && (
            <button
              type="button"
              onClick={() => {
                void logout()
                navigate("/login?next=/app")
              }}
              className={`flex w-full items-center rounded-lg text-xs text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 ${
                collapsed ? "justify-center p-2" : "gap-2 px-2 py-2"
              }`}
              title={user.email}
            >
              <LogOut className="h-3.5 w-3.5 shrink-0" />
              {!collapsed && <span className="truncate">{user.email}</span>}
            </button>
          )}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col bg-[#f7f7f5]">
        <header className="sticky top-0 z-40 flex h-12 items-center gap-2 border-b border-neutral-200 bg-white px-3 md:hidden">
          <Link to="/app" className="text-sm font-semibold text-neutral-900">
            Finsoeasy
          </Link>
          <div className="flex-1" />
          <Link
            to="/app/universe"
            className={`rounded px-2 py-1 text-xs ${
              onUniverse ? "bg-neutral-100 font-medium text-neutral-900" : "text-neutral-500"
            }`}
          >
            Universe
          </Link>
          <Link
            to="/app/book"
            className={`rounded px-2 py-1 text-xs ${
              onBook ? "bg-neutral-100 font-medium text-neutral-900" : "text-neutral-500"
            }`}
          >
            {bookError ? "Book unavailable" : `Book (${bookCount})`}
          </Link>
        </header>
        {collapsed && (
          <div className="sticky top-0 z-30 hidden h-9 items-center border-b border-neutral-200 bg-white px-3 md:flex">
            <button
              type="button"
              onClick={toggleCollapsed}
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
            >
              <PanelLeftOpen className="h-3.5 w-3.5" />
              Expand nav
            </button>
          </div>
        )}
        <main className="flex-1 overflow-auto bg-[#f7f7f5] text-neutral-900">{children}</main>
      </div>
    </div>
  )
}

function NavItem({
  to,
  active,
  icon,
  label,
  hint,
  badge,
  collapsed,
}: {
  to: string
  active: boolean
  icon: ReactNode
  label: string
  hint: string
  badge?: number | string
  collapsed: boolean
}) {
  return (
    <Link
      to={to}
      title={collapsed ? `${label} — ${hint}` : undefined}
      className={`flex items-start rounded-xl transition ${
        collapsed ? "justify-center p-2.5" : "gap-2.5 px-2.5 py-2.5"
      } ${
        active
          ? "bg-neutral-100 text-neutral-900"
          : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900"
      }`}
    >
      <span className={collapsed ? "" : "mt-0.5"}>{icon}</span>
      {!collapsed && (
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="text-sm font-medium">{label}</span>
            {badge != null && (typeof badge === "string" || badge > 0) && (
              <span className="rounded-full bg-neutral-900 px-1.5 text-[10px] font-semibold text-white">
                {badge}
              </span>
            )}
          </span>
          <span className="block text-[11px] text-neutral-500">{hint}</span>
        </span>
      )}
    </Link>
  )
}
