/**
 * The 9-stage pipeline from the FYP defence deck, as types.
 * These mirror `backend/app/models/pipeline.py` one-for-one: change both together.
 */

export const STAGE_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9] as const
export type StageId = (typeof STAGE_IDS)[number]

/** Who drives a stage. Determines the card treatment in the pipeline UI. */
export type StageActor = 'human' | 'agent' | 'system'

export type StageStatus = 'idle' | 'running' | 'awaiting_human' | 'complete' | 'error' | 'skipped'

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
  /** Daraz projects: the Daraz Gap Engine's measurements, one per competitor. */
  daraz?: DarazPart[] | null
}

/** TreeSHAP: what pushed one account's chance of "good" up or down. */
export interface GradeDrivers {
  /** The average account's chance of "good", in percent. */
  start: number
  items: { label: string; value_text: string; points: number; actionable: boolean }[]
  /** Everything outside the top 5, so start + pushes = final. */
  others_points: number
  final: number
}

/** How one account did against accounts of a similar size (measured, not predicted). */
export interface ResultsSide {
  percentile: number
  quarter: number
  posts: number
  band: string
}

/** Kept in snake_case: it is passed through from the analysis as-is. */
export interface HabitRow {
  label: string
  you: string
  competitor: string
  typical: string | null
  you_percentile: number | null
  competitor_percentile: number | null
}

/** One line of the content check-up, measured by the trained models and written in plain words. */
export interface ComparisonRow {
  key: string
  kind: 'caption' | 'picture' | 'reel' | DarazKind
  /** do_more: works for jewellery shops and you rarely do it · doing_well: works and you do it ·
   *  competitor_does: your competitor clearly does it more (not proven to work). */
  group: 'do_more' | 'doing_well' | 'competitor_does' | 'fine'
  title: string
  /** What jewellery shops gained from it, in words ("" when not proven). */
  why: string
  tip: string
  you_text: string
  competitor_text: string | null
  you_share?: number
  competitor_share?: number | null
  /** Daraz: the top 20 listings' typical value for this lever, in words. */
  typical?: string
}

export type DarazKind =
  'daraz_price' | 'daraz_offer' | 'daraz_title' | 'daraz_photos' | 'daraz_content' | 'daraz_reviews'

/** One side of "Where you stand": results, never gaps. */
export interface DarazStanding {
  rank: number | null
  sold: number | null
  reviews: number | null
  rating: number | null
  price: number | null
  title: string | null
}

/** What the Daraz Gap Engine measured for one competitor listing. */
export interface DarazPart {
  competitor: string | null
  search_query: string
  standing: {
    search_word: string | null
    you: DarazStanding
    competitor: DarazStanding
    top_listings: number
    /** Set when no lever is outside the top listings range. */
    note?: string
  }
  comparison: ComparisonRow[]
  strengths: { kind: string; label: string; detail: string }[]
  reviews: { you: number; competitor: number; compared: boolean; note?: string }
  levers_proven: string[]
}

export interface AnalysisPart {
  competitor: string
  results?: {
    status: 'ran' | 'skipped'
    reason: string
    context?: 'behind' | 'even' | 'ahead'
    user?: ResultsSide
    competitor?: ResultsSide
    peers?: number
  }
  habits?: {
    status: 'ran' | 'skipped'
    reason: string
    checked?: number
    related?: number
    gaps: number
    /** Side-by-side comparison only: habits are never turned into gaps. */
    table?: HabitRow[]
  }
  formats?: {
    user?: Record<string, number>
    competitor?: Record<string, number>
    gaps?: number
    weak_spots?: number
    worth_testing?: number
  }
  /** The trained grader and its SHAP drivers: shown under "technical details" only. */
  model?: {
    status: 'ran' | 'skipped'
    reason: string
    user_grade?: string
    user_good_chance?: number
    competitor_grade?: string
    competitor_good_chance?: number
    user_drivers?: GradeDrivers
    competitor_drivers?: GradeDrivers
  }
  /** What the posts are about (topic model) and which hashtags do well. */
  topics?: {
    status: 'ran' | 'skipped' | 'error' | 'off'
    reason: string
    gaps?: number
    weak_spots?: number
    hashtag_gaps?: number
    hashtag_worth_testing?: number
    coverage?: { user: string; competitor: string }
    topics?: { user: Record<string, number>; competitor: Record<string, number> }
  }
  /** Picture and video scores from the models trained on people's ratings. */
  media?: {
    status: 'ran' | 'not_trained' | 'skipped' | 'error' | string
    reason: string
    gaps?: number
    models?: Record<
      string,
      {
        label: string
        scale: string
        available: boolean
        trained_on?: string
        n_train?: number
        srcc?: number
        description?: string
        baseline_srcc?: number | null
        problem?: string
      }
    >
    scored?: Record<
      'user' | 'competitor',
      { posts: number; scored: number; failed: number; videos_skipped: number }
    >
  }
  /** What works for the seller, measured on their own posts. Not gaps. */
  strengths?: { kind: string; label: string; detail: string }[]
  /** Layer 6: what the captions say, what the pictures show, how the reels open (trained models). */
  content?: {
    status: 'ran' | 'skipped' | 'error' | 'not_available'
    reason?: string
    /** Every measured trait side by side: you, the competitor and the typical jewellery shop. */
    comparison?: ComparisonRow[]
  }
  /** What the Strategist will read: strengths, weak spots, things to try. */
  report?: {
    works_for_you: { kind: string; label: string; detail: string }[]
    weak_spots: { id: string; title: string }[]
    to_try: { id: string; title: string }[]
    /** Real differences that are not proven yet: things to test. */
    worth_testing?: { id: string; title: string }[]
  }
}

export interface PipelineState {
  projectId: string
  currentStage: StageId
  stages: Record<StageId, StageState>
  /** Set when the pipeline is parked at stage 5 or 7 waiting on a person. */
  blockedOn: StageId | null
  updatedAt: string
}
