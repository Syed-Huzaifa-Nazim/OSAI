import type { HeroStep } from '@/components/shared/project-hero'
import type { PipelineState, StageId } from '@/types/pipeline'

/**
 * The six steps a user sees, everywhere in the app and on the public pages.
 *
 * The system keeps nine internal stages (input, scraping, storage, gap finding, review, strategy + critic,
 * approval, document, content); a user does not need that detail, so they are grouped into these six.
 * Two of the six are the user's own decisions (marked `you`).
 */
export const USER_STEPS: readonly { label: string; you: boolean; stages: StageId[]; built: boolean }[] = [
  { label: 'Collect posts', you: false, stages: [1, 2, 3], built: true },
  { label: 'Find gaps', you: false, stages: [4], built: true },
  { label: 'Review gaps', you: true, stages: [5], built: true },
  { label: 'Strategy + critic', you: false, stages: [6], built: false },
  { label: 'Approve strategy', you: true, stages: [7], built: false },
  { label: 'Create content', you: false, stages: [8, 9], built: false },
]

const DONE = new Set(['complete', 'skipped'])
const ACTIVE = new Set(['running', 'awaiting_human', 'error'])

/**
 * Where a project is, step by step, from its pipeline state.
 * Steps that are not built yet show as locked on real projects (the seeded demo walks all of them).
 */
export function userSteps(pipeline: PipelineState | undefined, isRealProject: boolean): HeroStep[] {
  const stages = pipeline?.stages
  let currentGiven = false
  return USER_STEPS.map((step) => {
    if (isRealProject && !step.built) return { label: step.label, state: 'locked' as const }
    const statuses = step.stages.map((id) => stages?.[id]?.status ?? 'idle')
    if (statuses.every((status) => DONE.has(status))) return { label: step.label, state: 'done' as const }
    if (!currentGiven && (statuses.some((status) => ACTIVE.has(status)) || statuses.some((s) => s === 'idle'))) {
      currentGiven = true
      return { label: step.label, state: 'current' as const }
    }
    return { label: step.label, state: 'todo' as const }
  })
}

/** What each step does, in a shop owner's words (public pages and the sign-in panel). */
export const USER_STEP_TEXT: readonly string[] = [
  'We read your page and your competitor’s: Instagram posts, or Daraz and Alibaba listings.',
  'We compare both pages and find what works for them that you are not doing yet, with real posts as proof.',
  'You keep the gaps that matter to your shop and drop the rest. Nothing moves on without you.',
  'A plan is written from the gaps you kept, then checked by a second reviewer for weak or unsupported points.',
  'You approve the plan, or ask for changes.',
  'Captions, images and short reels are prepared for the plan you approved.',
]
