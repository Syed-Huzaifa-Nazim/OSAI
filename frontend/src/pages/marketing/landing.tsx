import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Database,
  FileSearch,
  Lightbulb,
  PlayCircle,
  Quote,
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

  return (
    <>
      {/* ------------------------------------------------------------ hero */}
      <section className="relative overflow-hidden pb-16 pt-16 sm:pb-24 sm:pt-24">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="max-w-3xl"
          >
            <h1 className="font-display text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
              Competitor analysis that{' '}
              <span className="text-gradient-honey">shows its working</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
              OptiStratixAI reads your competitors&rsquo; landing pages and social media, finds the
              strategic gaps you are losing ground to, and turns them into a marketing strategy you
              can actually execute, with a human validating every major step.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link to="/signup">
                  Start an analysis
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
            <p className="mt-5 text-xs text-muted-foreground">
              Two mandatory human checkpoints per run. Every claim carries its source.
            </p>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring, delay: 0.15 }}
          className="container mt-16"
        >
          <p className="eyebrow mb-4">The pipeline, running</p>
          <PipelineTeaser />
        </motion.div>
      </section>

      {/* --------------------------------------------------------- problem */}
      <Section
        tinted
        eyebrow="The problem"
        title="Nobody is short of competitor data"
        description="What is missing is the step between having it and knowing what to do about it."
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
