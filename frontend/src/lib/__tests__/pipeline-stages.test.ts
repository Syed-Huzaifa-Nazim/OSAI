import { describe, expect, it } from 'vitest'
import {
  ACTOR_LABEL,
  CHECKPOINT_STAGES,
  PIPELINE_STAGES,
  STAGE_STATUS_LABEL,
  STAGE_STATUS_STYLES,
  getStage,
  getStageByKey,
  isCheckpoint,
} from '@/lib/pipeline-stages'
import { STAGE_COLOR_CLASSES } from '@/components/pipeline/stage-colors'

/**
 * The stage table drives routing, colour, copy and the checkpoint logic, so a
 * mistake here is silent and everywhere. These guard the invariants rather than
 * restating the data.
 */
describe('pipeline stage definitions', () => {
  it('describes exactly nine stages, numbered 1-9 in order', () => {
    expect(PIPELINE_STAGES).toHaveLength(9)
    expect(PIPELINE_STAGES.map((stage) => stage.id)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9])
  })

  it('marks stages 5 and 7 as the only human checkpoints', () => {
    const flagged = PIPELINE_STAGES.filter((stage) => stage.isCheckpoint).map((s) => s.id)
    expect(flagged).toEqual([5, 7])
    expect(CHECKPOINT_STAGES).toEqual([5, 7])
    expect(isCheckpoint(5)).toBe(true)
    expect(isCheckpoint(7)).toBe(true)
    expect(isCheckpoint(6)).toBe(false)
  })

  it('gives every checkpoint a route, since a human has to be able to reach it', () => {
    for (const stage of PIPELINE_STAGES.filter((s) => s.isCheckpoint)) {
      expect(stage.route).toBeTruthy()
    }
  })

  it('assigns both checkpoints to the human actor', () => {
    for (const stage of PIPELINE_STAGES.filter((s) => s.isCheckpoint)) {
      expect(stage.actor).toBe('human')
    }
  })

  it('uses a unique key and colour token per stage', () => {
    expect(new Set(PIPELINE_STAGES.map((s) => s.key)).size).toBe(9)
    expect(new Set(PIPELINE_STAGES.map((s) => s.colorToken)).size).toBe(9)
  })

  it('has a colour class entry for every stage', () => {
    // Tailwind cannot see dynamic class names, so a missing entry would render
    // an unstyled card rather than throwing.
    for (const stage of PIPELINE_STAGES) {
      expect(STAGE_COLOR_CLASSES[stage.id]).toBeDefined()
      expect(STAGE_COLOR_CLASSES[stage.id].text).toContain(`stage-${stage.id}`)
    }
  })

  it('resolves stages by id and by key', () => {
    expect(getStage(4).key).toBe('insight')
    expect(getStageByKey('review_strategy').id).toBe(7)
  })

  it('throws on an unknown stage rather than returning undefined', () => {
    // @ts-expect-error: deliberately out of range
    expect(() => getStage(12)).toThrow()
  })

  it('labels and styles every status', () => {
    const statuses = ['idle', 'running', 'awaiting_human', 'complete', 'error', 'skipped'] as const
    for (const status of statuses) {
      expect(STAGE_STATUS_LABEL[status]).toBeTruthy()
      expect(STAGE_STATUS_STYLES[status].badge).toBeTruthy()
    }
  })

  it('names the human actor as "You"', () => {
    expect(ACTOR_LABEL.human).toBe('You')
  })
})
