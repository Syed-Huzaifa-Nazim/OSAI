import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import {
  ArrowRight,
  ChevronRight,
  CircleCheck,
  Folder,
  Hourglass,
  Plus,
  type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorState, LoadingCards } from '@/components/shared/state-views'
import { useProjects } from '@/hooks/use-projects'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { useAuthStore } from '@/stores/auth-store'
import { errorMessage } from '@/lib/api-client'
import { groupByPlatform } from '@/lib/platform-groups'
import { PlatformLinks } from '@/components/shared/platform-picker'
import { cn } from '@/lib/utils'
import { spring, staggerContainer, staggerItem } from '@/lib/motion'

function greeting(): string {
  const hour = new Date().getHours()
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
}

/* ------------------------------------------------------------------------------------------------ art */

/** A glass panel with rising bars and a golden orbit (the hero's picture). */
function InsightArt() {
  const reduced = useReducedMotion()
  const bars = [34, 48, 62, 80, 100]
  return (
    <svg viewBox="0 0 420 240" className="h-full w-full" aria-hidden="true">
      <defs>
        <linearGradient id="dash-bar" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="hsl(var(--primary))" />
          <stop offset="1" stopColor="hsl(var(--primary) / 0.55)" />
        </linearGradient>
        <linearGradient id="dash-orbit" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="hsl(var(--warning))" stopOpacity="0" />
          <stop offset="0.5" stopColor="hsl(var(--warning))" />
          <stop offset="1" stopColor="hsl(var(--warning))" stopOpacity="0.1" />
        </linearGradient>
        <linearGradient id="dash-glass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="hsl(var(--card))" stopOpacity="0.85" />
          <stop offset="1" stopColor="hsl(var(--card))" stopOpacity="0.35" />
        </linearGradient>
      </defs>
      <g transform="translate(205 120) rotate(-8) translate(-205 -120)">
        <rect x="95" y="30" width="230" height="170" rx="22" fill="url(#dash-glass)" stroke="hsl(var(--primary) / 0.25)" />
        <rect x="118" y="52" width="80" height="9" rx="4.5" fill="hsl(var(--primary) / 0.18)" />
        <rect x="118" y="68" width="48" height="7" rx="3.5" fill="hsl(var(--primary) / 0.12)" />
        {bars.map((h, i) => (
          <motion.rect
            key={h}
            x={140 + i * 34}
            width="20"
            rx="10"
            fill="url(#dash-bar)"
            initial={reduced ? false : { height: 0, y: 182 }}
            animate={{ height: h, y: 182 - h }}
            transition={{ duration: 0.9, ease: 'easeOut', delay: 0.2 + i * 0.1 }}
          />
        ))}
      </g>
      <motion.ellipse
        cx="215"
        cy="135"
        rx="175"
        ry="52"
        fill="none"
        stroke="url(#dash-orbit)"
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray="420 700"
        transform="rotate(-14 215 135)"
        initial={reduced ? false : { strokeDashoffset: 420 }}
        animate={reduced ? undefined : { strokeDashoffset: [420, -700] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
      />
      {[
        { x: 62, y: 70, r: 9 },
        { x: 372, y: 52, r: 6 },
        { x: 352, y: 196, r: 5 },
      ].map(({ x, y, r }) => (
        <motion.path
          key={`${x}-${y}`}
          d={`M${x} ${y - r} L${x + r * 0.3} ${y - r * 0.3} L${x + r} ${y} L${x + r * 0.3} ${y + r * 0.3} L${x} ${y + r} L${x - r * 0.3} ${y + r * 0.3} L${x - r} ${y} L${x - r * 0.3} ${y - r * 0.3} Z`}
          fill="hsl(var(--card))"
          animate={reduced ? undefined : { opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2.4, repeat: Infinity, delay: x / 200 }}
        />
      ))}
    </svg>
  )
}

/** A folder with a plus badge and sparkles (the workspace picture). */
function FolderArt() {
  return (
    <svg viewBox="0 0 220 140" className="h-20 w-auto lg:h-24" aria-hidden="true">
      <ellipse cx="110" cy="124" rx="92" ry="12" fill="hsl(var(--primary) / 0.08)" />
      <path d="M62 34 h34 l10 12 h50 a10 10 0 0 1 10 10 v52 a10 10 0 0 1 -10 10 h-94 a10 10 0 0 1 -10 -10 v-64 a10 10 0 0 1 10 -10 z" fill="hsl(var(--primary))" />
      <path d="M52 58 h120 a8 8 0 0 1 8 9 l-6 42 a10 10 0 0 1 -10 9 h-104 a10 10 0 0 1 -10 -9 l-6 -42 a8 8 0 0 1 8 -9 z" fill="hsl(var(--primary) / 0.55)" />
      <path d="M52 58 h120 a8 8 0 0 1 8 9 l-6 42 a10 10 0 0 1 -10 9 h-104 a10 10 0 0 1 -10 -9 l-6 -42 a8 8 0 0 1 8 -9 z" fill="hsl(var(--card) / 0.55)" />
      <circle cx="166" cy="108" r="17" fill="hsl(var(--primary))" stroke="hsl(var(--card))" strokeWidth="4" />
      <path d="M166 100 v16 M158 108 h16" stroke="hsl(var(--primary-foreground))" strokeWidth="3" strokeLinecap="round" />
      <path d="M38 40 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 z" fill="hsl(var(--primary) / 0.5)" />
      <path d="M184 22 l2.5 6 6 2.5 -6 2.5 -2.5 6 -2.5 -6 -6 -2.5 6 -2.5 z" fill="hsl(var(--primary) / 0.45)" />
    </svg>
  )
}

/* ------------------------------------------------------------------------------------------------ pieces */

function StatCard({
  label,
  value,
  icon: Icon,
  to,
  tone,
}: {
  label: string
  value: number
  icon: LucideIcon
  to: string
  tone: 'primary' | 'warm' | 'green'
}) {
  const look = {
    primary: { card: 'from-primary/[0.06]', icon: 'bg-primary/10 text-primary' },
    warm: { card: 'from-warning/15', icon: 'bg-warning/20 text-warning-ink' },
    green: { card: 'from-success/10', icon: 'bg-success/15 text-success' },
  }[tone]
  return (
    <motion.div variants={staggerItem} whileHover={{ y: -3 }} transition={spring} className="h-full">
      <Link
        to={to}
        className={cn(
          'card-soft group relative flex h-full items-center gap-4 overflow-hidden border border-border/15 bg-gradient-to-br to-transparent px-4 py-3',
          look.card,
        )}
      >
        <span className={cn('flex size-12 shrink-0 items-center justify-center rounded-full', look.icon)}>
          <Icon className="size-6" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-display text-2xl font-bold tabular-nums leading-none">{value}</p>
          <p className="mt-1 text-sm text-muted-foreground">{label}</p>
        </div>
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-card text-primary shadow-sm transition-transform group-hover:translate-x-0.5">
          <ArrowRight className="size-4" aria-hidden="true" />
        </span>
        <svg viewBox="0 0 160 40" className="pointer-events-none absolute -bottom-1 right-0 h-8 w-40 opacity-50" aria-hidden="true">
          <path d="M0 36 C 40 30, 70 10, 110 18 S 150 12, 160 6 L160 40 L0 40 Z" className="fill-primary/10" />
        </svg>
      </Link>
    </motion.div>
  )
}

/* ------------------------------------------------------------------------------------------------ page */

export default function DashboardPage() {
  useDocumentTitle('Dashboard')
  const { data: projects, isLoading, isError, error, refetch } = useProjects()
  const user = useAuthStore((state) => state.user)

  const list = projects ?? []
  const awaiting = list.filter((project) => project.status === 'awaiting_review')
  const totalGaps = list.reduce((sum, project) => sum + project.gapCount, 0)
  const firstName = (user?.fullName ?? '').trim().split(/\s+/)[0]

  return (
    <div className="space-y-4">
      {/* hero */}
      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring}
        className="card-soft relative overflow-hidden border border-border/15 bg-gradient-to-br from-card via-card to-primary/15 px-5 py-5 sm:px-7"
      >
        <div className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-primary/10 blur-3xl" aria-hidden="true" />
        <div className="relative flex items-center gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
              {greeting()}
              {firstName ? `, ${firstName}` : ''}!
            </h1>
            <p className="mt-1 text-sm text-muted-foreground sm:text-base">
              Let&apos;s turn your competitors&apos; pages into clear insights.
            </p>
            <Link
              to="/app/projects/new"
              className="group mt-4 flex max-w-sm items-center gap-3 rounded-full border border-border/20 bg-card/90 p-1.5 pr-3 shadow-sm transition-all hover:border-primary/40 hover:shadow-glow"
            >
              <span className="flex size-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <ChevronRight className="size-4" aria-hidden="true" />
              </span>
              <span className="flex-1 text-sm text-muted-foreground">Start a new analysis…</span>
              <ArrowRight className="size-4 text-primary transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </Link>
          </div>
          <div className="hidden h-36 w-80 shrink-0 md:block">
            <InsightArt />
          </div>
        </div>
      </motion.section>

      {isError ? (
        <ErrorState
          message={errorMessage(error)}
          onRetry={() => {
            void refetch()
          }}
        />
      ) : isLoading ? (
        <LoadingCards count={3} />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
            {/* workspace */}
            <motion.section
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...spring, delay: 0.05 }}
              className="card-soft flex flex-col border border-border/15 p-4 sm:p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="flex size-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <Folder className="size-5" aria-hidden="true" />
                  </span>
                  <div>
                    <h2 className="font-display text-lg font-bold">Your workspace</h2>
                    <p className="text-sm text-muted-foreground">Your projects by platform</p>
                  </div>
                </div>
                <Link to="/app/projects" className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-primary hover:underline">
                  View all projects <ArrowRight className="size-4" />
                </Link>
              </div>
              {list.length > 0 ? (
                <div className="mt-3">
                  <PlatformLinks
                    groups={groupByPlatform(list).map((g) => ({
                      ...g,
                      count: g.projects.length,
                      note: g.projects.some((p) => p.status === 'awaiting_review')
                        ? `${g.projects.filter((p) => p.status === 'awaiting_review').length} awaiting you`
                        : undefined,
                    }))}
                  />
                </div>
              ) : null}
              <div className="flex flex-1 flex-col items-center justify-center gap-2 pt-3">
                <motion.div animate={{ y: [0, -4, 0] }} transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}>
                  <FolderArt />
                </motion.div>
                {list.length === 0 ? (
                  <Button asChild className="rounded-full">
                    <Link to="/app/projects/new">
                      <Plus /> Start your first analysis
                    </Link>
                  </Button>
                ) : (
                  <Button asChild className="rounded-full">
                    <Link to="/app/projects">
                      Explore projects <ArrowRight />
                    </Link>
                  </Button>
                )}
              </div>
            </motion.section>

            {/* numbers */}
            <motion.div variants={staggerContainer} initial="initial" animate="animate" className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 lg:grid-rows-3">
              <StatCard label="Total projects" value={list.length} icon={Folder} to="/app/projects" tone="primary" />
              <StatCard
                label="Awaiting you"
                value={awaiting.length}
                icon={Hourglass}
                to={awaiting[0] ? `/app/projects/${awaiting[0].id}/review-gaps` : '/app/projects'}
                tone="warm"
              />
              <StatCard label="Gaps found" value={totalGaps} icon={CircleCheck} to="/app/reports" tone="green" />
            </motion.div>
          </div>
        </>
      )}
    </div>
  )
}
