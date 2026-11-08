import { EmptyState, PageHeader } from '../../design-system'
import { useT } from '../../i18n'

export function ReviewPage() {
  const t = useT()
  return (
    <>
      <PageHeader title={t('review.title')} />
      <EmptyState title={t('common.soon')} description={t('common.soonDescription')} />
    </>
  )
}
