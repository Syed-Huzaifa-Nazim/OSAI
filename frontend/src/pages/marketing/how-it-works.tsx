import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Brain, Boxes, Database, Layers, Plug, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Section } from '@/components/marketing/section'
import { PIPELINE_STAGES, ACTOR_LABEL } from '@/lib/pipeline-stages'
import { STAGE_COLOR_CLASSES } from '@/components/pipeline/stage-colors'
import { resolveStageIcon } from '@/components/pipeline/stage-icon'
import { cn } from '@/lib/utils'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { revealOnScroll, spring, staggerContainer, staggerItem, viewportOnce } from '@/lib/motion'

const FOUNDATION = [
  { icon: Brain, label: 'LLM layer', value: 'GPT-4o class model for agent reasoning' },
  { icon: Database, label: 'Vector database', value: 'ChromaDB, one collection per project' },
  { icon: Layers, label: 'Embeddings', value: 'OpenAI embeddings over cleaned chunks' },
  { icon: Boxes, label: 'Orchestration', value: 'LangChain / CrewAI multi-agent layer' },
  { icon: Plug, label: 'APIs & integrations', value: 'Web search, social and SEO sources' },
  { icon: Activity, label: 'Monitoring', value: 'Per-stage timing, tokens and cost' },
]

/** The long-form walkthrough: every stage, scroll-revealed in order. */
export default function HowItWorksPage() {
  useDocumentTitle('How it works')

  return (
    <>
      <section className="pb-8 pt-16 sm:pt-24">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="max-w-3xl"
          >
            <p className="eyebrow">How it works</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              The nine stages, end to end
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-muted-foreground">
              Every run follows the same path. Four agents handle acquisition, analysis, strategy
              and critique; you hold the two gates that decide what gets written and what ships.
            </p>
          </motion.div>
        </div>
      </section>

      <Section>
        <ol className="relative space-y-5">
          {PIPELINE_STAGES.map((stage, index) => {
            const Icon = resolveStageIcon(stage.icon)
            const colors = STAGE_COLOR_CLASSES[stage.id]
            return (
              <motion.li
                key={stage.id}
                variants={revealOnScroll}
                initial="initial"
                whileInView="whileInView"
                viewport={viewportOnce}
                transition={{ delay: Math.min(index, 3) * 0.04 }}
              >
                <Card
                  glass={stage.isCheckpoint}
                  className={cn(
                    'relative overflow-hidden p-6 sm:p-7',
                    stage.isCheckpoint && 'border-brand-butter-cream/35',
                  )}
                >
                  <div className="flex flex-wrap items-start gap-5">
                    <div className="flex items-center gap-4">
                      <span className="font-mono text-2xl tabular-nums text-muted-foreground/50">
                        {String(stage.id).padStart(2, '0')}
                      </span>
                      <span
                        className={cn(
                          'flex size-11 shrink-0 items-center justify-center rounded-full',
                          colors.bgSoft,
                          colors.text,
                        )}
                      >
                        <Icon className="size-5" />
                      </span>
                    </div>
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="font-display text-lg font-semibold">{stage.title}</h2>
                        <Badge variant={stage.actor === 'human' ? 'secondary' : 'outline'}>
                          {ACTOR_LABEL[stage.actor]}
                        </Badge>
                        {stage.isCheckpoint ? (
                          <Badge variant="secondary">Mandatory checkpoint</Badge>
                        ) : null}
                      </div>
                      <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
                        {stage.summary}
                      </p>
                    </div>
                  </div>
                </Card>
              </motion.li>
            )
          })}
        </ol>
      </Section>

      <Section
        tinted
        eyebrow="System foundation"
        title="What runs underneath"
        description="The infrastructure layer the nine stages sit on."
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
              <Card className="h-full p-5">
                <span className="flex size-9 items-center justify-center rounded-full bg-primary/12 text-primary">
                  <item.icon className="size-4" />
                </span>
                <h3 className="mt-4 text-sm font-medium">{item.label}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{item.value}</p>
              </Card>
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
