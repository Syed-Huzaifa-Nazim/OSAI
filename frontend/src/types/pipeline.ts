/**
 * The 9-stage pipeline from the FYP defence deck, as types.
 * These mirror `backend/app/models/pipeline.py` one-for-one: change both together.
 */

export const STAGE_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9] as const
export type StageId = (typeof STAGE_IDS)[number]

/** Who drives a stage. Determines the card treatment in the pipeline UI. */
export type StageActor = 'human' | 'agent' | 'system'

export type StageStatus =
  | 'idle'
  | 'running'
  | 'awaiting_human'
  | 'complete'
  | 'error'
  | 'skipped'

export interface StageDefinition {
  id: StageId
  /** URL-safe key used in API paths and route params. */
  key: StageKey
  title: string
  /** One line, deck wording. */
  summary: string
  actor: StageActor
  /** Tailwind token suffix -> `bg-stage-4`, `text-stage-4`... */
  colorToken: `stage-${StageId}`
  /** lucide-react icon name, resolved in components/pipeline/stage-icon.tsx */
  icon: string
  /** Route within the project workspace this stage owns, if any. */
  route: string | null
  /** True for stages 5 and 7, the mandatory HITL checkpoints. */
  isCheckpoint: boolean
}

export type StageKey =
  | 'input'
  | 'scout'
  | 'preprocess'
  | 'insight'
  | 'review_gaps'
  | 'strategy'
  | 'review_strategy'
  | 'document'
  | 'automation'

export interface StageState {
  id: StageId
  status: StageStatus
  /** 0-100. Only meaningful while `status === 'running'`. */
  progress: number
  startedAt: string | null
  completedAt: string | null
  /** Short human-readable line shown under the stage title while running. */
  message: string | null
  error: string | null
  /** Populated for agent stages once a run finishes. */
  metrics: StageMetrics | null
}

export interface StageMetrics {
  /** Sources touched, chunks embedded, gaps found. Whatever the stage counts. */
  itemsProcessed: number
  durationMs: number
  /** Null when the stage makes no LLM calls (stages 1, 3, 5, 7). */
  tokensUsed: number | null
  costUsd: number | null
  /** Why parts of the stage produced nothing (e.g. too few comments). */
  notes?: string[]
  /** Stage 4 (Instagram): what each part of the analysis found, per competitor. */
  analysis?: AnalysisPart[] | null
}

/** Kept in snake_case: it is passed through from the analysis as-is. */
export interface AnalysisPart {
  competitor: string
  model: {
    status: 'ran' | 'skipped'
    reason: string
    user_grade?: string
    user_good_chance?: number
    competitor_grade?: string
    competitor_good_chance?: number
    difference?: number
    clear_difference?: boolean
    low_confidence?: boolean
    habit_gaps: number
  }
  media_mix: {
    user?: Record<string, number>
    competitor?: Record<string, number>
    gaps?: number
  }
  trend: { user?: number | null; competitor?: number | null; gaps?: number }
  comments: {
    status: 'ran' | 'skipped'
    reason: string
    user?: { comments: number; scored: number; positive: number | null; negative: number | null }
    competitor?: { comments: number; scored: number; positive: number | null; negative: number | null }
    gaps: number
  }
  media_quality: { status: string; reason: string }
}

export interface PipelineState {
  projectId: string
  currentStage: StageId
  stages: Record<StageId, StageState>
  /** Set when the pipeline is parked at stage 5 or 7 waiting on a person. */
  blockedOn: StageId | null
  updatedAt: string
}