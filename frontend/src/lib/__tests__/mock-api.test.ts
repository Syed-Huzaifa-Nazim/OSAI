import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mockApi } from '@/lib/mock/mock-api'
import { DEMO_PROJECT_ID } from '@/lib/mock/demo-data'

/**
 * Demo mode is what a defence audience actually sees, so its state machine
 * deserves the same scrutiny as the real one, particularly that it stops at
 * the human checkpoints instead of running straight through.
 */
describe('mock pipeline', () => {
  beforeEach(async () => {
    await mockApi.resetPipeline(DEMO_PROJECT_ID)
  })

  afterEach(() => {
    // A test that installs fake timers must not leak them into the next one,
    // whose setup awaits a real timer.
    vi.useRealTimers()
  })

  it('serves the seeded demo project, badged as demo data', async () => {
    const project = await mockApi.getProject(DEMO_PROJECT_ID)
    expect(project.brandName).toBe('Verdant Roast')
    expect(project.isDemo).toBe(true)
  })

  it('starts every stage idle after a reset, except the intake', async () => {
    const pipeline = await mockApi.getPipeline(DEMO_PROJECT_ID)
    expect(pipeline.stages[1].status).toBe('complete')
    expect(pipeline.stages[2].status).toBe('idle')
    expect(pipeline.blockedOn).toBeNull()
  })

  it('parks at the gap checkpoint instead of running to completion', async () => {
    vi.useFakeTimers()

    // startPipeline awaits its own simulated latency, so the promise cannot be
    // awaited until the fake clock has been moved past it.
    const started = mockApi.startPipeline(DEMO_PROJECT_ID)
    await vi.advanceTimersByTimeAsync(1_000)
    await started

    // Long enough for stages 2, 3 and 4 to finish at their simulated speeds.
    await vi.advanceTimersByTimeAsync(40_000)

    const pipeline = await mockApi.getPipeline(DEMO_PROJECT_ID)
    expect(pipeline.stages[4].status).toBe('complete')
    expect(pipeline.stages[5].status).toBe('awaiting_human')
    expect(pipeline.blockedOn).toBe(5)
    // Stage 6 must not have started without a human decision.
    expect(pipeline.stages[6].status).toBe('idle')
  })
})
