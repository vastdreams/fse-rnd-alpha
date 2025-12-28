import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

import { ThemeProvider } from "@/components/theme-provider"
import { SidebarProvider, useSidebar } from "@/components/sidebar-context"
import { Sidebar } from "@/components/layout/Sidebar"
import { Navbar } from "@/components/layout/Navbar"
import { Footer } from "@/components/layout/Footer"
import { Overview } from "@/pages/Overview"
import { Companies } from "@/pages/Companies"
import { CompanyDetail } from "@/pages/CompanyDetail"
import { Factors } from "@/pages/Factors"
import { Backtests } from "@/pages/Backtests"
import { Statistics } from "@/pages/Statistics"
import { Research } from "@/pages/Research"
import { Portfolio } from "@/pages/Portfolio"
import { Documentation } from "@/pages/Documentation"
import { Methodology } from "@/pages/Methodology"
import { Paper1 } from "@/pages/papers/Paper1"
import { Paper2 } from "@/pages/papers/Paper2"
import { Paper3 } from "@/pages/papers/Paper3"
import { Paper4 } from "@/pages/papers/Paper4"
import { MainPaper } from "@/pages/papers/MainPaper"
import { Whitepaper } from "@/pages/Whitepaper"
import { Subscribe } from "@/pages/Subscribe"
import { Donate } from "@/pages/Donate"
import { Admin } from "@/pages/Admin"
import { Unsubscribe } from "@/pages/Unsubscribe"
import { Terms } from "@/pages/Terms"
import { Privacy } from "@/pages/Privacy"
import { cn } from "@/lib/utils"
import { usePageView } from "@/lib/analytics"
import { SessionIndicator } from "@/components/SessionIndicator"
import { SubscribePopup } from "@/components/SubscribePopup"

// Configure React Query with aggressive caching
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      // Cache data for 5 minutes by default
      staleTime: 5 * 60 * 1000,
      // Keep unused data in cache for 30 minutes
      gcTime: 30 * 60 * 1000,
    },
  },
})

// Analytics wrapper to track page views
function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  usePageView()
  return <>{children}</>
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const { collapsed, isMobile } = useSidebar()
  
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Sidebar />
      {/* Main content area - adjusts based on sidebar state and mobile */}
      <div className={cn(
        "transition-all duration-300 flex-1 flex flex-col",
        isMobile ? "ml-0" : (collapsed ? "ml-16" : "ml-64")
      )}>
        <Navbar />
        <main className="p-4 md:p-6 flex-1">{children}</main>
        <Footer />
      </div>
      {/* Session indicator - dev only */}
      <SessionIndicator />
      {/* Subscribe popup - appears after 20s */}
      <SubscribePopup />
    </div>
  )
}

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="rd-alpha-theme">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <SidebarProvider>
            <AnalyticsProvider>
              <AppLayout>
                <Routes>
                  {/* Main Paper is the landing page */}
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
                  {/* Paper Routes - /papers/main redirects to home */}
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
              </AppLayout>
            </AnalyticsProvider>
          </SidebarProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
