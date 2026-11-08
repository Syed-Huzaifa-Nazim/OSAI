import type { PipelineState } from '@/types/pipeline'

/**
 * Where a scrape-and-display run has got to.
 *
 * Every comparison type runs the same two stages and then stops: stage 2 reads
 * both sides, stage 3 embeds their text. Shared by the pages that show that
 * progress, so a product comparison and a website comparison can never drift
 * into reporting the same run differently.
 */
export type ScrapePhase = 'idle' | 'scraping' | 'embedding' | 'failed' | 'done'

export function phaseOf(state: PipelineState): { phase: ScrapePhase; error: string | null } {
  const scrape = state.stages[2]
  const embed = state.stages[3]
  if (scrape.status === 'error') return { phase: 'failed', error: scrape.error }
  if (embed.status === 'error') return { phase: 'failed', error: embed.error }
  if (scrape.status === 'running') return { phase: 'scraping', error: null }
  if (embed.status === 'running') return { phase: 'embedding', error: null }
  if (embed.status === 'complete') return { phase: 'done', error: null }
  // Stage 2 finished but stage 3 has not been picked up yet: still working.
  if (scrape.status === 'complete') return { phase: 'embedding', error: null }
  return { phase: 'idle', error: null }
}
