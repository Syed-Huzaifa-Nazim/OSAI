import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { pipelineApi } from '@/lib/api/services'
import { queryKeys } from '@/lib/query-client'
import { config } from '@/lib/config'
import { errorMessage } from '@/lib/api-client'
import type { PipelineState } from '@/types/pipeline'

/**
 * Polls pipeline status while anything is running, and stops once the run is
 * parked at a human checkpoint or finished. No point burning requests while
 * the system is waiting on a person.
 *
 * Supabase Realtime / WebSockets are the natural upgrade here; see
 * docs/architecture.md.
 */
export function usePipeline(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.pipeline(projectId ?? ''),
    queryFn: () => pipelineApi.get(projectId as string),
    enabled: Boolean(projectId),
    refetchInterval: (query) => {
      const data = query.state.data as PipelineState | undefined
      if (!data) return false
      const running = Object.values(data.stages).some((stage) => stage.status === 'running')
      return running ? config.pipelinePollMs : false
    },
  })
}

export function useSources(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.sources(projectId ?? ''),
    queryFn: () => pipelineApi.sources(projectId as string),
    enabled: Boolean(projectId),
  })
}

export function useStartPipeline(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => pipelineApi.start(projectId),
    onSuccess: (state) => {
      client.setQueryData(queryKeys.projects.pipeline(projectId), state)
      toast.success('Pipeline started', {
        description: 'The Scout Agent is collecting competitor data.',
      })
    },
    onError: (error) => {
      toast.error('Could not start the pipeline', { description: errorMessage(error) })
    },
  })
}

export function useResetPipeline(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => pipelineApi.reset(projectId),
    onSuccess: async (state) => {
      client.setQueryData(queryKeys.projects.pipeline(projectId), state)
      await client.invalidateQueries({ queryKey: queryKeys.projects.detail(projectId) })
      toast.success('Pipeline reset', { description: 'All stage output has been cleared.' })
    },
    onError: (error) => {
      toast.error('Could not reset the pipeline', { description: errorMessage(error) })
    },
  })
}
