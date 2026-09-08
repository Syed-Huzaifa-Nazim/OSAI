import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'
import { Logo } from '@/components/shared/logo'
import { ThemeToggle } from '@/components/shared/theme-toggle'
import { spring } from '@/lib/motion'
import { PIPELINE_STAGES } from '@/lib/pipeline-stages'
import { STAGE_COLOR_CLASSES } from '@/components/pipeline/stage-colors'
import { resolveStageIcon } from '@/components/pipeline/stage-icon'
import { cn } from '@/lib/utils'

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
        <div className="flex h-full flex-col justify-center gap-3 p-10">
          <p className="eyebrow mb-3">The nine stages</p>
          {PIPELINE_STAGES.map((stage, index) => {
            const Icon = resolveStageIcon(stage.icon)
            const colors = STAGE_COLOR_CLASSES[stage.id]
            return (
              <motion.div
                key={stage.id}
                initial={{ opacity: 0, x: 18 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...spring, delay: 0.05 * index }}
                className="flex items-center gap-3"
              >
                <span
                  className={cn(
                    'flex size-8 shrink-0 items-center justify-center rounded-full',
                    colors.bgSoft,
                    colors.text,
                  )}
                >
                  <Icon className="size-3.5" />
                </span>
                <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                  {String(stage.id).padStart(2, '0')}
                </span>
                <span
                  className={cn(
                    'text-sm',
                    stage.isCheckpoint ? 'font-medium text-brand-butter-cream' : 'text-foreground/80',
                  )}
                >
                  {stage.title}
                </span>
              </motion.div>
            )
          })}
          <p className="mt-4 max-w-xs text-xs leading-relaxed text-muted-foreground">
            Two of those nine stages are yours. The system will not write a strategy, or finish one,
            without your sign-off.
          </p>
        </div>
      </aside>
    </div>
  )
}
