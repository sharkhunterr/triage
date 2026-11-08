import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCheck, FolderSearch, Square } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { useRootFolders } from '../../api/categories'
import { api, type Schemas } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import { Button, Card, EmptyState, Field, PageHeader, Select, useToast } from '../../design-system'
import { useT } from '../../i18n'
import { DecisionCard } from '../decisions/parts'

type Scan = Schemas['ScanOut']

function useScans() {
  return useQuery({
    queryKey: ['scans'],
    queryFn: () => api<Scan[]>('/scans'),
    refetchInterval: (query) => (query.state.data?.some((s) => s.state === 'running') ? 2_000 : false),
  })
}

function ScanResults({ scan }: { scan: Scan }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const results = useQuery({
    queryKey: ['scan-results', scan.id, scan.done],
    queryFn: () => api<DecisionSummary[]>(`/scans/${scan.id}/results`),
  })
  const applyAll = useMutation({
    mutationFn: () =>
      api<{ applied: number }>('/decisions/apply-confident', { method: 'POST', body: { scan_id: scan.id } }),
    onSuccess: (r) => {
      toast(t('review.appliedCount', { count: r.applied }), 'success')
      return queryClient.invalidateQueries()
    },
  })
  const groups: [string, DecisionSummary[]][] = [
    ['scans.toMove', (results.data ?? []).filter((d) => ['proposed', 'moving', 'moved'].includes(d.status))],
    ['scans.doubtful', (results.data ?? []).filter((d) => d.status === 'held')],
    ['scans.inPlace', (results.data ?? []).filter((d) => d.status === 'in_place')],
  ]
  const proposals = groups[0]?.[1].filter((d) => d.status === 'proposed').length ?? 0
  return (
    <div className="flex flex-col gap-5">
      {proposals > 0 && (
        <div>
          <Button
            variant="primary"
            icon={<CheckCheck className="size-4" aria-hidden />}
            loading={applyAll.isPending}
            onClick={() => applyAll.mutate()}
          >
            {t('scans.applyConfident', { count: proposals })}
          </Button>
        </div>
      )}
      {groups.map(([key, items]) =>
        items.length ? (
          <section key={key}>
            <h3 className="mb-2 font-semibold">
              {t(key)} <span className="text-muted">({items.length})</span>
            </h3>
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {items.map((d) => (
                <li key={d.id}>
                  <DecisionCard decision={d} />
                </li>
              ))}
            </ul>
          </section>
        ) : null,
      )}
    </div>
  )
}

export function ScansPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const folders = useRootFolders()
  const scans = useScans()
  const [folder, setFolder] = useState('')
  const start = useMutation({
    mutationFn: (root_folder_path: string) =>
      api<Scan>('/scans', { method: 'POST', body: { root_folder_path } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scans'] }),
    onError: (error) => toast(error.message, 'danger'),
  })
  const cancel = useMutation({
    mutationFn: (id: number) => api<Scan>(`/scans/${id}/cancel`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scans'] }),
  })
  const latest = scans.data?.[0]
  const running = latest?.state === 'running'
  const defaultFolder = folders.data?.find((f) => f.is_intake)?.path ?? folders.data?.[0]?.path ?? ''
  const submit = (event: FormEvent) => {
    event.preventDefault()
    start.mutate(folder || defaultFolder)
  }

  return (
    <>
      <PageHeader title={t('scans.title')} description={t('scans.subtitle')} />
      <Card className="mb-4">
        <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Field label={t('scans.folder')} hint={t('scans.folderHint')}>
              {(id, desc) => (
                <Select
                  id={id}
                  aria-describedby={desc}
                  value={folder || defaultFolder}
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
          <Button
            type="submit"
            variant="primary"
            icon={<FolderSearch className="size-4" aria-hidden />}
            loading={start.isPending}
            disabled={running || !folders.data?.length}
          >
            {t('scans.start')}
          </Button>
        </form>
      </Card>

      {!latest ? (
        <EmptyState title={t('scans.emptyTitle')} description={t('scans.emptyText')} />
      ) : (
        <Card>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-semibold">
                <code>{latest.root_folder_path}</code>
              </h2>
              <p className="text-sm text-muted">
                {t(`scans.state.${latest.state}`)} ·{' '}
                {t('scans.progress', { done: latest.done, total: latest.total })}
              </p>
            </div>
            {running && (
              <Button
                size="sm"
                icon={<Square className="size-4" aria-hidden />}
                loading={cancel.isPending}
                onClick={() => cancel.mutate(latest.id)}
              >
                {t('scans.cancel')}
              </Button>
            )}
          </div>
          <progress
            className="mb-4 h-2 w-full accent-[var(--accent)]"
            max={Math.max(latest.total, 1)}
            value={latest.done}
            aria-label={t('scans.progressLabel')}
          />
          <ScanResults scan={latest} />
        </Card>
      )}
    </>
  )
}
