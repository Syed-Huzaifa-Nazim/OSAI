import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { projectsApi, type CreateProjectInput } from '@/lib/api/services'
import { queryKeys } from '@/lib/query-client'
import { errorMessage } from '@/lib/api-client'

export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects.list(),
    queryFn: projectsApi.list,
  })
}

export function useProject(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.detail(id ?? ''),
    queryFn: () => projectsApi.get(id as string),
    enabled: Boolean(id),
  })
}

export function useCompetitors(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.competitors(projectId ?? ''),
    queryFn: () => projectsApi.competitors(projectId as string),
    enabled: Boolean(projectId),
  })
}

export function useCreateProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateProjectInput) => projectsApi.create(input),
    onSuccess: async (project) => {
      await client.invalidateQueries({ queryKey: queryKeys.projects.all })
      // Every comparison type scrapes on creation now, whatever it compares.
      toast.success('Project created', {
        description: `${project.brandName} is being scraped now.`,
      })
    },
    onError: (error) => {
      toast.error('Could not create the project', { description: errorMessage(error) })
    },
  })
}

export function useDeleteProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => projectsApi.remove(id),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.projects.all })
      toast.success('Project deleted')
    },
    onError: (error) => {
      toast.error('Could not delete the project', { description: errorMessage(error) })
    },
  })
}
