import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Ban, CheckCheck, FolderInput } from 'lucide-react'
import { Tabs } from 'radix-ui'
import { useState } from 'react'
import { Link } from 'react-router'
import { useCategories } from '../../api/categories'
import { api } from '../../api/client'
import type { DecisionSummary } from '../../api/decisions'
import {
  Button,
  Card,
  Dialog,
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
  useToast,
} from '../../design-system'
import { useT } from '../../i18n'
import { categoryButton } from '../categories/colors'
import { useDecisionAction } from '../decisions/DecisionActions'
import { ConfidenceMeter, Poster, ReasonText, StatusBadge } from '../decisions/parts'
import { Reanalyze, ReviewAll } from './ReviewAll'

const useReview = () =>
  useQuery({
    queryKey: ['review'],
    queryFn: () => api<DecisionSummary[]>('/review'),
    refetchInterval: 15_000,
  })

function ReviewCard({ decision }: { decision: DecisionSummary }) {
  const t = useT()
  const categories = useCategories()
  const action = useDecisionAction()
  const proposal = decision.status === 'proposed'
  const proposed = decision.target_category ?? decision.top_category
  const choices = (categories.data ?? []).filter((c) => c.root_folder_path)

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex gap-3">
        <Poster url={decision.movie.poster_url} title={decision.movie.title} />
        <div className="min-w-0 flex-1">
          <Link to={`/decisions/${decision.id}`} className="font-medium hover:underline">
            {decision.movie.title}
            {decision.movie.year ? <span className="text-muted"> ({decision.movie.year})</span> : null}
          </Link>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <StatusBadge status={decision.status} />
            <ConfidenceMeter value={decision.confidence} />
          </div>
          {proposal && proposed ? (
            <p className="mt-1 text-sm">{t('review.wouldMove', { category: proposed.name })}</p>
          ) : (
            <ul className="mt-1 list-disc pl-4 text-xs text-muted">
              {decision.reasons.map((reason) => (
                <li key={JSON.stringify(reason)}>
                  <ReasonText reason={reason} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {choices.map((category) => (
          <Button
            key={category.id}
            size="sm"
            {...categoryButton(category.id, proposed?.id === category.id)}
            icon={<FolderInput className="size-4" aria-hidden />}
            loading={action.isPending}
            onClick={() =>
              action.mutate({ id: decision.id, action: 'apply', body: { category_id: category.id } })
            }
          >
            {category.name}
          </Button>
        ))}
        <Button
          size="sm"
          variant="ghost"
          icon={<Ban className="size-4" aria-hidden />}
          loading={action.isPending}
          onClick={() =>
            proposal
              ? action.mutate({ id: decision.id, action: 'dismiss' })
              : action.mutate({ id: decision.id, action: 'apply', body: { target: 'intake' } })
          }
        >
          {proposal ? t('decision.dismiss') : t('decision.leave')}
        </Button>
      </div>
    </Card>
  )
}

function ApplyConfident({ count }: { count: number }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const apply = useMutation({
    mutationFn: () => api<{ applied: number }>('/decisions/apply-confident', { method: 'POST', body: {} }),
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
  const review = useReview()
  if (review.isPending) return <Spinner label={t('common.loading')} />
  if (review.isError)
    return (
      <ErrorState title={t('common.error')} onRetry={() => review.refetch()} retryLabel={t('common.retry')} />
    )
  const held = review.data.filter((d) => d.status === 'held')
  const proposals = review.data.filter((d) => d.status === 'proposed')
  const tab =
    'flex-1 rounded-lg px-3 py-2 text-sm font-medium text-muted data-[state=active]:bg-surface data-[state=active]:text-text data-[state=active]:shadow-sm'

  return (
    <>
      <PageHeader
        title={t('review.title')}
        description={t('review.subtitle')}
        actions={
          <>
            <Reanalyze />
            <ReviewAll items={[...proposals, ...held]} />
            <ApplyConfident count={proposals.filter((p) => p.confidence > 0).length} />
          </>
        }
      />
      <Tabs.Root defaultValue={held.length || !proposals.length ? 'held' : 'proposals'}>
        <Tabs.List aria-label={t('review.title')} className="mb-4 flex gap-1 rounded-xl bg-surface-2 p-1">
          <Tabs.Trigger value="held" className={tab}>
            {t('review.held', { count: held.length })}
          </Tabs.Trigger>
          <Tabs.Trigger value="proposals" className={tab}>
            {t('review.proposals', { count: proposals.length })}
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="held">
          {held.length === 0 ? (
            <EmptyState title={t('review.emptyHeld')} description={t('review.emptyHeldText')} />
          ) : (
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {held.map((d) => (
                <li key={d.id}>
                  <ReviewCard decision={d} />
                </li>
              ))}
            </ul>
          )}
        </Tabs.Content>
        <Tabs.Content value="proposals">
          {proposals.length === 0 ? (
            <EmptyState title={t('review.emptyProposals')} description={t('review.emptyProposalsText')} />
          ) : (
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {proposals.map((d) => (
                <li key={d.id}>
                  <ReviewCard decision={d} />
                </li>
              ))}
            </ul>
          )}
        </Tabs.Content>
      </Tabs.Root>
    </>
  )
}
