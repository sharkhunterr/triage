import { useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router'
import { api } from '../../api/client'
import type { DecisionDetail } from '../../api/decisions'
import { Button, useToast } from '../../design-system'
import { useT } from '../../i18n'
import { useFromHere } from './parts'

/** Analyse the movie now with today's rules: a new decision in the intake folder, a simulation elsewhere. */
export function AnalyzeButton({ radarrId }: { radarrId: number }) {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const here = useFromHere()
  const analyze = useMutation({
    mutationFn: () => api<DecisionDetail>(`/movies/${radarrId}/analyze`, { method: 'POST' }),
    onSuccess: (decision) => {
      toast(t('decision.analyzed'), 'success')
      navigate(`/decisions/${decision.id}`, { state: here })
      return queryClient.invalidateQueries()
    },
    onError: (error) => toast(error.message, 'danger'),
  })
  return (
    <Button
      size="sm"
      icon={<RefreshCw className="size-4" aria-hidden />}
      loading={analyze.isPending}
      onClick={() => analyze.mutate()}
    >
      {analyze.isPending ? t('decision.analyzing') : t('decision.analyze')}
    </Button>
  )
}
