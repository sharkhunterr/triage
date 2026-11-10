import {
  ArrowRight,
  ArrowRightLeft,
  Bot,
  CircleCheck,
  CircleHelp,
  CircleSlash,
  Film,
  FolderOpen,
  Lock,
  type LucideIcon,
  MapPin,
  PenLine,
  Search,
  Sparkles,
  TriangleAlert,
  Undo2,
  UserRound,
} from 'lucide-react'
import { useState } from 'react'
import { useIntl } from 'react-intl'
import { Link, useSearchParams } from 'react-router'
import { useCategories } from '../../api/categories'
import { type DecisionFilters, type DecisionSummary, useDecisionPages } from '../../api/decisions'
import { Button, EmptyState, ErrorState, Input, PageHeader, Select, Spinner } from '../../design-system'
import { useT } from '../../i18n'
import { CategoryDot, categoryColor, tint } from '../categories/colors'
import { isUndo, useFromHere } from './parts'
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

const STATUS_ICON: Record<string, [LucideIcon, string]> = {
  moved: [CircleCheck, 'text-success'],
  in_place: [MapPin, 'text-success'],
  moving: [ArrowRightLeft, 'text-info'],
  proposed: [Sparkles, 'text-accent'],
  held: [CircleHelp, 'text-warning'],
  failed: [TriangleAlert, 'text-danger'],
  corrected: [PenLine, 'text-muted'],
}

/** How sure Triage was, as a ring in the category's color. */
function Ring({ value, color }: { value: number; color: string }) {
  const t = useT()
  const percent = Math.round(value * 100)
  const r = 15
  const length = 2 * Math.PI * r
  return (
    <div
      className="relative size-11 shrink-0"
      role="img"
      aria-label={t('history.confidence', { value: percent })}
    >
      <svg viewBox="0 0 40 40" className="size-full -rotate-90" aria-hidden>
        <circle cx="20" cy="20" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="4" />
        <circle
          cx="20"
          cy="20"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={length}
          strokeDashoffset={length * (1 - Math.min(1, Math.max(0, value)))}
        />
      </svg>
      <span
        className="absolute inset-0 grid place-items-center text-[11px] font-semibold tabular-nums"
        aria-hidden
      >
        {percent}
      </span>
    </div>
  )
}

/** One decision of the history: a row of the day's timeline. */
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
  const [Icon, tone] = undo
    ? [Undo2, 'text-muted']
    : (STATUS_ICON[decision.status] ?? [CircleSlash, 'text-muted'])
  const when = decision.decided_at ?? decision.created_at
  return (
    <Link
      to={`/decisions/${decision.id}`}
      state={here}
      className="flex items-center gap-3 px-3 py-3 transition-colors hover:bg-surface-2/60 focus-visible:outline-2 focus-visible:-outline-offset-2 sm:px-4"
    >
      <div className="relative shrink-0">
        {decision.movie.poster_url ? (
          <img
            src={decision.movie.poster_url}
            alt=""
            loading="lazy"
            className="h-[4.5rem] w-12 rounded-lg object-cover shadow-sm ring-1 ring-border"
          />
        ) : (
          <div
            className="grid h-[4.5rem] w-12 place-items-center rounded-lg bg-surface-2 ring-1 ring-border"
            aria-hidden
          >
            <Film className="size-4 text-muted" />
          </div>
        )}
        <span
          className={`absolute -right-1.5 -bottom-1.5 grid size-6 place-items-center rounded-full bg-surface ring-2 ring-surface ${tone}`}
        >
          <Icon className="size-4" aria-hidden />
        </span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="line-clamp-2 leading-snug font-medium">
          {decision.movie.title}
          {decision.movie.year ? (
            <span className="font-normal text-muted"> · {decision.movie.year}</span>
          ) : null}
        </p>
        <p className="flex min-w-0 items-center gap-1.5 text-xs text-muted">
          <span className={`shrink-0 font-medium ${tone}`}>
            {undo ? t('status.undone') : t(`status.${decision.status}`)}
          </span>
          <span aria-hidden>·</span>
          <time dateTime={when} className="shrink-0 tabular-nums">
            {intl.formatTime(when, { timeStyle: 'short' })}
          </time>
          <span aria-hidden>·</span>
          <span
            className="inline-flex min-w-0 items-center gap-1"
            title={t(owner ? 'history.byOwner' : 'history.byTriage')}
          >
            {owner ? (
              <UserRound className="size-3 shrink-0" aria-hidden />
            ) : (
              <Bot className="size-3 shrink-0" aria-hidden />
            )}
            <span className="truncate">{t(owner ? 'history.you' : 'history.triage')}</span>
          </span>
          {decision.movie.lock ? (
            <Lock
              role="img"
              className="size-3 shrink-0 text-info"
              aria-label={t('lock.title', { folder: decision.movie.lock.folder })}
            />
          ) : null}
        </p>
        <p className="flex min-w-0 items-center gap-1.5 text-xs">
          {stays ? (
            (to ?? from) && <PlaceChip place={(to ?? from) as Place} strong />
          ) : (
            <>
              <PlaceChip place={from as Place} />
              <ArrowRight className="size-3 shrink-0 text-muted" aria-label={t('history.to')} />
              <PlaceChip place={to as Place} strong />
            </>
          )}
        </p>
      </div>
      <Ring value={decision.confidence} color={categoryColor(to?.id)} />
    </Link>
  )
}

/** The day's movies per library, as one thin bar in the categories' colors. */
function DayStrip({ items, place }: { items: DecisionSummary[]; place: ReturnType<typeof usePlaces> }) {
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
                  <HistoryItem decision={decision} place={place} />
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
