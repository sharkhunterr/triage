import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Undo2 } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import { Button, Dialog, Field, Select, Spinner, useToast } from '../../design-system'
import { useT } from '../../i18n'

type Reverted = { count: number; items: DecisionSummary[] }
const PERIODS = { hour: 3_600_000, day: 86_400_000, week: 604_800_000, all: 0 } as const
type Period = keyof typeof PERIODS

const body = (period: Period, dry_run: boolean) => ({
  since: PERIODS[period] ? new Date(Date.now() - PERIODS[period]).toISOString() : null,
  dry_run,
})

/** Puts back every movie moved during a period, after showing which ones. */
export function UndoMoves() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [period, setPeriod] = useState<Period>('day')
  const preview = useQuery({
    queryKey: ['revert-preview', period],
    queryFn: () => api<Reverted>('/decisions/revert', { method: 'POST', body: body(period, true) }),
    enabled: open,
    staleTime: 0,
  })
  const undo = useMutation({
    mutationFn: () => api<Reverted>('/decisions/revert', { method: 'POST', body: body(period, false) }),
    onSuccess: (result) => {
      toast(t('undo.started', { count: result.count }), 'success')
      setOpen(false)
      return queryClient.invalidateQueries()
    },
    onError: (error) => toast(error.message, 'danger'),
  })
  const items = preview.data?.items ?? []
  const shown = items.slice(0, 8)

  return (
    <>
      <Button icon={<Undo2 className="size-4" aria-hidden />} onClick={() => setOpen(true)}>
        {t('undo.open')}
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={t('undo.title')}
        description={t('undo.text')}
        closeLabel={t('common.close')}
      >
        <div className="flex flex-col gap-4">
          <Field label={t('undo.period')}>
            {(id) => (
              <Select id={id} value={period} onChange={(e) => setPeriod(e.target.value as Period)}>
                {(Object.keys(PERIODS) as Period[]).map((p) => (
                  <option key={p} value={p}>
                    {t(`undo.${p}`)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          {preview.isPending ? (
            <Spinner label={t('common.loading')} />
          ) : items.length === 0 ? (
            <p className="text-sm text-muted">{t('undo.none')}</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm">
              {shown.map((d) => (
                <li key={d.id} className="flex flex-wrap justify-between gap-x-3">
                  <span className="font-medium">
                    {d.movie.title} {d.movie.year ? `(${d.movie.year})` : ''}
                  </span>
                  <span className="text-muted">
                    <code>{d.target_root_folder}</code> → <code>{d.from_root_folder}</code>
                  </span>
                </li>
              ))}
              {items.length > shown.length && (
                <li className="text-muted">{t('undo.more', { count: items.length - shown.length })}</li>
              )}
            </ul>
          )}
          <div className="flex justify-end gap-2">
            <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
            <Button
              variant="danger"
              loading={undo.isPending}
              disabled={items.length === 0}
              onClick={() => undo.mutate()}
            >
              {t('undo.confirm', { count: items.length })}
            </Button>
          </div>
        </div>
      </Dialog>
    </>
  )
}
