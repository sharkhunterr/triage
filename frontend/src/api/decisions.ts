import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { api, type Schemas } from './client'

export type DecisionSummary = Schemas['DecisionSummary']
export type DecisionDetail = Schemas['DecisionDetail']
export type Dashboard = Schemas['Dashboard']
export type DecisionPage = Schemas['DecisionPage']

export const useDashboard = () =>
  useQuery({ queryKey: ['dashboard'], queryFn: () => api<Dashboard>('/dashboard'), refetchInterval: 15_000 })

export const useDecision = (id: number) =>
  useQuery({
    queryKey: ['decision', id],
    queryFn: () => api<DecisionDetail>(`/decisions/${id}`),
    refetchInterval: (query) => (query.state.data?.status === 'moving' ? 3_000 : false),
  })

export type DecisionFilters = { status?: string[]; source?: string; category?: number; q?: string }

export function useDecisionPages(filters: DecisionFilters) {
  return useInfiniteQuery({
    queryKey: ['decisions', filters],
    initialPageParam: undefined as number | undefined,
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams()
      for (const status of filters.status ?? []) params.append('status', status)
      if (filters.source) params.set('source', filters.source)
      if (filters.category) params.set('category', String(filters.category))
      if (filters.q) params.set('q', filters.q)
      if (pageParam) params.set('cursor', String(pageParam))
      return api<DecisionPage>(`/decisions?${params}`)
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  })
}
