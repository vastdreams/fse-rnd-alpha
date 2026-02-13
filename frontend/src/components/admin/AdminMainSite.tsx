/** Main site (finsoeasy.com) dashboard – GA4 status, config, deployment info. */
import type { AdminData } from "./useAdminData"
import { UNIFIED_GA4_PROPERTY } from "./admin-types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, BarChart3, Monitor, ExternalLink } from "lucide-react"

interface Props { data: AdminData }

export function AdminMainSite({ data }: Props) {
  const { cacheMessage, setCacheMessage } = data

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-green-500/30 bg-green-500/5">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">GA4 Status</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent><div className="text-lg font-semibold text-green-500">Active</div><p className="text-xs text-muted-foreground">Tracking live on site</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Property ID</CardTitle>
            <BarChart3 className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent><div className="text-lg font-mono font-semibold text-blue-500">{UNIFIED_GA4_PROPERTY}</div><p className="text-xs text-muted-foreground">Shared with research site</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Server</CardTitle>
            <Monitor className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent><div className="text-lg font-mono font-semibold text-purple-500">13.210.239.75</div><p className="text-xs text-muted-foreground">Sydney (ap-southeast-2)</p></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-500" />GA4 Tracking Active on finsoeasy.com
            <Badge variant="outline" className="ml-2 border-green-500/50 text-green-500">Live</Badge>
          </CardTitle>
          <CardDescription>Unified analytics tracking is installed and collecting data</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-green-900/20 rounded-lg border border-green-500/30">
            <p className="text-xs text-green-400 mb-2 flex items-center gap-2"><CheckCircle className="w-3 h-3" /> Currently installed in layout.tsx:</p>
            <pre className="text-xs font-mono text-green-400 overflow-x-auto whitespace-pre-wrap">{`gtag('config', '${UNIFIED_GA4_PROPERTY}', {\n  cookie_domain: '.finsoeasy.com',\n  cookie_flags: 'SameSite=None;Secure'\n});`}</pre>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" asChild>
              <a href="https://analytics.google.com/analytics/web/#/report-home/a123456789w123456789p123456789" target="_blank" rel="noopener noreferrer">
                <BarChart3 className="w-4 h-4 mr-2" />Open GA4 Dashboard<ExternalLink className="w-3 h-3 ml-2" />
              </a>
            </Button>
            <Button variant="outline" onClick={() => { navigator.clipboard.writeText(UNIFIED_GA4_PROPERTY); setCacheMessage("Copied GA4 ID!"); setTimeout(() => setCacheMessage(""), 2000) }}>
              Copy Property ID
            </Button>
          </div>
          {cacheMessage && <div className="p-2 rounded bg-green-500/10 border border-green-500/20 text-green-400 text-sm">{cacheMessage}</div>}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Deployment Info</CardTitle><CardDescription>Main site server details</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            {[["EC2 Instance", "i-0fa8fcc0259caa8e9"], ["Region", "ap-southeast-2"], ["SSH Key", "finsoeasy-key.pem"]].map(([label, val]) => (
              <div key={label} className="flex items-center justify-between p-2 rounded bg-muted">
                <span className="text-sm">{label}</span><code className="text-xs font-mono">{val}</code>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>View Combined Analytics</CardTitle><CardDescription>See data from both sites in GA4</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">Once tracking is added, view combined analytics by:</p>
            <ol className="text-sm space-y-2 list-decimal list-inside text-muted-foreground">
              <li>Go to GA4 → Reports → Engagement</li>
              <li>Add comparison by Hostname</li>
              <li>Compare research.finsoeasy.com vs finsoeasy.com</li>
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
