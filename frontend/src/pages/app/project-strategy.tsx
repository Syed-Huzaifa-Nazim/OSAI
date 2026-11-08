import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, ShieldAlert, Swords } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/shared/page-header'
import { InitiativeCard } from '@/components/shared/initiative-card'
import { CriticPanel } from '@/components/shared/critic-panel'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { CriticImpactChart } from '@/components/charts/critic-impact-chart'
import { useStrategy } from '@/hooks/use-insights'
import { usePipeline } from '@/hooks/use-pipeline'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { staggerContainer } from '@/lib/motion'

/** Stage 6 output: the strategy, with the Critic's work shown rather than hidden. */
export default function StrategyPage() {
  const projectId = useProjectId()
  const project = useProject(projectId)
  const pipeline = usePipeline(projectId)
  const { data: strategy, isLoading, isError, error, refetch } = useStrategy(projectId)

  useDocumentTitle(project.data ? `${project.data.brandName} · Strategy` : 'Strategy')

  if (isError) {
    return (
      <ErrorState
        message={errorMessage(error)}
        onRetry={() => {
          void refetch()
        }}
      />
    )
  }

  if (isLoading) return <LoadingState rows={4} />

  if (!strategy) {
    const running = pipeline.data?.stages[6].status === 'running'
    return (
      <div className="space-y-7">
        <PageHeader
          eyebrow="Stage 6 · Strategist + Critic"
          title="Strategy"
          description="Two agents in tension: one drafts, the other challenges."
        />
        <EmptyState
          title={running ? 'The agents are working' : 'No strategy has been generated yet'}
          description={
            running
              ? 'The Strategist is drafting initiatives and the Critic is reviewing them. This page fills in as soon as stage 6 completes.'
              : 'Strategy generation starts once you have prioritised the gaps at the first human checkpoint.'
          }
          icon={<Swords className="size-5" />}
          action={
            <Button asChild variant="outline">
              <Link
                to={`/app/projects/${projectId}/${
                  pipeline.data?.blockedOn === 5 ? 'review-gaps' : 'pipeline'
                }`}
              >
                {pipeline.data?.blockedOn === 5 ? 'Review the gaps first' : 'Go to the pipeline'}
              </Link>
            </Button>
          }
        />
      </div>
    )
  }

  const majorInterventions = strategy.criticFeedback.filter((item) => item.severity === 'major')
  const awaitingApproval = pipeline.data?.blockedOn === 7

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Stage 6 · Strategist + Critic"
        title={strategy.title}
        description="Drafted by the Strategist, then challenged by the Critic. Both passes are on the record."
        actions={
          awaitingApproval ? (
            <Button asChild>
              <Link to={`/app/projects/${projectId}/review-strategy`}>
                Review and approve
                <ArrowRight />
              </Link>
            </Button>
          ) : undefined
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">Version {strategy.version}</Badge>
        <Badge variant="outline">{strategy.initiatives.length} initiatives</Badge>
        <Badge variant="secondary">{strategy.criticFeedback.length} critic interventions</Badge>
        {majorInterventions.length > 0 ? (
          <Badge variant="destructive">
            <ShieldAlert />
            {majorInterventions.length} major
          </Badge>
        ) : null}
      </div>

      <Card glass className="p-6">
        <p className="eyebrow">Executive summary</p>
        <p className="mt-3 text-base leading-relaxed">{strategy.executiveSummary}</p>
      </Card>

      <Tabs defaultValue="initiatives">
        <TabsList>
          <TabsTrigger value="initiatives">Initiatives</TabsTrigger>
          <TabsTrigger value="critic">Critic transparency</TabsTrigger>
        </TabsList>

        <TabsContent value="initiatives">
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="space-y-4"
          >
            {strategy.initiatives.map((initiative, index) => (
              <InitiativeCard
                key={initiative.id}
                initiative={initiative}
                index={index}
                feedback={strategy.criticFeedback}
              />
            ))}
          </motion.div>
        </TabsContent>

        <TabsContent value="critic">
          <div className="space-y-5">
            <Card className="flex items-start gap-3 border-primary/25 bg-primary/5 p-4">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-primary" />
              <p className="text-sm text-muted-foreground">
                <span className="font-medium text-foreground">Why this is shown.</span> The Critic
                exists to catch claims the Strategist could not support. Hiding its work would make
                that claim impossible to check, so every intervention, including the ones that
                removed content entirely, is listed here.
              </p>
            </Card>

            <CriticImpactChart feedback={strategy.criticFeedback} />
            <CriticPanel feedback={strategy.criticFeedback} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
