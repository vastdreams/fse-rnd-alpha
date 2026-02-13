/** Overview, Subscribers, and Donations tab content (research site). */
import type { AdminData } from "./useAdminData"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Settings, Database, Activity, RefreshCw, CheckCircle, Users, Heart, Mail, DollarSign } from "lucide-react"

interface Props { data: AdminData; activeTab: string }

export function AdminDataTabs({ data, activeTab }: Props) {
  const { cacheClearing, cacheMessage, handleClearCache, subscribersData, donationsData } = data

  return (
    <>
      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Cache Management</CardTitle><CardDescription>Clear application cache to refresh data</CardDescription></CardHeader>
            <CardContent className="space-y-4">
              <Button onClick={handleClearCache} disabled={cacheClearing} variant="outline" className="w-full">
                {cacheClearing
                  ? <span className="flex items-center gap-2"><RefreshCw className="w-4 h-4 animate-spin" />Clearing...</span>
                  : <span className="flex items-center gap-2"><RefreshCw className="w-4 h-4" />Clear Cache</span>}
              </Button>
              {cacheMessage && (
                <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-600 text-sm flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />{cacheMessage}
                </div>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Quick Links</CardTitle><CardDescription>Navigate to key sections</CardDescription></CardHeader>
            <CardContent>
              <div className="grid gap-2">
                <a href="/api/docs" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors"><Database className="w-4 h-4 text-blue-500" /><span>API Documentation</span></a>
                <a href="/" className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors"><Activity className="w-4 h-4 text-green-500" /><span>Main Paper</span></a>
                <a href="/portfolio" className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors"><Settings className="w-4 h-4 text-purple-500" /><span>R&amp;D ETF</span></a>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Subscribers Tab */}
      {activeTab === "subscribers" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Mail className="w-5 h-5 text-emerald-500" />Newsletter Subscribers</CardTitle>
            <CardDescription>{subscribersData?.count || 0} total subscribers</CardDescription>
          </CardHeader>
          <CardContent>
            {subscribersData?.subscribers && subscribersData.subscribers.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead><TableHead>First Name</TableHead><TableHead>Last Name</TableHead>
                    <TableHead>Profession</TableHead><TableHead>Source</TableHead><TableHead>Subscribed At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {subscribersData.subscribers.map((sub, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-medium">{sub.email}</TableCell>
                      <TableCell className="text-muted-foreground">{sub.first_name || "-"}</TableCell>
                      <TableCell className="text-muted-foreground">{sub.last_name || "-"}</TableCell>
                      <TableCell className="text-muted-foreground">{sub.profession || "-"}</TableCell>
                      <TableCell><Badge variant="outline" className="capitalize">{sub.source?.replace(/_/g, " ") || "website"}</Badge></TableCell>
                      <TableCell className="text-muted-foreground">{new Date(sub.subscribed_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground"><Users className="w-12 h-12 mx-auto mb-4 opacity-50" /><p>No subscribers yet</p></div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Donations Tab */}
      {activeTab === "donations" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><DollarSign className="w-5 h-5 text-pink-500" />Donations History</CardTitle>
            <CardDescription>{donationsData?.count || 0} donations totaling ${donationsData?.total_amount?.toFixed(2) || "0.00"}</CardDescription>
          </CardHeader>
          <CardContent>
            {donationsData?.donations && donationsData.donations.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow><TableHead>Email</TableHead><TableHead>Amount</TableHead><TableHead>Type</TableHead><TableHead>Date</TableHead></TableRow>
                </TableHeader>
                <TableBody>
                  {donationsData.donations.map((donation, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-medium">{donation.email}</TableCell>
                      <TableCell className="text-emerald-600 font-semibold">${donation.amount.toFixed(2)}</TableCell>
                      <TableCell><Badge variant={donation.is_recurring ? "default" : "outline"}>{donation.is_recurring ? "Monthly" : "One-time"}</Badge></TableCell>
                      <TableCell className="text-muted-foreground">{new Date(donation.created_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground"><Heart className="w-12 h-12 mx-auto mb-4 opacity-50" /><p>No donations yet</p></div>
            )}
          </CardContent>
        </Card>
      )}
    </>
  )
}
