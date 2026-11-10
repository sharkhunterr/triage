import { CheckCircle2, PlugZap, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  type Check,
  type Service,
  type SettingsPatch,
  type SettingsView,
  useTestService,
} from '../../api/settings'
import { Button, Field, Input, Select } from '../../design-system'
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

const TMDB_LANGUAGES = [
  'fr-FR',
  'fr-CA',
  'fr-BE',
  'en-US',
  'en-GB',
  'de-DE',
  'es-ES',
  'it-IT',
  'pt-BR',
  'nl-NL',
]

/** The TMDB language-country: the synopsis language and the country whose age ratings are kept. */
export function TmdbLanguage({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const t = useT()
  const label = (code: string) => {
    const [lang, country] = code.split('-')
    try {
      const names = (type: 'language' | 'region') =>
        new Intl.DisplayNames([document.documentElement.lang || 'en'], { type })
      return `${names('language').of(lang ?? '')} (${names('region').of(country ?? '')})`
    } catch {
      return code
    }
  }
  const options = TMDB_LANGUAGES.includes(value) ? TMDB_LANGUAGES : [value, ...TMDB_LANGUAGES]
  return (
    <Field label={t('settings.tmdbLanguage')} hint={t('settings.tmdbLanguageHint')}>
      {(id, desc) => (
        <Select id={id} aria-describedby={desc} value={value} onChange={(e) => onChange(e.target.value)}>
          {options.map((code) => (
            <option key={code} value={code}>
              {label(code)}
            </option>
          ))}
        </Select>
      )}
    </Field>
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
      {test.isPending ? (
        <p role="status" className="text-sm text-muted">
          {t('settings.testing')}
        </p>
      ) : test.isError ? (
        <CheckResult check={{ ok: false, detail: test.error.message, latency_ms: 0 }} />
      ) : (
        <CheckResult check={test.data} />
      )}
    </div>
  )
}
