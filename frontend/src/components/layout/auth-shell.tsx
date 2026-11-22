import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'
import { Logo } from '@/components/shared/logo'
import { ThemeToggle } from '@/components/shared/theme-toggle'
import { spring } from '@/lib/motion'

interface AuthShellProps {
  title: string
  subtitle: string
  children: ReactNode
  footer?: ReactNode
}

/**
 * Login and signup are full pages, not dialogs. Split layout: the form on the
 * left, a quiet rendering of the nine-stage pipeline on the right so the
 * product's shape is visible before you are inside it.
 */
export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <div className="canvas-grain grid min-h-screen bg-background lg:grid-cols-[1fr_0.85fr]">
      <div className="relative z-10 flex flex-col px-5 py-6 sm:px-10">
        <div className="flex items-center justify-between">
          <Link to="/">
            <Logo />
          </Link>
          <ThemeToggle />
        </div>

        <div className="flex flex-1 items-center justify-center py-10">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="w-full max-w-[400px]"
          >
            <Link
              to="/"
              className="mb-8 inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-primary"
            >
              <ArrowLeft className="size-3.5" />
              Back to site
            </Link>
            <h1 className="font-display text-2xl font-semibold tracking-tight">{title}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
            <div className="mt-8">{children}</div>
            {footer ? <div className="mt-6 text-sm text-muted-foreground">{footer}</div> : null}
          </motion.div>
        </div>
      </div>

      <aside className="relative z-10 hidden overflow-hidden border-l border-border/15 bg-card/30 lg:block">
        <div className="relative flex h-full flex-col items-center justify-center p-10 text-center">
          <div className="pointer-events-none absolute inset-[15%] rounded-full bg-primary/20 blur-3xl" aria-hidden="true" />
          <motion.img
            src="/brand/logo-large.png"
            alt="OptiStratixAI"
            className="relative w-full max-w-[22rem] select-none drop-shadow-[0_24px_40px_hsl(var(--shadow-color)/0.35)]"
            draggable={false}
            initial={{ opacity: 0, scale: 0.92, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: [0, -8, 0] }}
            transition={{ opacity: { duration: 0.5 }, scale: { duration: 0.5 }, y: { duration: 6, repeat: Infinity, ease: 'easeInOut' } }}
          />
          <p className="relative mt-8 font-display text-3xl font-extrabold tracking-tight">OptiStratixAI</p>
          <p className="relative mt-2 max-w-xs text-sm text-muted-foreground">
            See what works for your competitors. Find your gaps. Grow your shop.
          </p>
        </div>
      </aside>
    </div>
  )
}
