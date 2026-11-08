import { CheckCircle2, Clock, Hand, Inbox, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { useDashboard } from '../../api/decisions'
import { Badge, Card, EmptyState, ErrorState, PageHeader, Spinner } from '../../design-system'
import { useT } from '../../i18n'
import { DecisionCard } from '../decisions/parts'

function Stat({ label, value, icon, to }: { label: string; value: number; icon: ReactNode; to: string }) {
  return (
    <Link to={to} className="rounded-card focus-visible:outline-2">
      <Card className="flex items-center gap-3 transition-colors hover:bg-surface-2">
        <div className="rounded-lg bg-surface-2 p-2">{icon}</div>
        <div>
          <p className="text-2xl font-semibold tabular-nums">{value}</p>
          <p className="text-xs text-muted">{label}</p>
        </div>
      </Card>
    </Link>
  )
}

function SetupChecklist({ radarr, categories }: { radarr: boolean; categories: number }) {
  const t = useT()
  if (radarr && categories > 0) return null
  return (
    <Card className="mb-4 border-accent/40 bg-accent/5">
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
  const { counts, latest, mode } = dashboard.data

  return (
    <>
      <PageHeader
        title={t('dashboard.title')}
        description={t('dashboard.subtitle')}
        actions={
          <Link to="/settings">
            <Badge tone={mode === 'automatic' ? 'success' : 'accent'}>{t(`mode.${mode}`)}</Badge>
          </Link>
        }
      />
      <SetupChecklist radarr={dashboard.data.radarr_configured} categories={dashboard.data.categories} />
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat
          label={t('dashboard.moved')}
          value={counts.moved}
          icon={<CheckCircle2 className="size-5 text-success" aria-hidden />}
          to="/history?status=moved"
        />
        <Stat
          label={t('dashboard.toReview')}
          value={counts.held + counts.proposed}
          icon={<Hand className="size-5 text-warning" aria-hidden />}
          to="/review"
        />
        <Stat
          label={t('dashboard.inProgress')}
          value={counts.moving}
          icon={<Clock className="size-5 text-info" aria-hidden />}
          to="/history?status=moving"
        />
        <Stat
          label={t('dashboard.failed')}
          value={counts.failed}
          icon={<TriangleAlert className="size-5 text-danger" aria-hidden />}
          to="/history?status=failed"
        />
      </div>
      <h2 className="mb-3 text-lg font-semibold">{t('dashboard.latest')}</h2>
      {latest.length === 0 ? (
        <EmptyState title={t('dashboard.emptyTitle')} description={t('dashboard.emptyDescription')} />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {latest.map((decision) => (
            <li key={decision.id}>
              <DecisionCard decision={decision} />
            </li>
          ))}
        </ul>
      )}
      {counts.moved_last_7_days > 0 && (
        <p className="mt-4 flex items-center gap-2 text-sm text-muted">
          <Inbox className="size-4" aria-hidden />
          {t('dashboard.week', { count: counts.moved_last_7_days })}
        </p>
      )}
    </>
  )
}
