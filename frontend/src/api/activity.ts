import { useQuery } from '@tanstack/react-query'
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
