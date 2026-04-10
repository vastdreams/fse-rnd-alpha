import type { ReactNode } from "react"

import { Footer } from "@/components/layout/Footer"
import { Navbar } from "@/components/layout/Navbar"
import { Sidebar } from "@/components/layout/Sidebar"
import { SessionIndicator } from "@/components/SessionIndicator"
import { useSidebar } from "@/components/sidebar-context"
import { SubscribePopup } from "@/components/SubscribePopup"
import { cn } from "@/lib/utils"

function ShellLayout({ children }: { children: ReactNode }) {
  const { collapsed, isMobile } = useSidebar()

  const contentMargin = isMobile ? "ml-0" : collapsed ? "ml-16" : "ml-64"

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Sidebar />
      <div className={cn("transition-all duration-300 flex-1 flex flex-col", contentMargin)}>
        <Navbar />
        <main className="p-4 md:p-6 flex-1">{children}</main>
        <Footer />
      </div>
      <SessionIndicator />
      <SubscribePopup />
    </div>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  return <ShellLayout>{children}</ShellLayout>
}
