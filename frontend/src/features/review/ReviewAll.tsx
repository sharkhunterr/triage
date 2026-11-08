import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ListChecks, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { useCategories } from '../../api/categories'
import { api } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import { Button, cx, Dialog, Select, Spinner, useToast } from '../../design-system'
import { useT } from '../../i18n'
import { CategoryDot, tint } from '../categories/colors'
import { Poster } from '../decisions/parts'

/** `cat:<id>` moves to that category, `intake` leaves (or dismisses), `later` does nothing. */
type Choice = `cat:${number}` | 'intake' | 'later'

const initialChoice = (d: DecisionSummary): Choice => {
  const proposed = d.target_category ?? d.top_category
  return d.status === 'proposed' && proposed ? `cat:${proposed.id}` : 'later'
}

/** One dialog to decide every waiting movie: proposals start accepted, doubts start "later". */
export function ReviewAll({ items }: { items: DecisionSummary[] }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const categories = useCategories()
  const [open, setOpen] = useState(false)
  const [choices, setChoices] = useState<Record<number, Choice>>({})
  const libraries = (categories.data ?? []).filter((c) => c.root_folder_path)
  const choiceOf = (d: DecisionSummary) => choices[d.id] ?? initialChoice(d)
  const set = (id: number, choice: Choice) => setChoices((c) => ({ ...c, [id]: choice }))
  const setAll = (pick: (d: DecisionSummary) => Choice) =>
    setChoices(Object.fromEntries(items.map((d) => [d.id, pick(d)])))

  const chosen = items.filter((d) => choiceOf(d) !== 'later')
  const moves = chosen.filter((d) => choiceOf(d).startsWith('cat:')).length
  const apply = useMutation({
    mutationFn: () =>
      api<{ applied: number; failed: number[] }>('/decisions/bulk', {
        method: 'POST',
        body: {
          items: chosen.map((d) => {
            const choice = choiceOf(d)
            return choice === 'intake'
              ? { id: d.id, target: 'intake' }
              : { id: d.id, category_id: Number(choice.slice(4)) }
          }),
        },
      }),
    onSuccess: (result) => {
      toast(t('reviewAll.done', { count: result.applied }), result.failed.length ? 'danger' : 'success')
      setOpen(false)
      setChoices({})
      return queryClient.invalidateQueries()
    },
    onError: (error) => toast(error.message, 'danger'),
  })

  if (items.length === 0) return null
  return (
    <>
      <Button icon={<ListChecks className="size-4" aria-hidden />} onClick={() => setOpen(true)}>
        {t('reviewAll.open')}
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={t('reviewAll.title', { count: items.length })}
        description={t('reviewAll.text')}
        closeLabel={t('common.close')}
      >
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => setAll(initialChoice)}>
              {t('reviewAll.acceptProposals')}
            </Button>
            <Button
              size="sm"
              onClick={() =>
                setAll((d) => {
                  const best = d.target_category ?? d.top_category
                  return best ? `cat:${best.id}` : 'later'
                })
              }
            >
              {t('reviewAll.bestGuess')}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setAll(() => 'later')}>
              {t('reviewAll.allLater')}
            </Button>
          </div>
          {categories.isPending ? (
            <Spinner label={t('common.loading')} />
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {items.map((d) => {
                const choice = choiceOf(d)
                const categoryId = choice.startsWith('cat:') ? Number(choice.slice(4)) : undefined
                return (
                  <li key={d.id} className="flex items-center gap-3 py-2">
                    <Poster url={d.movie.poster_url} title={d.movie.title} size="sm" />
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <p className="truncate text-sm font-medium" id={`review-all-${d.id}`}>
                        {d.movie.title}
                        {d.movie.year ? <span className="text-muted"> ({d.movie.year})</span> : null}
                      </p>
                      <p className="text-xs text-muted">
                        {t(`status.${d.status}`)} · {Math.round(d.confidence * 100)}%
                      </p>
                    </div>
                    <Select
                      aria-labelledby={`review-all-${d.id}`}
                      className={cx('w-40 shrink-0 font-medium', categoryId != null && 'cat-tint')}
                      style={categoryId != null ? tint(categoryId) : undefined}
                      value={choice}
                      onChange={(e) => set(d.id, e.target.value as Choice)}
                    >
                      <option value="later">{t('reviewAll.later')}</option>
                      {libraries.map((c) => (
                        <option key={c.id} value={`cat:${c.id}`}>
                          → {c.name}
                        </option>
                      ))}
                      <option value="intake">
                        {d.status === 'proposed' ? t('decision.dismiss') : t('decision.leave')}
                      </option>
                    </Select>
                  </li>
                )
              })}
            </ul>
          )}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
            <p className="flex items-center gap-2 text-sm text-muted">
              {libraries.map((c) => {
                const n = items.filter((d) => choiceOf(d) === `cat:${c.id}`).length
                return n ? (
                  <span key={c.id} className="flex items-center gap-1">
                    <CategoryDot id={c.id} /> {n}
                  </span>
                ) : null
              })}
              {t('reviewAll.summary', { moves, others: chosen.length - moves })}
            </p>
            <div className="flex gap-2">
              <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
              <Button
                variant="primary"
                loading={apply.isPending}
                disabled={chosen.length === 0}
                onClick={() => apply.mutate()}
              >
                {t('reviewAll.apply', { count: chosen.length })}
              </Button>
            </div>
          </div>
        </div>
      </Dialog>
    </>
  )
}

/** Classifies every waiting movie again with today's rules, after saying how many. */
export function Reanalyze() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const preview = useQuery({
    queryKey: ['reanalyze-preview'],
    queryFn: () =>
      api<{ count: number }>('/decisions/reanalyze', { method: 'POST', body: { dry_run: true } }),
    enabled: open,
    staleTime: 0,
  })
  const run = useMutation({
    mutationFn: () => api<{ count: number }>('/decisions/reanalyze', { method: 'POST', body: {} }),
    onSuccess: (result) => {
      toast(t('reanalyze.started', { count: result.count }), 'success')
      setOpen(false)
      return queryClient.invalidateQueries()
    },
    onError: (error) => toast(error.message, 'danger'),
  })
  const count = preview.data?.count ?? 0
  return (
    <>
      <Button icon={<RefreshCw className="size-4" aria-hidden />} onClick={() => setOpen(true)}>
        {t('reanalyze.open')}
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={t('reanalyze.title')}
        description={t('reanalyze.text')}
        closeLabel={t('common.close')}
      >
        <div className="flex flex-col gap-4">
          {preview.isPending ? (
            <Spinner label={t('common.loading')} />
          ) : (
            <p className="text-sm font-medium">{t('reanalyze.count', { count })}</p>
          )}
          <div className="flex justify-end gap-2">
            <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
            <Button
              variant="primary"
              loading={run.isPending}
              disabled={count === 0}
              onClick={() => run.mutate()}
            >
              {t('reanalyze.confirm', { count })}
            </Button>
          </div>
        </div>
      </Dialog>
    </>
  )
}
