import { useMutation, useQueryClient } from '@tanstack/react-query'
import { RotateCcw, Undo2 } from 'lucide-react'
import { api } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import { Button, Card, useToast } from '../../design-system'
import { useT } from '../../i18n'
import { ChoiceSlider } from '../review/ChoiceSlider'

// chosen on the movie's sheet: the lock says so
type Target = ({ category_id: number } | { target: 'intake' }) & { via?: 'sheet' }

export function useDecisionAction() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const t = useT()
  return useMutation({
    mutationFn: ({
      id,
      action,
      body,
    }: {
      id: number
      action: 'apply' | 'dismiss' | 'correct' | 'revert'
      body?: Target
    }) => api(`/decisions/${id}/${action}`, { method: 'POST', body: body ?? {} }),
    onSuccess: () => {
      toast(t('decision.done'), 'success')
      return queryClient.invalidateQueries()
    },
    onError: (error) => toast(error.message, 'danger'),
  })
}

/** What the owner can do with a decision, depending on where it stands (data-model state machine). */
export function DecisionActions({ decision }: { decision: DecisionSummary }) {
  const t = useT()
  const action = useDecisionAction()
  const awaiting = decision.status === 'held' || decision.status === 'proposed'
  const correctable = decision.status === 'moved'
  if (!awaiting && !correctable && decision.status !== 'failed') return null
  const undo = correctable && decision.from_root_folder && (
    <Button
      size="sm"
      variant="ghost"
      icon={<Undo2 className="size-4" aria-hidden />}
      loading={action.isPending}
      onClick={() => action.mutate({ id: decision.id, action: 'revert' })}
    >
      {t('decision.undo', { folder: decision.from_root_folder })}
    </Button>
  )

  return (
    <Card>
      <h2 className="mb-1 font-semibold">
        {correctable ? t('decision.correctTitle') : t('decision.decideTitle')}
      </h2>
      <p className="mb-3 text-sm text-muted">
        {correctable ? t('decision.correctHint') : t('decision.decideHint')}
      </p>
      {awaiting || correctable ? (
        <ChoiceSlider decision={decision} correct={correctable} via="sheet" />
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2 empty:hidden">
        {decision.status === 'failed' && decision.target_category && (
          <Button
            variant="primary"
            icon={<RotateCcw className="size-4" aria-hidden />}
            loading={action.isPending}
            onClick={() =>
              action.mutate({
                id: decision.id,
                action: 'apply',
                body: { category_id: decision.target_category?.id ?? 0, via: 'sheet' },
              })
            }
          >
            {t('decision.retry')}
          </Button>
        )}
        {undo}
      </div>
    </Card>
  )
}
