import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCheck, ChevronLeft, ChevronRight } from 'lucide-react'
import { Tabs } from 'radix-ui'
import { type ReactNode, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'
import type { Schemas } from '../../api/client'
import { api } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import {
  Button,
  Dialog,
  EmptyState,
  ErrorState,
  PageHeader,
  Select,
  Spinner,
  useToast,
} from '../../design-system'
import { useT } from '../../i18n'
import { TimelineRow, usePlaces } from '../decisions/Timeline'
import { ChoiceSlider } from './ChoiceSlider'
import { Reanalyze, ReviewAll } from './ReviewAll'

type ReviewPageData = Schemas['ReviewPage']
type Tab = 'held' | 'proposed'

export const PER_PAGE = [12, 24, 48, 96] as const
const PER_KEY = 'triage.review.perPage'

function storedPerPage(): number {
  try {
    const value = Number(localStorage.getItem(PER_KEY))
    return (PER_PAGE as readonly number[]).includes(value) ? value : 24
  } catch {
    return 24
  }
}

/** One page of a review tab — hundreds of proposals are not loaded at every look. */
const useReviewPage = (tab: Tab, page: number, perPage: number) =>
  useQuery({
    queryKey: ['review', tab, page, perPage],
    queryFn: () => api<ReviewPageData>(`/review/page?tab=${tab}&page=${page}&per_page=${perPage}`),
    placeholderData: keepPreviousData,
    refetchInterval: 15_000,
  })

/** The pages of a tab, and how many movies a page shows. */
export function Pager({
  page,
  pages,
  perPage,
  total,
  onPage,
  onPerPage,
}: {
  page: number
  pages: number
  perPage: number
  total: number
  onPage: (page: number) => void
  onPerPage: (perPage: number) => void
}) {
  const t = useT()
  const first = total ? (page - 1) * perPage + 1 : 0
  const last = Math.min(total, page * perPage)
  return (
    <nav aria-label={t('review.pages')} className="mt-4 flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-muted">{t('review.range', { first, last, total })}</p>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          icon={<ChevronLeft className="size-4" aria-hidden />}
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          {t('review.previous')}
        </Button>
        <span className="px-1 text-sm tabular-nums" aria-live="polite">
          {t('review.pageOf', { page, pages })}
        </span>
        <Button size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          {t('review.next')} <ChevronRight className="size-4" aria-hidden />
        </Button>
        <Select
          aria-label={t('review.perPage')}
          className="h-9 w-auto"
          value={String(perPage)}
          onChange={(e) => onPerPage(Number(e.target.value))}
        >
          {PER_PAGE.map((n) => (
            <option key={n} value={n}>
              {t('review.perPageOption', { count: n })}
            </option>
          ))}
        </Select>
      </div>
    </nav>
  )
}

/** Applies every sure proposal — of the review queue, or of one check when `scanId` is given. */
export function ApplyConfident({ count, scanId }: { count: number; scanId?: number }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const apply = useMutation({
    mutationFn: () =>
      api<{ applied: number }>('/decisions/apply-confident', {
        method: 'POST',
        body: scanId === undefined ? {} : { scan_id: scanId },
      }),
    onSuccess: (result) => {
      toast(t('review.appliedCount', { count: result.applied }), 'success')
      setOpen(false)
      return queryClient.invalidateQueries()
    },
  })
  if (count === 0) return null
  return (
    <>
      <Button
        variant="primary"
        icon={<CheckCheck className="size-4" aria-hidden />}
        onClick={() => setOpen(true)}
      >
        {t('review.applyConfident')}
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={t('review.applyConfidentTitle', { count })}
        description={t('review.applyConfidentText')}
        closeLabel={t('common.close')}
      >
        <div className="flex justify-end gap-2">
          <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="primary" loading={apply.isPending} onClick={() => apply.mutate()}>
            {t('common.confirm')}
          </Button>
        </div>
      </Dialog>
    </>
  )
}

export function ReviewPage() {
  const t = useT()
  const [params, setParams] = useSearchParams()
  const asked = params.get('tab')
  const [tab, setTab] = useState<Tab>(asked === 'proposed' ? 'proposed' : 'held')
  const page = Math.max(1, Number(params.get('page')) || 1)
  const [perPage, setPerPage] = useState(storedPerPage)
  const review = useReviewPage(tab, page, perPage)
  const place = usePlaces()
  const current = review.data
  // nothing held but proposals waiting: open on the proposals (unless a tab was asked)
  useEffect(() => {
    if (!asked && tab === 'held' && current && !current.held && current.proposed) setTab('proposed')
  }, [asked, tab, current])
  const shown = tab

  const go = (next: { tab?: Tab; page?: number }) => {
    const nextTab = next.tab ?? shown
    if (next.tab) setTab(next.tab)
    const nextPage = next.page ?? 1
    setParams(
      (p) => {
        p.set('tab', nextTab)
        if (nextPage > 1) p.set('page', String(nextPage))
        else p.delete('page')
        return p
      },
      { replace: !next.page },
    )
    window.scrollTo({ top: 0, behavior: 'smooth' })
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

  if (!current && review.isPending) return <Spinner label={t('common.loading')} />
  if (!current)
    return (
      <ErrorState title={t('common.error')} onRetry={() => review.refetch()} retryLabel={t('common.retry')} />
    )
  const pages = Math.max(1, Math.ceil(current.total / current.per_page))
  const tabClass =
    'flex-1 rounded-lg px-3 py-2 text-sm font-medium text-muted data-[state=active]:bg-surface data-[state=active]:text-text data-[state=active]:shadow-sm'
  const list = (items: DecisionSummary[], empty: ReactNode) =>
    items.length === 0 ? (
      empty
    ) : (
      <>
        <ul
          className="mx-auto max-w-3xl divide-y divide-border overflow-hidden rounded-card border border-border bg-surface"
          aria-busy={review.isFetching || undefined}
        >
          {items.map((d) => (
            <li key={d.id}>
              <TimelineRow
                decision={d}
                place={place}
                note={d.status === 'held'}
                choose={(meta) => <ChoiceSlider decision={d} aside={meta} />}
              />
            </li>
          ))}
        </ul>
        {current.total > Math.min(...PER_PAGE) ? (
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
      <PageHeader
        title={t('review.title')}
        description={t('review.subtitle')}
        actions={
          <>
            <Reanalyze />
            <ReviewAll count={current.held + current.proposed} />
            <ApplyConfident count={current.confident} />
          </>
        }
      />
      <Tabs.Root value={shown} onValueChange={(value) => go({ tab: value as Tab })}>
        <Tabs.List aria-label={t('review.title')} className="mb-4 flex gap-1 rounded-xl bg-surface-2 p-1">
          <Tabs.Trigger value="held" className={tabClass}>
            {t('review.held', { count: current.held })}
          </Tabs.Trigger>
          <Tabs.Trigger value="proposed" className={tabClass}>
            {t('review.proposals', { count: current.proposed })}
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="held">
          {shown === 'held'
            ? list(
                current.items,
                <EmptyState title={t('review.emptyHeld')} description={t('review.emptyHeldText')} />,
              )
            : null}
        </Tabs.Content>
        <Tabs.Content value="proposed">
          {shown === 'proposed'
            ? list(
                current.items,
                <EmptyState
                  title={t('review.emptyProposals')}
                  description={t('review.emptyProposalsText')}
                />,
              )
            : null}
        </Tabs.Content>
      </Tabs.Root>
    </>
  )
}
