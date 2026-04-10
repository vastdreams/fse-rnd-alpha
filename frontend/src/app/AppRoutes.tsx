import { Navigate, Route, Routes } from "react-router-dom"

import { Admin } from "@/pages/Admin"
import { Backtests } from "@/pages/Backtests"
import { Companies } from "@/pages/Companies"
import { CompanyDetail } from "@/pages/CompanyDetail"
import { Documentation } from "@/pages/Documentation"
import { Donate } from "@/pages/Donate"
import { Factors } from "@/pages/Factors"
import { Methodology } from "@/pages/Methodology"
import { Overview } from "@/pages/Overview"
import { Portfolio } from "@/pages/Portfolio"
import { Privacy } from "@/pages/Privacy"
import { Research } from "@/pages/Research"
import { Statistics } from "@/pages/Statistics"
import { Subscribe } from "@/pages/Subscribe"
import { Terms } from "@/pages/Terms"
import { Unsubscribe } from "@/pages/Unsubscribe"
import { Whitepaper } from "@/pages/Whitepaper"
import { MainPaper } from "@/pages/papers/MainPaper"
import { Paper1 } from "@/pages/papers/Paper1"
import { Paper2 } from "@/pages/papers/Paper2"
import { Paper3 } from "@/pages/papers/Paper3"
import { Paper4 } from "@/pages/papers/Paper4"

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<MainPaper />} />
      <Route path="/overview" element={<Overview />} />
      <Route path="/companies" element={<Companies />} />
      <Route path="/companies/:ticker" element={<CompanyDetail />} />
      <Route path="/factors" element={<Factors />} />
      <Route path="/backtests" element={<Backtests />} />
      <Route path="/statistics" element={<Statistics />} />
      <Route path="/research" element={<Research />} />
      <Route path="/analysis" element={<Navigate to="/research" replace />} />
      <Route path="/portfolio" element={<Portfolio />} />
      <Route path="/documentation" element={<Documentation />} />
      <Route path="/methodology" element={<Methodology />} />
      <Route path="/papers/main" element={<Navigate to="/" replace />} />
      <Route path="/papers/1" element={<Paper1 />} />
      <Route path="/papers/2" element={<Paper2 />} />
      <Route path="/papers/3" element={<Paper3 />} />
      <Route path="/papers/4" element={<Paper4 />} />
      <Route path="/whitepaper" element={<Whitepaper />} />
      <Route path="/subscribe" element={<Subscribe />} />
      <Route path="/donate" element={<Donate />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/unsubscribe" element={<Unsubscribe />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/privacy" element={<Privacy />} />
    </Routes>
  )
}
