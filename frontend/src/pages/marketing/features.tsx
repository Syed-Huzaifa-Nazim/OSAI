import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Check,
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
import {
  ApproveVisual,
  CollectVisual,
  ContentVisual,
  ExplainVisual,
  GapsVisual,
  ReviewVisual,
  StrategyVisual,
} from '@/components/marketing/feature-visuals'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { cn } from '@/lib/utils'
import { revealOnScroll, spring, springSoft, viewportOnce } from '@/lib/motion'

interface Feature {
  icon: typeof Radar
  eyebrow: string
  title: string
  body: string
  points: { label: string; detail: string }[]
  accent: string
  human?: boolean
  /** Not built yet: shown with a Coming soon badge. */
  comingSoon?: boolean
  /** The small animated picture of what this step does. */
  visual: () => React.JSX.Element
}

const FEATURES: Feature[] = [
  {
    icon: Radar,
    eyebrow: 'Step 1 · Collect posts',
    title: 'Scout Engine',
    visual: CollectVisual,
    body: 'Reads exactly the links you give it and nothing else: the latest Instagram posts of both accounts (photos, reels, likes, comments, hashtags), or Daraz and Alibaba product listings. It is a collector, not an agent: it makes no decisions.',
    points: [
      {
        label: 'Instagram through Apify',
        detail: 'Posts, captions, likes, comments and cover pictures of both accounts, up to 30 posts each.',
      },
      {
        label: 'Daraz and Alibaba',
        detail: 'Product listings read with BeautifulSoup, with Playwright when a page needs a browser.',
      },
      {
        label: 'Stored per project',
        detail: 'Captions and comments are embedded and kept in Supabase (pgvector), so explanations can search them.',
      },
    ],
    accent: 'text-stage-2',
  },
  {
    icon: Lightbulb,
    eyebrow: 'Step 2 · Find gaps',
    title: 'Gap Engine',
    visual: GapsVisual,
    body: 'Compares the two accounts post by post and keeps only the differences that hold up: what the competitor does more and does well, what works worse on your own page, and photos that look poorly made. Every gap is found by statistics and a trained model, not written by a language model.',
    points: [
      {
        label: 'What it compares',
        detail: 'Types of post (photo, reel, carousel), hashtags, your own weak spots, picture quality and the profile.',
      },
      {
        label: 'How sure, stated honestly',
        detail: 'Statistical tests decide High, Medium or Low. A real difference that could still be chance is shown as "Not proven yet: worth testing".',
      },
      {
        label: 'Real posts attached',
        detail: 'Each gap carries the posts behind it, with their likes, comments and dates.',
      },
    ],
    accent: 'text-stage-4',
  },
  {
    icon: Sparkles,
    eyebrow: 'Step 2 · Explanations',
    title: 'Explained in simple words',
    visual: ExplainVisual,
    body: 'Press Explain on any gap: you get what the numbers show, why it counts as a gap, and why that kind of difference can matter, in a few short sentences. The language model only rephrases what it is given; it cannot add facts.',
    points: [
      {
        label: 'From your own posts',
        detail: 'The gap’s example posts plus the closest posts found by searching both accounts (retrieval).',
      },
      {
        label: 'General reasons from checked facts',
        detail: 'A small knowledge base of sourced facts; a general reason without a real source is removed.',
      },
      {
        label: 'Every reference checked',
        detail: 'Code removes any reference to a post or fact the model was not given, and says so.',
      },
    ],
    accent: 'text-primary',
  },
  {
    icon: ListChecks,
    eyebrow: 'Step 3 · Review gaps',
    title: 'Your decision',
    visual: ReviewVisual,
    body: 'Nothing moves on until you have been through the gaps and decided which ones are real for your shop.',
    points: [
      { label: 'Keep or drop each gap', detail: 'Dropped gaps never reach the strategy.' },
      { label: 'Set your own priority', detail: 'You decide what matters most, not the system.' },
      { label: 'Notes and a PDF report', detail: 'Add notes, then download all gaps or only the ones you kept.' },
    ],
    accent: 'text-stage-5',
    human: true,
  },
  {
    icon: Swords,
    eyebrow: 'Step 4 · Strategy + critic',
    title: 'A plan, then a second opinion',
    visual: StrategyVisual,
    body: 'Being built. A plan will be written from the gaps you kept, then checked by a second reviewer (the critic) that looks for weak, unclear or unsupported points and shows what it changed.',
    points: [
      { label: 'Built only from kept gaps', detail: 'The plan works from your decisions, not from everything found.' },
      { label: 'Changes are visible', detail: 'Before and after are both kept, so you can see what the critic changed and why.' },
    ],
    accent: 'text-stage-6',
    comingSoon: true,
  },
  {
    icon: ShieldCheck,
    eyebrow: 'Step 5 · Approve strategy',
    title: 'Your approval',
    visual: ApproveVisual,
    body: 'Being built. You will read the plan with the critic’s notes visible, then approve it or send it back with your changes.',
    points: [
      { label: 'Approve or ask for changes', detail: 'A change request produces a new version of the plan.' },
      { label: 'Decisions are kept', detail: 'Who decided, what, and when.' },
    ],
    accent: 'text-stage-7',
    human: true,
    comingSoon: true,
  },
  {
    icon: FileText,
    eyebrow: 'Step 6 · Create content',
    title: 'Content for your plan',
    visual: ContentVisual,
    body: 'Being built. For the plan you approved: a strategy document, and the content to carry it out, such as captions, images and short reels.',
    points: [
      { label: 'Tied to the plan', detail: 'Every piece of content traces back to the part of the plan it serves.' },
      { label: 'Yours to edit', detail: 'Keep, change or drop anything that is suggested.' },
    ],
    accent: 'text-stage-9',
    comingSoon: true,
  },
]

export default function FeaturesPage() {
  useDocumentTitle('Features')

  return (
    <>
      <section className="pb-0 pt-10 sm:pt-14">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="max-w-3xl"
          >
            <p className="eyebrow">Features</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              Six steps, and what each one does today
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-muted-foreground">
              Steps 1 to 3 work now. Steps 4 to 6 are being built, and are marked so.
            </p>
          </motion.div>
        </div>
      </section>

      <Section>
        <div className="space-y-5">
          {FEATURES.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, x: index % 2 ? 60 : -60, rotate: index % 2 ? 2.5 : -2.5 }}
              whileInView={{ opacity: 1, x: 0, rotate: 0 }}
              viewport={viewportOnce}
              transition={springSoft}
            >
              <Card
                glass={feature.human}
                className={cn(
                  'relative grid items-center gap-8 overflow-hidden p-6 sm:p-8 lg:grid-cols-[1.05fr_1fr]',
                  feature.human && 'border-brand-butter-cream/35',
                  index % 2 === 1 && 'lg:[&>*:first-child]:order-2',
                )}
              >
                <div className="relative space-y-4">
                  <div className="flex items-center gap-3">
                    <span
                      className={cn(
                        'bg-gradient-to-b bg-clip-text font-display text-5xl font-extrabold leading-none text-transparent',
                        feature.human ? 'from-warning to-warning/30' : feature.comingSoon ? 'from-blush to-blush/30' : 'from-primary to-primary/30',
                      )}
                    >
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span className={cn('flex size-10 items-center justify-center rounded-full bg-muted/60', feature.accent)}>
                      <feature.icon className="size-5" />
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="eyebrow">{feature.eyebrow}</p>
                    {feature.human ? <Badge variant="warning">Your decision</Badge> : null}
                    {feature.comingSoon ? <Badge variant="muted">Coming soon</Badge> : null}
                  </div>
                  <h2 className="font-display text-2xl font-semibold tracking-tight">{feature.title}</h2>
                  <p className="text-sm leading-relaxed text-muted-foreground">{feature.body}</p>
                  <ul className="space-y-2">
                    {feature.points.map((point, pointIndex) => (
                      <motion.li
                        key={point.label}
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={viewportOnce}
                        transition={{ ...springSoft, delay: 0.1 + pointIndex * 0.08 }}
                        className="flex gap-2.5 text-sm"
                      >
                        <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                          <Check className="size-3" strokeWidth={3} aria-hidden="true" />
                        </span>
                        <span>
                          <span className="font-medium">{point.label}.</span>{' '}
                          <span className="text-muted-foreground">{point.detail}</span>
                        </span>
                      </motion.li>
                    ))}
                  </ul>
                </div>

                <div className="relative self-center">
                  <feature.visual />
                </div>
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
              <Link to="/how-it-works">How it works</Link>
            </Button>
          </div>
        </motion.div>
      </Section>
    </>
  )
}
