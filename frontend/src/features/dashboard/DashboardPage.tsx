import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  CheckCircle2,
  CircleCheck,
  CircleDashed,
  CircleX,
  Clock,
  Library,
  PartyPopper,
  Server,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
} from 'lucide-react'
import { type ReactNode, useState } from 'react'
import { useIntl } from 'react-intl'
import { Link } from 'react-router'
import { api, type Schemas } from '../../api/client'
import { useDashboard } from '../../api/decisions'
import { Card, cx, EmptyState, ErrorState, PageHeader, Spinner } from '../../design-system'
import { useT } from '../../i18n'
import { categoryColor } from '../categories/colors'
import { Poster, StatusBadge, useFromHere } from '../decisions/parts'
import { ApplyConfident } from '../review/ReviewPage'

type Dashboard = Schemas['Dashboard']
type Status = Schemas['StatusOut']

const SERVICE_ICON = {
  ok: <CircleCheck className="size-4 text-success" aria-hidden />,
  down: <CircleX className="size-4 text-danger" aria-hidden />,
  disabled: <CircleDashed className="size-4 text-muted" aria-hidden />,
} as const

function SetupChecklist({ radarr, categories }: { radarr: boolean; categories: number }) {
  const t = useT()
  if (radarr && categories > 0) return null
  return (
    <Card className="border-accent/40 bg-accent/5">
      <h2 className="font-semibold">{t('dashboard.setupTitle')}</h2>
      <ol className="mt-2 flex flex-col gap-1 text-sm">
        <li>
          {radarr ? '✓ ' : '1. '}
          <Link className="text-accent underline" to="/settings">
            {t('dashboard.setupRadarr')}
          </Link>
        </li>
        <li>
          {categories > 0 ? '✓ ' : '2. '}
          <Link className="text-accent underline" to="/categories">
            {t('dashboard.setupCategories')}
          </Link>
        </li>
        <li>
          3.{' '}
          <Link className="text-accent underline" to="/scans">
            {t('dashboard.setupScan')}
          </Link>
        </li>
      </ol>
      <Link className="mt-3 inline-block text-sm font-medium text-accent underline" to="/setup">
        {t('wizard.reopen')}
      </Link>
    </Card>
  )
}

/** What waits for the owner, first: the movies to decide and the proposals to apply in one go. */
function Waiting({ data }: { data: Dashboard }) {
  const t = useT()
  const { held, proposed } = data.counts
  const total = held + proposed
  if (total === 0)
    return (
      <Card className="flex items-center gap-4 border-success/30 bg-success/5">
        <div className="rounded-full bg-success/15 p-3">
          <PartyPopper className="size-6 text-success" aria-hidden />
        </div>
        <div>
          <p className="text-lg font-semibold">{t('dashboard.allSorted')}</p>
          <p className="text-sm text-muted">{t('dashboard.allSortedText')}</p>
        </div>
      </Card>
    )
  return (
    <section
      aria-labelledby="waiting"
      className="relative overflow-hidden rounded-card bg-linear-to-br from-accent to-[color-mix(in_oklab,var(--accent)_55%,var(--cat-5))] p-5 text-accent-contrast shadow-sm"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -top-16 -right-16 size-56 rounded-full bg-white/10 blur-2xl"
      />
      <p className="text-sm font-medium opacity-90">{t('dashboard.toReview')}</p>
      <h2 id="waiting" className="mt-1 text-3xl font-bold tabular-nums sm:text-4xl">
        {t('dashboard.waiting', { count: total })}
      </h2>
      <p className="mt-1 text-sm opacity-90">{t('dashboard.waitingSplit', { held, proposed })}</p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Link
          to={held ? '/review?tab=held' : '/review?tab=proposed'}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-surface px-4 text-sm font-semibold text-text shadow-sm hover:bg-surface-2 focus-visible:outline-2"
        >
          {t('dashboard.decide')} <ArrowRight className="size-4" aria-hidden />
        </Link>
        <div className="[&_button]:bg-white/15 [&_button]:text-accent-contrast [&_button:hover]:bg-white/25">
          <ApplyConfident count={data.confident} />
        </div>
      </div>
    </section>
  )
}

function Kpi({
  label,
  value,
  icon,
  to,
  hint,
  tone,
}: {
  label: string
  value: number
  icon: ReactNode
  to: string
  hint?: ReactNode
  tone?: 'danger'
}) {
  return (
    <Link to={to} className="rounded-card focus-visible:outline-2">
      <Card
        className={cx(
          'flex h-full flex-col gap-2 transition-colors hover:bg-surface-2',
          tone === 'danger' && value > 0 && 'border-danger/40 bg-danger/5',
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-medium text-muted">{label}</p>
          {icon}
        </div>
        <p className="text-3xl font-semibold tabular-nums">{value}</p>
        {hint ? <p className="text-xs text-muted">{hint}</p> : null}
      </Card>
    </Link>
  )
}

/** The week against the one before: up, down or steady. */
function Trend({ now, before }: { now: number; before: number }) {
  const t = useT()
  if (!before) return now ? <span>{t('dashboard.trendNew')}</span> : <span>{t('dashboard.trendNone')}</span>
  const change = Math.round(((now - before) / before) * 100)
  const up = change >= 0
  return (
    <span className={cx('inline-flex items-center gap-1 font-medium', up ? 'text-success' : 'text-warning')}>
      {up ? (
        <TrendingUp className="size-3.5" aria-hidden />
      ) : (
        <TrendingDown className="size-3.5" aria-hidden />
      )}
      {t('dashboard.trend', { change: `${up ? '+' : ''}${change}` })}
    </span>
  )
}

type View = 'sorted' | 'categories' | 'analyzed'
const VIEWS: View[] = ['sorted', 'categories', 'analyzed']
const VIEW_KEY = 'triage.dashboard.month'

type Day = Dashboard['days'][number]
type Series = { key: string; label: string; color: string; value: (day: Day) => number }

function savedView(): View {
  try {
    const saved = localStorage.getItem(VIEW_KEY)
    return VIEWS.includes(saved as View) ? (saved as View) : 'sorted'
  } catch {
    return 'sorted'
  }
}

/** The stacks a view draws, bottom first, and its line of summary. */
function useSeries(view: View, data: Dashboard): { series: Series[]; summary: string } {
  const t = useT()
  const { days } = data
  const sum = (value: (day: Day) => number) => days.reduce((total, day) => total + value(day), 0)
  if (view === 'analyzed') {
    const total = sum((day) => day.analyzed ?? 0)
    const unsure = sum((day) => day.unsure ?? 0)
    return {
      series: [
        {
          key: 'sure',
          label: t('dashboard.sure'),
          color: 'var(--success)',
          value: (day) => (day.analyzed ?? 0) - (day.unsure ?? 0),
        },
        {
          key: 'unsure',
          label: t('dashboard.unsure'),
          color: 'var(--warning)',
          value: (day) => day.unsure ?? 0,
        },
      ],
      summary: t('dashboard.analyzedSummary', {
        total,
        share: total ? Math.round(((total - unsure) / total) * 100) : 0,
      }),
    }
  }
  if (view === 'categories') {
    const series = data.libraries
      .map((lib) => ({
        key: lib.key,
        label: lib.name,
        color: categoryColor(lib.id),
        value: (day: Day) => day.categories?.[lib.key] ?? 0,
      }))
      .filter((s) => sum(s.value) > 0)
    return {
      series,
      summary: t('dashboard.categoriesSummary', { total: sum((day) => day.moved), count: series.length }),
    }
  }
  const total = sum((day) => day.moved)
  const auto = sum((day) => day.auto)
  return {
    series: [
      { key: 'auto', label: t('dashboard.byTriage'), color: 'var(--accent)', value: (day) => day.auto },
      {
        key: 'owner',
        label: t('dashboard.byYou'),
        color: 'color-mix(in srgb, var(--accent) 35%, transparent)',
        value: (day) => day.moved - day.auto,
      },
    ],
    summary: t('dashboard.monthSummary', { total, share: total ? Math.round((auto / total) * 100) : 0 }),
  }
}

/** The last 30 days, a bar a day — what was sorted (by Triage alone or by the owner), into which
 * category, or what was analysed (sure or in doubt): one chart, the view picked above it. */
function Month({ data }: { data: Dashboard }) {
  const t = useT()
  const intl = useIntl()
  const [view, setView] = useState<View>(savedView)
  const pick = (next: View) => {
    setView(next)
    try {
      localStorage.setItem(VIEW_KEY, next)
    } catch {
      // a private window: the view is simply not remembered
    }
  }
  const { days } = data
  const { series, summary } = useSeries(view, data)
  const totals = days.map((day) => series.reduce((sum, s) => sum + s.value(day), 0))
  const peak = Math.max(1, ...totals)
  const label = (day: string) =>
    day ? intl.formatDate(`${day}T12:00:00Z`, { day: 'numeric', month: 'short', timeZone: 'UTC' }) : ''
  const tip = (day: Day) =>
    [
      label(day.day),
      ...series.map((s) => t('dashboard.seriesValue', { label: s.label, count: s.value(day) })),
    ].join(' · ')
  return (
    <Card className="flex flex-col gap-4 lg:col-span-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">{t('dashboard.month')}</h2>
        <p className="text-sm text-muted">{summary}</p>
      </div>
      <fieldset className="flex w-full gap-1 rounded-lg bg-surface-2 p-1 sm:w-auto sm:self-start">
        <legend className="sr-only">{t('dashboard.view')}</legend>
        {VIEWS.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={view === value}
            onClick={() => pick(value)}
            className={cx(
              'h-9 flex-1 rounded-md px-3 text-sm font-medium transition-colors sm:flex-none',
              view === value ? 'bg-surface text-text shadow-sm' : 'text-muted hover:text-text',
            )}
          >
            {t(`dashboard.view.${value}`)}
          </button>
        ))}
      </fieldset>
      {totals.every((total) => total === 0) ? (
        <p className="py-8 text-center text-sm text-muted">
          {t(view === 'analyzed' ? 'dashboard.analyzedEmpty' : 'dashboard.monthEmpty')}
        </p>
      ) : (
        <>
          <ol className="flex h-36 items-end gap-[3px]" aria-label={t('dashboard.month')}>
            {days.map((day, index) => (
              <li
                key={day.day}
                className="group relative flex h-full flex-1 flex-col justify-end"
                title={tip(day)}
              >
                <span className="sr-only">{tip(day)}</span>
                {totals[index] ? (
                  <span
                    aria-hidden
                    className="flex w-full flex-col-reverse overflow-hidden rounded-t-[3px] transition group-hover:brightness-110"
                    style={{ height: `${((totals[index] ?? 0) / peak) * 100}%` }}
                  >
                    {series.map((s) => (
                      <span key={s.key} style={{ flexGrow: s.value(day), background: s.color }} />
                    ))}
                  </span>
                ) : (
                  <span aria-hidden className="h-[2px] w-full rounded-full bg-border" />
                )}
              </li>
            ))}
          </ol>
          <div className="-mt-2 flex justify-between text-xs text-muted" aria-hidden>
            <span>{label(days[0]?.day ?? '')}</span>
            <span>{label(days[days.length - 1]?.day ?? '')}</span>
          </div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
            {series.map((s) => (
              <li key={s.key} className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-sm" style={{ background: s.color }} aria-hidden /> {s.label}
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  )
}

/** Each library and how many movies were sorted into it, in its category's colour. */
function Libraries({ libraries }: { libraries: Dashboard['libraries'] }) {
  const t = useT()
  const total = libraries.reduce((sum, lib) => sum + lib.count, 0)
  return (
    <Card className="flex flex-col gap-3">
      <h2 className="flex items-center gap-2 font-semibold">
        <Library className="size-4 text-muted" aria-hidden /> {t('dashboard.libraries')}
      </h2>
      {libraries.length === 0 ? (
        <p className="text-sm text-muted">{t('dashboard.librariesEmpty')}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {libraries.map((lib) => {
            const share = total ? lib.count / total : 0
            return (
              <li key={lib.id}>
                <Link
                  to={`/history?category=${lib.id}&status=moved`}
                  className="group block focus-visible:outline-2"
                >
                  <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
                    <span className="truncate font-medium group-hover:underline">{lib.name}</span>
                    <span className="tabular-nums text-muted">
                      {lib.count} · {Math.round(share * 100)} %
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.max(share * 100, lib.count ? 2 : 0)}%`,
                        background: categoryColor(lib.id),
                      }}
                    />
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

/** The connected services at a glance; the details on the status page. */
function Services() {
  const t = useT()
  const status = useQuery({
    queryKey: ['status'],
    queryFn: () => api<Status>('/status'),
    refetchInterval: 30_000,
  })
  const services = Object.entries(status.data?.services ?? {})
  const down = services.filter(([, s]) => s.state === 'down').length
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold">
          <Server className="size-4 text-muted" aria-hidden /> {t('dashboard.services')}
        </h2>
        <Link to="/status" className="text-xs font-medium text-accent hover:underline">
          {t('dashboard.details')}
        </Link>
      </div>
      {status.isPending ? (
        <Spinner label={t('common.loading')} />
      ) : (
        <>
          <p className={cx('text-sm', down ? 'font-medium text-danger' : 'text-muted')}>
            {down ? t('dashboard.servicesDown', { count: down }) : t('dashboard.servicesOk')}
          </p>
          <ul className="grid grid-cols-1 gap-1.5 text-sm">
            {services.map(([name, service]) => (
              <li key={name} className="flex items-center gap-2">
                {SERVICE_ICON[service.state as keyof typeof SERVICE_ICON] ?? SERVICE_ICON.disabled}
                <span className={cx(service.state === 'disabled' && 'text-muted')}>
                  {t(`service.${name}`)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  )
}

/** The last decisions, a line each: the poster, the movie, where it goes and where it stands. */
function Latest({ latest }: { latest: Dashboard['latest'] }) {
  const t = useT()
  const here = useFromHere()
  return (
    <Card className="flex flex-col gap-2 lg:col-span-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">{t('dashboard.latest')}</h2>
        <Link to="/history" className="text-xs font-medium text-accent hover:underline">
          {t('dashboard.seeHistory')}
        </Link>
      </div>
      {latest.length === 0 ? (
        <EmptyState title={t('dashboard.emptyTitle')} description={t('dashboard.emptyDescription')} />
      ) : (
        <ul className="-mx-2 flex flex-col">
          {latest.slice(0, 6).map((decision) => {
            const category = decision.target_category ?? decision.top_category
            return (
              <li key={decision.id}>
                <Link
                  to={`/decisions/${decision.id}`}
                  state={here}
                  className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-surface-2 focus-visible:outline-2"
                >
                  <Poster url={decision.movie.poster_url} title={decision.movie.title} size="sm" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">
                      {decision.movie.title}
                      {decision.movie.year ? (
                        <span className="text-muted"> ({decision.movie.year})</span>
                      ) : null}
                    </p>
                    {category ? (
                      <p className="flex items-center gap-1.5 truncate text-xs text-muted">
                        <span
                          aria-hidden
                          className="size-2 shrink-0 rounded-full"
                          style={{ background: categoryColor(category.id) }}
                        />
                        {category.name}
                      </p>
                    ) : null}
                  </div>
                  <StatusBadge status={decision.status} />
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

export function DashboardPage() {
  const t = useT()
  const dashboard = useDashboard()
  if (dashboard.isPending) return <Spinner label={t('common.loading')} />
  if (dashboard.isError)
    return (
      <ErrorState
        title={t('common.error')}
        onRetry={() => dashboard.refetch()}
        retryLabel={t('common.retry')}
      />
    )
  const data = dashboard.data
  const { counts, mode } = data
  const automatic = mode === 'automatic'

  return (
    <>
      <PageHeader
        title={t('dashboard.title')}
        description={t('dashboard.subtitle')}
        actions={
          <Link
            to="/settings"
            className={cx(
              'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium',
              automatic
                ? 'border-success/40 bg-success/10 text-success'
                : 'border-accent/40 bg-accent/10 text-accent',
            )}
          >
            <span className={cx('size-2 rounded-full', automatic ? 'bg-success' : 'bg-accent')} aria-hidden />
            {t(`mode.${mode}`)}
          </Link>
        }
      />
      <div className="flex flex-col gap-4">
        <SetupChecklist radarr={data.radarr_configured} categories={data.categories} />
        <Waiting data={data} />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Kpi
            label={t('dashboard.thisWeek')}
            value={counts.moved_last_7_days}
            icon={<CheckCircle2 className="size-4 text-success" aria-hidden />}
            to="/history?status=moved"
            hint={<Trend now={counts.moved_last_7_days} before={data.previous_week} />}
          />
          <Kpi
            label={t('dashboard.moved')}
            value={counts.moved}
            icon={<Library className="size-4 text-accent" aria-hidden />}
            to="/history?status=moved"
            hint={t('dashboard.sinceStart')}
          />
          <Kpi
            label={t('dashboard.inProgress')}
            value={counts.moving}
            icon={<Clock className="size-4 text-info" aria-hidden />}
            to="/activity"
            hint={t('dashboard.inProgressHint')}
          />
          <Kpi
            label={t('dashboard.failed')}
            value={counts.failed}
            icon={<TriangleAlert className="size-4 text-danger" aria-hidden />}
            to="/history?status=failed"
            tone="danger"
            hint={counts.failed ? t('dashboard.failedHint') : t('dashboard.failedNone')}
          />
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Month data={data} />
          <Libraries libraries={data.libraries} />
          <Latest latest={data.latest} />
          <Services />
        </div>
      </div>
    </>
  )
}
