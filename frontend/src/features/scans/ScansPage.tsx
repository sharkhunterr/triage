import { EmptyState, PageHeader } from '../../design-system'
import { useT } from '../../i18n'

export function ScansPage() {
  const t = useT()
  return (
    <>
      <PageHeader title={t('scans.title')} />
      <EmptyState title={t('common.soon')} description={t('common.soonDescription')} />
    </>
  )
}
