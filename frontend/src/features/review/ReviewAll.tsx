import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ListChecks, RefreshCw } from 'lucide-react'
import { type ReactNode, useState } from 'react'
import { useNavigate } from 'react-router'
import { useCategories } from '../../api/categories'
import { api } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import { Button, cx, Dialog, Spinner, useToast } from '../../design-system'
import { useT } from '../../i18n'
import { CategoryDot, tint } from '../categories/colors'
import { ChoiceInfo, Poster } from '../decisions/parts'

/** `cat:<id>` moves to that category, `intake` leaves (or dismisses), `later` does nothing. */
type Choice = `cat:${number}` | 'intake' | 'later'

const initialChoice = (d: DecisionSummary): Choice => {
  const proposed = d.target_category ?? d.top_category
  return d.status === 'proposed' && proposed ? `cat:${proposed.id}` : 'later'
}

/** One dialog to decide every waiting movie: proposals start accepted, doubts start "later". */
export function ReviewAll({ count }: { count: number }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const categories = useCategories()
  const [open, setOpen] = useState(false)
  // the whole queue, only once the window is open (the page itself shows one page of it)
  const queue = useQuery({
    queryKey: ['review', 'all'],
    queryFn: () => api<DecisionSummary[]>('/review'),
    enabled: open,
  })
  const items = queue.data ?? []
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

  if (count === 0) return null
  return (
    <>
      <Button icon={<ListChecks className="size-4" aria-hidden />} onClick={() => setOpen(true)}>
        {t('reviewAll.open')}
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={t('reviewAll.title', { count: queue.data ? items.length : count })}
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
          {categories.isPending || queue.isPending ? (
            <Spinner label={t('common.loading')} />
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {items.map((d) => {
                const choice = choiceOf(d)
                const proposed = d.target_category ?? d.top_category
                const pill = (value: Choice, label: ReactNode, categoryId?: number) => {
                  const selected = choice === value
                  return (
                    <label
                      key={value}
                      className={cx(
                        'cursor-pointer rounded-full border px-2.5 py-1 text-xs font-medium transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2',
                        categoryId != null
                          ? selected
                            ? 'cat-fill'
                            : 'cat-tint hover:brightness-95'
                          : selected
                            ? 'border-text bg-text text-surface'
                            : 'border-border text-muted hover:bg-surface-2',
                      )}
                      style={categoryId != null ? tint(categoryId) : undefined}
                    >
                      <input
                        type="radio"
                        className="sr-only"
                        name={`review-all-choice-${d.id}`}
                        checked={selected}
                        onChange={() => set(d.id, value)}
                      />
                      {label}
                    </label>
                  )
                }
                return (
                  <li key={d.id} className="flex flex-col gap-2 py-2.5">
                    <div className="flex items-center gap-3">
                      <Poster url={d.movie.poster_url} title={d.movie.title} size="sm" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium" id={`review-all-${d.id}`}>
                          {d.movie.title}
                          {d.movie.year ? <span className="text-muted"> ({d.movie.year})</span> : null}
                        </p>
                        <p className="flex items-center gap-1.5 text-xs text-muted">
                          {t(`status.${d.status}`)} · {Math.round(d.confidence * 100)}%
                          {proposed && (
                            <>
                              {' '}
                              · <CategoryDot id={proposed.id} className="size-2" /> {proposed.name}
                            </>
                          )}
                        </p>
                      </div>
                    </div>
                    <fieldset aria-labelledby={`review-all-${d.id}`} className="flex flex-wrap gap-1.5">
                      {libraries.map((c) =>
                        pill(
                          `cat:${c.id}`,
                          <>
                            {c.name} <ChoiceInfo decision={d} categoryKey={c.key} />
                          </>,
                          c.id,
                        ),
                      )}
                      {pill('intake', d.status === 'proposed' ? t('decision.dismiss') : t('decision.leave'))}
                      {pill('later', t('reviewAll.later'))}
                    </fieldset>
                  </li>
                )
              })}
            </ul>
          )}
          <div className="sticky -bottom-5 -mx-5 flex flex-wrap items-center justify-between gap-2 border-t border-border bg-surface px-5 py-3">
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

type Scope = 'all' | 'waiting' | 'new'
type Reanalyzed = { count: number; all: number; waiting: number; new: number }

/** Analyses movies of the intake folder (all, waiting, or new ones) after saying how many. */
export function Reanalyze() {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [scope, setScope] = useState<Scope>('all')
  const preview = useQuery({
    queryKey: ['reanalyze-preview'],
    queryFn: () => api<Reanalyzed>('/decisions/reanalyze', { method: 'POST', body: { dry_run: true } }),
    enabled: open,
    staleTime: 0,
  })
  const run = useMutation({
    mutationFn: () => api<Reanalyzed>('/decisions/reanalyze', { method: 'POST', body: { scope } }),
    onSuccess: (result) => {
      toast(t('reanalyze.started', { count: result.count }), 'success')
      setOpen(false)
      navigate('/activity')
      return queryClient.invalidateQueries()
    },
    onError: (error) => toast(error.message, 'danger'),
  })
  const counts = preview.data
  const count = counts?.[scope] ?? 0
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
          {preview.isPending || !counts ? (
            <Spinner label={t('common.loading')} />
          ) : (
            <fieldset className="flex flex-col gap-2">
              <legend className="sr-only">{t('reanalyze.title')}</legend>
              {(['all', 'waiting', 'new'] as const).map((value) => (
                <label
                  key={value}
                  className={cx(
                    'flex cursor-pointer items-start gap-3 rounded-xl border p-3 has-[:focus-visible]:outline-2',
                    scope === value ? 'border-accent bg-accent/10' : 'border-border hover:bg-surface-2',
                  )}
                >
                  <input
                    type="radio"
                    name="reanalyze-scope"
                    className="mt-1"
                    checked={scope === value}
                    onChange={() => setScope(value)}
                  />
                  <span className="flex flex-1 flex-col">
                    <span className="flex items-baseline justify-between gap-2 font-medium">
                      {t(`reanalyze.scope.${value}`)}
                      <span className="text-sm tabular-nums text-muted">{counts[value]}</span>
                    </span>
                    <span className="text-xs text-muted">{t(`reanalyze.scope.${value}Hint`)}</span>
                  </span>
                </label>
              ))}
            </fieldset>
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
