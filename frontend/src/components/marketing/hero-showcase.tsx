import { motion, useMotionValue, useSpring, useTransform, type MotionValue } from 'framer-motion'
import { Heart, Lightbulb, MessageCircle, Rocket, Send, Sparkle, TrendingUp } from 'lucide-react'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { spring } from '@/lib/motion'

/*
 * The landing hero's picture: a shop's post in a tilted 3D window, the platforms the project reads floating around
 * it, and what the tool does on cards beside it. Moving the mouse over it shifts each layer by a different amount
 * (parallax). The logos and the photo are files in public/hero/.
 */
const PLATFORMS: {
  name: string
  /** A full app icon is shown as it is; a bare symbol sits on a white tile. */
  src: string
  tile: 'icon' | 'mark'
  place: string
  size: string
  angle: number
  drift: number
  seconds: number
  depth: number
}[] = [
  { name: 'Instagram', src: '/hero/instagram.png', tile: 'icon', place: 'left-[30%] -top-[4%]', size: 'size-20 sm:size-28', angle: -9, drift: -10, seconds: 5.5, depth: 34 },
  { name: 'Facebook (planned)', src: '/hero/facebook.png', tile: 'icon', place: 'left-[2%] top-[30%]', size: 'size-[4.5rem] sm:size-24', angle: -10, drift: 9, seconds: 6.2, depth: 28 },
  { name: 'Daraz', src: '/hero/daraz-mark.png', tile: 'mark', place: 'left-[0%] top-[62%]', size: 'size-16 sm:size-[5.5rem]', angle: -12, drift: -8, seconds: 5.8, depth: 24 },
  { name: 'Alibaba', src: '/hero/alibaba-mark.png', tile: 'mark', place: 'left-[22%] top-[82%]', size: 'size-14 sm:size-[4.5rem]', angle: 8, drift: 7, seconds: 4.9, depth: 30 },
]

const FEATURES = [
  {
    lines: ['Find what', 'works'],
    icon: <TrendingUp className="size-5 text-white" strokeWidth={2.5} />,
    tone: 'from-primary to-primary/60',
    place: 'right-[0%] top-[22%]',
  },
  {
    lines: ['Get smart', 'suggestions'],
    icon: <Lightbulb className="size-5 text-warning-foreground" strokeWidth={2.5} />,
    tone: 'from-warning to-warning/60',
    place: 'right-[6%] top-[45%]',
  },
  {
    lines: ['Create winning', 'content'],
    icon: <Rocket className="size-5 text-white" strokeWidth={2.5} />,
    tone: 'from-primary/90 to-primary/50',
    place: 'right-[-2%] top-[68%]',
  },
]

/** How the shop window leans (as in the design): right side nearer, top rising to the right, left edge slanted. */
const TILT = { perspective: 900, rotateY: -26, rotateX: 4, rotateZ: 3, skewX: -7 }

/** A layer that shifts with the mouse: deeper layers move more. */
function useLayer(x: MotionValue<number>, y: MotionValue<number>, depth: number) {
  return {
    x: useTransform(x, (v) => v * depth),
    y: useTransform(y, (v) => v * depth),
  }
}

export function HeroShowcase() {
  const reduced = usePrefersReducedMotion()
  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const mx = useSpring(rawX, { stiffness: 120, damping: 18 })
  const my = useSpring(rawY, { stiffness: 120, damping: 18 })
  const windowLayer = useLayer(mx, my, 14)
  const cardLayer = useLayer(mx, my, 22)
  const tiltY = useTransform(mx, (v) => TILT.rotateY + v * 8)
  const tiltX = useTransform(my, (v) => TILT.rotateX - v * 6)
  // one layer per logo, in a fixed order (hooks cannot run in a loop)
  const logoLayers = [
    useLayer(mx, my, PLATFORMS[0]?.depth ?? 0),
    useLayer(mx, my, PLATFORMS[1]?.depth ?? 0),
    useLayer(mx, my, PLATFORMS[2]?.depth ?? 0),
    useLayer(mx, my, PLATFORMS[3]?.depth ?? 0),
  ]

  const onMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (reduced) return
    const box = event.currentTarget.getBoundingClientRect()
    rawX.set((event.clientX - box.left) / box.width - 0.5)
    rawY.set((event.clientY - box.top) / box.height - 0.5)
  }
  const onLeave = () => {
    rawX.set(0)
    rawY.set(0)
  }

  return (
    <div
      className="relative mx-auto aspect-[1/1.02] w-full max-w-[36rem]"
      style={{ perspective: 1200 }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      aria-hidden="true"
    >
      <div className="absolute inset-[8%] rounded-full bg-primary/25 blur-3xl" />

      {/* the shop's post: a tilted 3D window with two cards stacked behind it */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring, delay: 0.1 }}
        className="absolute left-[17%] top-[11%] w-[62%]"
        style={reduced ? undefined : { x: windowLayer.x, y: windowLayer.y }}
      >
        <motion.div
          style={{
            transformPerspective: TILT.perspective,
            rotateY: reduced ? TILT.rotateY : tiltY,
            rotateX: reduced ? TILT.rotateX : tiltX,
            rotateZ: TILT.rotateZ,
            skewX: TILT.skewX,
          }}
          className="relative"
        >
          <div className="absolute -right-[6%] -top-[3%] bottom-[4%] left-[8%] rounded-2xl border border-border/15 bg-card/70 shadow-lg" />
          <div className="relative overflow-hidden rounded-2xl border border-white/60 bg-card shadow-[0_30px_60px_-20px_hsl(var(--shadow-color)/0.55)]">
            <div className="flex items-center gap-2 px-3 py-2.5">
              <span className="size-5 rounded-full bg-gradient-to-br from-primary to-primary/50" />
              <span className="h-2 w-16 rounded-full bg-muted" />
              <span className="ml-auto h-2 w-6 rounded-full bg-muted" />
            </div>
            <div className="aspect-[4/3.4] bg-secondary">
              <img src="/hero/product.jpg" alt="" className="size-full object-cover" loading="eager" draggable={false} />
            </div>
            <div className="flex items-center gap-2.5 px-3 py-2.5">
              <Heart className="size-5 fill-destructive/80 text-destructive/80" />
              <MessageCircle className="size-5 text-muted-foreground" />
              <Send className="size-5 text-muted-foreground" />
              <span className="ml-auto h-2 w-10 rounded-full bg-muted" />
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* the sweeping arrow, drawn in once */}
      <svg viewBox="0 0 400 400" className="pointer-events-none absolute inset-0 z-10 h-full w-full overflow-visible" role="presentation">
        <defs>
          <linearGradient id="hero-arrow" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.2" />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.95" />
          </linearGradient>
        </defs>
        <motion.path
          d="M40 355 C 130 400, 215 370, 238 305"
          fill="none"
          stroke="url(#hero-arrow)"
          strokeWidth="11"
          strokeLinecap="round"
          initial={{ pathLength: reduced ? 1 : 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.4, delay: 0.7, ease: 'easeInOut' }}
        />
        <motion.path
          d="M221 319 L238 305 L242 327"
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="11"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.95 }}
          transition={{ delay: 2.0 }}
        />
      </svg>

      {/* what the tool does, stacked beside the window */}
      {FEATURES.map((feature, index) => (
        <motion.div key={feature.lines.join(' ')} className={`absolute z-20 ${feature.place}`} style={reduced ? undefined : cardLayer}>
          <motion.div
            initial={{ opacity: 0, x: 30, scale: 0.9 }}
            animate={reduced ? { opacity: 1, x: 0, scale: 1 } : { opacity: 1, x: 0, scale: 1, y: [0, index % 2 ? 7 : -7, 0] }}
            transition={
              reduced
                ? { delay: 0.5 + index * 0.15 }
                : {
                    opacity: { delay: 0.5 + index * 0.15 },
                    x: { ...spring, delay: 0.5 + index * 0.15 },
                    scale: { ...spring, delay: 0.5 + index * 0.15 },
                    y: { duration: 5 + index, repeat: Infinity, ease: 'easeInOut', delay: 1.3 },
                  }
            }
            whileHover={{ scale: 1.05 }}
            className="flex items-center gap-3 rounded-2xl border border-white/70 bg-card/95 px-3.5 py-3 shadow-[0_18px_40px_-16px_hsl(var(--shadow-color)/0.45)] backdrop-blur sm:gap-3.5 sm:px-4 sm:py-3.5"
          >
            <span
              className={`flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br shadow-md sm:size-11 ${feature.tone}`}
            >
              {feature.icon}
            </span>
            <span className="text-xs font-semibold leading-tight sm:text-sm">
              {feature.lines[0]}
              <br />
              {feature.lines[1]}
            </span>
          </motion.div>
        </motion.div>
      ))}

      {/* the platforms, each floating on its own and at its own depth */}
      {PLATFORMS.map((platform, index) => (
        <motion.div
          key={platform.name}
          className={`absolute z-20 ${platform.place}`}
          style={reduced ? { rotate: platform.angle } : { rotate: platform.angle, ...logoLayers[index] }}
        >
          <motion.div
            animate={reduced ? undefined : { y: [0, platform.drift, 0], rotate: [0, platform.angle > 0 ? -5 : 5, 0] }}
            transition={{ duration: platform.seconds, repeat: Infinity, ease: 'easeInOut', delay: index * 0.3 }}
          >
            <motion.span
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 260, damping: 13, delay: 0.35 + index * 0.13 }}
              whileHover={{ scale: 1.18 }}
              title={platform.name}
              className={`flex ${platform.size} items-center justify-center overflow-hidden rounded-[24%] shadow-[0_18px_36px_-12px_rgba(40,20,90,0.55)] ${
                platform.tile === 'mark' ? 'bg-white p-[17%]' : ''
              }`}
            >
              <img src={platform.src} alt="" className="size-full object-contain" draggable={false} />
            </motion.span>
          </motion.div>
        </motion.div>
      ))}

      {/* twinkling sparkles */}
      {[
        { left: '18%', top: '6%', delay: 0, size: 'size-5' },
        { left: '62%', top: '2%', delay: 1.4, size: 'size-4' },
        { left: '94%', top: '88%', delay: 1.1, size: 'size-5' },
        { left: '8%', top: '20%', delay: 2.2, size: 'size-3.5' },
        { left: '70%', top: '94%', delay: 0.6, size: 'size-4' },
      ].map((spot) => (
        <motion.span
          key={spot.left + spot.top}
          className="absolute text-primary/70"
          style={{ left: spot.left, top: spot.top }}
          animate={reduced ? undefined : { opacity: [0.2, 1, 0.2], scale: [0.7, 1.25, 0.7], rotate: [0, 45, 0] }}
          transition={{ duration: 3.2, repeat: Infinity, delay: spot.delay }}
        >
          <Sparkle className={`${spot.size} fill-primary/40`} />
        </motion.span>
      ))}
    </div>
  )
}
