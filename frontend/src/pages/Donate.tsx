import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Heart, Coffee, Globe, BookOpen, Shield, Zap, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"

const donationTiers = [
  { amount: 5, label: "Coffee", description: "Buy us a coffee", icon: Coffee },
  { amount: 25, label: "Supporter", description: "Support data costs", icon: Heart },
  { amount: 100, label: "Patron", description: "Expand research scope", icon: Globe },
  { amount: 500, label: "Champion", description: "Fund new alphas", icon: Zap },
]

export function Donate() {
  const [selectedAmount, setSelectedAmount] = useState<number | null>(25)
  const [customAmount, setCustomAmount] = useState("")

  const finalAmount = customAmount ? parseInt(customAmount) : selectedAmount

  const handleDonate = () => {
    // In production, this would redirect to Stripe
    alert(`Thank you for your ${finalAmount ? `$${finalAmount}` : ''} donation intent! Stripe integration coming soon.`)
  }

  const impactAreas = [
    { icon: BookOpen, title: "Free Research", description: "Keep all research papers and analysis freely accessible to everyone" },
    { icon: Globe, title: "Global Coverage", description: "Expand coverage to international markets and emerging economies" },
    { icon: Shield, title: "Data Quality", description: "Maintain premium data feeds for accurate, reliable research" },
    { icon: Zap, title: "New Alphas", description: "Fund research into additional asymmetric alpha strategies" },
  ]

  return (
    <div className="max-w-4xl mx-auto py-8 space-y-8">
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
                      ? "border-pink-500 bg-pink-50 dark:bg-pink-900/20"
                      : "border-border hover:border-pink-300 hover:bg-pink-50/50 dark:hover:bg-pink-900/10"
                  )}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <tier.icon className={cn(
                      "w-4 h-4",
                      selectedAmount === tier.amount && !customAmount ? "text-pink-500" : "text-muted-foreground"
                    )} />
                    <span className="font-bold text-lg">${tier.amount}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{tier.description}</p>
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

            {/* Donate button */}
            <Button 
              onClick={handleDonate}
              disabled={!finalAmount}
              className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600 text-white"
            >
              <Heart className="w-5 h-5 mr-2" />
              Donate {finalAmount ? `$${finalAmount}` : ""}
            </Button>

            <p className="text-xs text-center text-muted-foreground">
              Secure payment via Stripe. One-time donation.
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
      <Card className="bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-900/50 dark:to-slate-800/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center">
              <Zap className="w-6 h-6 text-emerald-500" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">Roadmap: More Asymmetric Alphas</h3>
              <p className="text-sm text-muted-foreground mb-3">
                With your support, we plan to expand research into additional evidence-based factor strategies:
              </p>
              <div className="flex flex-wrap gap-2">
                {["Quality Factor", "Momentum Anomalies", "Patent Alpha", "ESG Integration", "Global Markets"].map((item) => (
                  <span key={item} className="px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
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
            href="https://github.com/finsoeasy/fse-rnd-alpha"
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

