import {
  ArrowRight,
  ArrowRightLeft,
  Bot,
  CircleCheck,
  CircleHelp,
  CircleSlash,
  Film,
  FolderOpen,
  type LucideIcon,
  MapPin,
  PenLine,
  Sparkles,
  TriangleAlert,
  Undo2,
  UserRound,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { useIntl } from 'react-intl'
import { Link } from 'react-router'
import { useCategories } from '../../api/categories'
import type { DecisionSummary } from '../../api/decisions'
import { useT } from '../../i18n'
import { CategoryDot, categoryColor, tint } from '../categories/colors'
import { isUndo, LockBadge, ReasonText, useFromHere } from './parts'

type Place = { id: number | null; name: string }
export type Places = (folder: string | null | undefined) => Place | null

/** A folder as the owner knows it: the category whose library it is, else its last segment. */
export function usePlaces(): Places {
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

/** One decision as a timeline row: the poster with its status, where the movie goes, how sure Triage
 * is. A check's waiting movie gets its choice under it instead (`choose`): the title on the whole
 * width, the way and the ring under it, then the choice across the row, given the status line to show
 * beside its confirm button. */
export function TimelineRow({
  decision,
  place,
  note = false,
  choose,
}: {
  decision: DecisionSummary
  place: Places
  note?: boolean // the reasons too (a doubt: why Triage hesitates)
  choose?: (meta: ReactNode) => ReactNode
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

  const poster = (
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
  )
  const title = (
    <p className="line-clamp-2 leading-snug font-medium">
      {decision.movie.title}
      {decision.movie.year ? <span className="font-normal text-muted"> · {decision.movie.year}</span> : null}
    </p>
  )
  const meta = (
    <p
      className={`flex min-w-0 items-center gap-x-1.5 text-xs text-muted ${choose ? 'flex-wrap gap-y-0.5' : ''}`}
    >
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
      <LockBadge lock={decision.movie.lock} />
    </p>
  )
  const way = (
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
  )
  const reasons =
    note && decision.reasons.length > 0 ? (
      <p className="line-clamp-2 text-xs text-muted">
        {decision.reasons.map((reason, index) => (
          <span key={JSON.stringify(reason)}>
            {index > 0 ? ' ' : ''}
            <ReasonText reason={reason} />
          </span>
        ))}
      </p>
    ) : null
  const ring = <Ring value={decision.confidence} color={categoryColor(to?.id)} />

  if (choose)
    return (
      <div className="flex flex-col gap-3 px-3 py-3 sm:px-4">
        <Link
          to={`/decisions/${decision.id}`}
          state={here}
          className="-m-1.5 flex gap-3 rounded-lg p-1.5 transition-colors hover:bg-surface-2/60 focus-visible:outline-2"
        >
          {poster}
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            {title}
            <div className="flex items-center gap-2">
              <div className="min-w-0 flex-1">{way}</div>
              {ring}
            </div>
            {reasons}
          </div>
        </Link>
        <div className="border-t border-border pt-3">{choose(meta)}</div>
      </div>
    )
  return (
    <Link
      to={`/decisions/${decision.id}`}
      state={here}
      className="flex items-center gap-3 px-3 py-3 transition-colors hover:bg-surface-2/60 focus-visible:outline-2 focus-visible:-outline-offset-2 sm:px-4"
    >
      {poster}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {title}
        {meta}
        {way}
        {reasons}
      </div>
      {ring}
    </Link>
  )
}
