import { EmptyState, PageHeader } from '../../design-system'
import { useT } from '../../i18n'

export function DecisionPage() {
  const t = useT()
  return (
    <>
      <PageHeader title={t('decision.title')} />
      <EmptyState title={t('common.soon')} description={t('common.soonDescription')} />
    </>
  )
}
