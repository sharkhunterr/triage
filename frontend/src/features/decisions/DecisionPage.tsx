import { ArrowLeft, Bot, Database, FolderInput } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { useDecision } from '../../api/decisions'
import { Badge, Card, ErrorState, Spinner } from '../../design-system'
import { useT } from '../../i18n'
import { DecisionActions } from './DecisionActions'
import { ConfidenceMeter, Poster, ReasonText, StatusBadge } from './parts'
import { RequestBadge } from './RequestBadge'
import { SimulateButton } from './SimulateButton'

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
  const facts = decision.signals.filter((s) => s.kind === 'fact')
  const fallback = decision.signals.find((s) => s.kind === 'fallback')
  const maxScore = Math.max(1, ...Object.values(decision.scores))

  return (
    <article className="flex flex-col gap-4">
      <Link to="/history" className="inline-flex items-center gap-1 text-sm text-muted hover:text-text">
        <ArrowLeft className="size-4" aria-hidden /> {t('nav.history')}
      </Link>
      <Card className="flex gap-4">
        <Poster url={decision.movie.poster_url} title={decision.movie.title} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold">
            {decision.movie.title}
            {decision.movie.year ? <span className="text-muted"> ({decision.movie.year})</span> : null}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={decision.status} />
            <Badge>{t(`source.${decision.source}`)}</Badge>
            {decision.actor === 'owner' && <Badge tone="info">{t('decision.byOwner')}</Badge>}
            <RequestBadge check={decision.request_check} />
            <SimulateButton radarrId={decision.movie.radarr_id} />
          </div>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-muted">{t('decision.category')}</dt>
            <dd>{decision.target_category?.name ?? decision.top_category?.name ?? '—'}</dd>
            <dt className="text-muted">{t('decision.confidence')}</dt>
            <dd>
              <ConfidenceMeter value={decision.confidence} threshold={decision.threshold} />
            </dd>
            <dt className="text-muted">
              <FolderInput className="inline size-4" aria-hidden /> {t('decision.folders')}
            </dt>
            <dd className="break-all">
              <code>{decision.from_root_folder ?? '—'}</code> →{' '}
              <code>{decision.target_root_folder ?? '—'}</code>
            </dd>
          </dl>
          {decision.error && (
            <p role="alert" className="mt-2 text-sm text-danger">
              {decision.error}
            </p>
          )}
        </div>
      </Card>

      <DecisionActions decision={decision} />

      {decision.reasons.length > 0 && (
        <Card>
          <h2 className="mb-2 font-semibold">{t('decision.why')}</h2>
          <ul className="list-disc pl-5 text-sm">
            {decision.reasons.map((reason) => (
              <li key={JSON.stringify(reason)}>
                <ReasonText reason={reason} />
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card>
        <h2 className="mb-1 flex items-center gap-2 font-semibold">
          <Database className="size-4" aria-hidden /> {t('decision.metadata')}
        </h2>
        <p className="mb-3 text-xs text-muted">{t('decision.metadataHint')}</p>
        {facts.length === 0 && !fallback ? (
          <p className="text-sm text-muted">{t('decision.noSignal')}</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted">
              <tr>
                <th className="py-1 font-medium">{t('decision.signal')}</th>
                <th className="py-1 font-medium">{t('decision.category')}</th>
                <th className="py-1 text-right font-medium">{t('categories.ruleWeight')}</th>
              </tr>
            </thead>
            <tbody>
              {facts.map((s) => (
                <tr key={`${s.rule_id}-${s.value}`} className="border-t border-border">
                  <td className="py-1.5">
                    {t(`field.${s.field}`)} {t(`operator.${s.operator}`)} <strong>{String(s.value)}</strong>
                    {s.decisive ? (
                      <>
                        {' '}
                        <Badge tone="accent">{t('categories.decisive')}</Badge>
                      </>
                    ) : null}
                  </td>
                  <td className="py-1.5">{names[String(s.category_key)] ?? String(s.category_key)}</td>
                  <td className="py-1.5 text-right tabular-nums">+{String(s.weight)}</td>
                </tr>
              ))}
              {fallback && (
                <tr className="border-t border-border">
                  <td className="py-1.5">{t('decision.fallbackSignal')}</td>
                  <td className="py-1.5">{names[String(fallback.category_key)]}</td>
                  <td className="py-1.5 text-right tabular-nums">+{String(fallback.weight)}</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-muted">{t('decision.allMetadata')}</summary>
          <dl className="mt-2 grid gap-2 sm:grid-cols-2">
            {Object.entries(decision.facts).map(([field, values]) => (
              <div key={field}>
                <dt className="text-xs text-muted">{t(`field.${field}`)}</dt>
                <dd>{values.length ? values.join(', ') : '—'}</dd>
              </div>
            ))}
          </dl>
        </details>
      </Card>

      <Card className={decision.ai ? 'border-info/40' : undefined}>
        <h2 className="mb-1 flex items-center gap-2 font-semibold">
          <Bot className="size-4" aria-hidden /> {t('decision.ai')}
        </h2>
        {!decision.ai ? (
          <p className="text-sm text-muted">{t('decision.aiNotAsked')}</p>
        ) : decision.ai.error ? (
          <p className="text-sm text-warning">
            {t('decision.aiError', { error: String(decision.ai.error) })}
          </p>
        ) : (
          <>
            <p className="mb-2 text-xs text-muted">{t('decision.aiHint')}</p>
            <p className="text-sm">
              {t('decision.aiChose', {
                category:
                  decision.ai.category === 'unsure'
                    ? t('decision.aiUnsure')
                    : (names[String(decision.ai.category)] ?? String(decision.ai.category)),
                confidence: `${Math.round(Number(decision.ai.confidence) * 100)}%`,
              })}
            </p>
            <blockquote className="mt-2 border-l-2 border-info pl-3 text-sm italic">
              {String(decision.ai.reasoning)}
            </blockquote>
            <p className="mt-1 text-xs text-muted">{String(decision.ai.model ?? '')}</p>
          </>
        )}
      </Card>

      <Card>
        <h2 className="mb-2 font-semibold">{t('decision.scores')}</h2>
        <ul className="flex flex-col gap-2">
          {Object.entries(decision.scores)
            .sort(([, a], [, b]) => b - a)
            .map(([key, value]) => (
              <li key={key} className="text-sm">
                <div className="flex justify-between">
                  <span>{names[key] ?? key}</span>
                  <span className="tabular-nums text-muted">{value}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-surface-2">
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{ width: `${(value / maxScore) * 100}%` }}
                  />
                </div>
              </li>
            ))}
        </ul>
      </Card>

      {decision.audit.length > 0 && (
        <Card>
          <h2 className="mb-2 font-semibold">{t('decision.trail')}</h2>
          <ol className="flex flex-col gap-1 text-sm">
            {decision.audit.map((event) => (
              <li key={`${event.at}-${event.action}`}>
                <time className="text-muted">{new Date(event.at).toLocaleString()}</time> —{' '}
                {t(`audit.${event.action}`)} ({t(`actor.${event.actor}`)}){' '}
                {event.to_path && <code>{event.to_path}</code>}
                {event.result !== 'ok' && <Badge tone="danger">{event.result}</Badge>}
              </li>
            ))}
          </ol>
        </Card>
      )}
    </article>
  )
}
