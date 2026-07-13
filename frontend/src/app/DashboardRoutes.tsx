/**
 * PATH: frontend/src/app/DashboardRoutes.tsx
 * PURPOSE: Standalone portfolio product routes.
 * W3 dual-run: new evidence-ranked surfaces (/app = Universe, /app/company/:t
 * eight tabs, /app/book server books) are primary; the old bundle views stay
 * reachable at /app/legacy/* until cutover completes.
 */
import { Navigate, Route, Routes, useParams } from "react-router-dom"
import { RequireAuth } from "@/components/auth/RequireAuth"
import { Login } from "@/pages/Login"
import { Register } from "@/pages/Register"
import { ResetPassword } from "@/pages/ResetPassword"
import { VerifyEmail } from "@/pages/VerifyEmail"
import { InvestigatePage } from "@/pages/portfolio/InvestigatePage"
import { MyBookPage } from "@/pages/portfolio/MyBookPage"
import { UniversePage } from "@/pages/portfolio/UniversePage"
import { CompanyResearchPage } from "@/pages/portfolio/CompanyResearchPage"
import { BookPage } from "@/pages/portfolio/BookPage"
import { SaasCompanyDeepDive } from "@/pages/SaasCompanyDeepDive"

function LegacyCompanyRedirect() {
  const { ticker } = useParams<{ ticker: string }>()
  return <Navigate to={`/app/company/${ticker}`} replace />
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
      <Route path="/app/book" element={guard(<BookPage />)} />

      {/* Legacy bundle views (dual-run until cutover) */}
      <Route path="/app/legacy" element={guard(<InvestigatePage />)} />
      <Route path="/app/legacy/book" element={guard(<MyBookPage />)} />
      <Route path="/app/legacy/company/:ticker" element={guard(<SaasCompanyDeepDive />)} />
      <Route path="/app/investigate" element={<Navigate to="/app/legacy" replace />} />

      <Route path="/portfolio" element={<Navigate to="/app" replace />} />
      <Route path="/portfolio/saas/:ticker" element={<LegacyCompanyRedirect />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  )
}
