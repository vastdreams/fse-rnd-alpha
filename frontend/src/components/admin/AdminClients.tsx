/** Clients dashboard – summary cards, portal list, quick actions. */
import type { AdminData } from "./useAdminData"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Briefcase, FileText, Globe, ExternalLink, CreditCard, Leaf, CheckCircle, Copy } from "lucide-react"
import type { ClientPortal } from "./admin-types"

function getClientPortalIcon(id: string) {
  if (id === "ozpremium") return <CreditCard className="w-5 h-5 text-blue-400" />
  if (id === "ecojv") return <Leaf className="w-5 h-5 text-green-400" />
  return <Briefcase className="w-5 h-5 text-slate-300" />
}

interface Props { data: AdminData }

export function AdminClients({ data }: Props) {
  const { clientPortals, clientsLoading, clientsError, cacheMessage, setCacheMessage } = data

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    setCacheMessage(`Copied ${label}!`)
    setTimeout(() => setCacheMessage(""), 2000)
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Clients</CardTitle>
            <Briefcase className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">{clientPortals.filter((c) => c.status === "active").length}</div>
            <p className="text-xs text-muted-foreground">With live investor portals</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <FileText className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">{clientPortals.reduce((acc, c) => acc + c.documents.length, 0)}</div>
            <p className="text-xs text-muted-foreground">Across all client portals</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sectors</CardTitle>
            <Globe className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-500">{new Set(clientPortals.map((c) => c.sector)).size}</div>
            <p className="text-xs text-muted-foreground">Financial Services, Renewables</p>
          </CardContent>
        </Card>
      </div>

      {/* Client Portals List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Briefcase className="w-5 h-5 text-blue-500" />Client Portals</CardTitle>
          <CardDescription>Manage portal metadata. Credentials are never returned to this browser.</CardDescription>
        </CardHeader>
        <CardContent>
          {clientsLoading && <div className="text-sm text-muted-foreground">Loading client portals…</div>}
          {clientsError && <div className="text-sm text-red-400">{clientsError}</div>}
          <div className="space-y-4">
            {!clientsLoading && clientPortals.length === 0 && (
              <div className="text-sm text-muted-foreground">No client portals configured. Create `backend/admin_clients.json` from `backend/admin_clients.example.json` on the server.</div>
            )}
            {clientPortals.map((client) => (
              <ClientPortalCard key={client.id} client={client} onCopy={copyToClipboard} />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Access Control</CardTitle><CardDescription>Manage credentials outside the browser</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">Client portal credentials are intentionally not stored in the repository or exposed through the admin API.</p>
            <p className="text-xs text-muted-foreground">Rotate credentials through the approved target-side secret and access-control process, then verify the portal separately.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Add New Client</CardTitle><CardDescription>Steps to onboard a new investor portal</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            <ol className="text-sm space-y-2 list-decimal list-inside text-muted-foreground">
              <li>Create investor deck (HTML or embedded doc)</li>
              <li>Add route in <code className="text-xs">/src/app/[client]/page.tsx</code></li>
              <li>Set password protection</li>
              <li>Deploy and test portal access</li>
              <li>Update `backend/admin_clients.json` (server-only config; not committed)</li>
            </ol>
          </CardContent>
        </Card>
      </div>

      {cacheMessage && (
        <div className="fixed bottom-4 right-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm flex items-center gap-2 animate-in slide-in-from-bottom-4">
          <CheckCircle className="w-4 h-4" />{cacheMessage}
        </div>
      )}
    </div>
  )
}

/** Single client portal card. */
function ClientPortalCard({ client, onCopy }: { client: ClientPortal; onCopy: (text: string, label: string) => void }) {
  return (
    <div className="p-4 rounded-lg border border-slate-700 bg-slate-900/50 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">{getClientPortalIcon(client.id)}</div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-lg">{client.name}</h3>
              <Badge variant={client.status === "active" ? "default" : "secondary"} className={client.status === "active" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" : ""}>{client.status}</Badge>
              {client.afsl && <Badge variant="outline" className="text-xs">AFSL {client.afsl}</Badge>}
            </div>
            <p className="text-sm text-muted-foreground mt-1">{client.description}</p>
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><Globe className="w-3 h-3" />{client.location}</span>
              <span className="flex items-center gap-1"><FileText className="w-3 h-3" />{client.documents.length} documents</span>
            </div>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={() => window.open(client.portalUrl, '_blank')}>
          <ExternalLink className="w-3 h-3 mr-1" />View Portal
        </Button>
      </div>
      <div className="mt-4 pt-4 border-t border-slate-700/50">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="p-3 rounded-lg bg-slate-800/50">
            <div className="flex items-center justify-between">
              <div><p className="text-xs text-muted-foreground mb-1">Portal URL</p><code className="text-sm font-mono text-blue-400">{client.portalUrl}</code></div>
              <Button size="sm" variant="ghost" onClick={() => onCopy(client.portalUrl, `${client.name} URL`)}><Copy className="w-3 h-3" /></Button>
            </div>
          </div>
        </div>
      </div>
      <div className="mt-4 pt-4 border-t border-slate-700/50">
        <p className="text-xs text-muted-foreground mb-2">Available Documents:</p>
        <div className="flex flex-wrap gap-2">
          {client.documents.map((doc, i) => (<Badge key={i} variant="outline" className="text-xs"><FileText className="w-3 h-3 mr-1" />{doc}</Badge>))}
        </div>
      </div>
    </div>
  )
}
