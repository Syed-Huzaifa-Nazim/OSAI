import { motion, useReducedMotion } from 'framer-motion'
import { Send } from 'lucide-react'

/** A paper plane in the middle with the platforms we compare floating around it (Contact page). */
const LOGOS = [
  { src: '/hero/instagram.png', name: 'Instagram', x: '12%', y: '18%', delay: 0 },
  { src: '/hero/daraz-mark.png', name: 'Daraz', x: '74%', y: '14%', delay: 0.8 },
  { src: '/hero/alibaba-mark.png', name: 'Alibaba', x: '70%', y: '68%', delay: 1.6 },
]

export function ContactVisual() {
  const reduce = useReducedMotion()
  return (
    <div className="relative h-44 overflow-hidden rounded-2xl bg-gradient-to-br from-primary/10 via-card to-warning/15" aria-hidden="true">
      <svg viewBox="0 0 300 170" className="absolute inset-0 size-full">
        <motion.path
          d="M20 150 C 90 120, 120 60, 150 85 S 230 40, 280 20"
          fill="none"
          className="stroke-primary/40"
          strokeWidth="2"
          strokeDasharray="6 6"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.6, ease: 'easeOut' }}
        />
      </svg>
      <motion.span
        className="absolute left-1/2 top-1/2 flex size-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-xl"
        animate={reduce ? undefined : { y: ['-50%', '-62%', '-50%'], rotate: [0, -6, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      >
        <Send className="size-7" />
      </motion.span>
      {LOGOS.map((logo) => (
        <motion.img
          key={logo.name}
          src={logo.src}
          alt=""
          className="absolute size-10 rounded-xl bg-card object-contain p-1.5 shadow-md"
          style={{ left: logo.x, top: logo.y }}
          animate={reduce ? undefined : { y: [0, -8, 0] }}
          transition={{ duration: 3.4, repeat: Infinity, ease: 'easeInOut', delay: logo.delay }}
        />
      ))}
    </div>
  )
}
