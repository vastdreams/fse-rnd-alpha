import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { BrowserRouter } from "react-router-dom"

import { SidebarProvider } from "@/components/sidebar-context"
import { ThemeProvider } from "@/components/theme-provider"
import { usePageView } from "@/lib/analytics"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
    },
  },
})

function AnalyticsProvider({ children }: { children: ReactNode }) {
  usePageView()
  return <>{children}</>
}

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider defaultTheme="light" storageKey="rd-alpha-theme">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <SidebarProvider>
            <AnalyticsProvider>{children}</AnalyticsProvider>
          </SidebarProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
