import { motion } from 'framer-motion'
import { GraduationCap, Target } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Section } from '@/components/marketing/section'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { initials } from '@/lib/utils'
import { revealOnScroll, spring, staggerContainer, staggerItem, viewportOnce } from '@/lib/motion'

const TEAM = [
  { name: 'Hadia', roll: '23-AI-01' },
  { name: 'Syed Huzaifa Nazim', roll: '23-AI-23' },
  { name: 'Muhammad Waqas Ali', roll: '23-AI-59' },
  { name: 'Muhammad Umar Khan', roll: '23-AI-71' },
]

const OBJECTIVES = [
  {
    title: 'RAG pipeline',
    body: 'Implement a multi-agent retrieval-augmented-generation pipeline that extracts, processes and analyses real-world competitor data rather than reasoning from a model’s priors.',
  },
  {
    title: 'Multi-platform analysis',
    body: 'Perform comparative analysis across both landing pages and social media, so findings hold across the channels a business actually competes on.',
  },
  {
    title: 'Human-in-the-loop',
    body: 'Let users validate and refine AI-generated insights through explicit evaluation and approval steps, rather than accepting model output on trust.',
  },
]

const PROBLEMS = [
  'SMEs have access to large amounts of competitor data, but it is unstructured and hard to interpret.',
  'Existing tools do not perform true comparative analysis between a business and its competitors.',
  'Most AI tools generate generic, non-contextual suggestions that do not fit the specific business.',
  'Existing systems lack evidence-based reasoning, so their outputs are hard to trust or validate.',
]

export default function AboutPage() {
  useDocumentTitle('About')

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
        </div>
      </section>

      <Section
        eyebrow="The problem"
        title="Why this project exists"
        description="Four observations that the system is a direct response to."
      >
        <motion.ul
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={viewportOnce}
          className="grid gap-4 sm:grid-cols-2"
        >
          {PROBLEMS.map((problem, index) => (
            <motion.li key={problem} variants={staggerItem}>
              <Card className="h-full p-6">
                <span className="font-mono text-xs text-muted-foreground/60">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <p className="mt-3 text-sm leading-relaxed">{problem}</p>
              </Card>
            </motion.li>
          ))}
        </motion.ul>
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
              <Card glass className="h-full p-6">
                <span className="flex size-10 items-center justify-center rounded-full bg-primary/12 text-primary">
                  <Target className="size-5" />
                </span>
                <p className="eyebrow mt-5">Objective {index + 1}</p>
                <h3 className="mt-1.5 font-display text-lg font-semibold">{objective.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {objective.body}
                </p>
              </Card>
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
          {TEAM.map((member) => (
            <motion.div key={member.roll} variants={staggerItem}>
              <Card className="h-full p-6 text-center">
                <Avatar className="mx-auto size-14">
                  <AvatarFallback className="text-sm">{initials(member.name)}</AvatarFallback>
                </Avatar>
                <h3 className="mt-4 font-display text-base font-semibold">{member.name}</h3>
                <p className="mt-1 font-mono text-xs text-muted-foreground">{member.roll}</p>
              </Card>
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
