/**
 * PATH: research/frontend/src/pages/Admin.tsx
 * PURPOSE: Unified Admin Dashboard for Finsoeasy properties and clients.
 * WHY: Single admin interface for research.finsoeasy.com, finsoeasy.com, and client portals.
 * FLOW: JWT Login → Site Select → Dashboard (Research | Main | Clients)
 */
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Lock, LogOut, Shield, Globe, BarChart3, Users, Heart, Clock, CheckCircle, Settings, FlaskConical, Building2, Briefcase, ExternalLink } from "lucide-react"
import {
  useAdminData,
  AdminLogin, AdminMainSite, AdminClients, AdminAnalytics, AdminDataTabs,
  UNIFIED_GA4_PROPERTY, type SiteKey, type SiteConfig,
} from "@/components/admin"
import { formatDuration } from "@/components/admin/admin-types"

const SITES: Record<SiteKey, SiteConfig> = {
  research: { key: "research", name: "R&D Alpha", domain: "research.finsoeasy.com", icon: <FlaskConical className="w-4 h-4" />, hasBackend: true, description: "Research platform with full backend access" },
  main: { key: "main", name: "Main Site", domain: "finsoeasy.com", icon: <Building2 className="w-4 h-4" />, hasBackend: false, description: "Main website - GA4 analytics only" },
  clients: { key: "clients", name: "Clients", domain: "finsoeasy.com", icon: <Briefcase className="w-4 h-4" />, hasBackend: false, description: "Manage client portals and access" },
}

export function Admin() {
  const data = useAdminData()
  const { isAuthenticated, adminUser, handleLogout, activeSite, setActiveSite, dashboardData, activeTab, setActiveTab, analyticsData, subscribersData, donationsData } = data
  const currentSite = SITES[activeSite]

  if (!isAuthenticated) return <AdminLogin data={data} />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3"><Shield className="w-8 h-8 text-blue-500" />Unified Admin Dashboard</h1>
          <p className="text-muted-foreground mt-1">Manage all Finsoeasy properties</p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="px-3 py-1"><Lock className="w-3 h-3 mr-2" />{adminUser?.username}</Badge>
          <Button variant="outline" onClick={handleLogout}><LogOut className="w-4 h-4 mr-2" />Logout</Button>
        </div>
      </div>

      {/* Site Selector */}
      <Card className="bg-gradient-to-r from-slate-900/50 to-slate-800/50 border-slate-700">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-muted-foreground"><Globe className="w-4 h-4" /><span>Select Property:</span></div>
            <div className="flex gap-2">
              {Object.values(SITES).map((site) => (
                <Button key={site.key} variant={activeSite === site.key ? "default" : "outline"} size="sm" onClick={() => setActiveSite(site.key)} className={activeSite === site.key ? "bg-blue-600 hover:bg-blue-700" : "hover:bg-slate-700"}>
                  {site.icon}<span className="ml-2">{site.name}</span>
                  {!site.hasBackend && <Badge variant="secondary" className="ml-2 text-[10px] px-1">GA4</Badge>}
                </Button>
              ))}
            </div>
            <a href={`https://${currentSite.domain}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-blue-400 transition-colors">
              {currentSite.domain}<ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </CardContent>
      </Card>

      {/* Welcome Card */}
      <Card className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border-blue-500/20">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                {currentSite.icon}<span className="font-semibold text-lg">{currentSite.name} Dashboard</span>
                {currentSite.hasBackend && dashboardData && <CheckCircle className="w-4 h-4 text-green-500" />}
              </div>
              <p className="text-sm text-muted-foreground">{currentSite.description}</p>
            </div>
            <Badge variant="outline" className="text-xs">GA4: {UNIFIED_GA4_PROPERTY}</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Research Stats Grid */}
      {activeSite === "research" && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {[
            { label: "Page Views", value: analyticsData?.totals.views || 0, icon: <BarChart3 className="h-4 w-4 text-blue-500" />, color: "text-blue-500", sub: "Last 30 days", tab: "analytics" as const },
            { label: "Visitors", value: analyticsData?.totals.unique_visitors || 0, icon: <Globe className="h-4 w-4 text-purple-500" />, color: "text-purple-500", sub: "Unique visitors", tab: "analytics" as const },
            { label: "Subscribers", value: subscribersData?.count || 0, icon: <Users className="h-4 w-4 text-emerald-500" />, color: "text-emerald-500", sub: "Newsletter signups", tab: "subscribers" as const },
            { label: "Donations", value: `$${donationsData?.total_amount?.toFixed(2) || "0.00"}`, icon: <Heart className="h-4 w-4 text-pink-500" />, color: "text-pink-500", sub: `${donationsData?.count || 0} donations`, tab: "donations" as const },
            { label: "Avg. Time", value: formatDuration(analyticsData?.totals.avg_duration_seconds || 0), icon: <Clock className="h-4 w-4 text-orange-500" />, color: "text-orange-500", sub: "Per page", tab: "overview" as const },
          ].map((stat) => (
            <Card key={stat.label} className={`cursor-pointer hover:border-current transition-colors`} onClick={() => setActiveTab(stat.tab)}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.label}</CardTitle>{stat.icon}
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
                <p className="text-xs text-muted-foreground">{stat.sub}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Site-specific content */}
      {activeSite === "main" && <AdminMainSite data={data} />}
      {activeSite === "clients" && <AdminClients data={data} />}

      {/* Research Tab Navigation */}
      {activeSite === "research" && (
        <div className="flex gap-2 border-b overflow-x-auto">
          {([
            { key: "overview", icon: <Settings className="w-4 h-4 mr-2" />, label: "Overview" },
            { key: "analytics", icon: <BarChart3 className="w-4 h-4 mr-2" />, label: "Analytics" },
            { key: "subscribers", icon: <Users className="w-4 h-4 mr-2" />, label: `Subscribers (${subscribersData?.count || 0})` },
            { key: "donations", icon: <Heart className="w-4 h-4 mr-2" />, label: `Donations (${donationsData?.count || 0})` },
          ] as const).map((tab) => (
            <Button key={tab.key} variant={activeTab === tab.key ? "default" : "ghost"} onClick={() => setActiveTab(tab.key)} className="rounded-b-none">
              {tab.icon}{tab.label}
            </Button>
          ))}
        </div>
      )}

      {/* Research Tab Content */}
      {activeSite === "research" && activeTab === "analytics" && <AdminAnalytics data={data} />}
      {activeSite === "research" && activeTab !== "analytics" && <AdminDataTabs data={data} activeTab={activeTab} />}
    </div>
  )
}
