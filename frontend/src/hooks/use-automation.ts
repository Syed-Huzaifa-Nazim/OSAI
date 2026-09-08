import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { automationApi, costApi, documentsApi } from '@/lib/api/services'
import { queryKeys } from '@/lib/query-client'
import { errorMessage } from '@/lib/api-client'
import type { ContentSuggestion } from '@/types/domain'

export function useDocument(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.document(projectId ?? ''),
    queryFn: () => documentsApi.get(projectId as string),
    enabled: Boolean(projectId),
  })
}

export function useRunCost(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.cost(projectId ?? ''),
    queryFn: () => costApi.get(projectId as string),
    enabled: Boolean(projectId),
  })
}

export function useSuggestions(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.automation(projectId ?? ''),
    queryFn: () => automationApi.list(projectId as string),
    enabled: Boolean(projectId),
  })
}

export function useGenerateSuggestions(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => automationApi.generate(projectId),
    onSuccess: (suggestions) => {
      client.setQueryData(queryKeys.projects.automation(projectId), suggestions)
      toast.success('Content suggestions ready', {
        description: `${suggestions.length} assets mapped to your approved initiatives.`,
      })
    },
    onError: (error) => {
      toast.error('Could not generate suggestions', { description: errorMessage(error) })
    },
  })
}

export function useUpdateSuggestion(projectId: string) {
  const client = useQueryClient()
  const key = queryKeys.projects.automation(projectId)

  return useMutation({
    mutationFn: ({
      suggestionId,
      patch,
    }: {
      suggestionId: string
      patch: { status?: ContentSuggestion['status']; body?: string | null }
    }) => automationApi.update(projectId, suggestionId, patch),
    onMutate: async ({ suggestionId, patch }) => {
      await client.cancelQueries({ queryKey: key })
      const previous = client.getQueryData<ContentSuggestion[]>(key)
      client.setQueryData<ContentSuggestion[]>(key, (current) =>
        current?.map((item) => (item.id === suggestionId ? { ...item, ...patch } : item)),
      )
      return { previous }
    },
    onError: (error, _variables, context) => {
      if (context?.previous) client.setQueryData(key, context.previous)
      toast.error('Could not update that asset', { description: errorMessage(error) })
    },
  })
}

export function useDraftSuggestion(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (suggestionId: string) => automationApi.draft(projectId, suggestionId),
    onSuccess: async (suggestion) => {
      await client.invalidateQueries({ queryKey: queryKeys.projects.automation(projectId) })
      toast.success('Draft generated', { description: suggestion.title })
    },
    onError: (error) => {
      toast.error('Could not draft that asset', { description: errorMessage(error) })
    },
  })
}
