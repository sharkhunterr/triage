import { Search } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { useCategories } from '../../api/categories'
import { type DecisionFilters, useDecisionPages } from '../../api/decisions'
import { Button, EmptyState, ErrorState, Input, PageHeader, Select, Spinner } from '../../design-system'
import { useT } from '../../i18n'
import { DecisionCard } from './parts'

const STATUSES = [
  'moved',
  'proposed',
  'held',
  'moving',
  'failed',
  'corrected',
  'dismissed',
  'left_in_intake',
  'in_place',
]

export function HistoryPage() {
  const t = useT()
  const [params, setParams] = useSearchParams()
  const categories = useCategories()
  const [query, setQuery] = useState(params.get('q') ?? '')
  const filters: DecisionFilters = {
    status: params.getAll('status'),
    source: params.get('source') ?? undefined,
    category: params.get('category') ? Number(params.get('category')) : undefined,
    q: params.get('q') ?? undefined,
  }
  const pages = useDecisionPages(filters)
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }
  const items = pages.data?.pages.flatMap((p) => p.items) ?? []

  return (
    <>
      <PageHeader title={t('history.title')} description={t('history.subtitle')} />
      <form
        aria-label={t('history.search')}
        className="mb-4 grid gap-2 sm:grid-cols-4"
        onSubmit={(e) => {
          e.preventDefault()
          update('q', query.trim())
        }}
      >
        <div className="relative sm:col-span-2">
          <Search className="pointer-events-none absolute top-3.5 left-3 size-4 text-muted" aria-hidden />
          <Input
            aria-label={t('history.search')}
            placeholder={t('history.search')}
            className="pl-9"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onBlur={() => update('q', query.trim())}
          />
        </div>
        <Select
          aria-label={t('history.status')}
          value={filters.status?.[0] ?? ''}
          onChange={(e) => update('status', e.target.value)}
        >
          <option value="">{t('history.allStatuses')}</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(`status.${s}`)}
            </option>
          ))}
        </Select>
        <Select
          aria-label={t('decision.category')}
          value={params.get('category') ?? ''}
          onChange={(e) => update('category', e.target.value)}
        >
          <option value="">{t('history.allCategories')}</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </form>

      {pages.isPending && <Spinner label={t('common.loading')} />}
      {pages.isError && (
        <ErrorState
          title={t('common.error')}
          onRetry={() => pages.refetch()}
          retryLabel={t('common.retry')}
        />
      )}
      {pages.isSuccess && items.length === 0 && (
        <EmptyState title={t('history.emptyTitle')} description={t('history.emptyText')} />
      )}
      <ul className="grid gap-3 md:grid-cols-2">
        {items.map((decision) => (
          <li key={decision.id}>
            <DecisionCard decision={decision} />
          </li>
        ))}
      </ul>
      {pages.hasNextPage && (
        <div className="mt-4 flex justify-center">
          <Button loading={pages.isFetchingNextPage} onClick={() => pages.fetchNextPage()}>
            {t('history.more')}
          </Button>
        </div>
      )}
    </>
  )
}
