import { ArrowRight, Bot, FolderOpen, Search, UserRound } from 'lucide-react'
import { useState } from 'react'
import { useIntl } from 'react-intl'
import { Link, useSearchParams } from 'react-router'
import { useCategories } from '../../api/categories'
import { type DecisionFilters, type DecisionSummary, useDecisionPages } from '../../api/decisions'
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Select,
  Spinner,
} from '../../design-system'
import { useT } from '../../i18n'
import { CategoryDot, categoryColor, tint } from '../categories/colors'
import { ConfidenceMeter, isUndo, LockBadge, Poster, StatusBadge, useFromHere } from './parts'
import { UndoMoves } from './UndoMoves'

type Place = { id: number | null; name: string }

/** A folder as the owner knows it: the category whose library it is, else its last segment. */
function usePlaces(): (folder: string | null | undefined) => Place | null {
  const categories = useCategories()
  const trim = (path: string) => path.replace(/\/+$/, '')
  return (folder) => {
    if (!folder) return null
    const category = categories.data?.find(
      (c) => c.root_folder_path && trim(c.root_folder_path) === trim(folder),
    )
    return category
      ? { id: category.id, name: category.name }
      : { id: null, name: trim(folder).split('/').pop() || folder }
  }
}

function PlaceChip({ place, strong = false }: { place: Place; strong?: boolean }) {
  if (place.id == null)
    return (
      <span className="inline-flex min-w-0 items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-muted">
        <FolderOpen className="size-3 shrink-0" aria-hidden />
        <span className="truncate">{place.name}</span>
      </span>
    )
  return (
    <span
      className={`inline-flex min-w-0 items-center gap-1 rounded-full border px-2 py-0.5 ${strong ? 'cat-tint font-medium' : 'border-border text-muted'}`}
      style={strong ? tint(place.id) : undefined}
    >
      <CategoryDot id={place.id} className="size-2" />
      <span className="truncate">{place.name}</span>
    </span>
  )
}

/** One decision of the history: where the movie went from and to, who decided, and how sure. */
function HistoryItem({
  decision,
  place,
}: {
  decision: DecisionSummary
  place: ReturnType<typeof usePlaces>
}) {
  const t = useT()
  const intl = useIntl()
  const here = useFromHere()
  const undo = isUndo(decision)
  const category = undo ? null : (decision.target_category ?? decision.top_category)
  const from = place(decision.from_root_folder)
  const to: Place | null = category
    ? { id: category.id, name: category.name }
    : place(decision.target_root_folder)
  const stays = !from || !to || (from.id ?? from.name) === (to.id ?? to.name)
  const owner = decision.actor === 'owner'
  return (
    <Link
      to={`/decisions/${decision.id}`}
      state={here}
      className="group block min-w-0 rounded-card focus-visible:outline-2"
    >
      <article
        className="relative flex gap-3 overflow-hidden rounded-card border border-border bg-surface p-3 pl-4 transition-[box-shadow,border-color] group-hover:border-[color-mix(in_srgb,var(--c)_50%,var(--border))] group-hover:shadow-md"
        style={tint(to?.id)}
      >
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-1"
          style={{ background: categoryColor(to?.id) }}
        />
        <Poster url={decision.movie.poster_url} title={decision.movie.title} />
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <div className="flex items-start gap-2">
            <p className="line-clamp-2 min-w-0 flex-1 leading-snug font-medium">
              {decision.movie.title}
              {decision.movie.year ? (
                <span className="font-normal text-muted"> ({decision.movie.year})</span>
              ) : null}
            </p>
            <time
              dateTime={decision.decided_at ?? decision.created_at}
              className="shrink-0 pt-0.5 text-xs text-muted tabular-nums"
            >
              {intl.formatTime(decision.decided_at ?? decision.created_at, { timeStyle: 'short' })}
            </time>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {undo ? <Badge>{t('status.undone')}</Badge> : <StatusBadge status={decision.status} />}
            <LockBadge lock={decision.movie.lock} />
          </div>
          <div className="flex min-w-0 items-center gap-1.5 text-xs">
            {stays ? (
              (to ?? from) && <PlaceChip place={(to ?? from) as Place} strong />
            ) : (
              <>
                <PlaceChip place={from as Place} />
                <ArrowRight className="size-3.5 shrink-0 text-muted" aria-label={t('history.to')} />
                <PlaceChip place={to as Place} strong />
              </>
            )}
          </div>
          <div className="mt-auto flex items-center justify-between gap-3 pt-0.5">
            <ConfidenceMeter value={decision.confidence} />
            <span
              className="inline-flex items-center gap-1 text-xs text-muted"
              title={t(owner ? 'history.byOwner' : 'history.byTriage')}
            >
              {owner ? (
                <UserRound className="size-3.5" aria-hidden />
              ) : (
                <Bot className="size-3.5" aria-hidden />
              )}
              {t(owner ? 'history.you' : 'history.triage')}
            </span>
          </div>
        </div>
      </article>
    </Link>
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
      <div className="flex flex-col gap-5">
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
            </h2>
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {day.map((decision) => (
                <li key={decision.id} className="flex">
                  <div className="w-full">
                    <HistoryItem decision={decision} place={place} />
                  </div>
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
