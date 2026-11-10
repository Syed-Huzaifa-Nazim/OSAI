import { Link } from 'react-router-dom'
import { Logo } from '@/components/shared/logo'
import { MARKETING_NAV } from './nav-config'

export function MarketingFooter() {
  return (
    <footer className="relative overflow-hidden border-t border-primary/20 bg-card/60">
      <div className="pointer-events-none absolute inset-x-0 bottom-[-3.5rem] text-center font-display text-[clamp(4rem,14vw,12rem)] font-bold leading-none tracking-[-0.08em] text-primary/[0.07] blur-[1px]">
        OptiStratixAI
      </div>
      <div className="container grid gap-10 py-14 md:grid-cols-[1.6fr_1fr_1fr]">
        <div className="space-y-4">
          <Logo />
          <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
            Human-in-the-loop multi-agentic RAG for smarter digital marketing. A Final Year Project
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

      <div className="relative z-10 border-t border-border/10">
        <div className="container flex flex-wrap items-center justify-between gap-3 py-5 text-xs text-muted-foreground">
          <p>© {new Date().getFullYear()} OptiStratixAI. Released under the MIT License.</p>
          <p>Dawood University of Engineering &amp; Technology · Department of AI</p>
        </div>
      </div>
    </footer>
  )
}
