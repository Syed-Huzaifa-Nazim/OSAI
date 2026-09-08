import type { StageId } from '@/types/pipeline'

/**
 * Tailwind cannot see dynamically built class names, so every stage colour
 * class is written out in full here for the JIT compiler to find.
 */
export const STAGE_COLOR_CLASSES: Record<
  StageId,
  { text: string; bg: string; bgSoft: string; border: string; ring: string; stroke: string }
> = {
  1: {
    text: 'text-stage-1',
    bg: 'bg-stage-1',
    bgSoft: 'bg-stage-1/15',
    border: 'border-stage-1/40',
    ring: 'ring-stage-1/30',
    stroke: 'stroke-stage-1',
  },
  2: {
    text: 'text-stage-2',
    bg: 'bg-stage-2',
    bgSoft: 'bg-stage-2/15',
    border: 'border-stage-2/40',
    ring: 'ring-stage-2/30',
    stroke: 'stroke-stage-2',
  },
  3: {
    text: 'text-stage-3',
    bg: 'bg-stage-3',
    bgSoft: 'bg-stage-3/15',
    border: 'border-stage-3/40',
    ring: 'ring-stage-3/30',
    stroke: 'stroke-stage-3',
  },
  4: {
    text: 'text-stage-4',
    bg: 'bg-stage-4',
    bgSoft: 'bg-stage-4/15',
    border: 'border-stage-4/40',
    ring: 'ring-stage-4/30',
    stroke: 'stroke-stage-4',
  },
  5: {
    text: 'text-stage-5',
    bg: 'bg-stage-5',
    bgSoft: 'bg-stage-5/15',
    border: 'border-stage-5/40',
    ring: 'ring-stage-5/30',
    stroke: 'stroke-stage-5',
  },
  6: {
    text: 'text-stage-6',
    bg: 'bg-stage-6',
    bgSoft: 'bg-stage-6/15',
    border: 'border-stage-6/40',
    ring: 'ring-stage-6/30',
    stroke: 'stroke-stage-6',
  },
  7: {
    text: 'text-stage-7',
    bg: 'bg-stage-7',
    bgSoft: 'bg-stage-7/15',
    border: 'border-stage-7/40',
    ring: 'ring-stage-7/30',
    stroke: 'stroke-stage-7',
  },
  8: {
    text: 'text-stage-8',
    bg: 'bg-stage-8',
    bgSoft: 'bg-stage-8/15',
    border: 'border-stage-8/40',
    ring: 'ring-stage-8/30',
    stroke: 'stroke-stage-8',
  },
  9: {
    text: 'text-stage-9',
    bg: 'bg-stage-9',
    bgSoft: 'bg-stage-9/15',
    border: 'border-stage-9/40',
    ring: 'ring-stage-9/30',
    stroke: 'stroke-stage-9',
  },
}
