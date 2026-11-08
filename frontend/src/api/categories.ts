import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Schemas } from './client'

export type Category = Schemas['CategoryOut']
export type Rule = Schemas['RuleOut']
export type RuleInput = Schemas['RuleIn']
export type CategoryInput = Schemas['CategoryIn']
export type Preset = Schemas['PresetOut']
export type RootFolder = Schemas['RootFolderOut']

export const useCategories = () =>
  useQuery({ queryKey: ['categories'], queryFn: () => api<Category[]>('/categories') })

export const usePresets = () => useQuery({ queryKey: ['presets'], queryFn: () => api<Preset[]>('/presets') })

export const useRootFolders = () =>
  useQuery({
    queryKey: ['root-folders'],
    queryFn: () => api<RootFolder[]>('/radarr/root-folders'),
    retry: false,
  })

function useInvalidate() {
  const client = useQueryClient()
  return () => client.invalidateQueries({ queryKey: ['categories'] })
}

export function useSaveCategory() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, body }: { id?: number; body: CategoryInput }) =>
      id === undefined
        ? api<Category>('/categories', { method: 'POST', body })
        : api<Category>(`/categories/${id}`, { method: 'PUT', body }),
    onSuccess: invalidate,
  })
}

export function useDeleteCategory() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: number) => api(`/categories/${id}`, { method: 'DELETE' }),
    onSuccess: invalidate,
  })
}

export function useReorderCategories() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (ids: number[]) => api('/categories/reorder', { method: 'POST', body: { ids } }),
    onSuccess: invalidate,
  })
}

export function useApplyPreset() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (key: string) => api<Category[]>(`/presets/${key}/apply`, { method: 'POST' }),
    onSuccess: invalidate,
  })
}
