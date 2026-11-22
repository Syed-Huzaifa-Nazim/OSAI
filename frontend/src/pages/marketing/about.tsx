import { motion } from 'framer-motion'
import { Database, GraduationCap, Quote, Scale, ShieldQuestion } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Section } from '@/components/marketing/section'
import { FanCards, type FanItem } from '@/components/marketing/fan-cards'
import { TiltCard } from '@/components/marketing/tilt-card'
import { LoopVisual, PlatformsVisual, RagVisual } from '@/components/marketing/extra-visuals'
import { ExplainVisual } from '@/components/marketing/feature-visuals'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { cn, initials } from '@/lib/utils'
import { revealOnScroll, spring, staggerContainer, staggerItem, viewportOnce } from '@/lib/motion'

const TEAM = [
  { name: 'Hadia', roll: '23-AI-01' },
  { name: 'Syed Huzaifa Nazim', roll: '23-AI-23' },
  { name: 'Muhammad Waqas Ali', roll: '23-AI-59' },
  { name: 'Muhammad Umar Khan', roll: '23-AI-71' },
]

/** Colours for the team cards' header strip and avatar. */
const TEAM_TONES = ['from-primary to-blush', 'from-warning to-blush', 'from-primary to-warning', 'from-blush to-primary']

const OBJECTIVES = [
  {
    title: 'RAG pipeline',
    visual: RagVisual,
    body: 'Implement a multi-agent retrieval-augmented-generation pipeline that extracts, processes and analyses real-world competitor data rather than reasoning from a model’s priors.',
  },
  {
    title: 'Multi-platform analysis',
    visual: PlatformsVisual,
    body: 'Compare a business with its competitor where it actually sells: Instagram today, and Daraz and Alibaba product listings. Facebook is planned.',
  },
  {
    title: 'Human-in-the-loop',
    visual: LoopVisual,
    body: 'Let users validate and refine AI-generated insights through explicit evaluation and approval steps, rather than accepting model output on trust.',
  },
]

const PROBLEMS: FanItem[] = [
  {
    icon: Database,
    title: 'Plenty of data, hard to read',
    body: 'SMEs have access to large amounts of competitor data, but it is unstructured and hard to interpret.',
  },
  {
    icon: Scale,
    title: 'No real side-by-side comparison',
    body: 'Existing tools do not perform true comparative analysis between a business and its competitors.',
  },
  {
    icon: Quote,
    title: 'Advice that fits nobody',
    body: 'Most AI tools generate generic, non-contextual suggestions that do not fit the specific business.',
  },
  {
    icon: ShieldQuestion,
    title: 'Hard to trust',
    body: 'Existing systems lack evidence-based reasoning, so their outputs are hard to trust or validate.',
  },
]

export default function AboutPage() {
  useDocumentTitle('About')

  return (
    <>
      <section className="pb-0 pt-10 sm:pt-14">
        <div className="container grid items-center gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="max-w-3xl"
          >
            <p className="eyebrow">About the project</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              Built as a Final Year Project, designed as a product
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-muted-foreground">
              OptiStratixAI is a human-in-the-loop multi-agentic RAG system for digital marketing
              strategy, developed at the Department of Artificial Intelligence, Dawood University of
              Engineering &amp; Technology.
            </p>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: 30, rotate: 3 }} animate={{ opacity: 1, x: 0, rotate: 0 }} transition={{ ...spring, delay: 0.15 }}>
            <ExplainVisual />
          </motion.div>
        </div>
      </section>

      <Section
        eyebrow="The problem"
        title="Why this project exists"
        description="Four observations that the system is a direct response to."
      >
        <FanCards items={PROBLEMS} label="Why this project exists" />
      </Section>

      <Section
        tinted
        eyebrow="Objectives"
        title="What the system set out to do"
      >
        <motion.div
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={viewportOnce}
          className="grid gap-5 md:grid-cols-3"
        >
          {OBJECTIVES.map((objective, index) => (
            <motion.div key={objective.title} variants={staggerItem}>
              <TiltCard>
              <Card glass className="h-full p-6">
                <objective.visual />
                <p className="eyebrow mt-5">Objective {index + 1}</p>
                <h3 className="mt-1.5 font-display text-lg font-semibold">{objective.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {objective.body}
                </p>
              </Card>
              </TiltCard>
            </motion.div>
          ))}
        </motion.div>
      </Section>

      <Section eyebrow="The team" title="Who built it">
        <motion.div
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={viewportOnce}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {TEAM.map((member, index) => (
            <motion.div key={member.roll} variants={staggerItem}>
              <TiltCard max={10}>
              <Card className="group relative h-full overflow-hidden p-6 text-center">
                <span className={cn('absolute inset-x-0 top-0 h-16 bg-gradient-to-r opacity-60 transition-opacity group-hover:opacity-100', TEAM_TONES[index % TEAM_TONES.length])} aria-hidden="true" />
                <motion.span
                  whileHover={{ rotate: 8, scale: 1.08 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 14 }}
                  className="relative mx-auto mt-4 flex size-16 items-center justify-center rounded-full bg-card shadow-lg ring-4 ring-card"
                >
                  <span className={cn('flex size-full items-center justify-center rounded-full bg-gradient-to-br font-display text-lg font-extrabold text-primary-foreground', TEAM_TONES[index % TEAM_TONES.length])}>
                    {initials(member.name)}
                  </span>
                </motion.span>
                <h3 className="mt-4 font-display text-base font-semibold">{member.name}</h3>
                <p className="mt-1 font-mono text-xs text-muted-foreground">{member.roll}</p>
              </Card>
              </TiltCard>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          variants={revealOnScroll}
          initial="initial"
          whileInView="whileInView"
          viewport={viewportOnce}
          className="mt-6"
        >
          <Card glass className="flex flex-wrap items-center gap-5 p-6">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary/12 text-primary">
              <GraduationCap className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-display text-base font-semibold">
                  Ms. Noor Ul Huda Soomro
                </h3>
                <Badge variant="outline">Supervisor</Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Lecturer, Department of Artificial Intelligence
              </p>
            </div>
          </Card>
        </motion.div>
      </Section>

      <Section tinted>
        <motion.div
          variants={revealOnScroll}
          initial="initial"
          whileInView="whileInView"
          viewport={viewportOnce}
        >
          <Card className="p-8 text-center sm:p-10">
            <p className="eyebrow">Affiliation</p>
            <h2 className="mt-3 font-display text-xl font-semibold sm:text-2xl">
              Dawood University of Engineering &amp; Technology
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Faculty of Information &amp; Computing Sciences · Department of Artificial Intelligence
            </p>
          </Card>
        </motion.div>
      </Section>
    </>
  )
}
