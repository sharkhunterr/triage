import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDown,
  ArrowLeft,
  Ban,
  Bot,
  Database,
  ExternalLink,
  Film,
  FolderOpen,
  Gavel,
  History,
  Lock,
  LockOpen,
  Scale,
} from 'lucide-react'
import { Popover } from 'radix-ui'
import type { ReactNode } from 'react'
import { useIntl } from 'react-intl'
import { Link, useLocation, useParams } from 'react-router'
import { api } from '../../api/client'
import { type DecisionDetail, useDecision } from '../../api/decisions'
import { Badge, Button, Card, cx, ErrorState, Spinner, useToast } from '../../design-system'
import { useT } from '../../i18n'
import { CategoryDot, categoryColor, tint } from '../categories/colors'
import { AnalyzeButton } from './AnalyzeButton'
import { DecisionActions } from './DecisionActions'
import { MatchCheck } from './MatchCheck'
import {
  backFrom,
  ConfidenceMeter,
  isUndo,
  knowsArrival,
  Poster,
  ReasonText,
  Requested,
  StatusBadge,
} from './parts'
import { RequestBadge } from './RequestBadge'

type Signal = DecisionDetail['signals'][number]
type Cat = { id: number; key: string; name: string; folder: string | null }
type Cats = Record<string, Cat>

/** Same comparison as the backend: case- and accent-insensitive. */
const norm = (value: unknown) => String(value).normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().trim()

export function DecisionPage() {
  const t = useT()
  const id = Number(useParams().id)
  const query = useDecision(id)
  const back = backFrom(useLocation().state) // the list it was opened from, its page and filters kept
  if (query.isPending) return <Spinner label={t('common.loading')} />
  if (query.isError)
    return (
      <ErrorState
        title={t('decision.notFound')}
        onRetry={() => query.refetch()}
        retryLabel={t('common.retry')}
      />
    )
  const decision = query.data
  const cats: Cats = Object.fromEntries(
    decision.categories.map((c) => [
      String(c.key),
      {
        id: Number(c.id),
        key: String(c.key),
        name: String(c.name),
        folder: c.root_folder_path ? String(c.root_folder_path) : null,
      },
    ]),
  )
  const name = (key: unknown) => cats[String(key)]?.name ?? String(key)

  return (
    <article className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <Link to={back.to} className="inline-flex items-center gap-1 text-sm text-muted hover:text-text">
          <ArrowLeft className="size-4" aria-hidden /> {t(back.label)}
        </Link>
        <AnalyzeButton radarrId={decision.movie.radarr_id} />
      </div>
      <Header decision={decision} />
      <DecisionActions decision={decision} />
      <Why decision={decision} name={name} cats={cats} />
      <MovieSheet decision={decision} cats={cats} />
      <Trail decision={decision} />
    </article>
  )
}

// ------------------------------------------------------------------ the movie and the verdict

function Header({ decision }: { decision: DecisionDetail }) {
  const t = useT()
  const undo = isUndo(decision)
  const category = undo ? null : (decision.target_category ?? decision.top_category)
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex gap-4">
        <Poster url={decision.movie.poster_url} title={decision.movie.title} size="lg" />
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <h1 className="text-xl leading-tight font-semibold sm:text-2xl">
            {decision.movie.title}
            {decision.movie.year ? (
              <span className="font-normal text-muted"> ({decision.movie.year})</span>
            ) : null}
            <LockButton decision={decision} />
          </h1>
          {knowsArrival(decision.movie) ? (
            <p className="text-sm text-muted">
              <Requested movie={decision.movie} full />
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-1.5">
            {undo ? <Badge>{t('status.undone')}</Badge> : <StatusBadge status={decision.status} />}
            <Badge>{t(`source.${decision.source}`)}</Badge>
            {decision.actor === 'owner' && <Badge tone="info">{t('decision.byOwner')}</Badge>}
            <RequestBadge check={decision.request_check} />
          </div>
          <p className="mt-1 text-sm text-muted">
            {undo ? t('verdict.undone') : t(`verdict.${decision.status}`)}
          </p>
          <p
            className="flex items-center gap-2 text-lg font-semibold"
            style={category ? { color: categoryColor(category.id) } : undefined}
          >
            {category && <CategoryDot id={category.id} className="size-3" />}
            {undo ? decision.target_root_folder : (category?.name ?? t('decision.noCategory'))}
          </p>
        </div>
      </div>

      <div className="grid gap-4 border-t border-border pt-4 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium tracking-wide text-muted uppercase">
            {t('decision.confidence')}
          </p>
          <ConfidenceMeter value={decision.confidence} threshold={decision.threshold} wide />
          {decision.threshold != null && (
            <p className="mt-1 text-xs text-muted">
              {t('decision.thresholdIs', { threshold: `${Math.round(decision.threshold * 100)}%` })}
            </p>
          )}
        </div>
        <div>
          <p className="mb-1 text-xs font-medium tracking-wide text-muted uppercase">
            {t('decision.folders')}
          </p>
          <div className="flex flex-col gap-0.5 text-sm">
            <FolderLine label={t('decision.from')} path={decision.from_root_folder} />
            <ArrowDown className="ml-1 size-3.5 text-muted" aria-hidden />
            <FolderLine
              label={t('decision.to')}
              path={decision.target_root_folder}
              categoryId={category?.id}
            />
          </div>
        </div>
      </div>
      {decision.error && (
        <p role="alert" className="text-sm text-danger">
          {decision.error}
        </p>
      )}
    </Card>
  )
}

function FolderLine({
  label,
  path,
  categoryId,
}: {
  label: string
  path?: string | null
  categoryId?: number
}) {
  const colored = categoryId != null && path
  return (
    <p
      className={cx(
        'flex min-w-0 items-start gap-2',
        colored && 'cat-tint rounded-lg border px-2 py-1 font-semibold',
      )}
      style={colored ? tint(categoryId) : undefined}
    >
      <FolderOpen className={cx('mt-0.5 size-4 shrink-0', !colored && 'text-muted')} aria-hidden />
      <span className="sr-only">{label}</span>
      <code className="min-w-0 break-words">{path ?? '—'}</code>
    </p>
  )
}

// ------------------------------------------------------------------ lock

/** Locked by a choice made by hand: a small padlock by the title; touched, it says where and when,
 * and offers the way out. */
function LockButton({ decision }: { decision: DecisionDetail }) {
  const t = useT()
  const intl = useIntl()
  const toast = useToast()
  const queryClient = useQueryClient()
  const lock = decision.movie.lock
  const unlock = useMutation({
    mutationFn: () => api(`/movies/${decision.movie.radarr_id}/lock`, { method: 'DELETE' }),
    onSuccess: () => {
      toast(t('lock.unlocked'), 'success')
      return queryClient.invalidateQueries()
    },
    onError: (error) => toast(error.message, 'danger'),
  })
  if (!lock) return null
  const label = t('lock.heading', { folder: lock.folder, via: t(`lock.via.${lock.via}`) })
  return (
    <Popover.Root>
      <Popover.Trigger
        aria-label={label}
        title={label}
        className="ml-1.5 inline-grid size-7 place-items-center rounded-full align-middle text-info hover:bg-info/10 focus-visible:outline-2"
      >
        <Lock className="size-4" aria-hidden />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={6}
          collisionPadding={16}
          className="z-50 flex w-72 flex-col gap-2 rounded-lg border border-border bg-surface p-3 text-sm shadow-lg"
        >
          <p className="font-medium">{label}</p>
          <p className="text-xs text-muted">
            {lock.at ? `${intl.formatDate(lock.at, { dateStyle: 'medium', timeStyle: 'short' })} · ` : ''}
            {t('lock.explain')}
          </p>
          <Button
            size="sm"
            icon={<LockOpen className="size-4" aria-hidden />}
            loading={unlock.isPending}
            onClick={() => unlock.mutate()}
          >
            {t('lock.unlock')}
          </Button>
          <Popover.Arrow className="fill-surface" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}

// ------------------------------------------------------------------ why

function Why({
  decision,
  name,
  cats,
}: {
  decision: DecisionDetail
  name: (key: unknown) => string
  cats: Cats
}) {
  const t = useT()
  const signals = decision.signals as Signal[]
  const exclusions = signals.filter((s) => s.kind === 'exclusion')
  const ranked = Object.entries(decision.scores).sort(([, a], [, b]) => b - a)
  const max = Math.max(1, ...ranked.map(([, v]) => v))
  const settled = ['moved', 'moving', 'in_place', 'corrected'].includes(decision.status)

  return (
    <Card className="flex flex-col gap-5">
      <div>
        <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold">
          <Gavel className="size-5" aria-hidden /> {t('why.title')}
        </h2>
        {!settled && decision.reasons.length > 0 && (
          <div className="rounded-lg border border-warning/40 bg-warning/5 p-3">
            <p className="mb-1 text-sm font-medium">{t('why.waiting')}</p>
            <ul className="list-disc pl-5 text-sm">
              {decision.reasons.map((reason) => (
                <li key={JSON.stringify(reason)}>
                  <ReasonText reason={reason} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <section>
        <h3 className="mb-2 flex items-center gap-2 font-semibold">
          <Scale className="size-4" aria-hidden /> {t('decision.scores')}
        </h3>
        <ul className="flex flex-col gap-3">
          {ranked.map(([key, value]) => {
            const own = signals.filter((s) => s.category_key === key)
            const excluded = exclusions.some((s) => s.category_key === key)
            return (
              <li key={key}>
                <div className="flex items-baseline justify-between gap-2 text-sm">
                  <span
                    className={cx(
                      'flex items-center gap-2 font-medium',
                      excluded && 'text-muted line-through',
                    )}
                  >
                    <CategoryDot id={cats[key]?.id} />
                    {name(key)}
                  </span>
                  <span className="tabular-nums text-muted">{t('why.points', { count: value })}</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-surface-2">
                  <div
                    className={cx('h-full rounded-full', excluded && 'bg-danger/40')}
                    style={{
                      width: `${(value / max) * 100}%`,
                      background: excluded ? undefined : categoryColor(cats[key]?.id),
                    }}
                  />
                </div>
                {own.length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {own.map((s) => (
                      <li key={`${s.kind}-${s.rule_id ?? 'f'}-${s.value}`}>
                        <SignalChip signal={s} categoryId={cats[key]?.id} />
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            )
          })}
        </ul>
      </section>

      <AiOpinion decision={decision} name={name} />
    </Card>
  )
}

function SignalChip({ signal, categoryId }: { signal: Signal; categoryId?: number }) {
  const t = useT()
  if (signal.kind === 'fallback')
    return (
      <span className="inline-flex rounded-full bg-surface-2 px-2.5 py-1 text-xs">
        +{String(signal.weight)} · {t('decision.fallbackSignal')}
      </span>
    )
  if (signal.kind === 'inference')
    return (
      <span
        className={cx(
          'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium',
          signal.ignored
            ? 'border-transparent bg-surface-2 text-muted line-through'
            : 'border-info/40 bg-info/10 text-info',
        )}
      >
        <Bot className="size-3" aria-hidden />+{String(signal.weight)} · {t('why.aiSignal')}
        {signal.ignored ? <span className="sr-only">({t('why.ignored')})</span> : null}
      </span>
    )
  const label = (
    <>
      {t(`field.${signal.field}`)} {t(`operator.${signal.operator}`)} <strong>{String(signal.value)}</strong>
    </>
  )
  if (signal.kind === 'exclusion')
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-danger/40 bg-danger/10 px-2.5 py-1 text-xs text-danger">
        <Ban className="size-3" aria-hidden /> {t('why.excludes')} · {label}
      </span>
    )
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs',
        signal.ignored ? 'border-transparent bg-surface-2 text-muted line-through' : 'cat-tint',
      )}
      style={signal.ignored ? undefined : tint(categoryId)}
    >
      +{String(signal.weight)} · {label}
      {signal.decisive ? <span className="font-semibold">· {t('categories.decisive')}</span> : null}
      {signal.ignored ? <span className="sr-only">({t('why.ignored')})</span> : null}
    </span>
  )
}

function exclusionOf(decision: DecisionDetail, key: string, t: (id: string) => string): string {
  return (decision.signals as Signal[])
    .filter((s) => s.kind === 'exclusion' && s.category_key === key)
    .map((s) => `${t(`field.${s.field}`)} ${t(`operator.${s.operator}`)} ${String(s.value)}`)
    .join(', ')
}

function AiOpinion({ decision, name }: { decision: DecisionDetail; name: (key: unknown) => string }) {
  const t = useT()
  const ai = decision.ai
  const inference = (decision.signals as Signal[]).find((s) => s.kind === 'inference')
  return (
    <section className={cx('rounded-lg border p-3', ai ? 'border-info/40 bg-info/5' : 'border-border')}>
      <h3 className="mb-1 flex flex-wrap items-center gap-2 font-semibold">
        <Bot className="size-4" aria-hidden /> {t('decision.ai')}
        {ai?.asked ? <Badge tone="info">{t(`why.asked.${String(ai.asked)}`)}</Badge> : null}
      </h3>
      {!ai ? (
        <p className="text-sm text-muted">{t('decision.aiNotAsked')}</p>
      ) : ai.error ? (
        <p className="text-sm text-warning">{t('decision.aiError', { error: String(ai.error) })}</p>
      ) : (
        <>
          <p className="text-sm">
            {t('decision.aiChose', {
              category: ai.category === 'unsure' ? t('decision.aiUnsure') : name(ai.category),
              confidence: `${Math.round(Number(ai.confidence) * 100)}%`,
            })}
            {inference && !inference.ignored
              ? ` ${t('why.aiAdded', { points: String(inference.weight) })}`
              : ''}
          </p>
          {inference?.ignored ? (
            <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-danger/10 px-2.5 py-1.5 text-sm text-danger">
              <Ban className="mt-0.5 size-4 shrink-0" aria-hidden />
              {t('why.aiIgnored', {
                category: name(ai.category),
                rule: exclusionOf(decision, String(ai.category), t),
              })}
            </p>
          ) : null}
          <blockquote className="mt-2 border-l-2 border-info pl-3 text-sm italic">
            {String(ai.reasoning)}
          </blockquote>
          <p className="mt-1 text-xs text-muted">
            {t('decision.aiHint')} {ai.model ? `· ${String(ai.model)}` : ''}
          </p>
        </>
      )}
    </section>
  )
}

// ------------------------------------------------------------------ the movie's metadata

const LANGUAGES = typeof Intl.DisplayNames === 'function' ? Intl.DisplayNames : undefined

function MovieSheet({ decision, cats }: { decision: DecisionDetail; cats: Cats }) {
  const t = useT()
  const facts = decision.facts
  const signals = (decision.signals as Signal[]).filter((s) => s.kind === 'fact' || s.kind === 'exclusion')
  const language = (code: string) => {
    try {
      return LANGUAGES
        ? (new LANGUAGES([document.documentElement.lang || 'en'], { type: 'language' }).of(code) ?? code)
        : code
    } catch {
      return code
    }
  }
  // Radarr names the language ("English"), TMDB gives its code ("en"): keep one, preferably the code
  const english = (code: string) => {
    try {
      return LANGUAGES ? (new LANGUAGES(['en'], { type: 'language' }).of(code) ?? code) : code
    } catch {
      return code
    }
  }
  const languages = (values: string[]) => {
    const seen = new Map<string, string>()
    for (const v of [...values].sort((a, b) => a.length - b.length)) {
      const key = norm(v.length <= 3 ? english(v) : v)
      if (!seen.has(key)) seen.set(key, v)
    }
    return [...seen.values()]
  }
  // the matching is done on the raw value; the language is only translated for display
  type Row = [string, string[], (v: string) => string]
  const rows: Row[] = [
    ['genre', facts.genre ?? [], (v) => v],
    ['keyword', facts.keyword ?? [], (v) => v],
    ['company', facts.company ?? [], (v) => v],
    ['certification', [...(facts.certification ?? [])].sort(), (v) => v],
    ['original_language', languages(facts.original_language ?? []), language],
  ]
  const filled = rows.filter(([, values]) => values.length > 0)
  const missing = rows
    .filter(([, values]) => values.length === 0)
    .map(([field]) => t(`field.${field}`).toLocaleLowerCase())
  const wikidata = facts.wikidata ?? []
  const destination = (decision.target_category ?? decision.top_category)?.id
  const used = Object.values(cats).filter(
    (c) => c.id === destination || signals.some((s) => s.category_key === c.key),
  )
  const chips = (field: string, values: string[], display: (v: string) => string = (v) => v) => (
    <ul className="flex flex-wrap gap-1.5">
      {values.map((v) => (
        <li key={v}>
          <FactChip
            label={display(v)}
            matches={signals.filter((s) => s.field === field && norm(s.value) === norm(v))}
            cats={cats}
          />
        </li>
      ))}
    </ul>
  )
  return (
    <Card className="flex flex-col gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Film className="size-5" aria-hidden /> {t('sheet.title')}
      </h2>
      <MatchCheck radarrId={decision.movie.radarr_id} />
      <div>
        <h3 className="flex items-center gap-2 font-semibold">
          <Database className="size-4" aria-hidden /> {t('decision.metadata')}
        </h3>
        <p className="text-xs text-muted">{t('decision.metadataHint')}</p>
      </div>
      {used.length > 0 && (
        <div className="flex flex-col gap-1.5 rounded-lg bg-surface-2 p-3 text-xs">
          <ul className="flex flex-wrap gap-x-4 gap-y-1">
            {used.map((c) => (
              <li
                key={c.key}
                className="flex items-center gap-1.5 font-medium"
                style={{ color: categoryColor(c.id) }}
              >
                <CategoryDot id={c.id} />
                {c.name}
                {c.folder && <code className="font-normal text-muted">{c.folder}</code>}
              </li>
            ))}
          </ul>
          <p className="text-muted">{t('sheet.legend')}</p>
        </div>
      )}
      <Source
        title={t('sheet.fromTmdb')}
        link={
          decision.movie.tmdb_id
            ? { href: `https://www.themoviedb.org/movie/${decision.movie.tmdb_id}`, label: 'TMDB' }
            : undefined
        }
      >
        {decision.overview ? (
          <p className="text-sm leading-relaxed">{decision.overview}</p>
        ) : (
          <p className="text-sm text-muted">{t('sheet.noOverview')}</p>
        )}
        {filled.length ? (
          <dl className="grid gap-3 sm:grid-cols-2">
            {filled.map(([field, values, display]) => (
              <div key={field} className={field === 'keyword' ? 'sm:col-span-2' : undefined}>
                <dt className="mb-1 text-xs font-medium tracking-wide text-muted uppercase">
                  {t(`field.${field}`)}
                </dt>
                <dd>{chips(field, values, display)}</dd>
              </div>
            ))}
          </dl>
        ) : null}
        {missing.length ? (
          <p className="text-xs text-muted">{t('sheet.missing', { fields: missing.join(', ') })}</p>
        ) : null}
      </Source>
      {wikidata.length || decision.wikipedia ? (
        <Source
          title={t('sheet.fromWiki')}
          link={
            decision.wikipedia?.url
              ? { href: decision.wikipedia.url, label: t('sheet.wikipedia') }
              : undefined
          }
        >
          {decision.wikipedia ? (
            <p className="text-sm leading-relaxed">{decision.wikipedia.extract}</p>
          ) : null}
          {wikidata.length ? (
            <div>
              <p className="mb-1 text-xs font-medium tracking-wide text-muted uppercase">
                {t('field.wikidata')}
              </p>
              {chips('wikidata', wikidata)}
            </div>
          ) : null}
        </Source>
      ) : null}
    </Card>
  )
}

/** One source of the movie's metadata in its own box, its name above, a link to it on the right. */
function Source({
  title,
  link,
  children,
}: {
  title: string
  link?: { href: string; label: string }
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold">{title}</h4>
        {link ? (
          <a
            href={link.href}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
          >
            {link.label} <ExternalLink className="size-3" aria-hidden />
          </a>
        ) : null}
      </div>
      {children}
    </section>
  )
}

function FactChip({ label, matches, cats }: { label: string; matches: Signal[]; cats: Cats }) {
  const t = useT()
  const exclusion = matches.find((s) => s.kind === 'exclusion')
  const counted = matches.filter((s) => s.kind === 'fact' && !s.ignored)
  const ignored = matches.filter((s) => s.kind === 'fact' && s.ignored)
  const base = 'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs'
  if (exclusion) {
    const category = cats[String(exclusion.category_key)]
    return (
      <span className={cx(base, 'border-danger/40 bg-danger/10 font-medium text-danger')}>
        <Ban className="size-3" aria-hidden />
        {label}
        <span className="sr-only">({t('sheet.excludes', { category: category?.name ?? '' })})</span>
      </span>
    )
  }
  const main = counted[0] ?? ignored[0]
  if (!main) return <span className={cx(base, 'border-transparent bg-surface-2')}>{label}</span>
  const category = cats[String(main.category_key)]
  return (
    <span
      className={cx(base, 'cat-tint font-medium', counted.length === 0 && 'line-through opacity-70')}
      style={tint(category?.id)}
    >
      {label}
      {counted.slice(1).map((s) => (
        <CategoryDot key={String(s.category_key)} id={cats[String(s.category_key)]?.id} className="size-2" />
      ))}
      <span className="sr-only">
        ({counted.map((s) => cats[String(s.category_key)]?.name).join(', ') || t('why.ignored')})
      </span>
    </span>
  )
}

// ------------------------------------------------------------------ audit trail

function Trail({ decision }: { decision: DecisionDetail }) {
  const t = useT()
  if (decision.audit.length === 0) return null
  return (
    <Card>
      <h2 className="mb-2 flex items-center gap-2 font-semibold">
        <History className="size-4" aria-hidden /> {t('decision.trail')}
      </h2>
      <ol className="flex flex-col gap-2 text-sm">
        {decision.audit.map((event) => (
          <li key={`${event.at}-${event.action}`} className="flex flex-col">
            <span>
              {t(`audit.${event.action}`)} ({t(`actor.${event.actor}`)})
              {event.result !== 'ok' && (
                <>
                  {' '}
                  <Badge tone="danger">{event.result}</Badge>
                </>
              )}
            </span>
            <span className="text-xs text-muted">
              <time>{new Date(event.at).toLocaleString()}</time>
              {event.to_path && (
                <>
                  {' '}
                  → <code className="break-words">{event.to_path}</code>
                </>
              )}
            </span>
          </li>
        ))}
      </ol>
    </Card>
  )
}
