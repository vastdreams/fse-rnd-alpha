import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Heart, Coffee, Globe, BookOpen, Shield, Zap, ExternalLink, RefreshCw, Loader2, AlertCircle, CheckCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSearchParams } from "react-router-dom"

// API base URL - in production nginx proxies /api to backend, in dev use localhost:8000
const API_BASE = import.meta.env.VITE_API_URL || ""

const donationTiers = [
  { amount: 5, label: "Coffee", description: "Buy us a coffee", icon: Coffee },
  { amount: 25, label: "Supporter", description: "Support data costs", icon: Heart },
  { amount: 100, label: "Patron", description: "Expand research scope", icon: Globe },
  { amount: 500, label: "Champion", description: "Fund new alphas", icon: Zap },
]

export function Donate() {
  const [selectedAmount, setSelectedAmount] = useState<number | null>(25)
  const [customAmount, setCustomAmount] = useState("")
  const [isRecurring, setIsRecurring] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stripeConfigured, setStripeConfigured] = useState<boolean | null>(null)
  const [searchParams] = useSearchParams()
  
  const isSuccess = searchParams.get("success") === "true"
  const isCanceled = searchParams.get("canceled") === "true"

  const finalAmount = customAmount ? parseInt(customAmount) : selectedAmount

  // Check if Stripe is configured
  useEffect(() => {
    fetch(`${API_BASE}/api/donations/config`)
      .then(res => res.json())
      .then((data: { configured: boolean }) => setStripeConfigured(data.configured))
      .catch(() => setStripeConfigured(false))
  }, [])

  const handleDonate = async () => {
    if (!finalAmount || finalAmount < 1) {
      setError("Please select or enter a valid amount")
      return
    }
    
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE}/api/donations/create-checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: finalAmount,
          is_recurring: isRecurring,
          success_url: `${window.location.origin}/donate?success=true`,
          cancel_url: `${window.location.origin}/donate?canceled=true`,
        }),
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }
      
      const data = await response.json() as { checkout_url: string; session_id: string }
      
      // Redirect to Stripe checkout
      window.location.href = data.checkout_url
    } catch (err: unknown) {
      console.error("Donation error:", err)
      const message = err instanceof Error ? err.message : "Failed to process donation. Please try again."
      setError(message)
      setIsLoading(false)
    }
  }

  const impactAreas = [
    { icon: BookOpen, title: "Free Research", description: "Keep all research papers and analysis freely accessible to everyone" },
    { icon: Globe, title: "Global Coverage", description: "Expand coverage to international markets and emerging economies" },
    { icon: Shield, title: "Data Quality", description: "Maintain premium data feeds for accurate, reliable research" },
    { icon: Zap, title: "New Alphas", description: "Fund research into additional asymmetric alpha strategies" },
  ]

  // Show success message if redirected from Stripe
  if (isSuccess) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-6">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-emerald-500 to-green-500">
          <CheckCircle className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Thank You!</h1>
        <p className="text-muted-foreground text-lg">
          Your donation has been received. You are helping keep R&D research free and accessible to everyone.
        </p>
        <div className="flex justify-center gap-4 pt-4">
          <Button variant="outline" onClick={() => window.location.href = "/donate"}>
            Make Another Donation
          </Button>
          <Button onClick={() => window.location.href = "/"}>
            Back to Research
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8 space-y-8">
      {/* Canceled notice */}
      {isCanceled && (
        <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg p-4 text-center">
          <p className="text-amber-800 dark:text-amber-200">
            Your donation was canceled. No worries - you can try again anytime!
          </p>
        </div>
      )}
      
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-pink-500 to-rose-500">
          <Heart className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Support Free Research</h1>
        <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
          Help us keep quality financial research free and accessible. Your donation supports data costs, 
          server infrastructure, and expansion into new alpha strategies.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Donation Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Choose an Amount</CardTitle>
            <CardDescription>Every contribution helps maintain and expand our research</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Preset amounts */}
            <div className="grid grid-cols-2 gap-3">
              {donationTiers.map((tier) => (
                <button
                  key={tier.amount}
                  onClick={() => {
                    setSelectedAmount(tier.amount)
                    setCustomAmount("")
                  }}
                  className={cn(
                    "p-4 rounded-xl border-2 transition-all text-left",
                    selectedAmount === tier.amount && !customAmount
                      ? "border-pink-500 bg-pink-100 dark:bg-pink-950 dark:border-pink-400"
                      : "border-border hover:border-pink-300 dark:hover:border-pink-600 hover:bg-pink-50/50 dark:hover:bg-pink-900/20"
                  )}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <tier.icon className={cn(
                      "w-4 h-4",
                      selectedAmount === tier.amount && !customAmount ? "text-pink-500 dark:text-pink-400" : "text-muted-foreground"
                    )} />
                    <span className={cn(
                      "font-bold text-lg",
                      selectedAmount === tier.amount && !customAmount ? "text-foreground" : ""
                    )}>${tier.amount}</span>
                  </div>
                  <p className={cn(
                    "text-xs",
                    selectedAmount === tier.amount && !customAmount ? "text-pink-700 dark:text-pink-300" : "text-muted-foreground"
                  )}>{tier.description}</p>
                </button>
              ))}
            </div>

            {/* Custom amount */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Custom Amount</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <input
                  type="number"
                  min="1"
                  placeholder="Enter amount"
                  value={customAmount}
                  onChange={(e) => {
                    setCustomAmount(e.target.value)
                    setSelectedAmount(null)
                  }}
                  className="w-full h-12 pl-8 pr-4 rounded-lg border bg-background focus:ring-2 focus:ring-pink-500 focus:border-pink-500 outline-none"
                />
              </div>
            </div>

            {/* Recurring toggle */}
            <div className="flex items-center justify-between p-4 rounded-xl border bg-muted/30">
              <div className="flex items-center gap-3">
                <RefreshCw className={cn("w-5 h-5", isRecurring ? "text-pink-500" : "text-muted-foreground")} />
                <div>
                  <p className="font-medium text-sm">Make it monthly</p>
                  <p className="text-xs text-muted-foreground">Support ongoing research</p>
                </div>
              </div>
              <button
                onClick={() => setIsRecurring(!isRecurring)}
                className={cn(
                  "relative w-12 h-7 rounded-full transition-colors duration-200",
                  isRecurring ? "bg-pink-500" : "bg-slate-300 dark:bg-slate-600"
                )}
              >
                <span
                  className={cn(
                    "absolute top-1 left-1 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200",
                    isRecurring && "translate-x-5"
                  )}
                />
              </button>
            </div>

            {/* Error message */}
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {/* Donate button */}
            <Button 
              onClick={handleDonate}
              disabled={!finalAmount || isLoading || stripeConfigured === false}
              className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600 text-white disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Redirecting to checkout...
                </>
              ) : (
                <>
                  <Heart className="w-5 h-5 mr-2" />
                  {isRecurring ? "Donate " : "Donate "}
                  {finalAmount ? `$${finalAmount}` : ""}
                  {isRecurring && "/month"}
                </>
              )}
            </Button>

            {stripeConfigured === false && (
              <p className="text-xs text-center text-amber-600 dark:text-amber-400">
                Payment processing is being set up. Please check back soon or contact us directly.
              </p>
            )}
            
            <p className="text-xs text-center text-muted-foreground">
              Secure payment via Stripe. {isRecurring ? "Cancel anytime." : "One-time donation."}
            </p>
          </CardContent>
        </Card>

        {/* Impact */}
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Your Impact</h3>
          {impactAreas.map((area) => (
            <div key={area.title} className="flex gap-4 p-4 rounded-lg bg-card border">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-pink-500/10 flex items-center justify-center">
                <area.icon className="w-5 h-5 text-pink-500" />
              </div>
              <div>
                <h4 className="font-medium">{area.title}</h4>
                <p className="text-sm text-muted-foreground">{area.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Future plans */}
      <Card className="bg-gradient-to-r from-slate-100 to-slate-50 dark:from-slate-800 dark:to-slate-900 border dark:border-slate-700">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-emerald-500/20 dark:bg-emerald-500/10 flex items-center justify-center">
              <Zap className="w-6 h-6 text-emerald-500" />
            </div>
            <div>
              <h3 className="font-semibold mb-1 text-foreground">Roadmap: More Asymmetric Alphas</h3>
              <p className="text-sm text-muted-foreground mb-3">
                With your support, we plan to expand research into additional evidence-based factor strategies:
              </p>
              <div className="flex flex-wrap gap-2">
                {["Quality Factor", "Momentum Anomalies", "Patent Alpha", "ESG Integration", "Global Markets"].map((item) => (
                  <span key={item} className="px-2 py-1 rounded-full bg-emerald-500/20 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-xs font-medium border border-emerald-200 dark:border-emerald-800">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Alternative support */}
      <div className="text-center space-y-4 pt-4 border-t">
        <p className="text-muted-foreground">Other ways to support our research</p>
        <div className="flex justify-center gap-4">
          <a
            href="https://github.com/vastdreams/rd-alpha-research"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            Star on GitHub
          </a>
          <a
            href="/subscribe"
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <Heart className="w-4 h-4" />
            Subscribe to Newsletter
          </a>
        </div>
      </div>
    </div>
  )
}

