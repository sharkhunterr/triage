import {
  ArrowDown,
  ArrowLeft,
  Ban,
  Bot,
  Database,
  Film,
  FolderOpen,
  Gavel,
  History,
  Scale,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { type DecisionDetail, useDecision } from '../../api/decisions'
import { Badge, Card, cx, ErrorState, Spinner } from '../../design-system'
import { useT } from '../../i18n'
import { DecisionActions } from './DecisionActions'
import { ConfidenceMeter, Poster, ReasonText, StatusBadge } from './parts'
import { RequestBadge } from './RequestBadge'
import { SimulateButton } from './SimulateButton'

type Signal = DecisionDetail['signals'][number]

export function DecisionPage() {
  const t = useT()
  const id = Number(useParams().id)
  const query = useDecision(id)
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
  const names = Object.fromEntries(decision.categories.map((c) => [String(c.key), String(c.name)]))
  const name = (key: unknown) => names[String(key)] ?? String(key)

  return (
    <article className="flex flex-col gap-4">
      <Link to="/history" className="inline-flex items-center gap-1 text-sm text-muted hover:text-text">
        <ArrowLeft className="size-4" aria-hidden /> {t('nav.history')}
      </Link>
      <Header decision={decision} />
      <DecisionActions decision={decision} />
      <Why decision={decision} name={name} />
      <MovieSheet decision={decision} />
      <Trail decision={decision} />
    </article>
  )
}

// ------------------------------------------------------------------ the movie and the verdict

function Header({ decision }: { decision: DecisionDetail }) {
  const t = useT()
  const category = decision.target_category ?? decision.top_category
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
          </h1>
          <div className="flex flex-wrap items-center gap-1.5">
            <StatusBadge status={decision.status} />
            <Badge>{t(`source.${decision.source}`)}</Badge>
            {decision.actor === 'owner' && <Badge tone="info">{t('decision.byOwner')}</Badge>}
            <RequestBadge check={decision.request_check} />
          </div>
          <p className="mt-1 text-sm text-muted">{t(`verdict.${decision.status}`)}</p>
          <p className="text-lg font-semibold">{category?.name ?? t('decision.noCategory')}</p>
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
            <FolderLine label={t('decision.to')} path={decision.target_root_folder} strong />
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

function FolderLine({ label, path, strong }: { label: string; path?: string | null; strong?: boolean }) {
  return (
    <p className="flex min-w-0 items-start gap-2">
      <FolderOpen className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
      <span className="sr-only">{label}</span>
      <code className={cx('min-w-0 break-words', strong && 'font-semibold')}>{path ?? '—'}</code>
    </p>
  )
}

// ------------------------------------------------------------------ why

function Why({ decision, name }: { decision: DecisionDetail; name: (key: unknown) => string }) {
  const t = useT()
  const signals = decision.signals as Signal[]
  const exclusions = signals.filter((s) => s.kind === 'exclusion')
  const facts = signals.filter((s) => s.kind === 'fact')
  const fallback = signals.find((s) => s.kind === 'fallback')
  const decisive = facts.find((s) => s.decisive && !s.ignored)
  const ranked = Object.entries(decision.scores).sort(([, a], [, b]) => b - a)
  const max = Math.max(1, ...ranked.map(([, v]) => v))
  const settled = ['moved', 'moving', 'in_place', 'corrected'].includes(decision.status)

  const headline: ReactNode[] = []
  for (const s of exclusions)
    headline.push(
      t('why.excluded', {
        category: name(s.category_key),
        field: t(`field.${s.field}`),
        value: String(s.value),
      }),
    )
  if (decisive)
    headline.push(
      t('why.decisive', {
        category: name(decisive.category_key),
        field: t(`field.${decisive.field}`),
        value: String(decisive.value),
      }),
    )
  else if (fallback) headline.push(t('why.fallback', { category: name(fallback.category_key) }))
  else if (ranked[0] && ranked[0][1] > 0)
    headline.push(
      t('why.scores', {
        top: name(ranked[0][0]),
        topScore: ranked[0][1],
        second: ranked[1] ? name(ranked[1][0]) : '—',
        secondScore: ranked[1]?.[1] ?? 0,
      }),
    )

  return (
    <Card className="flex flex-col gap-5">
      <div>
        <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold">
          <Gavel className="size-5" aria-hidden /> {t('why.title')}
        </h2>
        {headline.length > 0 ? (
          <ul className="flex flex-col gap-1 text-sm">
            {headline.map((line) => (
              <li key={String(line)}>{line}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">{t('decision.noSignal')}</p>
        )}
        {!settled && decision.reasons.length > 0 && (
          <div className="mt-3 rounded-lg border border-warning/40 bg-warning/5 p-3">
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
            const own = signals.filter((s) => s.category_key === key && s.kind !== 'inference')
            const excluded = exclusions.some((s) => s.category_key === key)
            return (
              <li key={key}>
                <div className="flex items-baseline justify-between gap-2 text-sm">
                  <span className={cx('font-medium', excluded && 'text-muted line-through')}>
                    {name(key)}
                  </span>
                  <span className="tabular-nums text-muted">{t('why.points', { count: value })}</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-surface-2">
                  <div
                    className={cx('h-full rounded-full', excluded ? 'bg-danger/40' : 'bg-accent')}
                    style={{ width: `${(value / max) * 100}%` }}
                  />
                </div>
                {own.length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {own.map((s) => (
                      <li key={`${s.kind}-${s.rule_id ?? 'f'}-${s.value}`}>
                        <SignalChip signal={s} />
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

function SignalChip({ signal }: { signal: Signal }) {
  const t = useT()
  if (signal.kind === 'fallback')
    return (
      <span className="inline-flex rounded-full bg-surface-2 px-2.5 py-1 text-xs">
        +{String(signal.weight)} · {t('decision.fallbackSignal')}
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
        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs',
        signal.ignored ? 'bg-surface-2 text-muted line-through' : 'bg-accent/10',
      )}
    >
      +{String(signal.weight)} · {label}
      {signal.decisive ? <span className="font-semibold">· {t('categories.decisive')}</span> : null}
      {signal.ignored ? <span className="sr-only">({t('why.ignored')})</span> : null}
    </span>
  )
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
            {inference?.ignored ? ` ${t('why.aiIgnored')}` : ''}
          </p>
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

function MovieSheet({ decision }: { decision: DecisionDetail }) {
  const t = useT()
  const facts = decision.facts
  const language = (code: string) => {
    try {
      return LANGUAGES
        ? (new LANGUAGES([document.documentElement.lang || 'en'], { type: 'language' }).of(code) ?? code)
        : code
    } catch {
      return code
    }
  }
  const rows: [string, string[]][] = [
    ['genre', facts.genre ?? []],
    ['company', facts.company ?? []],
    ['certification', facts.certification ?? []],
    ['original_language', (facts.original_language ?? []).map(language)],
  ]
  const keywords = facts.keyword ?? []
  return (
    <Card className="flex flex-col gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Film className="size-5" aria-hidden /> {t('sheet.title')}
      </h2>
      {decision.overview ? (
        <p className="text-sm leading-relaxed">{decision.overview}</p>
      ) : (
        <p className="text-sm text-muted">{t('sheet.noOverview')}</p>
      )}
      <div>
        <h3 className="flex items-center gap-2 font-semibold">
          <Database className="size-4" aria-hidden /> {t('decision.metadata')}
        </h3>
        <p className="text-xs text-muted">{t('decision.metadataHint')}</p>
      </div>
      <dl className="grid gap-4 sm:grid-cols-2">
        {rows.map(([field, values]) => (
          <div key={field}>
            <dt className="mb-1 text-xs font-medium tracking-wide text-muted uppercase">
              {t(`field.${field}`)}
            </dt>
            <dd>
              <Chips values={values} />
            </dd>
          </div>
        ))}
      </dl>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted">
          {t('sheet.keywords', { count: keywords.length })}
        </summary>
        <div className="mt-2">
          <Chips values={keywords} />
        </div>
      </details>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3 text-xs text-muted">
        <span>{t('sheet.sources')}</span>
        <SimulateButton radarrId={decision.movie.radarr_id} />
      </div>
    </Card>
  )
}

function Chips({ values }: { values: string[] }) {
  if (values.length === 0) return <span className="text-sm text-muted">—</span>
  return (
    <ul className="flex flex-wrap gap-1.5">
      {values.map((v) => (
        <li key={v} className="rounded-full bg-surface-2 px-2.5 py-1 text-xs">
          {v}
        </li>
      ))}
    </ul>
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
