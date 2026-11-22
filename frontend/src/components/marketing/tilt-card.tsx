import { useRef } from 'react'
import { motion, useMotionTemplate, useMotionValue, useReducedMotion, useSpring, useTransform } from 'framer-motion'
import { cn } from '@/lib/utils'

/**
 * A card that tilts towards the pointer in 3D, with a soft shine following it. Settles back flat when the
 * pointer leaves. Flat (no tilt) with reduced motion or on touch screens, where there is no hover.
 */
export function TiltCard({ children, className, max = 8 }: { children: React.ReactNode; className?: string; max?: number }) {
  const reduce = useReducedMotion()
  const ref = useRef<HTMLDivElement>(null)
  const px = useMotionValue(0.5)
  const py = useMotionValue(0.5)
  const rotateY = useSpring(useTransform(px, [0, 1], [-max, max]), { stiffness: 220, damping: 20 })
  const rotateX = useSpring(useTransform(py, [0, 1], [max, -max]), { stiffness: 220, damping: 20 })
  const shineX = useTransform(px, (v) => `${v * 100}%`)
  const shineY = useTransform(py, (v) => `${v * 100}%`)
  const shine = useMotionTemplate`radial-gradient(260px circle at ${shineX} ${shineY}, hsl(var(--primary) / 0.12), transparent 70%)`

  if (reduce) return <div className={cn('h-full', className)}>{children}</div>

  return (
    <motion.div
      ref={ref}
      className={cn('group relative h-full [transform-style:preserve-3d]', className)}
      style={{ rotateX, rotateY, transformPerspective: 900 }}
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 260, damping: 22 }}
      onPointerMove={(event) => {
        if (event.pointerType !== 'mouse') return
        const box = ref.current?.getBoundingClientRect()
        if (!box) return
        px.set((event.clientX - box.left) / box.width)
        py.set((event.clientY - box.top) / box.height)
      }}
      onPointerLeave={() => {
        px.set(0.5)
        py.set(0.5)
      }}
    >
      {children}
      <motion.span
        className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: shine }}
        aria-hidden="true"
      />
    </motion.div>
  )
}
