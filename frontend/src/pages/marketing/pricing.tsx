import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Check, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Section } from '@/components/marketing/section'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { cn } from '@/lib/utils'
import { revealOnScroll, spring, staggerContainer, staggerItem, viewportOnce } from '@/lib/motion'

interface Tier {
  name: string
  tagline: string
  monthly: number | null
  annual: number | null
  runs: string
  features: string[]
  cta: string
  highlighted?: boolean
}

/**
 * PLACEHOLDER PRICING: not reviewed or approved.
 *
 * The FYP deck contains no commercial model, so these numbers, limits and tier
 * names are invented to give the page a plausible shape. Nothing here should be
 * treated as settled; the banner at the top of the page says so to visitors.
 */
const TIERS: Tier[] = [
  {
    name: 'Pilot',
    tagline: 'Run one analysis end to end and see what comes out.',
    monthly: 0,
    annual: 0,
    runs: '1 analysis per month',
    features: [
      'Up to 2 competitors per run',
      'All nine pipeline stages',
      'Both human checkpoints',
      'Markdown export',
      'Community support',
    ],
    cta: 'Start free',
  },
  {
    name: 'Pro',
    tagline: 'For a marketing team running analyses continuously.',
    monthly: 49,
    annual: 39,
    runs: '10 analyses per month',
    features: [
      'Up to 5 competitors per run',
      'PDF and DOCX export',
      'Critic transparency panel',
      'Stage-9 content generation',
      'Run cost and token tracking',
      'Email support',
    ],
    cta: 'Choose Pro',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    tagline: 'For agencies running this across a client portfolio.',
    monthly: null,
    annual: null,
    runs: 'Unlimited analyses',
    features: [
      'Unlimited competitors per run',
      'Multiple reviewers per checkpoint',
      'Custom data sources',
      'Bring your own model keys',
      'SSO and audit export',
      'Dedicated support',
    ],
    cta: 'Talk to us',
  },
]

const FAQS = [
  {
    q: 'Is this pricing final?',
    a: 'No. OptiStratixAI is a Final Year Project and these tiers are placeholder content added to give the page a realistic shape. No billing is implemented and no payment is collected anywhere in the application.',
  },
  {
    q: 'What counts as one analysis?',
    a: 'One project taken through the pipeline: acquisition, embedding, gap analysis, both human checkpoints, strategy generation and the final document. Re-running stage 6 after requesting a revision does not count as a new analysis.',
  },
  {
    q: 'Why is there a limit on competitors per run?',
    a: 'Each competitor adds sources to scrape, chunks to embed and context for the agents to reason over. The limits keep a run fast enough to sit through and cheap enough to be worth running often.',
  },
  {
    q: 'Can I skip the human checkpoints?',
    a: 'No, and that is deliberate. The two review stages are what separate this from a generic suggestion engine. Removing them would remove the reason to trust the output.',
  },
]

export default function PricingPage() {
  useDocumentTitle('Pricing')
  const [annual, setAnnual] = useState(false)

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
            <p className="eyebrow">Pricing</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              Placeholder pricing
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-muted-foreground">
              A plausible tier structure, so the page exists and the shape can be reviewed. The
              numbers are invented.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...spring, delay: 0.08 }}
            className="mt-8"
          >
            <Card className="flex items-start gap-3 border-brand-butter-cream/30 bg-brand-butter-cream/5 p-4">
              <Info className="mt-0.5 size-4 shrink-0 text-brand-butter-cream" />
              <p className="text-sm text-muted-foreground">
                <span className="font-medium text-foreground">This page is a placeholder.</span> The
                FYP scope contains no commercial model, so these tiers, limits and prices were
                invented to fill the page and need your review before they mean anything. No billing
                is wired up anywhere in the product.
              </p>
            </Card>
          </motion.div>

          <div className="mt-8 flex items-center gap-3">
            <Label htmlFor="billing-cycle" className="text-sm text-muted-foreground">
              Monthly
            </Label>
            <Switch id="billing-cycle" checked={annual} onCheckedChange={setAnnual} />
            <Label htmlFor="billing-cycle" className="text-sm text-muted-foreground">
              Annual
            </Label>
            <Badge variant="secondary">Save 20%</Badge>
          </div>
        </div>
      </section>

      <Section className="pt-8">
        <motion.div
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={viewportOnce}
          className="grid gap-5 lg:grid-cols-3"
        >
          {TIERS.map((tier) => {
            const price = annual ? tier.annual : tier.monthly
            return (
              <motion.div key={tier.name} variants={staggerItem}>
                <Card
                  glass={tier.highlighted}
                  className={cn(
                    'flex h-full flex-col p-7',
                    tier.highlighted && 'border-primary/40 shadow-glow',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="font-display text-lg font-semibold">{tier.name}</h2>
                    {tier.highlighted ? <Badge>Most complete</Badge> : null}
                  </div>
                  <p className="mt-2 min-h-[40px] text-sm text-muted-foreground">{tier.tagline}</p>

                  <div className="mt-6 flex items-baseline gap-1.5">
                    {price === null ? (
                      <span className="font-display text-3xl font-semibold">Custom</span>
                    ) : (
                      <>
                        <span className="font-display text-4xl font-semibold tabular-nums">
                          ${price}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {price === 0 ? '' : `/ month${annual ? ', billed annually' : ''}`}
                        </span>
                      </>
                    )}
                  </div>
                  <p className="mt-1.5 text-xs text-muted-foreground">{tier.runs}</p>

                  <ul className="mt-6 flex-1 space-y-2.5">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex gap-2.5 text-sm">
                        <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                        <span className="text-muted-foreground">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    asChild
                    className="mt-7 w-full"
                    variant={tier.highlighted ? 'default' : 'outline'}
                  >
                    <Link to={tier.monthly === null ? '/contact' : '/signup'}>
                      {tier.cta}
                      <ArrowRight />
                    </Link>
                  </Button>
                </Card>
              </motion.div>
            )
          })}
        </motion.div>
      </Section>

      <Section tinted eyebrow="Questions" title="Before you ask">
        <motion.div
          variants={revealOnScroll}
          initial="initial"
          whileInView="whileInView"
          viewport={viewportOnce}
          className="max-w-3xl"
        >
          <Accordion type="single" collapsible>
            {FAQS.map((faq) => (
              <AccordionItem key={faq.q} value={faq.q}>
                <AccordionTrigger>{faq.q}</AccordionTrigger>
                <AccordionContent>{faq.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </motion.div>
      </Section>
    </>
  )
}
