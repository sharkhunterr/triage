import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleCheck, CircleDashed, CircleX, RefreshCw, RotateCcw, TriangleAlert } from 'lucide-react'
import { api, type Schemas } from '../../api/client'
import { Badge, Button, Card, ErrorState, PageHeader, Spinner, useToast } from '../../design-system'
import { useT } from '../../i18n'

type Status = Schemas['StatusOut']

const ICON = {
  ok: <CircleCheck className="size-5 text-success" aria-hidden />,
  down: <CircleX className="size-5 text-danger" aria-hidden />,
  disabled: <CircleDashed className="size-5 text-muted" aria-hidden />,
} as const

const when = (value?: string | null) => (value ? new Date(value).toLocaleString() : '—')

export function StatusPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const status = useQuery({
    queryKey: ['status'],
    queryFn: () => api<Status>('/status'),
    refetchInterval: 30_000,
  })
  const poll = useMutation({
    mutationFn: () => api('/poll', { method: 'POST' }),
    onSuccess: () => {
      toast(t('status.polling'), 'success')
      setTimeout(() => queryClient.invalidateQueries(), 2_000)
    },
  })
  const retry = useMutation({
    mutationFn: (id: number) => api(`/work-items/${id}/retry`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries(),
  })
  if (status.isPending) return <Spinner label={t('common.loading')} />
  if (status.isError)
    return (
      <ErrorState title={t('common.error')} onRetry={() => status.refetch()} retryLabel={t('common.retry')} />
    )
  const data = status.data

  return (
    <>
      <PageHeader
        title={t('status.title')}
        description={t('status.subtitle')}
        actions={
          <Button
            icon={<RefreshCw className="size-4" aria-hidden />}
            loading={poll.isPending}
            onClick={() => poll.mutate()}
          >
            {t('status.checkNow')}
          </Button>
        }
      />
      <div className="flex flex-col gap-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(data.services).map(([name, service]) => (
            <Card key={name} className="flex items-start gap-3">
              {ICON[service.state as keyof typeof ICON] ?? ICON.disabled}
              <div className="min-w-0">
                <p className="font-medium">{t(`service.${name}`)}</p>
                <p className="text-sm text-muted">
                  {service.state === 'disabled'
                    ? t('status.disabled')
                    : service.detail || t(`status.${service.state}`)}
                </p>
              </div>
            </Card>
          ))}
        </div>

        <Card>
          <h2 className="mb-2 font-semibold">{t('status.worker')}</h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted">{t('status.mode')}</dt>
            <dd>
              <Badge tone={data.mode === 'automatic' ? 'success' : 'accent'}>{t(`mode.${data.mode}`)}</Badge>
            </dd>
            <dt className="text-muted">{t('status.lastPoll')}</dt>
            <dd>{when(data.last_poll_at)}</dd>
            <dt className="text-muted">{t('status.nextPoll')}</dt>
            <dd>{when(data.next_poll_at)}</dd>
            <dt className="text-muted">{t('status.queue')}</dt>
            <dd>
              {t('status.queueCounts', { pending: data.queue.pending ?? 0, failed: data.queue.failed ?? 0 })}
            </dd>
          </dl>
          {data.last_poll_error && (
            <p role="alert" className="mt-2 text-sm text-danger">
              {t('status.pollError', { error: data.last_poll_error })}
            </p>
          )}
        </Card>

        {data.folder_warnings.length > 0 && (
          <Card className="border-warning/40">
            <h2 className="mb-2 flex items-center gap-2 font-semibold">
              <TriangleAlert className="size-4 text-warning" aria-hidden /> {t('status.folderWarnings')}
            </h2>
            <ul className="flex flex-col gap-1 text-sm">
              {data.folder_warnings.map((w) => (
                <li key={w.path}>
                  {t(`status.folder.${w.problem}`, { category: w.category ?? '', path: w.path ?? '' })}
                </li>
              ))}
            </ul>
          </Card>
        )}

        <Card>
          <h2 className="mb-2 font-semibold">{t('status.failedItems')}</h2>
          {data.failed_items.length === 0 ? (
            <p className="text-sm text-muted">{t('status.noFailure')}</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {data.failed_items.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border p-3 text-sm"
                >
                  <div className="min-w-0">
                    <p className="font-medium">{t(`work.${item.kind}`)}</p>
                    <p className="break-words text-muted">{item.last_error}</p>
                  </div>
                  <Button
                    size="sm"
                    icon={<RotateCcw className="size-4" aria-hidden />}
                    loading={retry.isPending}
                    onClick={() => retry.mutate(item.id)}
                  >
                    {t('common.retry')}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
