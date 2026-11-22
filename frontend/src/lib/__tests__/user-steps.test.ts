import { describe, expect, it } from 'vitest'
import { userSteps, USER_STEPS } from '@/lib/user-steps'
import type { PipelineState } from '@/types/pipeline'

function pipeline(done: number[], active?: [number, string]): PipelineState {
  const stages: Record<number, { status: string }> = {}
  for (let id = 1; id <= 9; id++) stages[id] = { status: done.includes(id) ? 'complete' : 'idle' }
  if (active) stages[active[0]] = { status: active[1] }
  return { stages } as unknown as PipelineState
}

describe('the six user steps', () => {
  it('groups the nine internal stages into six, two of them the user’s', () => {
    expect(USER_STEPS.map((s) => s.label)).toEqual([
      'Collect posts', 'Find gaps', 'Review gaps', 'Strategy + critic', 'Approve strategy', 'Create content',
    ])
    expect(USER_STEPS.filter((s) => s.you).map((s) => s.label)).toEqual(['Review gaps', 'Approve strategy'])
    expect(USER_STEPS.flatMap((s) => s.stages).sort()).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9])
  })

  it('follows the project: done steps, the current one, and what comes next', () => {
    const steps = userSteps(pipeline([1, 2, 3, 4], [5, 'awaiting_human']), false)
    expect(steps.map((s) => s.state)).toEqual(['done', 'done', 'current', 'todo', 'todo', 'todo'])
  })

  it('locks the steps that are not built yet on a real project', () => {
    const steps = userSteps(pipeline([1, 2, 3, 4, 5]), true)
    expect(steps.map((s) => s.state)).toEqual(['done', 'done', 'done', 'locked', 'locked', 'locked'])
  })
})
