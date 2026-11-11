import { CheckCircle2, CircleDashed, Loader2, MinusCircle, Square, XCircle } from 'lucide-react'
import { Link } from 'react-router'
import {
  type Activity,
  type ActivityEntry,
  groupOf,
  isWorking,
  type StopBody,
  useActivity,
  useStopWork,
} from '../../api/activity'
import {
  Badge,
  Button,
  Card,
  cx,
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
  useToast,
} from '../../design-system'
import { useT } from '../../i18n'
import { StatusBadge, useFromHere } from '../decisions/parts'

type Step = ActivityEntry['steps'][number]

const DECISION_STATUSES = new Set([
  'moved',
  'moving',
  'proposed',
  'held',
  'failed',
  'in_place',
  'superseded',
  'dismissed',
])

/** The work in progress: how far the current run is, the job running now step by step, what waits
 * (each group stoppable, but moves and emails), the last ones. */
export function ActivityPage() {
  const t = useT()
  const query = useActivity()
  if (query.isPending) return <Spinner label={t('common.loading')} />
  if (query.isError || !query.data)
    return (
      <ErrorState title={t('common.error')} onRetry={() => query.refetch()} retryLabel={t('common.retry')} />
    )
  const activity = query.data
  return (
    <>
      <PageHeader title={t('activity.title')} description={t('activity.subtitle')} />
      <div className="flex flex-col gap-4">
        <RunCard activity={activity} />
        {activity.running && (
          <Card className="border-info/40">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="flex items-center gap-2 font-semibold">
                <Loader2 className="size-4 animate-spin text-info" aria-hidden /> {t('activity.now')}
              </h2>
              {activity.running.stoppable && (
                <StopButton
                  body={{
                    kind: groupOf(activity.running.kind) as StopBody['kind'],
                    scan_id: activity.running.scan_id,
                  }}
                />
              )}
            </div>
            <EntryView entry={activity.running} expanded />
          </Card>
        )}
        {activity.queue.length > 0 && (
          <section>
            <h2 className="mb-2 font-semibold">{t('activity.queued')}</h2>
            <ul className="divide-y divide-border rounded-card border border-border bg-surface">
              {activity.queue.map((group) => (
                <li key={`${group.kind}-${group.scan_id}`} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">
                      {group.kind === 'scan'
                        ? t('activity.queue.scan', { folder: group.folder ?? '—' })
                        : t(`activity.queue.${group.kind}`)}
                    </p>
                    <p className="text-xs text-muted">
                      {t('activity.queue.count', { count: group.count })}
                      {group.stoppable ? null : ` · ${t('activity.queue.always')}`}
                    </p>
                  </div>
                  {group.stoppable && (
                    <StopButton body={{ kind: group.kind as StopBody['kind'], scan_id: group.scan_id }} />
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}
        <section>
          <h2 className="mb-2 font-semibold">{t('activity.recent')}</h2>
          {activity.recent.length === 0 ? (
            <EmptyState title={t('activity.emptyTitle')} description={t('activity.emptyText')} />
          ) : (
            <ul className="flex flex-col gap-2">
              {activity.recent.slice(0, 25).map((entry) => (
                <li key={`${entry.id}-${entry.started_at}`}>
                  <Card className="p-3">
                    <EntryView entry={entry} />
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  )
}

export function runProgress(activity?: Activity) {
  const run = activity?.run
  if (!run) return { done: 0, total: 0, percent: 0 }
  const total = run.done + run.pending + (activity?.running ? 1 : 0)
  return { done: run.done, total, percent: total ? Math.round((run.done / total) * 100) : 100 }
}

/** Stops a group of work; the movies stay where they are, to analyse or check again later. */
function StopButton({ body, label }: { body: StopBody; label?: string }) {
  const t = useT()
  const toast = useToast()
  const stop = useStopWork()
  return (
    <Button
      size="sm"
      className="shrink-0 text-danger"
      icon={<Square className="size-3.5 fill-current" aria-hidden />}
      loading={stop.isPending}
      onClick={() =>
        stop.mutate(body, {
          onSuccess: ({ stopped }) => toast(t('activity.stopped', { count: stopped }), 'success'),
          onError: (error) => toast(error.message, 'danger'),
        })
      }
    >
      {label ?? t('activity.stop')}
    </Button>
  )
}

function RunCard({ activity }: { activity: Activity }) {
  const t = useT()
  const run = activity.run
  const working = isWorking(activity)
  const { done, total, percent } = runProgress(activity)
  const stoppable = activity.running?.stoppable || activity.queue.some((group) => group.stoppable)
  if (!run) return <p className="text-sm text-muted">{t('activity.idle')}</p>
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">{working ? t('activity.running') : t('activity.finished')}</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm tabular-nums text-muted">{t('activity.progress', { done, total })}</span>
          {stoppable && <StopButton body={{ kind: 'all' }} label={t('activity.stopAll')} />}
        </div>
      </div>
      <div
        className="mt-2 h-2.5 overflow-hidden rounded-full bg-surface-2"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={t('activity.running')}
      >
        <div
          className={cx('h-full rounded-full transition-all', working ? 'bg-accent' : 'bg-success')}
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-muted">
        {t('activity.counts', { pending: run.pending, failed: run.failed })} ·{' '}
        {t('activity.since', { time: new Date(run.started_at).toLocaleTimeString() })}
      </p>
    </Card>
  )
}

function EntryView({ entry, expanded = false }: { entry: ActivityEntry; expanded?: boolean }) {
  const t = useT()
  const here = useFromHere()
  const ms = entry.finished_at
    ? new Date(entry.finished_at).getTime() - new Date(entry.started_at).getTime()
    : null
  const title = entry.title ?? (entry.radarr_id ? `#${entry.radarr_id}` : '')
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-xs text-muted">{t(`work.${entry.kind}`)}</span>
        {entry.decision_id ? (
          <Link to={`/decisions/${entry.decision_id}`} state={here} className="font-medium hover:underline">
            {title}
          </Link>
        ) : (
          <span className="font-medium">{title}</span>
        )}
        {entry.outcome &&
          (DECISION_STATUSES.has(entry.outcome) ? (
            <StatusBadge status={entry.outcome} />
          ) : (
            <Badge>{t(`activity.outcome.${entry.outcome}`)}</Badge>
          ))}
        {entry.error && (
          <Badge tone="danger">{entry.retry ? t('activity.willRetry') : t('status.failed')}</Badge>
        )}
        {ms != null && <span className="ml-auto text-xs tabular-nums text-muted">{formatMs(ms)}</span>}
      </div>
      {entry.steps.length > 0 &&
        (expanded ? (
          <ol className="flex flex-col gap-1.5">
            {entry.steps.map((step) => (
              <li key={step.name} className="flex items-start gap-2 text-sm">
                <StepIcon step={step} />
                <span className="font-medium">{t(`activity.step.${step.name}`)}</span>
                <StepDetail step={step} />
              </li>
            ))}
          </ol>
        ) : (
          <ol className="flex flex-wrap gap-1.5">
            {entry.steps.map((step) => (
              <li
                key={step.name}
                className={cx(
                  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs',
                  step.state === 'failed' ? 'bg-danger/10 text-danger' : 'bg-surface-2',
                  step.state === 'skipped' && 'text-muted',
                )}
              >
                <StepIcon step={step} small />
                {t(`activity.step.${step.name}`)}
                <StepDetail step={step} />
              </li>
            ))}
          </ol>
        ))}
      {entry.error && <p className="text-xs text-danger">{entry.error}</p>}
    </div>
  )
}

function StepDetail({ step }: { step: Step }) {
  const t = useT()
  const detail =
    step.state === 'skipped' && step.detail ? t(`activity.skip.${step.detail}`) : (step.detail ?? null)
  return (
    <>
      {detail && <span className="text-muted">· {detail}</span>}
      {step.ms != null && step.ms >= 200 && (
        <span className="text-muted tabular-nums">· {formatMs(step.ms)}</span>
      )}
    </>
  )
}

function StepIcon({ step, small = false }: { step: Step; small?: boolean }) {
  const size = small ? 'size-3' : 'mt-0.5 size-4 shrink-0'
  if (step.state === 'running') return <Loader2 className={cx(size, 'animate-spin text-info')} aria-hidden />
  if (step.state === 'done') return <CheckCircle2 className={cx(size, 'text-success')} aria-hidden />
  if (step.state === 'failed') return <XCircle className={cx(size, 'text-danger')} aria-hidden />
  if (step.state === 'skipped') return <MinusCircle className={cx(size, 'text-muted')} aria-hidden />
  return <CircleDashed className={size} aria-hidden />
}

const formatMs = (ms: number) => (ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`)
