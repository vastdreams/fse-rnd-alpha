/**
 * PATH: src/components/layout/Footer.tsx
 * PURPOSE: Site-wide footer with legal links and copyright
 */

import { Link } from "react-router-dom"

export function Footer() {
  const currentYear = new Date().getFullYear()
  
  return (
    <footer className="border-t bg-muted/30 py-6 mt-auto">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          {/* Copyright */}
          <div className="text-sm text-muted-foreground text-center md:text-left">
            <p>© {currentYear} FSE Research and Investments. All rights reserved.</p>
            <p className="text-xs mt-1">R&D Alpha — Factor-Based Investment Research</p>
          </div>
          
          {/* Links */}
          <div className="flex flex-wrap justify-center gap-4 text-sm">
            <Link 
              to="/terms" 
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Terms of Service
            </Link>
            <span className="text-muted-foreground/50">|</span>
            <Link 
              to="/privacy" 
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Privacy Policy
            </Link>
            <span className="text-muted-foreground/50">|</span>
            <a 
              href="https://finsoeasy.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              finsoeasy.com
            </a>
          </div>
        </div>
        
        {/* Disclaimer */}
        <div className="mt-4 pt-4 border-t border-border/50">
          <p className="text-xs text-muted-foreground/70 text-center max-w-3xl mx-auto">
            <strong>Disclaimer:</strong> The content on this website is for informational purposes only and does not constitute investment advice. 
            Past performance is not indicative of future results. All investments involve risk, including potential loss of principal.
          </p>
        </div>
      </div>
    </footer>
  )
}

