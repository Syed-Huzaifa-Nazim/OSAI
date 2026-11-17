import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion, useScroll, useSpring, useTransform } from 'framer-motion'
import {
  ArrowRight,
  ArrowDown,
  Check,
  Database,
  FileSearch,
  Lightbulb,
  PlayCircle,
  Quote,
  Sparkles,
  ShieldCheck,
  Swords,
  UserRoundCheck,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Section } from '@/components/marketing/section'
import { PipelineTeaser } from '@/components/marketing/pipeline-teaser'
import { ComparisonTable } from '@/components/marketing/comparison-table'
import { AgentCard } from '@/components/marketing/agent-card'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { spring, staggerContainer, staggerItem, revealOnScroll, viewportOnce } from '@/lib/motion'

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
  const heroRef = useRef<HTMLElement>(null)
  const reducedMotion = useReducedMotion()
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const artY = useSpring(useTransform(scrollYProgress, [0, 1], [0, 130]), {
    stiffness: 90,
    damping: 24,
  })
  const artRotate = useSpring(useTransform(scrollYProgress, [0, 1], [0, 9]), {
    stiffness: 80,
    damping: 25,
  })
  const artScale = useTransform(scrollYProgress, [0, 0.85], [1, 0.84])

  return (
    <>
      {/* ------------------------------------------------------------ hero */}
      <section ref={heroRef} className="marketing-hero relative isolate overflow-hidden pb-14 pt-10 sm:pb-20 sm:pt-16">
        <div aria-hidden="true" className="marketing-hero__glow" />
        <div className="container relative grid min-h-[560px] items-center gap-8 lg:grid-cols-[minmax(0,1.03fr)_minmax(360px,0.97fr)] lg:gap-3">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="relative z-10 max-w-3xl py-8 lg:py-12"
          >
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-white/70 px-3.5 py-2 text-xs font-medium text-foreground shadow-sm backdrop-blur">
              <Sparkles className="size-3.5 text-primary" />
              Competitor research, turned into a clear next step
            </div>
            <h1 className="max-w-[720px] font-display text-[2.7rem] font-semibold leading-[1.02] tracking-[-0.055em] sm:text-6xl lg:text-[4.65rem]">
              Know what your competitors are doing.
              <span className="mt-2 block text-primary">Know what to do next.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
              See the evidence behind every insight, choose the gaps that matter, and leave with a
              practical strategy your team can act on. You stay in control at every important step.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Button asChild size="lg" className="rounded-full px-6 shadow-lg shadow-primary/20">
                <Link to="/signup">
                  Start an analysis
                  <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="rounded-full border-foreground/15 bg-white/70 px-6">
                <Link to="/how-it-works">
                  <PlayCircle />
                  See how it works
                </Link>
              </Button>
            </div>
            <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium text-muted-foreground">
              <span className="inline-flex items-center gap-1.5"><Check className="size-3.5 text-primary" /> Sources attached to findings</span>
              <span className="inline-flex items-center gap-1.5"><Check className="size-3.5 text-primary" /> You approve the strategy</span>
            </div>
          </motion.div>

          <div className="relative mx-auto flex min-h-[360px] w-full max-w-[560px] items-center justify-center sm:min-h-[470px] lg:mx-0">
            <div aria-hidden="true" className="absolute inset-[9%] rounded-full bg-primary/10 blur-3xl" />
            <motion.div
              initial={{ opacity: 0, y: 46, scale: 0.88, rotate: -8 }}
              whileInView={{ opacity: 1, y: 0, scale: 1, rotate: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ ...spring, delay: 0.12 }}
              style={reducedMotion ? undefined : { y: artY, rotate: artRotate, scale: artScale }}
              className="relative z-10 w-full"
            >
              <img
                src="/images/emerald-strategy-3d.png"
                alt="Sculptural emerald ribbons and a warm amber crystal, representing evidence becoming a strategy"
                className="relative z-10 mx-auto w-full max-w-[520px] drop-shadow-[0_28px_45px_rgba(8,28,21,0.16)]"
                fetchPriority="high"
              />
              <div className="pointer-events-none absolute inset-x-[12%] bottom-[6%] h-[12%] rounded-[50%] bg-primary/20 blur-2xl" />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20, y: 12 }}
              whileInView={{ opacity: 1, x: 0, y: 0 }}
              viewport={{ once: true }}
              transition={{ ...spring, delay: 0.42 }}
              className="absolute bottom-[8%] right-0 z-20 w-[min(235px,55%)] rounded-2xl border border-white/70 bg-white/85 p-4 shadow-xl shadow-emerald-950/10 backdrop-blur-xl sm:bottom-[10%] sm:right-[2%]"
            >
              <div className="flex items-center justify-between gap-2 text-xs font-semibold">
                <span>From evidence to action</span><span className="size-2 rounded-full bg-primary" />
              </div>
              <div className="mt-3 flex items-end gap-1.5" aria-hidden="true">
                {[34, 52, 44, 70, 58, 88, 76, 100].map((height, index) => (
                  <span key={index} className="flex-1 rounded-t-sm bg-gradient-to-t from-primary/35 to-primary" style={{ height: `${height * 0.28}px` }} />
                ))}
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground">A clearer view of your next move</p>
            </motion.div>

            <span className="absolute left-[3%] top-[20%] hidden rounded-full border border-primary/15 bg-white/70 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.18em] text-primary shadow-sm sm:block">Evidence → insight</span>
            <span className="absolute right-[4%] top-[12%] hidden rounded-full border border-amber-500/20 bg-amber-50/90 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.18em] text-amber-800 shadow-sm sm:block">Insight → strategy</span>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring, delay: 0.15 }}
          className="container relative mt-8 sm:mt-12"
        >
          <div className="mb-4 flex items-center gap-3">
            <p className="eyebrow">A clear path from research to a decision</p>
            <ArrowDown className="size-3.5 text-primary" />
          </div>
          <PipelineTeaser />
        </motion.div>
      </section>

      {/* --------------------------------------------------------- problem */}
      <Section
        tinted
        eyebrow="The problem"
        title="Nobody is short of competitor data"
        description="OptiStratixAI makes that step easier to see: real competitor evidence, useful comparisons, and a plan shaped around your business."
      >
        <motion.div
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={viewportOnce}
          className="grid gap-5 md:grid-cols-3"
        >
          {PROBLEMS.map((problem) => (
            <motion.div key={problem.title} variants={staggerItem}>
              <Card className="h-full p-6">
                <span className="flex size-10 items-center justify-center rounded-full bg-primary/12 text-primary">
                  <problem.icon className="size-5" />
                </span>
                <h3 className="mt-5 font-display text-base font-semibold">{problem.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {problem.body}
                </p>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </Section>

      {/* ------------------------------------------------------ how it works */}
      <Section
        eyebrow="How it works"
        title="Nine stages. Two of them are yours."
        description="Four agents do the reading and the reasoning. You decide what matters and what ships."
      >
        <motion.div
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={viewportOnce}
          className="grid gap-5 md:grid-cols-2 lg:grid-cols-3"
        >
          <AgentCard
            icon={Database}
            eyebrow="Stages 2-3"
            title="Scout Agent"
            description="Collects competitor and market data from the web, social platforms, reviews, forums and news, then cleans, chunks and embeds it into a vector store scoped to your project."
            bullets={[
              'Landing pages and social posts',
              'Customer reviews and forum threads',
              'Retrievable corpus, not a scraped dump',
            ]}
            accentClassName="text-stage-2"
          />
          <AgentCard
            icon={Lightbulb}
            eyebrow="Stage 4"
            title="Insight Agent"
            description="Compares your brand against that corpus to identify gaps, opportunities and competitive trends, each scored for confidence and attached to the passage it came from."
            bullets={[
              'Gaps grouped by category',
              'Confidence scored, not asserted',
              'Every finding cites its source',
            ]}
            accentClassName="text-stage-4"
          />
          <AgentCard
            icon={UserRoundCheck}
            eyebrow="Stage 5"
            title="You review the gaps"
            description="Nothing is written until you have been through the list. Keep what fits the business, drop what does not, and reprioritise anything the agent misjudged."
            bullets={[
              'Accept, reject or reprioritise',
              'Leave a note the Strategist reads',
              'Your decisions are logged',
            ]}
            human
            accentClassName="text-stage-5"
          />
          <AgentCard
            icon={Swords}
            eyebrow="Stage 6"
            title="Strategist + Critic"
            description="The Strategist drafts initiatives against the gaps you kept. The Critic then challenges that draft for strength, clarity, feasibility and evidence, and you see exactly what it changed."
            bullets={[
              'Adversarial second pass',
              'Unsupported claims removed',
              'Before and after both visible',
            ]}
            accentClassName="text-stage-6"
          />
          <AgentCard
            icon={ShieldCheck}
            eyebrow="Stage 7"
            title="You approve the strategy"
            description="The final gate. Approve it for execution, or send it back with notes and let the two agents produce another version."
            bullets={[
              'Approve, reject or request revision',
              'Critic annotations shown inline',
              'Revisions are versioned',
            ]}
            human
            accentClassName="text-stage-7"
          />
          <AgentCard
            icon={FileSearch}
            eyebrow="Stages 8-9"
            title="Document and follow-through"
            description="An approved strategy becomes a full document with an implementation plan, then a set of content assets (blogs, SEO briefs, social and ads), mapped to the initiatives you signed off."
            bullets={[
              'Exportable strategy document',
              'Step-by-step action plan',
              'Content assets per initiative',
            ]}
            accentClassName="text-stage-8"
          />
        </motion.div>

        <motion.div
          variants={revealOnScroll}
          initial="initial"
          whileInView="whileInView"
          viewport={viewportOnce}
          className="mt-10"
        >
          <Button asChild variant="outline">
            <Link to="/how-it-works">
              Walk through all nine stages
              <ArrowRight />
            </Link>
          </Button>
        </motion.div>
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
          <Card glass className="overflow-hidden p-10 text-center sm:p-14">
            <h2 className="mx-auto max-w-2xl font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              Run your first analysis
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-muted-foreground">
              Add your brand and the competitors you care about. The Scout Agent takes it from
              there, and stops at the first checkpoint to hear from you.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
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
          </Card>
        </motion.div>
      </Section>
    </>
  )
}
