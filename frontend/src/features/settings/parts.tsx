import { CheckCircle2, PlugZap, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  type Check,
  type Service,
  type SettingsPatch,
  type SettingsView,
  useTestService,
} from '../../api/settings'
import { Button, Input } from '../../design-system'
import { useT } from '../../i18n'

export type Values = Record<string, string | number | string[]>

export function useSection(view: SettingsView | undefined, section: keyof SettingsView, fields: string[]) {
  const [values, setValues] = useState<Values>({})
  const fieldList = fields.join(',') // a stable key: the caller passes a new array each render
  useEffect(() => {
    if (!view) return
    const source = view[section] as unknown as Record<string, unknown>
    const next: Values = {}
    for (const field of fieldList.split(',')) {
      const value = source[field]
      // Secrets come back as {set}: their input starts empty and means "keep".
      next[field] =
        value && typeof value === 'object' && 'set' in (value as object) ? '' : (value as Values[string])
    }
    setValues(next)
  }, [view, section, fieldList])
  const set = (field: string, value: Values[string]) => setValues((v) => ({ ...v, [field]: value }))
  /** Only non-empty secrets are sent: an empty secret field means "keep the stored one". */
  const patch = (secrets: string[] = []): SettingsPatch => {
    const body: Record<string, unknown> = {}
    for (const [field, value] of Object.entries(values)) {
      if (secrets.includes(field) && value === '') continue
      body[field] = value
    }
    return { [section]: body }
  }
  return { values, set, patch }
}

export function CheckResult({ check }: { check?: Check }) {
  const t = useT()
  if (!check) return null
  return (
    <p
      role="status"
      className={`flex items-center gap-1 text-sm ${check.ok ? 'text-success' : 'text-danger'}`}
    >
      {check.ok ? (
        <CheckCircle2 className="size-4" aria-hidden />
      ) : (
        <XCircle className="size-4" aria-hidden />
      )}
      {check.detail === 'not_configured' ? t('settings.notConfigured') : check.detail}
      {check.ok && <span className="text-muted"> · {check.latency_ms} ms</span>}
    </p>
  )
}

export function SecretInput({
  id,
  set,
  value,
  onChange,
  describedBy,
}: {
  id: string
  set: boolean
  value: string
  onChange: (v: string) => void
  describedBy?: string
}) {
  const t = useT()
  return (
    <Input
      id={id}
      type="password"
      autoComplete="off"
      aria-describedby={describedBy}
      placeholder={set ? t('settings.secretSet') : t('settings.secretUnset')}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

/** Tries a service with the values typed so far (saved or not), and shows the answer. */
export function TestButton({
  service,
  patch,
  onResult,
}: {
  service: Service
  patch: () => SettingsPatch
  onResult?: (check: Check) => void
}) {
  const t = useT()
  const test = useTestService()
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        icon={<PlugZap className="size-4" aria-hidden />}
        loading={test.isPending}
        onClick={() => test.mutate({ service, patch: patch() }, { onSuccess: onResult })}
      >
        {t('settings.test')}
      </Button>
      <CheckResult check={test.data} />
    </div>
  )
}
