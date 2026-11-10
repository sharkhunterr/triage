import { ArrowRight, Bot, CalendarPlus, Film, Lock, Undo2, UserRound } from 'lucide-react'
import { useIntl } from 'react-intl'
import { Link, useLocation } from 'react-router'
import type { DecisionSummary } from '../../api/decisions'
import { Badge, Card, type Tone } from '../../design-system'
import { useT } from '../../i18n'

const STATUS_TONE: Record<string, Tone> = {
  moved: 'success',
  moving: 'info',
  proposed: 'accent',
  held: 'warning',
  failed: 'danger',
  dismissed: 'neutral',
  left_in_intake: 'neutral',
  superseded: 'neutral',
  simulated: 'info',
  in_place: 'success',
  corrected: 'neutral',
}

export function StatusBadge({ status }: { status: string }) {
  const t = useT()
  return <Badge tone={STATUS_TONE[status] ?? 'neutral'}>{t(`status.${status}`)}</Badge>
}

/** The movie is locked in the library the owner chose by hand, and where that choice was made. */
export function LockBadge({ lock }: { lock?: DecisionSummary['movie']['lock'] }) {
  const t = useT()
  if (!lock) return null
  return (
    <span title={t('lock.title', { folder: lock.folder })}>
      <Badge tone="info">
        <Lock className="size-3" aria-hidden />
        {t('lock.badge')} · {t(`lock.via.${lock.via}`)}
      </Badge>
    </span>
  )
}

export function Poster({
  url,
  title,
  size = 'md',
}: {
  url?: string | null
  title: string
  size?: 'sm' | 'md' | 'lg'
}) {
  const box = size === 'lg' ? 'w-28 h-42' : size === 'sm' ? 'w-10 h-15' : 'w-14 h-21'
  return url ? (
    <img
      src={url}
      alt={size === 'lg' ? title : ''}
      loading="lazy"
      className={`${box} shrink-0 rounded-md object-cover bg-surface-2`}
    />
  ) : (
    <div className={`${box} flex shrink-0 items-center justify-center rounded-md bg-surface-2`} aria-hidden>
      <Film className="size-5 text-muted" />
    </div>
  )
}

export function ConfidenceMeter({
  value,
  threshold,
  wide,
}: {
  value: number
  threshold?: number | null
  wide?: boolean
}) {
  const t = useT()
  const percent = Math.round(value * 100)
  const enough = threshold == null || value >= threshold
  return (
    <div className="flex items-center gap-2">
      <meter className="sr-only" min={0} max={100} value={percent} aria-label={t('decision.confidence')} />
      <div
        aria-hidden
        className={`relative h-2 overflow-hidden rounded-full bg-surface-2 ${wide ? 'flex-1' : 'w-24'}`}
      >
        <div
          className={`h-full rounded-full ${enough ? 'bg-success' : 'bg-warning'}`}
          style={{ width: `${percent}%` }}
        />
        {threshold != null && (
          <div
            className="absolute inset-y-0 w-0.5 bg-text/40"
            style={{ left: `${Math.round(threshold * 100)}%` }}
          />
        )}
      </div>
      <span className="text-xs tabular-nums text-muted">{percent}%</span>
    </div>
  )
}

type Reason = { code?: unknown; [key: string]: unknown }

export function ReasonText({ reason }: { reason: Reason }) {
  const t = useT()
  const code = String(reason.code ?? 'unknown')
  const values: Record<string, string | number> = {}
  for (const [key, value] of Object.entries(reason)) {
    if (key === 'code') continue
    if (typeof value === 'number')
      values[key] = key === 'confidence' || key === 'threshold' ? `${Math.round(value * 100)}%` : value
    else if (Array.isArray(value)) values[key] = value.join(', ')
    else if (value != null) values[key] = String(value)
  }
  return <>{t(`reason.${code}`, values)}</>
}

type MovieDates = Pick<DecisionSummary['movie'], 'requested_by' | 'requested_at' | 'added_at'>

/** Whether there is anything to say of who asked for the movie or when it arrived. */
export const knowsArrival = (movie: MovieDates) => Boolean(movie.requested_by || movie.added_at)

/** Who asked for the movie in Seerr and when — else when Radarr added it; nothing when neither is known.
 * `full` (the movie's sheet) says the hour too. */
export function Requested({ movie, full = false }: { movie: MovieDates; full?: boolean }) {
  const text = full ? '' : 'truncate'
  const t = useT()
  const intl = useIntl()
  const when = (value: string) =>
    intl.formatDate(
      value,
      full ? { dateStyle: 'medium', timeStyle: 'short' } : { day: 'numeric', month: 'short' },
    )
  if (movie.requested_by)
    return (
      <span className="inline-flex min-w-0 items-start gap-1">
        <UserRound className="mt-0.5 size-3.5 shrink-0" aria-hidden />
        <span className={text}>
          {movie.requested_at
            ? t('movie.requestedOn', { who: movie.requested_by, when: when(movie.requested_at) })
            : t('movie.requestedBy', { who: movie.requested_by })}
        </span>
      </span>
    )
  if (movie.added_at)
    return (
      <span className="inline-flex min-w-0 items-start gap-1">
        <CalendarPlus className="mt-0.5 size-3.5 shrink-0" aria-hidden />
        <span className={text}>{t('movie.addedOn', { when: when(movie.added_at) })}</span>
      </span>
    )
  return null
}

/** The pages a movie's sheet may be opened from, and how its back link names them. */
const ORIGINS: [string, string][] = [
  ['/review', 'nav.review'],
  ['/activity', 'nav.activity'],
  ['/history', 'nav.history'],
  ['/scans', 'nav.scans'],
  ['/status', 'nav.status'],
]

/** The state a link to a movie's sheet carries: the page it is opened from (its list page and filters
 * included), where the sheet's back link returns. */
export function useFromHere(): { from: string } {
  const location = useLocation()
  const kept = (location.state as { from?: unknown } | null)?.from
  // from one sheet to another (a new analysis): back still goes to the list the first was opened from
  if (location.pathname.startsWith('/decisions/') && typeof kept === 'string') return { from: kept }
  return { from: `${location.pathname}${location.search}` }
}

/** Where a sheet's back link goes, and its label: the page it was opened from, else the history. */
export function backFrom(state: unknown): { to: string; label: string } {
  const from = (state as { from?: unknown } | null)?.from
  if (typeof from !== 'string' || !from.startsWith('/') || from.startsWith('//'))
    return { to: '/history', label: 'nav.history' }
  if (from === '/' || from.startsWith('/?')) return { to: from, label: 'nav.dashboard' }
  const origin = ORIGINS.find(
    ([path]) => from === path || from.startsWith(`${path}?`) || from.startsWith(`${path}/`),
  )
  return { to: from, label: origin ? origin[1] : 'common.back' }
}

/** A correction with no category: the movie was put back in the folder it came from (an undo). */
export const isUndo = (decision: DecisionSummary) =>
  decision.source === 'correction' && !decision.target_category

export function DecisionCard({ decision }: { decision: DecisionSummary }) {
  const t = useT()
  const here = useFromHere()
  const undo = isUndo(decision)
  const category = undo ? null : (decision.target_category ?? decision.top_category)
  return (
    <Link
      to={`/decisions/${decision.id}`}
      state={here}
      className="block min-w-0 rounded-card focus-visible:outline-2"
    >
      <Card className="flex gap-3 transition-colors hover:bg-surface-2">
        <Poster url={decision.movie.poster_url} title={decision.movie.title} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="min-w-0 max-w-full truncate font-medium">
              {decision.movie.title}
              {decision.movie.year ? <span className="text-muted"> ({decision.movie.year})</span> : null}
            </p>
            {undo ? <Badge>{t('status.undone')}</Badge> : <StatusBadge status={decision.status} />}
            <LockBadge lock={decision.movie.lock} />
          </div>
          <p className="mt-1 flex items-center gap-1 text-sm text-muted">
            {undo ? (
              <>
                <Undo2 className="size-3.5" aria-hidden />
                <code className="truncate">{decision.target_root_folder}</code>
              </>
            ) : category ? (
              <>
                <ArrowRight className="size-3.5" aria-hidden />
                <span>{category.name}</span>
              </>
            ) : (
              <span>{t('decision.noCategory')}</span>
            )}
          </p>
          {decision.reasons[0] && decision.status !== 'moved' && (
            <p className="mt-1 line-clamp-1 text-xs text-muted">
              <ReasonText reason={decision.reasons[0]} />
            </p>
          )}
          <div className="mt-2">
            <ConfidenceMeter value={decision.confidence} />
          </div>
        </div>
      </Card>
    </Link>
  )
}

const PRIOR = 20 // the scoring engine's prior (domain/scoring.py)

/** A category's confidence were it chosen: its points against the best other one, as the rules compute it. */
export function choiceConfidence(decision: DecisionSummary, key: string): number {
  if (decision.excluded.includes(key)) return 0
  const own = decision.scores[key] ?? 0
  if (own <= 0) return 0
  const best = Math.max(
    0,
    ...Object.entries(decision.scores)
      .filter(([k]) => k !== key)
      .map(([, v]) => v),
  )
  return own / (own + best + PRIOR)
}

/** What a choice is worth: the rules' confidence, and the AI's when it picked this category. */
export function ChoiceInfo({ decision, categoryKey }: { decision: DecisionSummary; categoryKey: string }) {
  const t = useT()
  const ai = decision.ai
  const aiPicked = ai && !ai.error && ai.category === categoryKey
  if (decision.excluded.includes(categoryKey))
    return <span className="text-[0.8em] font-normal">· {t('choice.excluded')}</span>
  return (
    <span className="inline-flex items-center gap-1 text-[0.8em] font-normal tabular-nums">
      · {Math.round(choiceConfidence(decision, categoryKey) * 100)} %
      {aiPicked && (
        <span className="inline-flex items-center gap-0.5" title={t('choice.ai')}>
          · <Bot className="size-3" aria-hidden />
          <span className="sr-only">{t('choice.ai')}</span> {Math.round(Number(ai.confidence) * 100)} %
        </span>
      )}
    </span>
  )
}
