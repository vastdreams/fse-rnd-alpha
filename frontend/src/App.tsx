/**
 * PATH: frontend/src/App.tsx
 * PURPOSE: Split research site vs standalone Finsoeasy Portfolio dashboard.
 */
import { useLocation } from "react-router-dom"
import { AppProviders } from "@/app/AppProviders"
import { AppRoutes } from "@/app/AppRoutes"
import { AppShell } from "@/app/AppShell"
import { DashboardRoutes } from "@/app/DashboardRoutes"
import { DashboardShell } from "@/app/DashboardShell"

function isPortfolioHost() {
  if (typeof window === "undefined") return false
  const h = window.location.hostname
  return h === "portfolio.finsoeasy.com" || h === "portfolio.localhost" || h.startsWith("portfolio.")
}

function RootLayout() {
  const location = useLocation()
  const portfolioHost = isPortfolioHost()
  const onDashboard =
    portfolioHost ||
    location.pathname.startsWith("/app") ||
    location.pathname.startsWith("/portfolio") ||
    // Auth pages opened for the dashboard product
    ((location.pathname === "/login" ||
      location.pathname === "/register" ||
      location.pathname === "/verify-email" ||
      location.pathname === "/reset-password") &&
      new URLSearchParams(location.search).get("next")?.startsWith("/app"))

  if (onDashboard || portfolioHost) {
    return (
      <DashboardShell>
        <DashboardRoutes portfolioHost={portfolioHost} />
      </DashboardShell>
    )
  }

  return (
    <AppShell>
      <AppRoutes />
    </AppShell>
  )
}

function App() {
  return (
    <AppProviders>
      <RootLayout />
    </AppProviders>
  )
}

export default App
