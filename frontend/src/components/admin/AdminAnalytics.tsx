/** Analytics tab – page views, device breakdown, visitor management. */
import type { AdminData } from "./useAdminData"
import { formatDuration } from "./admin-types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { BarChart3, Monitor, Smartphone, Globe, Ban, UserX } from "lucide-react"

interface Props { data: AdminData }

export function AdminAnalytics({ data }: Props) {
  const { analyticsData, visitorsData, myVisitorId, blockVisitor, unblockVisitor } = data

  return (
    <div className="space-y-6">
      {/* Page Views */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><BarChart3 className="w-5 h-5 text-blue-500" />Page Views (Last 30 Days)</CardTitle>
          <CardDescription>Traffic breakdown by page</CardDescription>
        </CardHeader>
        <CardContent>
          {analyticsData?.pages && analyticsData.pages.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Page</TableHead><TableHead className="text-right">Views</TableHead>
                  <TableHead className="text-right">Unique Visitors</TableHead><TableHead className="text-right">Avg. Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analyticsData.pages.map((page, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-mono text-sm">{page.page}</TableCell>
                    <TableCell className="text-right font-semibold">{page.views}</TableCell>
                    <TableCell className="text-right">{page.unique_visitors}</TableCell>
                    <TableCell className="text-right text-muted-foreground">{formatDuration(page.avg_duration)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground"><BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" /><p>No page view data yet</p></div>
          )}
        </CardContent>
      </Card>

      {/* Device + Visitor ID */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Device Breakdown</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analyticsData?.devices && Object.entries(analyticsData.devices).map(([device, count]) => (
                <div key={device} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {device === "desktop" ? <Monitor className="w-4 h-4" /> : <Smartphone className="w-4 h-4" />}
                    <span className="capitalize">{device}</span>
                  </div>
                  <Badge variant="outline">{count}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Your Visitor ID</CardTitle><CardDescription>Block this to exclude yourself from analytics</CardDescription></CardHeader>
          <CardContent>
            <div className="p-3 bg-muted rounded-lg font-mono text-sm break-all mb-4">{myVisitorId}</div>
            <Button variant="outline" className="w-full" onClick={() => blockVisitor(myVisitorId, "Admin - self excluded")}>
              <UserX className="w-4 h-4 mr-2" />Exclude Myself from Analytics
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Visitors List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Globe className="w-5 h-5 text-purple-500" />Visitors</CardTitle>
          <CardDescription>{visitorsData?.count || 0} total visitors tracked</CardDescription>
        </CardHeader>
        <CardContent>
          {visitorsData?.visitors && visitorsData.visitors.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Visitor ID</TableHead><TableHead>Device</TableHead><TableHead className="text-right">Visits</TableHead>
                  <TableHead>Last Seen</TableHead><TableHead>Status</TableHead><TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visitorsData.visitors.map((visitor) => (
                  <TableRow key={visitor.visitor_id} className={visitor.is_blocked ? "opacity-50" : ""}>
                    <TableCell className="font-mono text-xs">
                      {visitor.visitor_id.slice(0, 12)}...
                      {visitor.visitor_id === myVisitorId && <Badge className="ml-2" variant="secondary">You</Badge>}
                    </TableCell>
                    <TableCell>{visitor.device === "desktop" ? <Monitor className="w-4 h-4" /> : <Smartphone className="w-4 h-4" />}</TableCell>
                    <TableCell className="text-right font-semibold">{visitor.total_visits}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">{visitor.last_seen ? new Date(visitor.last_seen).toLocaleString() : "N/A"}</TableCell>
                    <TableCell>{visitor.is_blocked ? <Badge variant="destructive">Blocked</Badge> : <Badge variant="outline">Active</Badge>}</TableCell>
                    <TableCell>
                      {visitor.is_blocked ? (
                        <Button size="sm" variant="ghost" onClick={() => unblockVisitor(visitor.visitor_id)}>Unblock</Button>
                      ) : (
                        <Button size="sm" variant="ghost" onClick={() => blockVisitor(visitor.visitor_id)}><Ban className="w-3 h-3" /></Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground"><Globe className="w-12 h-12 mx-auto mb-4 opacity-50" /><p>No visitors tracked yet</p></div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
