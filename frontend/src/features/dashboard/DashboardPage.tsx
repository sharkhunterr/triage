import { EmptyState, PageHeader } from '../../design-system'
import { useT } from '../../i18n'

export function DashboardPage() {
  const t = useT()
  return (
    <>
      <PageHeader title={t('dashboard.title')} />
      <EmptyState title={t('common.soon')} description={t('common.soonDescription')} />
    </>
  )
}
