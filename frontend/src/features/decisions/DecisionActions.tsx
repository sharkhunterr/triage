import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Ban, FolderInput, RotateCcw, Undo2 } from 'lucide-react'
import { useCategories } from '../../api/categories'
import { api } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import { Button, Card, useToast } from '../../design-system'
import { useT } from '../../i18n'
import { categoryButton } from '../categories/colors'

type Target = { category_id: number } | { target: 'intake' }

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
  const categories = useCategories()
  const action = useDecisionAction()
  const choices = (categories.data ?? []).filter((c) => c.root_folder_path)
  const awaiting = decision.status === 'held' || decision.status === 'proposed'
  const correctable = decision.status === 'moved'
  if (!awaiting && !correctable && decision.status !== 'failed') return null
  const current = decision.target_category?.id

  return (
    <Card>
      <h2 className="mb-1 font-semibold">
        {correctable ? t('decision.correctTitle') : t('decision.decideTitle')}
      </h2>
      <p className="mb-3 text-sm text-muted">
        {correctable ? t('decision.correctHint') : t('decision.decideHint')}
      </p>
      <div className="flex flex-wrap gap-2">
        {decision.status === 'failed' && decision.target_category && (
          <Button
            variant="primary"
            icon={<RotateCcw className="size-4" aria-hidden />}
            loading={action.isPending}
            onClick={() =>
              action.mutate({
                id: decision.id,
                action: 'apply',
                body: { category_id: decision.target_category?.id ?? 0 },
              })
            }
          >
            {t('decision.retry')}
          </Button>
        )}
        {(awaiting || correctable) &&
          choices
            .filter((c) => !correctable || c.id !== current)
            .map((c) => (
              <Button
                key={c.id}
                {...categoryButton(c.id, awaiting && c.id === current)}
                icon={<FolderInput className="size-4" aria-hidden />}
                loading={action.isPending}
                onClick={() =>
                  action.mutate({
                    id: decision.id,
                    action: correctable ? 'correct' : 'apply',
                    body: { category_id: c.id },
                  })
                }
              >
                {t('decision.moveTo', { category: c.name })}
              </Button>
            ))}
        {correctable && decision.from_root_folder && (
          <Button
            icon={<Undo2 className="size-4" aria-hidden />}
            loading={action.isPending}
            onClick={() => action.mutate({ id: decision.id, action: 'revert' })}
          >
            {t('decision.undo', { folder: decision.from_root_folder })}
          </Button>
        )}
        {decision.status === 'held' && decision.source === 'intake' && (
          <Button
            variant="ghost"
            icon={<Ban className="size-4" aria-hidden />}
            loading={action.isPending}
            onClick={() => action.mutate({ id: decision.id, action: 'apply', body: { target: 'intake' } })}
          >
            {t('decision.leave')}
          </Button>
        )}
        {decision.status === 'proposed' && (
          <Button
            variant="ghost"
            icon={<Ban className="size-4" aria-hidden />}
            loading={action.isPending}
            onClick={() => action.mutate({ id: decision.id, action: 'dismiss' })}
          >
            {t('decision.dismiss')}
          </Button>
        )}
      </div>
    </Card>
  )
}
