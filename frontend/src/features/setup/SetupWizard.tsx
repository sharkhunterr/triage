import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronLeft, ChevronRight, Copy, Eye, KeyRound, Zap } from 'lucide-react'
import { type FormEvent, type ReactNode, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import {
  type Category,
  useApplyPreset,
  useCategories,
  useRootFolders,
  useSaveCategory,
} from '../../api/categories'
import { api } from '../../api/client'
import {
  type SettingsPatch,
  type SettingsView,
  useOllamaModels,
  useRegenerateWebhookSecret,
  useSaveSettings,
  useSettings,
} from '../../api/settings'
import { Badge, Button, Card, cx, ErrorState, Field, Input, Select, Spinner } from '../../design-system'
import { type Locale, useLocale, useT } from '../../i18n'
import { SecretInput, TestButton, useSection } from '../settings/parts'

const STEPS = ['welcome', 'radarr', 'intake', 'categories', 'tmdb', 'ai', 'email', 'seerr', 'finish'] as const
type Step = (typeof STEPS)[number]
const OPTIONAL: Step[] = ['tmdb', 'ai', 'email', 'seerr']

/**
 * The guided setup: shown after the owner account is created, reachable again from Settings.
 * Each step saves what it shows before moving on, so leaving half-way keeps what was done.
 */
export function SetupWizard() {
  const t = useT()
  const navigate = useNavigate()
  const settings = useSettings()
  const save = useSaveSettings()
  const [step, setStep] = useState<Step>('welcome')
  const [error, setError] = useState<string>()
  const index = STEPS.indexOf(step)
  const go = (delta: number) => {
    setError(undefined)
    setStep(STEPS[Math.min(STEPS.length - 1, Math.max(0, index + delta))] as Step)
  }
  const next = () => go(1)
  /** Saves the step's values, then moves on; an error stays on the step. */
  const saveAndNext = (patch: SettingsPatch) =>
    save.mutate(patch, { onSuccess: next, onError: (e) => setError(e.message) })
  const leave = () =>
    save.mutate(
      { wizard_completed: true },
      { onSuccess: () => navigate('/'), onError: (e) => setError(e.message) },
    )

  if (settings.isPending) return <Spinner label={t('common.loading')} />
  if (settings.isError || !settings.data)
    return (
      <ErrorState
        title={t('common.error')}
        onRetry={() => settings.refetch()}
        retryLabel={t('common.retry')}
      />
    )
  const view = settings.data
  const props = { view, saving: save.isPending, error, saveAndNext, next, back: () => go(-1) }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-2xl flex-col gap-4 p-4 sm:py-10">
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="size-9" />
          <div>
            <h1 className="text-lg font-semibold">{t('wizard.title')}</h1>
            <p className="text-xs text-muted">
              {t('wizard.progress', { current: index + 1, total: STEPS.length })}
            </p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={leave}>
          {view.wizard_completed ? t('wizard.close') : t('wizard.skipAll')}
        </Button>
      </header>
      <nav aria-label={t('wizard.steps')}>
        <ol className="flex gap-1">
          {STEPS.map((s, i) => (
            <li key={s} className="flex-1">
              <span
                aria-current={s === step ? 'step' : undefined}
                title={t(`wizard.${s}.title`)}
                className={cx('block h-1.5 rounded-full', i <= index ? 'bg-accent' : 'bg-border')}
              >
                <span className="sr-only">{t(`wizard.${s}.title`)}</span>
              </span>
            </li>
          ))}
        </ol>
      </nav>
      {step === 'welcome' && <Welcome next={next} />}
      {step === 'radarr' && <RadarrStep {...props} />}
      {step === 'intake' && <IntakeStep {...props} />}
      {step === 'categories' && <CategoriesStep {...props} />}
      {step === 'tmdb' && <TmdbStep {...props} />}
      {step === 'ai' && <AiStep {...props} />}
      {step === 'email' && <EmailStep {...props} />}
      {step === 'seerr' && <SeerrStep {...props} />}
      {step === 'finish' && <FinishStep {...props} />}
    </main>
  )
}

type StepProps = {
  view: SettingsView
  saving: boolean
  error?: string
  saveAndNext: (patch: SettingsPatch) => void
  next: () => void
  back: () => void
}

function Panel({
  step,
  children,
  footer,
  onSubmit,
}: {
  step: Step
  children: ReactNode
  footer: ReactNode
  onSubmit?: () => void
}) {
  const t = useT()
  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit?.()
  }
  return (
    <Card className="p-5">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div>
          <h2 className="flex flex-wrap items-center gap-2 text-xl font-semibold">
            {t(`wizard.${step}.title`)}
            {OPTIONAL.includes(step) && <Badge>{t('wizard.optional')}</Badge>}
          </h2>
          <p className="mt-1 text-sm text-muted">{t(`wizard.${step}.text`)}</p>
        </div>
        {children}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4">
          {footer}
        </div>
      </form>
    </Card>
  )
}

function Footer({
  back,
  skip,
  saving,
  error,
  disabled,
  submitLabel,
}: {
  back?: () => void
  skip?: () => void
  saving: boolean
  error?: string
  disabled?: boolean
  submitLabel?: string
}) {
  const t = useT()
  return (
    <>
      {back ? (
        <Button variant="ghost" icon={<ChevronLeft className="size-4" aria-hidden />} onClick={back}>
          {t('wizard.back')}
        </Button>
      ) : (
        <span />
      )}
      <div className="flex flex-wrap items-center justify-end gap-2">
        {error && (
          <p role="alert" className="w-full text-right text-sm text-danger">
            {error}
          </p>
        )}
        {skip && (
          <Button variant="ghost" onClick={skip}>
            {t('wizard.skip')}
          </Button>
        )}
        <Button type="submit" variant="primary" loading={saving} disabled={disabled}>
          {submitLabel ?? t('wizard.continue')}
          <ChevronRight className="size-4" aria-hidden />
        </Button>
      </div>
    </>
  )
}

// ------------------------------------------------------------------ steps

function Welcome({ next }: { next: () => void }) {
  const t = useT()
  const { locale, setLocale } = useLocale()
  const choose = (value: Locale) => {
    setLocale(value)
    // the server uses it for preset names and emails
    api('/auth/me/locale', { method: 'PUT', body: { locale: value } }).catch(() => {})
  }
  return (
    <Panel step="welcome" onSubmit={next} footer={<Footer saving={false} submitLabel={t('wizard.start')} />}>
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium">{t('wizard.welcome.language')}</legend>
        <div className="flex gap-2">
          {(['en', 'fr'] as const).map((value) => (
            <Button
              key={value}
              variant={locale === value ? 'primary' : 'secondary'}
              aria-pressed={locale === value}
              onClick={() => choose(value)}
            >
              {value === 'en' ? 'English' : 'Français'}
            </Button>
          ))}
        </div>
      </fieldset>
      <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
        <li>{t('wizard.welcome.point1')}</li>
        <li>{t('wizard.welcome.point2')}</li>
        <li>{t('wizard.welcome.point3')}</li>
      </ul>
    </Panel>
  )
}

function RadarrStep({ view, saving, error, saveAndNext, back }: StepProps) {
  const t = useT()
  const radarr = useSection(view, 'radarr', ['url', 'api_key'])
  const patch = () => radarr.patch(['api_key'])
  const ready = Boolean(radarr.values.url) && (Boolean(radarr.values.api_key) || view.radarr.api_key.set)
  return (
    <Panel
      step="radarr"
      onSubmit={() => saveAndNext(patch())}
      footer={<Footer back={back} saving={saving} error={error} disabled={!ready} />}
    >
      <Field label={t('settings.url')}>
        {(id) => (
          <Input
            id={id}
            type="url"
            required
            placeholder="http://radarr:7878"
            value={String(radarr.values.url ?? '')}
            onChange={(e) => radarr.set('url', e.target.value)}
          />
        )}
      </Field>
      <Field label={t('settings.apiKey')} hint={t('settings.radarrKeyHint')}>
        {(id, desc) => (
          <SecretInput
            id={id}
            describedBy={desc}
            set={view.radarr.api_key.set}
            value={String(radarr.values.api_key ?? '')}
            onChange={(v) => radarr.set('api_key', v)}
          />
        )}
      </Field>
      <TestButton service="radarr" patch={patch} />
    </Panel>
  )
}

function IntakeStep({ view, saving, error, saveAndNext, back }: StepProps) {
  const t = useT()
  const folders = useRootFolders()
  const [intake, setIntake] = useState<string[]>(view.radarr.intake_root_folders)
  const toggle = (path: string) =>
    setIntake((current) => (current.includes(path) ? current.filter((p) => p !== path) : [...current, path]))
  return (
    <Panel
      step="intake"
      onSubmit={() => saveAndNext({ radarr: { intake_root_folders: intake } })}
      footer={<Footer back={back} saving={saving} error={error} disabled={intake.length === 0} />}
    >
      {folders.isPending && <Spinner label={t('common.loading')} />}
      {folders.isError && (
        <p role="alert" className="text-sm text-danger">
          {t('wizard.intake.unreachable')}
        </p>
      )}
      <fieldset className="flex flex-col gap-2">
        <legend className="sr-only">{t('settings.intake')}</legend>
        {folders.data?.map((folder) => (
          <label
            key={folder.path}
            className={cx(
              'flex items-center gap-3 rounded-lg border p-3 text-sm',
              intake.includes(folder.path) ? 'border-accent bg-accent/5' : 'border-border',
            )}
          >
            <input
              type="checkbox"
              checked={intake.includes(folder.path)}
              onChange={() => toggle(folder.path)}
            />
            <code className="break-all">{folder.path}</code>
            {!folder.accessible && <Badge tone="warning">{t('categories.inaccessible')}</Badge>}
          </label>
        ))}
      </fieldset>
    </Panel>
  )
}

function CategoriesStep({ view, error, next, back }: StepProps) {
  const t = useT()
  const categories = useCategories()
  const folders = useRootFolders()
  const preset = useApplyPreset()
  const saveCategory = useSaveCategory()
  const [libraries, setLibraries] = useState<Record<number, string>>({})
  const [failure, setFailure] = useState<string>()
  useEffect(() => {
    setLibraries((current) => {
      const next = { ...current }
      for (const c of categories.data ?? []) if (!(c.id in next)) next[c.id] = c.root_folder_path ?? ''
      return next
    })
  }, [categories.data])
  const targets = (folders.data ?? []).filter((f) => !view.radarr.intake_root_folders.includes(f.path))
  const list = categories.data ?? []
  const missing = list.some((c) => !libraries[c.id])

  const submit = async () => {
    setFailure(undefined)
    try {
      for (const c of list) {
        const path = libraries[c.id] || null
        if (path !== c.root_folder_path) await saveCategory.mutateAsync({ id: c.id, body: asInput(c, path) })
      }
      next()
    } catch (e) {
      setFailure((e as Error).message)
    }
  }

  return (
    <Panel
      step="categories"
      onSubmit={submit}
      footer={
        <Footer
          back={back}
          saving={saveCategory.isPending}
          error={failure ?? error}
          disabled={list.length === 0 || missing}
        />
      }
    >
      {categories.isPending && <Spinner label={t('common.loading')} />}
      {categories.data && list.length === 0 && (
        <div className="flex flex-col items-start gap-2 rounded-lg border border-dashed border-border p-4">
          <p className="font-medium">{t('wizard.categories.presetTitle')}</p>
          <p className="text-sm text-muted">{t('wizard.categories.presetText')}</p>
          <Button
            variant="primary"
            loading={preset.isPending}
            onClick={() => preset.mutate('movies-animation')}
          >
            {t('categories.applyPreset')}
          </Button>
        </div>
      )}
      {list.length > 0 && (
        <ul className="flex flex-col gap-3">
          {list.map((c) => (
            <li key={c.id} className="rounded-lg border border-border p-3">
              <Field label={t('wizard.categories.libraryFor', { name: c.name })}>
                {(id) => (
                  <Select
                    id={id}
                    value={libraries[c.id] ?? ''}
                    onChange={(e) => setLibraries((l) => ({ ...l, [c.id]: e.target.value }))}
                  >
                    <option value="">—</option>
                    {targets.map((f) => (
                      <option key={f.path} value={f.path}>
                        {f.path}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <p className="mt-1 text-xs text-muted">
                {c.is_fallback ? `${t('categories.fallbackBadge')} · ` : ''}
                {t('categories.ruleCount', { count: c.rules.length })}
              </p>
            </li>
          ))}
        </ul>
      )}
      {list.length > 0 && <p className="text-xs text-muted">{t('wizard.categories.later')}</p>}
    </Panel>
  )
}

function asInput(c: Category, root_folder_path: string | null) {
  return {
    name: c.name,
    description: c.description,
    is_fallback: c.is_fallback,
    root_folder_path,
    rules: c.rules.map(({ field, operator, value, weight, decisive }) => ({
      field,
      operator,
      value,
      weight,
      decisive,
    })),
  }
}

function TmdbStep({ view, saving, error, saveAndNext, next, back }: StepProps) {
  const t = useT()
  const tmdb = useSection(view, 'tmdb', ['api_key'])
  const patch = () => tmdb.patch(['api_key'])
  return (
    <Panel
      step="tmdb"
      onSubmit={() => saveAndNext(patch())}
      footer={<Footer back={back} skip={next} saving={saving} error={error} />}
    >
      <Field label={t('settings.apiKey')} hint={t('wizard.tmdb.hint')}>
        {(id, desc) => (
          <SecretInput
            id={id}
            describedBy={desc}
            set={view.tmdb.api_key.set}
            value={String(tmdb.values.api_key ?? '')}
            onChange={(v) => tmdb.set('api_key', v)}
          />
        )}
      </Field>
      <TestButton service="tmdb" patch={patch} />
    </Panel>
  )
}

function AiStep({ view, saving, error, saveAndNext, next, back }: StepProps) {
  const t = useT()
  const ollama = useSection(view, 'ollama', ['url', 'model'])
  const queryClient = useQueryClient()
  const save = useSaveSettings()
  const models = useOllamaModels(Boolean(view.ollama.url))
  // A successful test keeps the address, so the installed models can be listed.
  const reached = () =>
    save.mutate(ollama.patch(), {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ollama-models'] }),
    })
  return (
    <Panel
      step="ai"
      onSubmit={() => saveAndNext(ollama.patch())}
      footer={<Footer back={back} skip={next} saving={saving} error={error} />}
    >
      <Field label={t('settings.url')} hint={t('settings.aiUrlHint')}>
        {(id, desc) => (
          <Input
            id={id}
            type="url"
            aria-describedby={desc}
            placeholder="http://ollama:11434"
            value={String(ollama.values.url ?? '')}
            onChange={(e) => ollama.set('url', e.target.value)}
          />
        )}
      </Field>
      <Field label={t('settings.model')} hint={t('wizard.ai.modelHint')}>
        {(id, desc) =>
          models.data?.length ? (
            <Select
              id={id}
              aria-describedby={desc}
              value={String(ollama.values.model ?? '')}
              onChange={(e) => ollama.set('model', e.target.value)}
            >
              <option value="">—</option>
              {models.data.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </Select>
          ) : (
            <Input
              id={id}
              aria-describedby={desc}
              placeholder="qwen3:8b"
              value={String(ollama.values.model ?? '')}
              onChange={(e) => ollama.set('model', e.target.value)}
            />
          )
        }
      </Field>
      <TestButton service="ollama" patch={() => ollama.patch()} onResult={(c) => c.ok && reached()} />
    </Panel>
  )
}

function EmailStep({ view, saving, error, saveAndNext, next, back }: StepProps) {
  const t = useT()
  const smtp = useSection(view, 'smtp', [
    'host',
    'port',
    'security',
    'username',
    'password',
    'sender',
    'recipient',
  ])
  const [baseUrl, setBaseUrl] = useState(view.base_url || window.location.origin)
  const patch = () => smtp.patch(['password'])
  const text = (field: string, label: string, type = 'text', placeholder?: string) => (
    <Field label={label}>
      {(id) => (
        <Input
          id={id}
          type={type}
          autoComplete="off"
          placeholder={placeholder}
          value={String(smtp.values[field] ?? '')}
          onChange={(e) => smtp.set(field, type === 'number' ? Number(e.target.value) : e.target.value)}
        />
      )}
    </Field>
  )
  return (
    <Panel
      step="email"
      onSubmit={() => saveAndNext({ ...patch(), base_url: baseUrl })}
      footer={<Footer back={back} skip={next} saving={saving} error={error} />}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        {text('host', t('settings.smtpHost'), 'text', 'smtp.example.org')}
        {text('port', t('settings.smtpPort'), 'number')}
        <Field label={t('settings.smtpSecurity')}>
          {(id) => (
            <Select
              id={id}
              value={String(smtp.values.security ?? 'starttls')}
              onChange={(e) => smtp.set('security', e.target.value)}
            >
              <option value="starttls">STARTTLS</option>
              <option value="ssl">SSL/TLS</option>
              <option value="none">{t('settings.smtpNone')}</option>
            </Select>
          )}
        </Field>
        {text('username', t('settings.smtpUser'))}
        <Field label={t('settings.smtpPassword')}>
          {(id) => (
            <SecretInput
              id={id}
              set={view.smtp.password.set}
              value={String(smtp.values.password ?? '')}
              onChange={(v) => smtp.set('password', v)}
            />
          )}
        </Field>
        {text('sender', t('settings.smtpFrom'), 'email')}
        {text('recipient', t('settings.smtpTo'), 'email')}
        <Field label={t('settings.baseUrl')} hint={t('settings.baseUrlHint')}>
          {(id, desc) => (
            <Input
              id={id}
              type="url"
              aria-describedby={desc}
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
            />
          )}
        </Field>
      </div>
      <TestButton service="smtp" patch={patch} />
    </Panel>
  )
}

function SeerrStep({ view, saving, error, saveAndNext, next, back }: StepProps) {
  const t = useT()
  const seerr = useSection(view, 'seerr', ['url', 'api_key'])
  const webhook = useRegenerateWebhookSecret()
  const patch = () => seerr.patch(['api_key'])
  return (
    <Panel
      step="seerr"
      onSubmit={() => saveAndNext(patch())}
      footer={<Footer back={back} skip={next} saving={saving} error={error} />}
    >
      <Field label={t('settings.url')}>
        {(id) => (
          <Input
            id={id}
            type="url"
            placeholder="http://jellyseerr:5055"
            value={String(seerr.values.url ?? '')}
            onChange={(e) => seerr.set('url', e.target.value)}
          />
        )}
      </Field>
      <Field label={t('settings.apiKey')}>
        {(id) => (
          <SecretInput
            id={id}
            set={view.seerr.api_key.set}
            value={String(seerr.values.api_key ?? '')}
            onChange={(v) => seerr.set('api_key', v)}
          />
        )}
      </Field>
      <TestButton service="seerr" patch={patch} />
      <div className="rounded-lg border border-border p-3 text-sm">
        <p className="font-medium">{t('settings.webhook')}</p>
        <p className="mt-1 text-xs text-muted">{t('settings.webhookHint')}</p>
        <p className="mt-2 flex items-center gap-2 break-all">
          <code>{view.webhook_url}</code>
          <Button
            size="sm"
            variant="ghost"
            aria-label={t('settings.copy')}
            onClick={() => navigator.clipboard?.writeText(view.webhook_url)}
          >
            <Copy className="size-4" aria-hidden />
          </Button>
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            icon={<KeyRound className="size-4" aria-hidden />}
            loading={webhook.isPending}
            onClick={() => webhook.mutate()}
          >
            {view.seerr.webhook_secret.set ? t('settings.webhookRegenerate') : t('settings.webhookGenerate')}
          </Button>
          {webhook.data && (
            <p className="text-xs">
              {t('settings.webhookSecretOnce')} <code className="break-all">{webhook.data.secret}</code>
            </p>
          )}
        </div>
      </div>
    </Panel>
  )
}

function FinishStep({ view, error, back }: StepProps) {
  const t = useT()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState(view.sorting.mode)
  const [scan, setScan] = useState(true)
  const intake = view.radarr.intake_root_folders[0]
  const finish = useMutation({
    mutationFn: async () => {
      await api('/settings', { method: 'PATCH', body: { wizard_completed: true, sorting: { mode } } })
      if (scan && intake) await api('/scans', { method: 'POST', body: { root_folder_path: intake } })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries()
      navigate(scan && intake ? '/scans' : '/')
    },
  })
  const summary: [string, boolean][] = [
    [t('service.radarr'), Boolean(view.radarr.url && view.radarr.api_key.set)],
    [t('settings.intake'), view.radarr.intake_root_folders.length > 0],
    [t('service.tmdb'), view.tmdb.api_key.set],
    [t('service.ollama'), Boolean(view.ollama.url && view.ollama.model)],
    [t('service.smtp'), Boolean(view.smtp.host && view.smtp.recipient)],
    [t('service.seerr'), Boolean(view.seerr.url && view.seerr.api_key.set)],
  ]
  const option = (value: 'preview' | 'automatic', icon: ReactNode) => (
    <label
      className={cx(
        'flex flex-1 cursor-pointer flex-col gap-1 rounded-xl border p-3',
        mode === value ? 'border-accent bg-accent/10' : 'border-border',
      )}
    >
      <span className="flex items-center gap-2 font-medium">
        <input type="radio" name="mode" checked={mode === value} onChange={() => setMode(value)} />
        {icon} {t(`mode.${value}`)}
      </span>
      <span className="text-xs text-muted">{t(`mode.${value}Hint`)}</span>
    </label>
  )
  return (
    <Panel
      step="finish"
      onSubmit={() => finish.mutate()}
      footer={
        <Footer
          back={back}
          saving={finish.isPending}
          error={finish.error?.message ?? error}
          submitLabel={t('wizard.finish.submit')}
        />
      }
    >
      <ul className="grid gap-2 sm:grid-cols-2">
        {summary.map(([label, done]) => (
          <li key={label} className="flex items-center gap-2 text-sm">
            {done ? (
              <Check className="size-4 text-success" aria-hidden />
            ) : (
              <span className="size-4 text-center text-muted" aria-hidden>
                –
              </span>
            )}
            {label}
            <span className="sr-only">{done ? t('wizard.finish.done') : t('wizard.finish.notSet')}</span>
          </li>
        ))}
      </ul>
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium">{t('mode.title')}</legend>
        <div className="flex flex-col gap-2 sm:flex-row">
          {option('preview', <Eye className="size-4" aria-hidden />)}
          {option('automatic', <Zap className="size-4" aria-hidden />)}
        </div>
      </fieldset>
      {intake && (
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-1"
            checked={scan}
            onChange={(e) => setScan(e.target.checked)}
          />
          <span>
            {t('wizard.finish.scan', { folder: intake })}
            <span className="block text-xs text-muted">{t('wizard.finish.scanHint')}</span>
          </span>
        </label>
      )}
    </Panel>
  )
}
