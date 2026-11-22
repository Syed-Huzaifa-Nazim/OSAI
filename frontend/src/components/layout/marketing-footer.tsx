import { Link } from 'react-router-dom'
import { Logo } from '@/components/shared/logo'
import { MARKETING_NAV } from './nav-config'

export function MarketingFooter() {
  return (
    <footer className="border-t border-border/15 bg-card/30">
      <div className="container grid gap-10 py-14 md:grid-cols-[1.6fr_1fr_1fr]">
        <div className="space-y-4">
          <Logo />
          <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
            Competitor analysis for small online shops: see what works for them, find your gaps, decide what to change. A Final Year Project
            at the Department of Artificial Intelligence, Dawood University of Engineering &amp;
            Technology.
          </p>
        </div>

        <nav aria-label="Footer">
          <h2 className="mb-3 text-sm font-medium">Product</h2>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {MARKETING_NAV.map((item) => (
              <li key={item.to}>
                <Link to={item.to} className="transition-colors hover:text-primary">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div>
          <h2 className="mb-3 text-sm font-medium">Account</h2>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              <Link to="/login" className="transition-colors hover:text-primary">
                Log in
              </Link>
            </li>
            <li>
              <Link to="/signup" className="transition-colors hover:text-primary">
                Create an account
              </Link>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-border/10">
        <div className="container flex flex-wrap items-center justify-between gap-3 py-5 text-xs text-muted-foreground">
          <p>© {new Date().getFullYear()} OptiStratixAI.</p>
          <p>Dawood University of Engineering &amp; Technology · Department of AI</p>
        </div>
      </div>
    </footer>
  )
}
