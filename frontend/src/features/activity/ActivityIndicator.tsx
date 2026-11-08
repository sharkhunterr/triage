import { Loader2 } from 'lucide-react'
import { Link } from 'react-router'
import { isWorking, useActivity } from '../../api/activity'
import { cx } from '../../design-system'
import { useT } from '../../i18n'
import { runProgress } from './ActivityPage'

/** Shown on every page while Triage works: how far it is, and a way to watch it. */
export function ActivityIndicator({ floating = false }: { floating?: boolean }) {
  const t = useT()
  const activity = useActivity().data
  if (!isWorking(activity)) return null
  const { done, total, percent } = runProgress(activity)
  return (
    <Link
      to="/activity"
      className={cx(
        'flex flex-col gap-1 rounded-xl border border-info/40 bg-surface px-3 py-2 text-xs shadow-sm hover:bg-surface-2',
        floating &&
          'fixed right-3 bottom-[calc(3.9rem+env(safe-area-inset-bottom))] z-30 w-52 shadow-lg lg:hidden',
      )}
    >
      <span className="flex items-center gap-2 font-medium">
        <Loader2 className="size-3.5 animate-spin text-info" aria-hidden />
        {t('activity.indicator', { done, total })}
      </span>
      <span className="truncate text-muted">{activity?.running?.title ?? t('activity.waiting')}</span>
      <span aria-hidden className="h-1 overflow-hidden rounded-full bg-surface-2">
        <span
          className="block h-full rounded-full bg-accent transition-all"
          style={{ width: `${percent}%` }}
        />
      </span>
    </Link>
  )
}
