import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Database, Download, ImageIcon, Layers, Sigma, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Section } from '@/components/marketing/section'
import { StepStory } from '@/components/marketing/step-story'
import {
  AppMini,
  CollectMini,
  ExplainMini,
  GapsMini,
  QualityMini,
  SearchMini,
} from '@/components/marketing/foundation-visuals'
import { CompareAnimation } from '@/components/shared/compare-animation'
import { TiltCard } from '@/components/marketing/tilt-card'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { revealOnScroll, spring, staggerContainer, staggerItem, viewportOnce } from '@/lib/motion'

const FOUNDATION = [
  {
    icon: Download,
    label: 'Collecting posts',
    visual: CollectMini,
    value: "Apify's Instagram scraper; Daraz and Alibaba listings read with BeautifulSoup, Playwright as fallback",
  },
  {
    icon: Sigma,
    label: 'Finding gaps',
    visual: GapsMini,
    value: 'Statistical tests on real posts (Fisher exact, Mann-Whitney), corrected with Benjamini-Hochberg',
  },
  {
    icon: ImageIcon,
    label: 'Picture quality',
    visual: QualityMini,
    value: 'A frozen ResNet-50 and a ridge regression we trained on KonIQ-10k photo ratings',
  },
  {
    icon: Database,
    label: 'Search and storage',
    visual: SearchMini,
    value: 'Supabase Postgres with pgvector; posts embedded with all-MiniLM-L6-v2',
  },
  {
    icon: Sparkles,
    label: 'Explanations',
    visual: ExplainMini,
    value: 'Groq LLM (gpt-oss-120b), written only from retrieved posts and checked facts; every citation verified',
  },
  {
    icon: Layers,
    label: 'The app',
    visual: AppMini,
    value: 'FastAPI backend, React and TypeScript frontend, PDF reports with ReportLab',
  },
]

/** The long-form walkthrough: every stage, scroll-revealed in order. */
export default function HowItWorksPage() {
  useDocumentTitle('How it works')

  return (
    <>
      <section className="pb-0 pt-10 sm:pt-14">
        <div className="container grid items-center gap-8 lg:grid-cols-[1.3fr_0.7fr]">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="max-w-3xl"
          >
            <p className="eyebrow">How it works</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              Six steps, from your link to your content
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-muted-foreground">
              Every run follows the same path. The Scout Engine reads both pages and the Gap Engine finds the
              gaps; you hold the two gates that decide what matters and what ships. The Strategist and Critic
              agents (steps 4 to 6) are being built.
            </p>
          </motion.div>
          <CompareAnimation />
        </div>
      </section>

      <Section>
        <StepStory />
      </Section>

      <Section
        tinted
        eyebrow="System foundation"
        title="What runs underneath"
        description="The tools and models behind the six steps."
      >
        <motion.div
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={viewportOnce}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {FOUNDATION.map((item) => (
            <motion.div key={item.label} variants={staggerItem}>
              <TiltCard>
              <Card className="h-full p-4">
                <item.visual />
                <h3 className="mt-4 flex items-center gap-2 font-display text-base font-semibold">
                  <span className="flex size-7 items-center justify-center rounded-full bg-primary/12 text-primary">
                    <item.icon className="size-3.5" />
                  </span>
                  {item.label}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">{item.value}</p>
              </Card>
              </TiltCard>
            </motion.div>
          ))}
        </motion.div>
      </Section>

      <Section>
        <motion.div
          variants={revealOnScroll}
          initial="initial"
          whileInView="whileInView"
          viewport={viewportOnce}
        >
          <Card glass className="p-10 text-center">
            <h2 className="font-display text-2xl font-semibold sm:text-3xl">
              Ready to run it on your own competitors?
            </h2>
            <div className="mt-7 flex flex-wrap justify-center gap-3">
              <Button asChild size="lg">
                <Link to="/signup">
                  Get started
                  <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/features">See the features</Link>
              </Button>
            </div>
          </Card>
        </motion.div>
      </Section>
    </>
  )
}
