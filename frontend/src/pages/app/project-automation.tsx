import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Clock,
  FileEdit,
  Mail,
  Megaphone,
  PenLine,
  Search,
  Sparkles,
  Trash2,
  Wand2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PageHeader } from '@/components/shared/page-header'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import {
  useDraftSuggestion,
  useGenerateSuggestions,
  useSuggestions,
  useUpdateSuggestion,
} from '@/hooks/use-automation'
import { useStrategy } from '@/hooks/use-insights'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { cn, titleCase, truncate } from '@/lib/utils'
import { staggerContainer, staggerItem } from '@/lib/motion'
import type { AssetKind, ContentSuggestion } from '@/types/domain'

const KIND_ICON: Record<AssetKind, typeof PenLine> = {
  blog: PenLine,
  social_post: Megaphone,
  ad_copy: Megaphone,
  seo_brief: Search,
  email: Mail,
}

type Filter = 'all' | AssetKind

/**
 * Stage 9: scalability and future automation, built as a working surface
 * rather than a roadmap card. Suggestions are mapped to approved initiatives,
 * and any of them can be drafted in full on demand.
 */
export default function AutomationPage() {
  const projectId = useProjectId()
  const project = useProject(projectId)
  const strategy = useStrategy(projectId)
  const { data: suggestions, isLoading, isError, error, refetch } = useSuggestions(projectId)
  const generate = useGenerateSuggestions(projectId)
  const update = useUpdateSuggestion(projectId)
  const draft = useDraftSuggestion(projectId)
  const [filter, setFilter] = useState<Filter>('all')
  const [reading, setReading] = useState<ContentSuggestion | null>(null)

  useDocumentTitle(project.data ? `${project.data.brandName} · Automation` : 'Automation')

  const active = useMemo(
    () => (suggestions ?? []).filter((item) => item.status !== 'dismissed'),
    [suggestions],
  )
  const dismissed = useMemo(
    () => (suggestions ?? []).filter((item) => item.status === 'dismissed'),
    [suggestions],
  )
  const visible = filter === 'all' ? active : active.filter((item) => item.kind === filter)
  const kinds = [...new Set(active.map((item) => item.kind))]

  const totalHours = active.reduce((sum, item) => sum + item.estimatedEffortHours, 0)

  const initiativeTitle = (id: string | null): string | null => {
    if (!id || !strategy.data) return null
    return strategy.data.initiatives.find((initiative) => initiative.id === id)?.title ?? null
  }

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

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Step 6 · Create content"
        title="Content assets"
        description="Each approved initiative, turned into the concrete pieces that would execute it."
        actions={
          <Button
            loading={generate.isPending}
            onClick={() => {
              generate.mutate()
            }}
          >
            <Wand2 />
            {(suggestions ?? []).length > 0 ? 'Regenerate' : 'Generate suggestions'}
          </Button>
        }
      />

      {isLoading ? (
        <LoadingState rows={4} />
      ) : (suggestions ?? []).length === 0 ? (
        <EmptyState
          title="No content suggestions yet"
          description={
            strategy.data
              ? 'Generate a set of assets mapped to the initiatives in your approved strategy.'
              : 'A strategy has to exist before stage 9 can map assets to it. Work through the pipeline first.'
          }
          icon={<Sparkles className="size-5" />}
          action={
            strategy.data ? (
              <Button
                loading={generate.isPending}
                onClick={() => {
                  generate.mutate()
                }}
              >
                <Wand2 />
                Generate suggestions
              </Button>
            ) : (
              <Button asChild variant="outline">
                <Link to={`/app/projects/${projectId}/pipeline`}>Go to the pipeline</Link>
              </Button>
            )
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <Tabs
              value={filter}
              onValueChange={(value) => {
                setFilter(value as Filter)
              }}
            >
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                {kinds.map((kind) => (
                  <TabsTrigger key={kind} value={kind}>
                    {titleCase(kind)}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <p className="ml-auto flex items-center gap-1.5 text-sm text-muted-foreground">
              <Clock className="size-3.5" />
              {totalHours}h estimated across {active.length} assets
            </p>
          </div>

          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="grid gap-4 md:grid-cols-2"
          >
            {visible.map((suggestion) => {
              const Icon = KIND_ICON[suggestion.kind]
              const linked = initiativeTitle(suggestion.linkedInitiativeId)
              return (
                <motion.div key={suggestion.id} variants={staggerItem} layout>
                  <Card
                    className={cn(
                      'flex h-full flex-col p-5',
                      suggestion.status === 'generated' && 'border-success/30',
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-stage-9/15 text-stage-9">
                        <Icon className="size-4" />
                      </span>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge variant="outline">{titleCase(suggestion.kind)}</Badge>
                        {suggestion.status === 'generated' ? (
                          <Badge variant="success">Drafted</Badge>
                        ) : null}
                      </div>
                    </div>

                    <h3 className="mt-4 font-display text-base font-semibold leading-snug">
                      {suggestion.title}
                    </h3>
                    <p className="mt-2 flex-1 text-sm text-muted-foreground">{suggestion.angle}</p>

                    {linked ? (
                      <p className="mt-3 text-xs text-muted-foreground">
                        <span className="text-foreground/70">Executes:</span>{' '}
                        {truncate(linked, 60)}
                      </p>
                    ) : null}

                    {suggestion.targetKeywords.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {suggestion.targetKeywords.map((keyword) => (
                          <Badge key={keyword} variant="muted">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    ) : null}

                    <div className="mt-4 flex items-center justify-between gap-2 border-t border-border/15 pt-4">
                      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Clock className="size-3" />
                        {suggestion.estimatedEffortHours}h · {suggestion.channel}
                      </span>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => {
                            update.mutate({
                              suggestionId: suggestion.id,
                              patch: { status: 'dismissed' },
                            })
                          }}
                          aria-label={`Dismiss ${suggestion.title}`}
                        >
                          <Trash2 />
                        </Button>
                        {suggestion.body ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setReading(suggestion)
                            }}
                          >
                            <FileEdit />
                            Read draft
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            loading={draft.isPending && draft.variables === suggestion.id}
                            onClick={() => {
                              draft.mutate(suggestion.id)
                            }}
                          >
                            <Wand2 />
                            Draft it
                          </Button>
                        )}
                      </div>
                    </div>
                  </Card>
                </motion.div>
              )
            })}
          </motion.div>

          {dismissed.length > 0 ? (
            <section className="space-y-3">
              <h2 className="font-display text-sm font-semibold text-muted-foreground">
                Dismissed ({dismissed.length})
              </h2>
              <div className="flex flex-wrap gap-2">
                {dismissed.map((suggestion) => (
                  <button
                    key={suggestion.id}
                    type="button"
                    onClick={() => {
                      update.mutate({
                        suggestionId: suggestion.id,
                        patch: { status: 'suggested' },
                      })
                    }}
                    className="rounded-full border border-border/25 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
                  >
                    {truncate(suggestion.title, 48)} · restore
                  </button>
                ))}
              </div>
            </section>
          ) : null}
        </>
      )}

      <Dialog
        open={reading !== null}
        onOpenChange={(open) => {
          if (!open) setReading(null)
        }}
      >
        <DialogContent className="max-h-[80vh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{reading?.title}</DialogTitle>
          </DialogHeader>
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-muted-foreground">
            {reading?.body}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  )
}
