import { describe, expect, it } from 'vitest'
import { mockApi } from '@/lib/mock/mock-api'
import { DEMO_PROJECT_ID } from '@/lib/mock/demo-data'

/**
 * Gap triage against the seeded demo project.
 *
 * Kept in its own file on purpose: resetting the pipeline clears the gaps it
 * produced, so a test that resets and a test that reads the seed cannot share
 * module state without one depending on the other's ordering. Vitest isolates
 * per file, which gives each set a clean seed.
 */
describe('mock gap triage', () => {
  it('produces gaps that each carry their evidence', async () => {
    const gaps = await mockApi.listGaps(DEMO_PROJECT_ID)

    expect(gaps.length).toBeGreaterThan(0)
    for (const gap of gaps) {
      // An uncited gap would defeat the point of the whole retrieval step.
      expect(gap.evidence.length).toBeGreaterThan(0)
      expect(gap.evidence[0]?.sourceUrl).toMatch(/^https?:\/\//)
      expect(gap.evidence[0]?.quote).toBeTruthy()
    }
  })

  it('starts every gap untriaged, so the checkpoint has real work to do', async () => {
    const gaps = await mockApi.listGaps(DEMO_PROJECT_ID)
    expect(gaps.every((gap) => gap.decision === 'pending')).toBe(true)
  })

  it('records a gap decision without discarding the agent priority', async () => {
    const [gap] = await mockApi.listGaps(DEMO_PROJECT_ID)
    expect(gap).toBeDefined()

    const updated = await mockApi.updateGap(DEMO_PROJECT_ID, gap!.id, {
      decision: 'accepted',
      userPriority: 'low',
    })

    expect(updated.decision).toBe('accepted')
    expect(updated.userPriority).toBe('low')
    // The disagreement between agent and human stays visible.
    expect(updated.priority).toBe(gap!.priority)
  })

  it('keeps a reviewer note against the gap', async () => {
    const [gap] = await mockApi.listGaps(DEMO_PROJECT_ID)
    const updated = await mockApi.updateGap(DEMO_PROJECT_ID, gap!.id, {
      reviewerNote: 'Not a priority this quarter.',
    })
    expect(updated.reviewerNote).toBe('Not a priority this quarter.')
  })
})
