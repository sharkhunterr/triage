import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderSearch, Lock, LockOpen, Square } from 'lucide-react'
import { Tabs } from 'radix-ui'
import { type FormEvent, type ReactNode, useState } from 'react'
import { useIntl } from 'react-intl'
import { useSearchParams } from 'react-router'
import { useRootFolders } from '../../api/categories'
import { api, type Schemas } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  PageHeader,
  Select,
  Spinner,
  Switch,
  useToast,
} from '../../design-system'
import { useT } from '../../i18n'
import { DecisionCard } from '../decisions/parts'
import { ApplyConfident, Pager, PER_PAGE, ReviewCard } from '../review/ReviewPage'

type Scan = Schemas['ScanOut']
type ScanPageData = Schemas['ScanPage']
type Tab = 'gaps' | 'held' | 'in_place'

const PER_KEY = 'triage.check.perPage'

function storedPerPage(): number {
  try {
    const value = Number(localStorage.getItem(PER_KEY))
    return (PER_PAGE as readonly number[]).includes(value) ? value : 24
  } catch {
    return 24
  }
}

function useScans() {
  return useQuery({
    queryKey: ['scans'],
    queryFn: () => api<Scan[]>('/scans'),
    refetchInterval: (query) => (query.state.data?.some((s) => s.state === 'running') ? 2_000 : false),
  })
}

/** One page of a check's tab; refreshed as the check goes. */
const useScanPage = (scan: Scan | undefined, tab: Tab, page: number, perPage: number) =>
  useQuery({
    // the check's progress is in the key: each movie checked brings its result in
    queryKey: ['scan-page', scan?.id, scan?.done, scan?.state, tab, page, perPage],
    queryFn: () => api<ScanPageData>(`/scans/${scan?.id}/page?tab=${tab}&page=${page}&per_page=${perPage}`),
    enabled: scan !== undefined,
    placeholderData: keepPreviousData,
    refetchInterval: 15_000,
  })

/** Start a check of any Radarr root folder — never automatic, only when the owner asks. */
function StartCheck({ running }: { running?: Scan }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [, setParams] = useSearchParams()
  const folders = useRootFolders()
  const [folder, setFolder] = useState('')
  const [respectLocks, setRespectLocks] = useState(true)
  const start = useMutation({
    mutationFn: (root_folder_path: string) =>
      api<Scan>('/scans', { method: 'POST', body: { root_folder_path, respect_locks: respectLocks } }),
    onSuccess: (scan) => {
      setParams({ scan: String(scan.id) })
      return queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
    onError: (error) => toast(error.message, 'danger'),
  })
  const cancel = useMutation({
    mutationFn: (id: number) => api<Scan>(`/scans/${id}/cancel`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries(),
  })
  const library = folders.data?.find((f) => !f.is_intake)?.path ?? folders.data?.[0]?.path ?? ''
  const submit = (event: FormEvent) => {
    event.preventDefault()
    start.mutate(folder || library)
  }
  return (
    <Card className="mb-4">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Field label={t('scans.folder')} hint={t('scans.folderHint')}>
              {(id, desc) => (
                <Select
                  id={id}
                  aria-describedby={desc}
                  value={folder || library}
                  onChange={(e) => setFolder(e.target.value)}
                >
                  {folders.data?.map((f) => (
                    <option key={f.path} value={f.path}>
                      {f.path}
                      {f.is_intake ? ` — ${t('scans.intake')}` : ''}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </div>
          {running ? (
            <Button
              icon={<Square className="size-4" aria-hidden />}
              loading={cancel.isPending}
              onClick={() => cancel.mutate(running.id)}
            >
              {t('scans.cancel')}
            </Button>
          ) : (
            <Button
              type="submit"
              variant="primary"
              icon={<FolderSearch className="size-4" aria-hidden />}
              loading={start.isPending}
              disabled={!folders.data?.length}
            >
              {t('scans.start')}
            </Button>
          )}
        </div>
        <Switch
          checked={respectLocks}
          onCheckedChange={setRespectLocks}
          label={t('check.respectLocks')}
          description={t(respectLocks ? 'check.respectLocksHint' : 'check.ignoreLocksHint')}
        />
      </form>
    </Card>
  )
}

/** Check a library for movies that belong in another one, and settle them like the review queue. */
export function ScansPage() {
  const t = useT()
  const intl = useIntl()
  const scans = useScans()
  const [params, setParams] = useSearchParams()
  const asked = Number(params.get('scan')) || undefined
  const tab = (['gaps', 'held', 'in_place'] as const).find((x) => x === params.get('tab')) ?? 'gaps'
  const page = Math.max(1, Number(params.get('page')) || 1)
  const [perPage, setPerPage] = useState(storedPerPage)
  const scan = scans.data?.find((s) => s.id === asked) ?? scans.data?.[0]
  const running = scans.data?.find((s) => s.state === 'running')
  // the other checks' gaps and doubts: the Check tab's badge counts them too
  const elsewhere = scans.data?.filter((s) => s.id !== scan?.id && s.waiting > 0) ?? []
  const results = useScanPage(scan, tab, page, perPage)
  const current = results.data

  const go = (next: { scan?: number; tab?: Tab; page?: number }) => {
    setParams(
      (p) => {
        if (next.scan) p.set('scan', String(next.scan))
        if (next.tab || next.scan) p.set('tab', next.tab ?? 'gaps')
        if (next.page && next.page > 1) p.set('page', String(next.page))
        else p.delete('page')
        return p
      },
      { replace: !next.page },
    )
    if (next.page) window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const changePerPage = (value: number) => {
    setPerPage(value)
    try {
      localStorage.setItem(PER_KEY, String(value))
    } catch {
      // a private window: the choice lasts this visit
    }
    go({})
  }

  const header = (
    <PageHeader
      title={t('check.title')}
      description={t('check.subtitle')}
      actions={current && scan ? <ApplyConfident count={current.confident} scanId={scan.id} /> : null}
    />
  )
  if (scans.isPending) return <Spinner label={t('common.loading')} />
  if (scans.isError)
    return (
      <ErrorState title={t('common.error')} onRetry={() => scans.refetch()} retryLabel={t('common.retry')} />
    )
  if (!scan)
    return (
      <>
        {header}
        <StartCheck />
        <EmptyState title={t('check.emptyTitle')} description={t('check.emptyText')} />
      </>
    )

  const pages = current ? Math.max(1, Math.ceil(current.total / current.per_page)) : 1
  const tabClass =
    'flex-1 rounded-lg px-2 py-2 text-sm font-medium text-muted data-[state=active]:bg-surface data-[state=active]:text-text data-[state=active]:shadow-sm'
  const list = (items: DecisionSummary[], empty: ReactNode, compact = false) =>
    items.length === 0 ? (
      empty
    ) : (
      <>
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2" aria-busy={results.isFetching || undefined}>
          {items.map((d) => (
            <li key={d.id}>
              {compact ? <DecisionCard decision={d} /> : <ReviewCard decision={d} checked />}
            </li>
          ))}
        </ul>
        {current && current.total > Math.min(...PER_PAGE) ? (
          <Pager
            page={current.page}
            pages={pages}
            perPage={current.per_page}
            total={current.total}
            onPage={(next) => go({ page: next })}
            onPerPage={changePerPage}
          />
        ) : null}
      </>
    )

  return (
    <>
      {header}
      <StartCheck running={running} />
      <Card className="mb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <h2 className="truncate font-semibold">
              <code>{scan.root_folder_path}</code>
            </h2>
            <p className="text-sm text-muted">
              {t(`scans.state.${scan.state}`)} · {t('scans.progress', { done: scan.done, total: scan.total })}
              {current?.applied ? ` · ${t('check.applied', { count: current.applied })}` : ''}
            </p>
            <p className="mt-0.5 inline-flex items-center gap-1 text-xs text-muted">
              {scan.respect_locks ? (
                <Lock className="size-3" aria-hidden />
              ) : (
                <LockOpen className="size-3" aria-hidden />
              )}
              {t(scan.respect_locks ? 'check.locksRespected' : 'check.locksIgnored')}
            </p>
          </div>
          {(scans.data?.length ?? 0) > 1 && (
            <Select
              aria-label={t('check.pick')}
              className="h-9 w-auto max-w-full"
              value={String(scan.id)}
              onChange={(e) => go({ scan: Number(e.target.value) })}
            >
              {scans.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {t('check.option', {
                    folder: s.root_folder_path,
                    date: intl.formatDate(s.started_at, { dateStyle: 'short', timeStyle: 'short' }),
                  })}
                  {s.waiting ? ` · ${t('check.waiting', { count: s.waiting })}` : ''}
                </option>
              ))}
            </Select>
          )}
        </div>
        {scan.state === 'running' && (
          // drawn with the theme's colors: a native <progress> takes the device's (green on Android, dark)
          <div
            className="mt-3 h-2.5 overflow-hidden rounded-full bg-surface-2"
            role="progressbar"
            aria-valuenow={scan.done}
            aria-valuemin={0}
            aria-valuemax={Math.max(scan.total, 1)}
            aria-label={t('scans.progressLabel')}
          >
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{ width: `${scan.total ? Math.round((scan.done / scan.total) * 100) : 0}%` }}
            />
          </div>
        )}
        {elsewhere.length > 0 && (
          <div className="mt-3 border-t border-border pt-3 text-sm">
            <p className="text-muted">{t('check.elsewhere')}</p>
            <ul className="mt-1.5 flex flex-wrap gap-2">
              {elsewhere.map((s) => (
                <li key={s.id}>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="border border-border"
                    onClick={() => go({ scan: s.id })}
                  >
                    <code>{s.root_folder_path}</code>
                    <span className="rounded-full bg-accent px-1.5 text-[10px] font-semibold text-accent-contrast">
                      {s.waiting}
                    </span>
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {!current ? (
        results.isError ? (
          <ErrorState
            title={t('common.error')}
            onRetry={() => results.refetch()}
            retryLabel={t('common.retry')}
          />
        ) : (
          <Spinner label={t('common.loading')} />
        )
      ) : (
        <Tabs.Root value={tab} onValueChange={(value) => go({ tab: value as Tab })}>
          <Tabs.List aria-label={t('check.title')} className="mb-4 flex gap-1 rounded-xl bg-surface-2 p-1">
            <Tabs.Trigger value="gaps" className={tabClass}>
              {t('check.gaps', { count: current.gaps })}
            </Tabs.Trigger>
            <Tabs.Trigger value="held" className={tabClass}>
              {t('check.held', { count: current.held })}
            </Tabs.Trigger>
            <Tabs.Trigger value="in_place" className={tabClass}>
              {t('check.inPlace', { count: current.in_place })}
            </Tabs.Trigger>
          </Tabs.List>
          <Tabs.Content value="gaps">
            {tab === 'gaps'
              ? list(
                  current.items,
                  <EmptyState title={t('check.emptyGaps')} description={t('check.emptyGapsText')} />,
                )
              : null}
          </Tabs.Content>
          <Tabs.Content value="held">
            {tab === 'held'
              ? list(
                  current.items,
                  <EmptyState title={t('check.emptyHeld')} description={t('check.emptyHeldText')} />,
                )
              : null}
          </Tabs.Content>
          <Tabs.Content value="in_place">
            {tab === 'in_place'
              ? list(
                  current.items,
                  <EmptyState title={t('check.emptyInPlace')} description={t('check.emptyInPlaceText')} />,
                  true,
                )
              : null}
          </Tabs.Content>
        </Tabs.Root>
      )}
    </>
  )
}
