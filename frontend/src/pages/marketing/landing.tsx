import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Check,
  Smartphone,
  Database,
  FileDown,
  Globe,
  Store,
  Link2,
  ScanSearch,
  FileSearch,
  PlayCircle,
  Quote,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Section } from '@/components/marketing/section'
import { ComparisonTable } from '@/components/marketing/comparison-table'
import { AppPhones } from '@/components/marketing/app-phones'
import { FanCards } from '@/components/marketing/fan-cards'
import { ReportVisual } from '@/components/marketing/extra-visuals'
import { StepStory } from '@/components/marketing/step-story'
import { HeroShowcase } from '@/components/marketing/hero-showcase'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { spring, staggerContainer, staggerItem, revealOnScroll, viewportOnce } from '@/lib/motion'

/** Where a comparison can run: Instagram in full; Daraz and Alibaba listings compared; Facebook planned. */
const PLATFORMS: { name: string; logo?: string; soon?: boolean }[] = [
  { name: 'Instagram', logo: '/hero/instagram.png' },
  { name: 'Daraz', logo: '/hero/daraz-mark.png' },
  { name: 'Alibaba', logo: '/hero/alibaba-mark.png' },
  { name: 'Facebook', logo: '/hero/facebook.png', soon: true },
]

const PROBLEMS = [
  {
    icon: Database,
    title: 'The data is there. The meaning is not.',
    body: 'SMEs can see everything their competitors publish. Turning that unstructured sprawl into a decision is the part nobody has solved.',
  },
  {
    icon: FileSearch,
    title: 'Existing tools do not actually compare',
    body: 'Scheduling suites report on your own posts. Trend tools report on the category. Neither puts you side by side with the people you are losing to.',
  },
  {
    icon: Quote,
    title: 'Generic advice is worse than none',
    body: 'Most AI marketing tools produce suggestions that would fit any business, which means they fit none, and offer no way to check whether they are true.',
  },
]

export default function LandingPage() {
  useDocumentTitle('OptiStratixAI')

  return (
    <>
      {/* ------------------------------------------------------------ hero */}
      <section className="relative overflow-hidden pb-8 pt-10 sm:pb-10 sm:pt-14">
        <div
          className="pointer-events-none absolute -right-40 -top-40 size-[36rem] rounded-full bg-primary/15 blur-3xl"
          aria-hidden="true"
        />
        <div className="container grid items-center gap-12 lg:grid-cols-[1.05fr_1fr]">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={spring}>
            <span className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              <Store className="size-3.5" aria-hidden="true" /> For small online sellers
            </span>
            <h1 className="mt-5 font-display text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              Outsmart your competitors, <span className="text-primary">wherever you sell</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
              Compare your Instagram or your Daraz and Alibaba listings with a competitor&rsquo;s. See
              what is working for them, find the gaps in your own, and turn them into a plan and content, with every
              finding backed by real data.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link to="/signup">
                  Start analyzing
                  <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/how-it-works">
                  <PlayCircle />
                  See how it works
                </Link>
              </Button>
            </div>
            <ul className="mt-6 flex flex-wrap items-center gap-2" aria-label="Where you can compare">
              {PLATFORMS.map((platform) => (
                <li
                  key={platform.name}
                  className="inline-flex items-center gap-1.5 rounded-full border border-border/20 bg-card px-2.5 py-1 text-xs font-medium shadow-sm"
                >
                  {platform.logo ? (
                    <img src={platform.logo} alt="" className="size-4 object-contain" />
                  ) : (
                    <Globe className="size-4 text-primary" aria-hidden="true" />
                  )}
                  {platform.name}
                  {platform.soon ? <span className="text-muted-foreground">· Soon</span> : null}
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm text-muted-foreground">
              You decide what matters: every gap is yours to keep or drop.
            </p>
          </motion.div>

          <HeroShowcase />
        </div>

        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="container mt-10"
        >
          <div className="card-soft grid gap-6 border border-border/15 p-6 sm:p-8 md:grid-cols-[1.2fr_repeat(3,1fr)] md:items-center">
            <div>
              <p className="font-display text-xl font-bold">Analyze. Review. Grow.</p>
              <p className="mt-1 text-sm text-muted-foreground">Your competitor analysis partner for online shops.</p>
            </div>
            {[
              { icon: Link2, text: 'Add your link and your competitor\'s link' },
              { icon: ScanSearch, text: 'We compare both and find what works for them' },
              { icon: FileDown, text: 'Keep what matters and download the report' },
            ].map((step) => (
              <motion.div key={step.text} variants={staggerItem} className="flex items-center gap-3 md:flex-col md:text-center">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <step.icon className="size-5" aria-hidden="true" />
                </span>
                <span className="text-sm font-medium">{step.text}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* --------------------------------------------------------- problem */}
      <Section
        tinted
        eyebrow="The problem"
        title="Nobody is short of competitor data"
        description="What is missing is the step between having it and knowing what to do about it."
      >
        <FanCards items={PROBLEMS} label="Three problems small sellers face" />
      </Section>

      {/* ------------------------------------------------------ how it works */}
      <Section
        eyebrow="How it works"
        title="Six steps. Two of them are yours."
        description="Scroll through them. The system reads and compares; you decide which gaps matter and which plan goes ahead. Steps 4 to 6 are being built."
      >
        <StepStory />

        <motion.div
          variants={revealOnScroll}
          initial="initial"
          whileInView="whileInView"
          viewport={viewportOnce}
          className="mt-10"
        >
          <Button asChild variant="outline">
            <Link to="/how-it-works">
              Walk through all six steps
              <ArrowRight />
            </Link>
          </Button>
        </motion.div>
      </Section>

      {/* ---------------------------------------------------------- phone app */}
      <Section tinted>
        <div className="grid items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <motion.div variants={revealOnScroll} initial="initial" whileInView="whileInView" viewport={viewportOnce}>
            <span className="inline-flex items-center gap-2 rounded-full bg-warning/20 px-3 py-1 text-xs font-semibold text-warning-ink">
              <Smartphone className="size-3.5" aria-hidden="true" /> Phone app · coming soon
            </span>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              Your competitor check, <span className="text-primary">in your pocket</span>
            </h2>
            <p className="mt-4 text-base leading-relaxed text-muted-foreground">
              A phone app is planned: see new gaps as they are found, keep or drop them with a tap, and read why each
              one matters, wherever you are.
            </p>
            <ul className="mt-5 space-y-2.5 text-sm">
              {['Your dashboard at a glance', 'Review gaps with one tap', 'Explanations with the real posts behind them'].map((line) => (
                <li key={line} className="flex items-center gap-2.5">
                  <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Check className="size-3" strokeWidth={3} aria-hidden="true" />
                  </span>
                  {line}
                </li>
              ))}
            </ul>
            <p className="mt-5 text-xs text-muted-foreground">Screens shown are a preview with example content.</p>
          </motion.div>
          <AppPhones />
        </div>
      </Section>

      {/* ------------------------------------------------------ comparison */}
      <Section
        tinted
        eyebrow="Where the gap is"
        title="Against the tools you are already paying for"
        description="Hootsuite schedules. BuzzSumo surfaces trends. Neither closes the loop between what a competitor is doing and what you should do about it."
      >
        <ComparisonTable />
      </Section>

      {/* -------------------------------------------------------------- CTA */}
      <Section>
        <motion.div
          variants={revealOnScroll}
          initial="initial"
          whileInView="whileInView"
          viewport={viewportOnce}
        >
          <Card glass className="overflow-hidden p-8 sm:p-12">
            <div className="grid items-center gap-10 lg:grid-cols-2">
              <div className="text-center lg:text-left">
                <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Run your first analysis</h2>
                <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-muted-foreground lg:mx-0">
                  Add your page and a competitor&rsquo;s. The Scout Engine reads both, the Gap Engine finds what works
                  for them that you are not doing yet, and then it stops and waits for you to decide.
                </p>
                <div className="mt-8 flex flex-wrap justify-center gap-3 lg:justify-start">
                  <Button asChild size="lg">
                    <Link to="/signup">
                      Create an account
                      <ArrowRight />
                    </Link>
                  </Button>
                  <Button asChild size="lg" variant="outline">
                    <Link to="/about">Read the project story</Link>
                  </Button>
                </div>
              </div>
              <ReportVisual />
            </div>
          </Card>
        </motion.div>
      </Section>
    </>
  )
}
