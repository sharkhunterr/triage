import { EmptyState, PageHeader } from '../../design-system'
import { useT } from '../../i18n'

export function StatusPage() {
  const t = useT()
  return (
    <>
      <PageHeader title={t('status.title')} />
      <EmptyState title={t('common.soon')} description={t('common.soonDescription')} />
    </>
  )
}
