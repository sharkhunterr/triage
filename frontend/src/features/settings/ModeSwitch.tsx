import { Eye, Zap } from 'lucide-react'
import { useState } from 'react'
import { useSaveSettings } from '../../api/settings'
import { Button, Card, cx, Dialog, useToast } from '../../design-system'
import { useT } from '../../i18n'

/** Preview ↔ Automatic. Turning automatic on asks for confirmation (Constitution I). */
export function ModeSwitch({ mode }: { mode: 'preview' | 'automatic' }) {
  const t = useT()
  const toast = useToast()
  const save = useSaveSettings()
  const [confirming, setConfirming] = useState(false)
  const set = (next: 'preview' | 'automatic') =>
    save.mutate(
      { sorting: { mode: next } },
      { onSuccess: () => toast(t(`mode.${next}`), 'success'), onSettled: () => setConfirming(false) },
    )
  const option = (value: 'preview' | 'automatic', icon: React.ReactNode) => (
    <button
      type="button"
      aria-pressed={mode === value}
      onClick={() => (value === 'automatic' ? setConfirming(true) : set('preview'))}
      disabled={mode === value}
      className={cx(
        'flex flex-1 flex-col items-start gap-1 rounded-xl border p-3 text-left transition-colors',
        mode === value ? 'border-accent bg-accent/10' : 'border-border hover:bg-surface-2',
      )}
    >
      <span className="flex items-center gap-2 font-medium">
        {icon} {t(`mode.${value}`)}
      </span>
      <span className="text-xs text-muted">{t(`mode.${value}Hint`)}</span>
    </button>
  )
  return (
    <Card>
      <h2 className="mb-1 text-lg font-semibold">{t('mode.title')}</h2>
      <p className="mb-3 text-sm text-muted">{t('mode.subtitle')}</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        {option('preview', <Eye className="size-4" aria-hidden />)}
        {option('automatic', <Zap className="size-4" aria-hidden />)}
      </div>
      <Dialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t('mode.confirmTitle')}
        description={t('mode.confirmText')}
        closeLabel={t('common.close')}
      >
        <div className="flex justify-end gap-2">
          <Button onClick={() => setConfirming(false)}>{t('common.cancel')}</Button>
          <Button variant="primary" loading={save.isPending} onClick={() => set('automatic')}>
            {t('mode.confirm')}
          </Button>
        </div>
      </Dialog>
    </Card>
  )
}
