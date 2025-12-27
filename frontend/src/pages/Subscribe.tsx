import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Mail, Check, Bell, FileText, TrendingUp, Shield } from "lucide-react"

export function Subscribe() {
  const [email, setEmail] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return
    
    setLoading(true)
    try {
      const response = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "subscribe_page" }),
      })
      const data = await response.json()
      if (data.success) {
        setSubmitted(true)
      }
    } catch (error) {
      console.error("Subscribe error:", error)
    } finally {
      setLoading(false)
    }
  }

  const benefits = [
    { icon: FileText, title: "Research Updates", description: "Get notified when we publish new research findings and papers" },
    { icon: TrendingUp, title: "Market Insights", description: "Analysis of R&D factor performance and market trends" },
    { icon: Bell, title: "Early Access", description: "Be the first to know about new features and data updates" },
    { icon: Shield, title: "No Spam", description: "We respect your inbox - only valuable research content" },
  ]

  if (submitted) {
    return (
      <div className="max-w-xl mx-auto py-12">
        <Card className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border-emerald-200 dark:border-emerald-800">
          <CardContent className="pt-8 pb-8 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500 mx-auto mb-4 flex items-center justify-center">
              <Check className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 mb-2">
              You're Subscribed!
            </h2>
            <p className="text-muted-foreground mb-4">
              Thank you for subscribing to R&D Alpha research updates.
            </p>
            <p className="text-sm text-muted-foreground">
              Check your inbox at <strong className="text-foreground">{email}</strong> for a confirmation email.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Subscribe to Research</h1>
        <p className="text-muted-foreground text-lg">
          Stay informed with the latest R&D factor research and market insights
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Subscription Form */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-blue-500" />
              Join Our Newsletter
            </CardTitle>
            <CardDescription>
              Get research updates delivered to your inbox
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">Email Address</label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="h-12"
                />
              </div>
              <Button 
                type="submit" 
                className="w-full h-12 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-medium"
                disabled={loading}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                    Subscribing...
                  </span>
                ) : (
                  "Subscribe for Free"
                )}
              </Button>
              <p className="text-xs text-center text-muted-foreground">
                By subscribing, you agree to receive research emails. Unsubscribe anytime.
              </p>
            </form>
          </CardContent>
        </Card>

        {/* Benefits */}
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">What You'll Get</h3>
          {benefits.map((benefit) => (
            <div key={benefit.title} className="flex gap-4 p-4 rounded-lg bg-card border">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <benefit.icon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h4 className="font-medium">{benefit.title}</h4>
                <p className="text-sm text-muted-foreground">{benefit.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Trust indicators */}
      <div className="text-center pt-4 border-t">
        <p className="text-sm text-muted-foreground">
          Join researchers and investors seeking asymmetric factors with comprehensive, evidence-backed insights into portfolio and investment strategies
        </p>
      </div>
    </div>
  )
}

