import { RefreshCw } from 'lucide-react'
import { useRootFolders } from '../../api/categories'
import { Button, useToast } from '../../design-system'
import { useT } from '../../i18n'

/** Reads Radarr's root folders again — after a library was added or renamed there — and says how many it found. */
export function RefreshFolders() {
  const t = useT()
  const toast = useToast()
  const folders = useRootFolders()
  const refresh = async () => {
    const result = await folders.refetch()
    if (result.isError) toast(t('folders.refreshFailed'), 'danger')
    else toast(t('folders.refreshed', { count: result.data?.length ?? 0 }), 'success')
  }
  return (
    <Button
      size="sm"
      loading={folders.isFetching}
      icon={<RefreshCw className="size-4" aria-hidden />}
      onClick={refresh}
    >
      {t('folders.refresh')}
    </Button>
  )
}
