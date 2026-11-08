import { EmptyState, PageHeader } from '../../design-system'
import { useT } from '../../i18n'

export function CategoriesPage() {
  const t = useT()
  return (
    <>
      <PageHeader title={t('categories.title')} />
      <EmptyState title={t('common.soon')} description={t('common.soonDescription')} />
    </>
  )
}
