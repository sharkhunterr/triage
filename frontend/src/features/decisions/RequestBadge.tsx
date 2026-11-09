import { Link2 } from 'lucide-react'
import { Badge } from '../../design-system'
import { useT } from '../../i18n'

type RequestCheck = { tracked?: unknown; status?: unknown } | null | undefined

/** Whether the request portal still follows the movie after a move (FR-022g). */
export function RequestBadge({ check }: { check: RequestCheck }) {
  const t = useT()
  if (!check) return null
  if (!check.tracked) return <Badge>{t('request.none')}</Badge>
  return (
    <Badge tone="success">
      <Link2 className="size-3" aria-hidden />
      {t('request.tracked')}
    </Badge>
  )
}
