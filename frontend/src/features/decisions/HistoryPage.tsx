import { Search } from 'lucide-react'
import { useState } from 'react'
import { useIntl } from 'react-intl'
import { useSearchParams } from 'react-router'
import { useCategories } from '../../api/categories'
import { type DecisionFilters, type DecisionSummary, useDecisionPages } from '../../api/decisions'
import { Button, EmptyState, ErrorState, Input, PageHeader, Select, Spinner } from '../../design-system'
import { useT } from '../../i18n'
import { categoryColor } from '../categories/colors'
import { type Places, TimelineRow, usePlaces } from './Timeline'
import { UndoMoves } from './UndoMoves'

/** The day's movies per library, as one thin bar in the categories' colors. */
function DayStrip({ items, place }: { items: DecisionSummary[]; place: Places }) {
  const counts = new Map<number | null, number>()
  for (const d of items) {
    const id = d.target_category?.id ?? d.top_category?.id ?? place(d.target_root_folder)?.id ?? null
    counts.set(id, (counts.get(id) ?? 0) + 1)
  }
  return (
    <div className="flex h-1.5 w-20 overflow-hidden rounded-full bg-surface-2" aria-hidden>
      {[...counts].map(([id, count]) => (
        <span
          key={String(id)}
          style={{ width: `${(count / items.length) * 100}%`, background: categoryColor(id) }}
        />
      ))}
    </div>
  )
}

/** The decisions by day, newest first: today, yesterday, then dates. */
function byDay(items: DecisionSummary[]) {
  const days = new Map<string, { key: string; at: string; items: DecisionSummary[] }>()
  for (const decision of items) {
    const at = decision.decided_at ?? decision.created_at
    const date = new Date(at)
    const key = `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`
    const day = days.get(key) ?? { key, at, items: [] }
    day.items.push(decision)
    days.set(key, day)
  }
  return [...days.values()]
}

function DayTitle({ at }: { at: string }) {
  const t = useT()
  const intl = useIntl()
  const day = new Date(at)
  const today = new Date()
  const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)
  const same = (a: Date, b: Date) => a.toDateString() === b.toDateString()
  const label = same(day, today)
    ? t('history.today')
    : same(day, yesterday)
      ? t('history.yesterday')
      : intl.formatDate(day, {
          weekday: 'long',
          day: 'numeric',
          month: 'long',
          year: day.getFullYear() === today.getFullYear() ? undefined : 'numeric',
        })
  return <span className="first-letter:uppercase">{label}</span>
}

const STATUSES = [
  'moved',
  'proposed',
  'held',
  'moving',
  'failed',
  'corrected',
  'dismissed',
  'left_in_intake',
  'in_place',
]

export function HistoryPage() {
  const t = useT()
  const [params, setParams] = useSearchParams()
  const categories = useCategories()
  const [query, setQuery] = useState(params.get('q') ?? '')
  const filters: DecisionFilters = {
    status: params.getAll('status'),
    source: params.get('source') ?? undefined,
    category: params.get('category') ? Number(params.get('category')) : undefined,
    q: params.get('q') ?? undefined,
  }
  const pages = useDecisionPages(filters)
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }
  const items = pages.data?.pages.flatMap((p) => p.items) ?? []
  const place = usePlaces()

  return (
    <>
      <PageHeader title={t('history.title')} description={t('history.subtitle')} actions={<UndoMoves />} />
      <form
        aria-label={t('history.search')}
        className="mb-4 grid gap-2 sm:grid-cols-4"
        onSubmit={(e) => {
          e.preventDefault()
          update('q', query.trim())
        }}
      >
        <div className="relative sm:col-span-2">
          <Search className="pointer-events-none absolute top-3.5 left-3 size-4 text-muted" aria-hidden />
          <Input
            aria-label={t('history.search')}
            placeholder={t('history.search')}
            className="pl-9"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onBlur={() => update('q', query.trim())}
          />
        </div>
        <Select
          aria-label={t('history.status')}
          value={filters.status?.[0] ?? ''}
          onChange={(e) => update('status', e.target.value)}
        >
          <option value="">{t('history.allStatuses')}</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(`status.${s}`)}
            </option>
          ))}
        </Select>
        <Select
          aria-label={t('decision.category')}
          value={params.get('category') ?? ''}
          onChange={(e) => update('category', e.target.value)}
        >
          <option value="">{t('history.allCategories')}</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </form>

      {pages.isPending && <Spinner label={t('common.loading')} />}
      {pages.isError && (
        <ErrorState
          title={t('common.error')}
          onRetry={() => pages.refetch()}
          retryLabel={t('common.retry')}
        />
      )}
      {pages.isSuccess && items.length === 0 && (
        <EmptyState title={t('history.emptyTitle')} description={t('history.emptyText')} />
      )}
      <div className="mx-auto flex max-w-3xl flex-col gap-5">
        {byDay(items).map(({ key, at, items: day }) => (
          <section key={key} aria-labelledby={`day-${key}`}>
            <h2
              id={`day-${key}`}
              className="sticky top-0 z-10 -mx-1 mb-2 flex items-center gap-2 bg-bg/90 px-1 py-1.5 text-sm font-semibold backdrop-blur"
            >
              <DayTitle at={at} />
              <span className="rounded-full bg-surface-2 px-2 text-xs font-medium text-muted tabular-nums">
                {day.length}
              </span>
              <span className="ml-auto">
                <DayStrip items={day} place={place} />
              </span>
            </h2>
            <ul className="divide-y divide-border overflow-hidden rounded-card border border-border bg-surface">
              {day.map((decision) => (
                <li key={decision.id}>
                  <TimelineRow decision={decision} place={place} />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      {pages.hasNextPage && (
        <div className="mt-4 flex justify-center">
          <Button loading={pages.isFetchingNextPage} onClick={() => pages.fetchNextPage()}>
            {t('history.more')}
          </Button>
        </div>
      )}
    </>
  )
}
