/**
 * In-memory stand-in for the FastAPI backend, used when demo mode is on.
 *
 * It implements the same call signatures as the real service modules in
 * lib/api/, including simulated latency and a pipeline that genuinely advances
 * over time, so the animated stepper has real state transitions to render
 * rather than a canned video. State lives for the browser session only.
 */

import {
  DEMO_PROJECT_ID,
  DEMO_USER_ID,
  demoCompetitors,
  demoDocument,
  demoGaps,
  demoPipeline,
  demoProject,
  demoReviews,
  demoRunCost,
  demoSources,
  demoStrategy,
  demoSuggestions,
} from './demo-data'
import type {
  Competitor,
  ContentSuggestion,
  Gap,
  GapDecision,
  GapPriority,
  HitlReview,
  Integration,
  Project,
  RunCost,
  ScrapedSource,
  Strategy,
  StrategyDocument,
} from '@/types/domain'
import type { PipelineState, StageId, StageState } from '@/types/pipeline'
import { makeId, sleep } from '../utils'

/** Deep clone so callers mutating results cannot corrupt the seed data. */
function clone<T>(value: T): T {
  return structuredClone(value)
}

interface MockState {
  projects: Project[]
  competitors: Competitor[]
  sources: ScrapedSource[]
  gaps: Gap[]
  strategies: Strategy[]
  documents: StrategyDocument[]
  suggestions: ContentSuggestion[]
  reviews: HitlReview[]
  pipelines: Record<string, PipelineState>
  costs: Record<string, RunCost>
  integrations: Integration[]
}

const state: MockState = {
  projects: [clone(demoProject)],
  competitors: clone(demoCompetitors),
  sources: clone(demoSources),
  gaps: clone(demoGaps),
  strategies: [clone(demoStrategy)],
  documents: [clone(demoDocument)],
  suggestions: clone(demoSuggestions),
  reviews: clone(demoReviews),
  pipelines: { [DEMO_PROJECT_ID]: clone(demoPipeline) },
  costs: { [DEMO_PROJECT_ID]: clone(demoRunCost) },
  integrations: [
    {
      id: 'int-1',
      featureKey: 'seo-audit',
      name: 'SEO Audit Module',
      description:
        'Teammate-built module. Runs a technical SEO audit against the brand site and folds the findings into the gap list.',
      status: 'available',
      connectedAt: null,
      config: null,
    },
    {
      id: 'int-2',
      featureKey: 'social-scheduler',
      name: 'Social Scheduler',
      description:
        'Teammate-built module. Pushes approved stage-9 content assets into a posting calendar.',
      status: 'available',
      connectedAt: null,
      config: null,
    },
    {
      id: 'int-3',
      featureKey: 'sentiment-tracker',
      name: 'Review Sentiment Tracker',
      description:
        'Teammate-built module. Continuous sentiment scan over review sources, feeding the Insight Agent.',
      status: 'coming_soon',
      connectedAt: null,
      config: null,
    },
  ],
}

/* --------------------------------------------------------------- timing --- */

/** Realistic-feeling latency without making the demo tedious. */
const LATENCY_MS = 320

/** How long each simulated agent stage takes, in ms. */
const STAGE_DURATION: Partial<Record<StageId, number>> = {
  2: 9_000,
  3: 6_000,
  4: 7_500,
  6: 10_000,
  8: 5_000,
  9: 6_000,
}

const STAGE_MESSAGES: Partial<Record<StageId, string[]>> = {
  2: [
    'Resolving competitor landing pages…',
    'Collecting social posts…',
    'Reading customer reviews…',
    'Scanning forums and trade news…',
  ],
  3: [
    'Cleaning and de-duplicating text…',
    'Chunking documents…',
    'Generating embeddings…',
    'Writing vectors to the project collection…',
  ],
  4: [
    'Retrieving relevant chunks…',
    'Comparing brand against competitors…',
    'Identifying gaps and opportunities…',
    'Scoring confidence and attaching evidence…',
  ],
  6: [
    'Strategist drafting initiatives…',
    'Critic reviewing for feasibility…',
    'Critic challenging unsupported claims…',
    'Merging the revised strategy…',
  ],
  8: ['Assembling sections…', 'Formatting the implementation plan…', 'Rendering the document…'],
  9: ['Mapping initiatives to assets…', 'Drafting content suggestions…'],
}

/** Timers per project, so a running simulation can be cancelled on reset. */
const timers = new Map<string, ReturnType<typeof setInterval>>()

function getPipeline(projectId: string): PipelineState {
  const existing = state.pipelines[projectId]
  if (existing) return existing
  const fresh = emptyPipeline(projectId)
  state.pipelines[projectId] = fresh
  return fresh
}

function emptyPipeline(projectId: string): PipelineState {
  const stages = {} as Record<StageId, StageState>
  for (let id = 1; id <= 9; id += 1) {
    stages[id as StageId] = {
      id: id as StageId,
      status: id === 1 ? 'complete' : 'idle',
      progress: id === 1 ? 100 : 0,
      startedAt: id === 1 ? new Date().toISOString() : null,
      completedAt: id === 1 ? new Date().toISOString() : null,
      message: null,
      error: null,
      metrics: null,
    }
  }
  return {
    projectId,
    currentStage: 1,
    blockedOn: null,
    updatedAt: new Date().toISOString(),
    stages,
  }
}

/**
 * Advances one stage over its simulated duration, then either stops at a
 * human checkpoint or rolls straight into the next automated stage.
 */
function runStage(projectId: string, stageId: StageId): void {
  const pipeline = getPipeline(projectId)
  const stage = pipeline.stages[stageId]
  const duration = STAGE_DURATION[stageId] ?? 5_000
  const messages = STAGE_MESSAGES[stageId] ?? []
  const startedAt = Date.now()

  stage.status = 'running'
  stage.progress = 0
  stage.startedAt = new Date().toISOString()
  stage.error = null
  pipeline.currentStage = stageId
  pipeline.blockedOn = null
  pipeline.updatedAt = new Date().toISOString()

  const existingTimer = timers.get(projectId)
  if (existingTimer) clearInterval(existingTimer)

  const timer = setInterval(() => {
    const elapsed = Date.now() - startedAt
    const progress = Math.min(100, Math.round((elapsed / duration) * 100))
    stage.progress = progress
    const messageIndex = Math.min(
      messages.length - 1,
      Math.floor((progress / 100) * messages.length),
    )
    stage.message = messages[messageIndex] ?? null
    pipeline.updatedAt = new Date().toISOString()

    if (progress < 100) return

    clearInterval(timer)
    timers.delete(projectId)
    completeStage(projectId, stageId, Date.now() - startedAt)
  }, 250)

  timers.set(projectId, timer)
}

function completeStage(projectId: string, stageId: StageId, durationMs: number): void {
  const pipeline = getPipeline(projectId)
  const stage = pipeline.stages[stageId]
  const project = state.projects.find((p) => p.id === projectId)

  stage.status = 'complete'
  stage.progress = 100
  stage.completedAt = new Date().toISOString()
  stage.metrics = stageMetrics(projectId, stageId, durationMs)
  stage.message = stageSummary(projectId, stageId)

  // Materialise whatever the stage produced.
  if (stageId === 2) seedSources(projectId)
  if (stageId === 4) seedGaps(projectId)
  if (stageId === 6) seedStrategy(projectId)
  if (stageId === 8) seedDocument(projectId)
  if (stageId === 9) seedSuggestions(projectId)

  const next = (stageId + 1) as StageId
  if (next > 9) {
    pipeline.currentStage = 9
    pipeline.blockedOn = null
    if (project) project.status = 'complete'
    pipeline.updatedAt = new Date().toISOString()
    return
  }

  // Stages 5 and 7 are the mandatory human checkpoints: park and wait.
  if (next === 5 || next === 7) {
    const checkpoint = pipeline.stages[next]
    checkpoint.status = 'awaiting_human'
    checkpoint.startedAt = new Date().toISOString()
    checkpoint.message =
      next === 5
        ? 'Waiting for you to prioritise the identified gaps'
        : 'Waiting for your final approval of the strategy'
    pipeline.currentStage = next
    pipeline.blockedOn = next
    pipeline.updatedAt = new Date().toISOString()
    if (project) {
      project.status = 'awaiting_review'
      project.currentStage = next
    }
    return
  }

  if (project) project.currentStage = next
  runStage(projectId, next)
}

function stageMetrics(
  projectId: string,
  stageId: StageId,
  durationMs: number,
): StageState['metrics'] {
  const counts: Partial<Record<StageId, number>> = {
    2: state.sources.filter((s) => s.projectId === projectId).length || 7,
    3: 196,
    4: state.gaps.filter((g) => g.projectId === projectId).length || 7,
    6: 4,
    8: 6,
    9: 5,
  }
  const tokens: Partial<Record<StageId, number>> = {
    2: 42_100,
    3: 61_400,
    4: 38_900,
    6: 34_600,
    8: 7_260,
    9: 5_400,
  }
  const usedTokens = tokens[stageId] ?? null
  return {
    itemsProcessed: counts[stageId] ?? 1,
    durationMs,
    tokensUsed: usedTokens,
    costUsd: usedTokens === null ? null : Number((usedTokens * 0.000012).toFixed(3)),
  }
}

function stageSummary(projectId: string, stageId: StageId): string | null {
  switch (stageId) {
    case 2:
      return `${state.sources.filter((s) => s.projectId === projectId).length} sources collected`
    case 3:
      return '196 chunks embedded into the project collection'
    case 4:
      return `${state.gaps.filter((g) => g.projectId === projectId).length} gaps identified`
    case 6:
      return '4 initiatives generated, 5 critic interventions'
    case 8:
      return 'Strategy document ready to export'
    case 9:
      return '5 content assets suggested'
    default:
      return null
  }
}

/* ----------------------------------------- materialising stage outputs ---- */

function seedSources(projectId: string): void {
  if (state.sources.some((s) => s.projectId === projectId)) return
  state.sources.push(
    ...clone(demoSources).map((source) => ({
      ...source,
      id: makeId('src'),
      projectId,
      scrapedAt: new Date().toISOString(),
    })),
  )
}

function seedGaps(projectId: string): void {
  if (state.gaps.some((g) => g.projectId === projectId)) return
  state.gaps.push(
    ...clone(demoGaps).map((gap) => ({
      ...gap,
      id: makeId('gap'),
      projectId,
      decision: 'pending' as GapDecision,
      createdAt: new Date().toISOString(),
    })),
  )
  const project = state.projects.find((p) => p.id === projectId)
  if (project) project.gapCount = state.gaps.filter((g) => g.projectId === projectId).length
}

function seedStrategy(projectId: string): void {
  if (state.strategies.some((s) => s.projectId === projectId)) return
  const accepted = state.gaps.filter(
    (g) => g.projectId === projectId && g.decision === 'accepted',
  )
  state.strategies.push({
    ...clone(demoStrategy),
    id: makeId('strategy'),
    projectId,
    status: 'awaiting_approval',
    addressedGapIds: accepted.map((g) => g.id),
    generatedAt: new Date().toISOString(),
    approvedAt: null,
  })
}

function seedDocument(projectId: string): void {
  if (state.documents.some((d) => d.projectId === projectId)) return
  const strategy = state.strategies.find((s) => s.projectId === projectId)
  state.documents.push({
    ...clone(demoDocument),
    id: makeId('doc'),
    projectId,
    strategyId: strategy?.id ?? 'unknown',
    generatedAt: new Date().toISOString(),
  })
}

function seedSuggestions(projectId: string): void {
  if (state.suggestions.some((s) => s.projectId === projectId)) return
  const strategy = state.strategies.find((s) => s.projectId === projectId)
  state.suggestions.push(
    ...clone(demoSuggestions).map((suggestion, index) => ({
      ...suggestion,
      id: makeId('sug'),
      projectId,
      linkedInitiativeId: strategy?.initiatives[index % strategy.initiatives.length]?.id ?? null,
      createdAt: new Date().toISOString(),
    })),
  )
}

/* ------------------------------------------------------------ the API ----- */

export const mockApi = {
  /* projects */
  async listProjects(): Promise<Project[]> {
    await sleep(LATENCY_MS)
    return clone(state.projects)
  },

  async getProject(id: string): Promise<Project> {
    await sleep(LATENCY_MS)
    const project = state.projects.find((p) => p.id === id)
    if (!project) throw new Error('Project not found')
    return clone(project)
  },

  async createProject(input: {
    brandName: string
    brandWebsite: string | null
    brandDescription: string
    industry: Project['industry']
    targetAudience: string
    objectives: string[]
    competitors: Omit<Competitor, 'id' | 'projectId' | 'createdAt'>[]
  }): Promise<Project> {
    await sleep(LATENCY_MS)
    const id = makeId('proj')
    const project: Project = {
      id,
      ownerId: DEMO_USER_ID,
      brandName: input.brandName,
      brandWebsite: input.brandWebsite,
      brandDescription: input.brandDescription,
      industry: input.industry,
      targetAudience: input.targetAudience,
      objectives: input.objectives,
      status: 'draft',
      currentStage: 1,
      competitorCount: input.competitors.length,
      gapCount: 0,
      isDemo: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    state.projects.unshift(project)
    state.competitors.push(
      ...input.competitors.map((competitor) => ({
        ...competitor,
        id: makeId('comp'),
        projectId: id,
        createdAt: new Date().toISOString(),
      })),
    )
    state.pipelines[id] = emptyPipeline(id)
    return clone(project)
  },

  async deleteProject(id: string): Promise<void> {
    await sleep(LATENCY_MS)
    const timer = timers.get(id)
    if (timer) {
      clearInterval(timer)
      timers.delete(id)
    }
    state.projects = state.projects.filter((p) => p.id !== id)
    delete state.pipelines[id]
  },

  async listCompetitors(projectId: string): Promise<Competitor[]> {
    await sleep(LATENCY_MS)
    return clone(state.competitors.filter((c) => c.projectId === projectId))
  },

  /* pipeline */
  async getPipeline(projectId: string): Promise<PipelineState> {
    // No artificial latency: this is polled, and the stepper should feel live.
    return clone(getPipeline(projectId))
  },

  async startPipeline(projectId: string): Promise<PipelineState> {
    await sleep(LATENCY_MS)
    const project = state.projects.find((p) => p.id === projectId)
    if (project) project.status = 'running'
    runStage(projectId, 2)
    return clone(getPipeline(projectId))
  },

  async resetPipeline(projectId: string): Promise<PipelineState> {
    await sleep(LATENCY_MS)
    const timer = timers.get(projectId)
    if (timer) {
      clearInterval(timer)
      timers.delete(projectId)
    }
    state.pipelines[projectId] = emptyPipeline(projectId)
    state.gaps = state.gaps.filter((g) => g.projectId !== projectId)
    state.sources = state.sources.filter((s) => s.projectId !== projectId)
    state.strategies = state.strategies.filter((s) => s.projectId !== projectId)
    state.documents = state.documents.filter((d) => d.projectId !== projectId)
    state.suggestions = state.suggestions.filter((s) => s.projectId !== projectId)
    state.reviews = state.reviews.filter((r) => r.projectId !== projectId)
    const project = state.projects.find((p) => p.id === projectId)
    if (project) {
      project.status = 'draft'
      project.currentStage = 1
      project.gapCount = 0
    }
    return clone(state.pipelines[projectId] as PipelineState)
  },

  /* sources */
  async listSources(projectId: string): Promise<ScrapedSource[]> {
    await sleep(LATENCY_MS)
    return clone(state.sources.filter((s) => s.projectId === projectId))
  },

  /* gaps + HITL #1 */
  async listGaps(projectId: string): Promise<Gap[]> {
    await sleep(LATENCY_MS)
    return clone(state.gaps.filter((g) => g.projectId === projectId))
  },

  async updateGap(
    projectId: string,
    gapId: string,
    patch: { decision?: GapDecision; userPriority?: GapPriority | null; reviewerNote?: string | null },
  ): Promise<Gap> {
    await sleep(160)
    const gap = state.gaps.find((g) => g.id === gapId && g.projectId === projectId)
    if (!gap) throw new Error('Gap not found')
    Object.assign(gap, patch)
    return clone(gap)
  },

  async submitGapReview(
    projectId: string,
    input: { notes: string | null; acceptedGapIds: string[] },
  ): Promise<HitlReview> {
    await sleep(LATENCY_MS)
    const review: HitlReview = {
      id: makeId('review'),
      projectId,
      stage: 5,
      reviewerId: DEMO_USER_ID,
      reviewerName: 'Demo Reviewer',
      decision: 'approved',
      notes: input.notes,
      affectedIds: input.acceptedGapIds,
      createdAt: new Date().toISOString(),
    }
    state.reviews.push(review)

    const pipeline = getPipeline(projectId)
    const checkpoint = pipeline.stages[5]
    checkpoint.status = 'complete'
    checkpoint.progress = 100
    checkpoint.completedAt = new Date().toISOString()
    checkpoint.message = `${input.acceptedGapIds.length} gaps prioritised`
    runStage(projectId, 6)

    return clone(review)
  },

  /* strategy + HITL #2 */
  async getStrategy(projectId: string): Promise<Strategy | null> {
    await sleep(LATENCY_MS)
    const strategy = state.strategies.find((s) => s.projectId === projectId)
    return strategy ? clone(strategy) : null
  },

  async submitStrategyReview(
    projectId: string,
    input: { decision: HitlReview['decision']; notes: string | null; flaggedIds: string[] },
  ): Promise<HitlReview> {
    await sleep(LATENCY_MS)
    const review: HitlReview = {
      id: makeId('review'),
      projectId,
      stage: 7,
      reviewerId: DEMO_USER_ID,
      reviewerName: 'Demo Reviewer',
      decision: input.decision,
      notes: input.notes,
      affectedIds: input.flaggedIds,
      createdAt: new Date().toISOString(),
    }
    state.reviews.push(review)

    const strategy = state.strategies.find((s) => s.projectId === projectId)
    const pipeline = getPipeline(projectId)
    const checkpoint = pipeline.stages[7]

    if (input.decision === 'approved') {
      if (strategy) {
        strategy.status = 'approved'
        strategy.approvedAt = new Date().toISOString()
      }
      checkpoint.status = 'complete'
      checkpoint.progress = 100
      checkpoint.completedAt = new Date().toISOString()
      checkpoint.message = 'Strategy approved for execution'
      runStage(projectId, 8)
    } else {
      // Revision requested or rejected: send it back to the Strategist.
      if (strategy) {
        strategy.status = 'revision_requested'
        strategy.version += 1
      }
      checkpoint.status = 'idle'
      checkpoint.message = null
      state.strategies = state.strategies.filter((s) => s.projectId !== projectId)
      runStage(projectId, 6)
    }
    return clone(review)
  },

  async listReviews(projectId: string): Promise<HitlReview[]> {
    await sleep(LATENCY_MS)
    return clone(state.reviews.filter((r) => r.projectId === projectId))
  },

  /* document */
  async getDocument(projectId: string): Promise<StrategyDocument | null> {
    await sleep(LATENCY_MS)
    const doc = state.documents.find((d) => d.projectId === projectId)
    return doc ? clone(doc) : null
  },

  /* automation */
  async listSuggestions(projectId: string): Promise<ContentSuggestion[]> {
    await sleep(LATENCY_MS)
    return clone(state.suggestions.filter((s) => s.projectId === projectId))
  },

  async generateSuggestions(projectId: string): Promise<ContentSuggestion[]> {
    await sleep(900)
    seedSuggestions(projectId)
    return clone(state.suggestions.filter((s) => s.projectId === projectId))
  },

  async updateSuggestion(
    projectId: string,
    suggestionId: string,
    patch: { status?: ContentSuggestion['status']; body?: string | null },
  ): Promise<ContentSuggestion> {
    await sleep(400)
    const suggestion = state.suggestions.find(
      (s) => s.id === suggestionId && s.projectId === projectId,
    )
    if (!suggestion) throw new Error('Suggestion not found')
    Object.assign(suggestion, patch)
    return clone(suggestion)
  },

  async draftSuggestion(projectId: string, suggestionId: string): Promise<ContentSuggestion> {
    await sleep(1400)
    const suggestion = state.suggestions.find(
      (s) => s.id === suggestionId && s.projectId === projectId,
    )
    if (!suggestion) throw new Error('Suggestion not found')
    suggestion.status = 'generated'
    suggestion.body = draftBodyFor(suggestion)
    return clone(suggestion)
  },

  /* cost */
  async getRunCost(projectId: string): Promise<RunCost> {
    await sleep(LATENCY_MS)
    const existing = state.costs[projectId]
    if (existing) return clone(existing)

    const pipeline = getPipeline(projectId)
    const byStage = Object.values(pipeline.stages)
      .filter((stage) => stage.metrics?.tokensUsed)
      .map((stage) => ({
        stage: stage.id,
        tokens: stage.metrics?.tokensUsed ?? 0,
        costUsd: stage.metrics?.costUsd ?? 0,
      }))
    return {
      projectId,
      totalTokens: byStage.reduce((sum, row) => sum + row.tokens, 0),
      totalCostUsd: Number(byStage.reduce((sum, row) => sum + row.costUsd, 0).toFixed(3)),
      byStage,
    }
  },

  /* integrations */
  async listIntegrations(): Promise<Integration[]> {
    await sleep(LATENCY_MS)
    return clone(state.integrations)
  },

  async toggleIntegration(id: string): Promise<Integration> {
    await sleep(500)
    const integration = state.integrations.find((i) => i.id === id)
    if (!integration) throw new Error('Integration not found')
    if (integration.status === 'coming_soon') {
      throw new Error('This module is not available yet.')
    }
    const connecting = integration.status !== 'connected'
    integration.status = connecting ? 'connected' : 'available'
    integration.connectedAt = connecting ? new Date().toISOString() : null
    return clone(integration)
  },

  /* contact */
  async submitContact(): Promise<void> {
    await sleep(700)
  },
}

function draftBodyFor(suggestion: ContentSuggestion): string {
  return [
    `# ${suggestion.title}`,
    '',
    `**Angle.** ${suggestion.angle}`,
    '',
    `**Channel.** ${suggestion.channel}`,
    '',
    suggestion.targetKeywords.length > 0
      ? `**Target keywords.** ${suggestion.targetKeywords.join(', ')}`
      : '**Target keywords.** Not applicable for this channel.',
    '',
    '---',
    '',
    'This is placeholder copy produced by the demo generator. In a live run the',
    'Scalability Agent drafts this section against the approved strategy and the',
    'retrieved competitor corpus, citing the same evidence trail used earlier in',
    'the pipeline.',
  ].join('\n')
}
