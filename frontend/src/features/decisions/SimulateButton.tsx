import { useMutation } from '@tanstack/react-query'
import { FlaskConical } from 'lucide-react'
import { useNavigate } from 'react-router'
import { api } from '../../api/client'
import type { DecisionDetail } from '../../api/decisions'
import { Button, useToast } from '../../design-system'
import { useT } from '../../i18n'

/** Re-run the classification with today's rules; nothing moves (FR-022b). */
export function SimulateButton({ radarrId }: { radarrId: number }) {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const simulate = useMutation({
    mutationFn: () => api<DecisionDetail>(`/movies/${radarrId}/simulate`, { method: 'POST' }),
    onSuccess: (decision) => navigate(`/decisions/${decision.id}`),
    onError: (error) => toast(error.message, 'danger'),
  })
  return (
    <Button
      size="sm"
      icon={<FlaskConical className="size-4" aria-hidden />}
      loading={simulate.isPending}
      onClick={() => simulate.mutate()}
    >
      {t('decision.simulate')}
    </Button>
  )
}
