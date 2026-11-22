import type { StageDefinition, StageId, StageKey, StageStatus } from '@/types/pipeline'

/**
 * The canonical 9-stage definition, straight from section 1.3 of the FYP deck.
 * Everything else in the pipeline UI reads from here, routes, colours, icons,
 * copy. Adding a stage means adding a row here and a `--stage-N` token.
 */
export const PIPELINE_STAGES: readonly StageDefinition[] = [
  {
    id: 1,
    key: 'input',
    title: 'User Input',
    summary: 'You provide brand details and the competitors worth watching.',
    actor: 'human',
    colorToken: 'stage-1',
    icon: 'PencilLine',
    route: null,
    isCheckpoint: false,
  },
  {
    id: 2,
    key: 'scout',
    title: 'Scout Engine',
    summary: 'Reads the links you gave: Instagram posts, web pages or product listings. It collects; it decides nothing.',
    actor: 'system',
    colorToken: 'stage-2',
    icon: 'Radar',
    route: null,
    isCheckpoint: false,
  },
  {
    id: 3,
    key: 'preprocess',
    title: 'Preprocessing & Storage',
    summary: 'Cleans, chunks, embeds and vectorises the corpus into ChromaDB.',
    actor: 'system',
    colorToken: 'stage-3',
    icon: 'Database',
    route: null,
    isCheckpoint: false,
  },
  {
    id: 4,
    key: 'insight',
    title: 'Gap Engine',
    summary: 'Compares both accounts post by post with statistics and a trained model, and keeps the differences that hold up.',
    actor: 'system',
    colorToken: 'stage-4',
    icon: 'Lightbulb',
    route: 'insights',
    isCheckpoint: false,
  },
  {
    id: 5,
    key: 'review_gaps',
    title: 'Human Review. Gap Refinement',
    summary: 'You review the identified gaps and prioritise the ones that matter.',
    actor: 'human',
    colorToken: 'stage-5',
    icon: 'ListChecks',
    route: 'review-gaps',
    isCheckpoint: true,
  },
  {
    id: 6,
    key: 'strategy',
    title: 'Strategist + Critic',
    summary:
      'The Strategist drafts data-driven strategy; the Critic challenges it for strength, clarity and feasibility.',
    actor: 'agent',
    colorToken: 'stage-6',
    icon: 'Swords',
    route: 'strategy',
    isCheckpoint: false,
  },
  {
    id: 7,
    key: 'review_strategy',
    title: 'Human Review. Final Approval',
    summary: 'You review the refined strategy and approve it for execution.',
    actor: 'human',
    colorToken: 'stage-7',
    icon: 'ShieldCheck',
    route: 'review-strategy',
    isCheckpoint: true,
  },
  {
    id: 8,
    key: 'document',
    title: 'Strategy Document',
    summary: 'Generates the full strategy document with step-by-step implementation guidance.',
    actor: 'system',
    colorToken: 'stage-8',
    icon: 'FileText',
    route: 'document',
    isCheckpoint: false,
  },
  {
    id: 9,
    key: 'automation',
    title: 'Scalability & Automation',
    summary: 'Suggests and drafts the follow-on content: blogs, SEO briefs, social and ads.',
    actor: 'agent',
    colorToken: 'stage-9',
    icon: 'Sparkles',
    route: 'automation',
    isCheckpoint: false,
  },
] as const

/** The two mandatory human checkpoints. Not optional UX, the trust story. */
export const CHECKPOINT_STAGES: readonly StageId[] = [5, 7]

export function getStage(id: StageId): StageDefinition {
  const stage = PIPELINE_STAGES.find((s) => s.id === id)
  if (!stage) throw new Error(`Unknown pipeline stage: ${id}`)
  return stage
}

export function getStageByKey(key: StageKey): StageDefinition {
  const stage = PIPELINE_STAGES.find((s) => s.key === key)
  if (!stage) throw new Error(`Unknown pipeline stage key: ${key}`)
  return stage
}

export function isCheckpoint(id: StageId): boolean {
  return CHECKPOINT_STAGES.includes(id)
}

/** Human-facing label for each status. Used by badges and screen readers. */
export const STAGE_STATUS_LABEL: Record<StageStatus, string> = {
  idle: 'Not started',
  running: 'Running',
  awaiting_human: 'Awaiting your input',
  complete: 'Complete',
  error: 'Failed',
  skipped: 'Skipped',
}

/**
 * Status -> Tailwind classes. Kept in one place so the stepper, the sidebar
 * badges and the project list can never drift apart.
 */
export const STAGE_STATUS_STYLES: Record<
  StageStatus,
  { dot: string; text: string; ring: string; badge: string }
> = {
  idle: {
    dot: 'bg-muted-foreground/40',
    text: 'text-muted-foreground',
    ring: 'ring-border/20',
    badge: 'bg-muted text-muted-foreground',
  },
  running: {
    dot: 'bg-primary',
    text: 'text-primary',
    ring: 'ring-primary/40',
    badge: 'bg-primary/15 text-primary',
  },
  awaiting_human: {
    dot: 'bg-brand-butter-cream',
    text: 'text-brand-butter-cream',
    ring: 'ring-brand-butter-cream/50',
    badge: 'bg-brand-butter-cream/15 text-brand-butter-cream',
  },
  complete: {
    dot: 'bg-success',
    text: 'text-success',
    ring: 'ring-success/35',
    badge: 'bg-success/15 text-success',
  },
  error: {
    dot: 'bg-destructive',
    text: 'text-destructive',
    ring: 'ring-destructive/40',
    badge: 'bg-destructive/15 text-destructive',
  },
  skipped: {
    dot: 'bg-muted-foreground/30',
    text: 'text-muted-foreground/70',
    ring: 'ring-border/10',
    badge: 'bg-muted/60 text-muted-foreground/70',
  },
}

export const ACTOR_LABEL: Record<StageDefinition['actor'], string> = {
  human: 'You',
  agent: 'AI Agent',
  system: 'System',
}
