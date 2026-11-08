import { EmptyState, PageHeader } from '../../design-system'
import { useT } from '../../i18n'

export function SettingsPage() {
  const t = useT()
  return (
    <>
      <PageHeader title={t('settings.title')} />
      <EmptyState title={t('common.soon')} description={t('common.soonDescription')} />
    </>
  )
}
