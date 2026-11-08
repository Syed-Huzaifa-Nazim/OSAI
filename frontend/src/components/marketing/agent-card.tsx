import type { LucideIcon } from 'lucide-react'
import { motion } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { staggerItem } from '@/lib/motion'

interface AgentCardProps {
  icon: LucideIcon
  eyebrow: string
  title: string
  description: string
  bullets: string[]
  accentClassName?: string
  /** Marks the two human checkpoints so they read differently from the agents. */
  human?: boolean
}

export function AgentCard({
  icon: Icon,
  eyebrow,
  title,
  description,
  bullets,
  accentClassName = 'text-primary',
  human = false,
}: AgentCardProps) {
  return (
    <motion.div variants={staggerItem} whileHover={{ y: -3 }} className="h-full">
      <Card
        glass
        className={cn('h-full p-6', human && 'border-brand-butter-cream/30')}
      >
        <div className="flex items-start justify-between gap-3">
          <span
            className={cn(
              'flex size-10 items-center justify-center rounded-full bg-muted/60',
              accentClassName,
            )}
          >
            <Icon className="size-5" />
          </span>
          {human ? <Badge variant="secondary">Human checkpoint</Badge> : null}
        </div>
        <p className="eyebrow mt-5">{eyebrow}</p>
        <h3 className="mt-1.5 font-display text-lg font-semibold">{title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        <ul className="mt-4 space-y-2">
          {bullets.map((bullet) => (
            <li key={bullet} className="flex gap-2 text-sm text-muted-foreground">
              <span className={cn('mt-1.5 size-1 shrink-0 rounded-full', human ? 'bg-brand-butter-cream' : 'bg-primary')} />
              {bullet}
            </li>
          ))}
        </ul>
      </Card>
    </motion.div>
  )
}
