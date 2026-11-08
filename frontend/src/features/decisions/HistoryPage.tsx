import { EmptyState, PageHeader } from '../../design-system'
import { useT } from '../../i18n'

export function HistoryPage() {
  const t = useT()
  return (
    <>
      <PageHeader title={t('history.title')} />
      <EmptyState title={t('common.soon')} description={t('common.soonDescription')} />
    </>
  )
}
