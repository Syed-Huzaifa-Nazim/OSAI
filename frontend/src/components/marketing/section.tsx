import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { revealOnScroll, viewportOnce } from '@/lib/motion'

interface SectionProps {
  eyebrow?: string
  title?: string
  description?: string
  children?: ReactNode
  className?: string
  /** Tints the band so long pages have rhythm rather than one flat scroll. */
  tinted?: boolean
  align?: 'left' | 'center'
}

export function Section({
  eyebrow,
  title,
  description,
  children,
  className,
  tinted = false,
  align = 'left',
}: SectionProps) {
  return (
    <section className={cn('py-10 sm:py-14', tinted && 'bg-card/30', className)}>
      <div className="container">
        {eyebrow || title || description ? (
          <motion.div
            variants={revealOnScroll}
            initial="initial"
            whileInView="whileInView"
            viewport={viewportOnce}
            className={cn(
              'mb-8 max-w-2xl space-y-3',
              align === 'center' && 'mx-auto text-center',
            )}
          >
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? (
              <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
                {title}
              </h2>
            ) : null}
            {description ? (
              <p className="text-base leading-relaxed text-muted-foreground">{description}</p>
            ) : null}
          </motion.div>
        ) : null}
        {children}
      </div>
    </section>
  )
}
