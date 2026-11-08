import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { gapsApi, strategyApi, type GapPatch } from '@/lib/api/services'
import { queryKeys } from '@/lib/query-client'
import { errorMessage } from '@/lib/api-client'
import type { Gap, ReviewDecision } from '@/types/domain'

export function useGaps(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.gaps(projectId ?? ''),
    queryFn: () => gapsApi.list(projectId as string),
    enabled: Boolean(projectId),
  })
}

/**
 * Optimistic gap triage. The reviewer is clicking through a list at speed at
 * HITL #1: waiting on a round trip per click would make the checkpoint feel
 * like a chore, which is exactly the wrong incentive for the trust feature.
 */
export function useUpdateGap(projectId: string) {
  const client = useQueryClient()
  const key = queryKeys.projects.gaps(projectId)

  return useMutation({
    mutationFn: ({ gapId, patch }: { gapId: string; patch: GapPatch }) =>
      gapsApi.update(projectId, gapId, patch),
    onMutate: async ({ gapId, patch }) => {
      await client.cancelQueries({ queryKey: key })
      const previous = client.getQueryData<Gap[]>(key)
      client.setQueryData<Gap[]>(key, (current) =>
        current?.map((gap) => (gap.id === gapId ? { ...gap, ...patch } : gap)),
      )
      return { previous }
    },
    onError: (error, _variables, context) => {
      if (context?.previous) client.setQueryData(key, context.previous)
      toast.error('Could not save that change', { description: errorMessage(error) })
    },
  })
}

export function useSubmitGapReview(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: { notes: string | null; acceptedGapIds: string[] }) =>
      gapsApi.submitReview(projectId, input),
    onSuccess: async (_review, input) => {
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.projects.pipeline(projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.projects.detail(projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.projects.reviews(projectId) }),
      ])
      toast.success('Gaps prioritised', {
        description: `${input.acceptedGapIds.length} gaps kept.`,
      })
    },
    onError: (error) => {
      toast.error('Could not submit your review', { description: errorMessage(error) })
    },
  })
}

export function useStrategy(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.strategy(projectId ?? ''),
    queryFn: () => strategyApi.get(projectId as string),
    enabled: Boolean(projectId),
  })
}

export function useReviews(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.reviews(projectId ?? ''),
    queryFn: () => strategyApi.reviews(projectId as string),
    enabled: Boolean(projectId),
  })
}

export function useSubmitStrategyReview(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      decision: ReviewDecision
      notes: string | null
      flaggedIds: string[]
    }) => strategyApi.submitReview(projectId, input),
    onSuccess: async (_review, input) => {
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.projects.pipeline(projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.projects.strategy(projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.projects.detail(projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.projects.reviews(projectId) }),
      ])
      if (input.decision === 'approved') {
        toast.success('Strategy approved', {
          description: 'Generating the strategy document now.',
        })
      } else {
        toast.success('Sent back for revision', {
          description: 'The Strategist and Critic will produce a new version.',
        })
      }
    },
    onError: (error) => {
      toast.error('Could not submit your decision', { description: errorMessage(error) })
    },
  })
}