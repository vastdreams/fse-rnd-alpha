/**
 * PATH: frontend/src/app/DashboardRoutes.tsx
 * PURPOSE: Standalone portfolio product routes.
 * Evidence-ranked surfaces are the sole investor product. Historical dashboard
 * URLs canonically redirect to the versioned /app journeys so bookmarks do not
 * split user state across legacy in-browser storage and durable server records.
 */
import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom"
import { RequireAuth } from "@/components/auth/RequireAuth"
import { Login } from "@/pages/Login"
import { Register } from "@/pages/Register"
import { ResetPassword } from "@/pages/ResetPassword"
import { VerifyEmail } from "@/pages/VerifyEmail"
import { UniversePage } from "@/pages/portfolio/UniversePage"
import { CompanyResearchPage } from "@/pages/portfolio/CompanyResearchPage"
import { CompanyReportPage } from "@/pages/portfolio/CompanyReportPage"
import { BookPage } from "@/pages/portfolio/BookPage"

function LegacyCompanyRedirect() {
  const { ticker } = useParams<{ ticker: string }>()
  const location = useLocation()
  return <Navigate to={`/app/company/${ticker}${location.search}`} replace />
}

function LegacyUniverseRedirect() {
  const location = useLocation()
  return <Navigate to={`/app${location.search}`} replace />
}

function LegacyBookRedirect() {
  const location = useLocation()
  return <Navigate to={`/app/book${location.search}`} replace />
}

const guard = (el: React.ReactNode) => <RequireAuth>{el}</RequireAuth>

export function DashboardRoutes({ portfolioHost = false }: { portfolioHost?: boolean }) {
  return (
    <Routes>
      {portfolioHost && <Route path="/" element={<Navigate to="/app" replace />} />}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* New evidence-ranked product */}
      <Route path="/app" element={guard(<UniversePage />)} />
      <Route path="/app/universe" element={guard(<UniversePage />)} />
      <Route path="/app/company/:ticker" element={guard(<CompanyResearchPage />)} />
      <Route path="/app/company/:ticker/report/:snapshotId" element={guard(<CompanyReportPage />)} />
      <Route path="/app/company/:ticker/report/:snapshotId" element={guard(<CompanyReportPage />)} />
      <Route path="/app/book" element={guard(<BookPage />)} />

      {/* Historical URLs retain bookmarks but cannot revive legacy local state. */}
      <Route path="/app/legacy" element={guard(<LegacyUniverseRedirect />)} />
      <Route path="/app/legacy/book" element={guard(<LegacyBookRedirect />)} />
      <Route path="/app/legacy/company/:ticker" element={guard(<LegacyCompanyRedirect />)} />
      <Route path="/app/investigate" element={<LegacyUniverseRedirect />} />

      <Route path="/portfolio" element={<LegacyUniverseRedirect />} />
      <Route path="/portfolio/saas/:ticker" element={<LegacyCompanyRedirect />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  )
}
