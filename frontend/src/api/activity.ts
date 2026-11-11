import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Schemas } from './client'

export type Activity = Schemas['ActivityOut']
export type ActivityEntry = Schemas['EntryOut']

/** The worker's live activity: polled every second and a half while it works, slowly otherwise. */
export const useActivity = () =>
  useQuery({
    queryKey: ['activity'],
    queryFn: () => api<Activity>('/activity'),
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.running || (data?.run?.pending ?? 0) > 0 ? 1500 : 10_000
    },
  })

export const isWorking = (activity?: Activity) =>
  Boolean(
    activity?.running || (activity?.run && !activity.run.finished_at) || (activity?.run?.pending ?? 0) > 0,
  )

export type Queued = Schemas['QueuedOut']
export type StopBody = Schemas['StopBody']

/** A job's group, as the Activity page stops it: a check's start and its movies are one check. */
export const groupOf = (kind: string) => (kind === 'scan_start' || kind === 'scan_movie' ? 'scan' : kind)

/** Stops a group of work (or all of it): the queued items are cancelled, the running one interrupted. */
export function useStopWork() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: StopBody) => api<Schemas['Stopped']>('/activity/stop', { method: 'POST', body }),
    onSuccess: () => queryClient.invalidateQueries(),
  })
}
