import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  FileText,
  Lightbulb,
  ListChecks,
  Radar,
  ShieldCheck,
  Sparkles,
  Swords,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Section } from '@/components/marketing/section'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { cn } from '@/lib/utils'
import { revealOnScroll, spring, viewportOnce } from '@/lib/motion'

interface Feature {
  icon: typeof Radar
  eyebrow: string
  title: string
  body: string
  points: { label: string; detail: string }[]
  accent: string
  human?: boolean
}

const FEATURES: Feature[] = [
  {
    icon: Radar,
    eyebrow: 'Stage 2 · Data acquisition',
    title: 'Scout Agent',
    body: 'Collects the raw material: competitor landing pages, social posts, customer reviews, forum threads and trade news. What it gathers is cleaned, chunked, embedded and stored as a retrievable corpus scoped to your project, not a pile of scraped HTML.',
    points: [
      {
        label: 'Multi-platform by default',
        detail: 'Landing pages and social media in the same run, so comparisons hold across both.',
      },
      {
        label: 'Review and forum signal',
        detail: 'Where customers say what they actually think, in their own words.',
      },
      {
        label: 'Per-project vector collection',
        detail: 'One ChromaDB collection per analysis; nothing leaks between projects.',
      },
    ],
    accent: 'text-stage-2',
  },
  {
    icon: Lightbulb,
    eyebrow: 'Stage 4 · Gap analysis',
    title: 'Insight Agent',
    body: 'Compares your brand against the corpus and returns specific, categorised gaps (content, SEO, social engagement, positioning, audience, conversion and pricing), each with a confidence score and the passages that support it.',
    points: [
      {
        label: 'Comparative, not descriptive',
        detail: 'Findings are about the distance between you and them, not a summary of either.',
      },
      {
        label: 'Confidence, stated honestly',
        detail: 'Every gap carries a score, so a weak signal is visibly a weak signal.',
      },
      {
        label: 'Evidence attached',
        detail: 'Quote, source, URL and retrieval relevance for each claim.',
      },
    ],
    accent: 'text-stage-4',
  },
  {
    icon: ListChecks,
    eyebrow: 'Stage 5 · Human checkpoint',
    title: 'Gap refinement',
    body: 'The first gate. The pipeline stops and waits: no strategy is drafted until a person has been through the gap list and decided which ones are real for this business.',
    points: [
      { label: 'Accept or reject each gap', detail: 'Rejected gaps never reach the Strategist.' },
      {
        label: 'Override the agent priority',
        detail: 'The model proposes; you decide what is actually critical.',
      },
      {
        label: 'Annotate for the Strategist',
        detail: 'Notes you leave become context for the next stage.',
      },
    ],
    accent: 'text-stage-5',
    human: true,
  },
  {
    icon: Swords,
    eyebrow: 'Stage 6 · Strategy generation',
    title: 'Strategist + Critic',
    body: 'Two agents, deliberately in tension. The Strategist drafts initiatives against the gaps you kept. The Critic then attacks that draft on four dimensions (strength, clarity, feasibility and evidence), and rewrites or removes what does not hold up.',
    points: [
      {
        label: 'Adversarial by design',
        detail: 'A second model whose job is to disagree with the first.',
      },
      {
        label: 'Transparent revisions',
        detail: 'Before and after are both kept, so you can see what changed and why.',
      },
      {
        label: 'Unsupported claims cut',
        detail: 'Initiatives with no basis in the intake or the corpus are removed outright.',
      },
    ],
    accent: 'text-stage-6',
  },
  {
    icon: ShieldCheck,
    eyebrow: 'Stage 7 · Human checkpoint',
    title: 'Final approval',
    body: 'The second gate. You read the strategy with the Critic annotations visible, then approve it for execution or send it back with notes for another version.',
    points: [
      {
        label: 'Approve, reject or revise',
        detail: 'A revision request loops back to stage 6 and produces a new version.',
      },
      {
        label: 'Critic panel always visible',
        detail: 'The disagreements are shown, not buried. That is the point.',
      },
      { label: 'Decisions are logged', detail: 'Reviewer, decision, notes and timestamp, kept.' },
    ],
    accent: 'text-stage-7',
    human: true,
  },
  {
    icon: FileText,
    eyebrow: 'Stage 8 · Output',
    title: 'Strategy document',
    body: 'An approved strategy is assembled into a document: executive summary, competitive position, prioritised gaps, initiatives, a week-by-week implementation plan, and the validation trail behind all of it.',
    points: [
      { label: 'Implementation plan', detail: 'Sequenced by effort and dependency, not by whim.' },
      { label: 'Validation trail included', detail: 'Which gaps were accepted, and by whom.' },
      { label: 'Exportable', detail: 'PDF, DOCX or Markdown.' },
    ],
    accent: 'text-stage-8',
  },
  {
    icon: Sparkles,
    eyebrow: 'Stage 9 · Scale',
    title: 'Content automation',
    body: 'Each approved initiative becomes concrete assets (blog outlines, SEO briefs, social posts, ad copy and email sequences), with the effort estimated so you can plan the quarter rather than guess at it.',
    points: [
      { label: 'Mapped to initiatives', detail: 'Every asset traces back to a strategy it serves.' },
      { label: 'Draft on demand', detail: 'Generate the full body for any asset you want to keep.' },
      { label: 'Dismiss what does not fit', detail: 'Suggestions are suggestions.' },
    ],
    accent: 'text-stage-9',
  },
]

export default function FeaturesPage() {
  useDocumentTitle('Features')

  return (
    <>
      <section className="pb-4 pt-16 sm:pt-24">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="max-w-3xl"
          >
            <p className="eyebrow">Features</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              Four agents, two gates, one document
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-muted-foreground">
              Each part of the pipeline does one job and hands off cleanly to the next. Here is what
              each of them actually produces.
            </p>
          </motion.div>
        </div>
      </section>

      <Section>
        <div className="space-y-6">
          {FEATURES.map((feature, index) => (
            <motion.div
              key={feature.title}
              variants={revealOnScroll}
              initial="initial"
              whileInView="whileInView"
              viewport={viewportOnce}
            >
              <Card
                glass={feature.human}
                className={cn(
                  'grid gap-8 p-7 sm:p-9 lg:grid-cols-[1fr_1.1fr]',
                  feature.human && 'border-brand-butter-cream/35',
                  index % 2 === 1 && 'lg:[&>*:first-child]:order-2',
                )}
              >
                <div className="space-y-4">
                  <span
                    className={cn(
                      'flex size-11 items-center justify-center rounded-full bg-muted/60',
                      feature.accent,
                    )}
                  >
                    <feature.icon className="size-5" />
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="eyebrow">{feature.eyebrow}</p>
                    {feature.human ? <Badge variant="secondary">Human checkpoint</Badge> : null}
                  </div>
                  <h2 className="font-display text-2xl font-semibold tracking-tight">
                    {feature.title}
                  </h2>
                  <p className="text-sm leading-relaxed text-muted-foreground">{feature.body}</p>
                </div>

                <ul className="space-y-4 self-center">
                  {feature.points.map((point) => (
                    <li key={point.label} className="rounded-md border border-border/20 bg-muted/25 p-4">
                      <p className="text-sm font-medium">{point.label}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{point.detail}</p>
                    </li>
                  ))}
                </ul>
              </Card>
            </motion.div>
          ))}
        </div>
      </Section>

      <Section tinted>
        <motion.div
          variants={revealOnScroll}
          initial="initial"
          whileInView="whileInView"
          viewport={viewportOnce}
          className="text-center"
        >
          <h2 className="font-display text-2xl font-semibold sm:text-3xl">
            See it run on your own competitors
          </h2>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg">
              <Link to="/signup">
                Start an analysis
                <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/pricing">View pricing</Link>
            </Button>
          </div>
        </motion.div>
      </Section>
    </>
  )
}
