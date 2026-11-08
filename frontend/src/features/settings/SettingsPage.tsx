import { Copy, KeyRound, Wand2 } from 'lucide-react'
import { type FormEvent, type ReactNode, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useRootFolders } from '../../api/categories'
import {
  type Service,
  type SettingsPatch,
  useOllamaModels,
  useRegenerateWebhookSecret,
  useSaveSettings,
  useSettings,
} from '../../api/settings'
import {
  Badge,
  Button,
  Card,
  ErrorState,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  useToast,
} from '../../design-system'
import { useT } from '../../i18n'
import { ModeSwitch } from './ModeSwitch'
import { SecretInput, TestButton, useSection } from './parts'

function Section({
  title,
  description,
  service,
  children,
  onSave,
  testPatch,
  saving,
}: {
  title: string
  description: string
  service?: Service
  children: ReactNode
  onSave: () => void
  testPatch?: () => SettingsPatch
  saving: boolean
}) {
  const t = useT()
  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSave()
  }
  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="text-sm text-muted">{description}</p>
        </div>
        {children}
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" variant="primary" loading={saving}>
            {t('common.save')}
          </Button>
          {service && testPatch && <TestButton service={service} patch={testPatch} />}
        </div>
      </form>
    </Card>
  )
}

export function SettingsPage() {
  const t = useT()
  const toast = useToast()
  const settings = useSettings()
  const save = useSaveSettings()
  const view = settings.data
  const radarr = useSection(view, 'radarr', ['url', 'api_key', 'intake_root_folders'])
  const tmdb = useSection(view, 'tmdb', ['api_key'])
  const ollama = useSection(view, 'ollama', ['url', 'model', 'timeout_s'])
  const seerr = useSection(view, 'seerr', ['url', 'api_key'])
  const smtp = useSection(view, 'smtp', [
    'host',
    'port',
    'security',
    'username',
    'password',
    'sender',
    'recipient',
  ])
  const sorting = useSection(view, 'sorting', [
    'threshold',
    'margin',
    'ai_weight',
    'poll_interval_s',
    'link_validity_days',
  ])
  const folders = useRootFolders()
  const models = useOllamaModels(Boolean(view?.ollama.url))
  const webhook = useRegenerateWebhookSecret()
  const [baseUrl, setBaseUrl] = useState('')
  useEffect(() => setBaseUrl(view?.base_url ?? ''), [view?.base_url])

  const persist = (patch: SettingsPatch) =>
    save.mutate(patch, {
      onSuccess: () => toast(t('common.saved'), 'success'),
      onError: (error) => toast(error.message, 'danger'),
    })

  if (settings.isPending) return <Spinner label={t('common.loading')} />
  if (settings.isError || !view)
    return (
      <ErrorState
        title={t('common.error')}
        onRetry={() => settings.refetch()}
        retryLabel={t('common.retry')}
      />
    )

  const intake = (radarr.values.intake_root_folders as string[] | undefined) ?? []
  const toggleIntake = (path: string) =>
    radarr.set(
      'intake_root_folders',
      intake.includes(path) ? intake.filter((p) => p !== path) : [...intake, path],
    )

  return (
    <>
      <PageHeader title={t('settings.title')} description={t('settings.subtitle')} />
      <div className="flex flex-col gap-4">
        <ModeSwitch mode={view.sorting.mode} />

        <Card className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{t('wizard.reopen')}</h2>
            <p className="text-sm text-muted">{t('wizard.reopenHint')}</p>
          </div>
          <Link
            to="/setup"
            className="inline-flex h-11 items-center gap-2 rounded-lg border border-border px-4 text-sm font-medium hover:bg-surface-2"
          >
            <Wand2 className="size-4" aria-hidden />
            {t('wizard.title')}
          </Link>
        </Card>

        <Section
          title={t('settings.radarr')}
          description={t('settings.radarrHint')}
          service="radarr"
          saving={save.isPending}
          testPatch={() => radarr.patch(['api_key'])}
          onSave={() => persist(radarr.patch(['api_key']))}
        >
          <Field label={t('settings.url')}>
            {(id) => (
              <Input
                id={id}
                type="url"
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
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-sm font-medium">{t('settings.intake')}</legend>
            <p className="text-xs text-muted">{t('settings.intakeHint')}</p>
            {folders.isError && <p className="text-sm text-warning">{t('settings.saveRadarrFirst')}</p>}
            {folders.data?.map((folder) => (
              <label key={folder.path} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={intake.includes(folder.path)}
                  onChange={() => toggleIntake(folder.path)}
                />
                <code>{folder.path}</code>
                {!folder.accessible && <Badge tone="warning">{t('categories.inaccessible')}</Badge>}
              </label>
            ))}
          </fieldset>
        </Section>

        <Section
          title={t('settings.tmdb')}
          description={t('settings.tmdbHint')}
          service="tmdb"
          saving={save.isPending}
          testPatch={() => tmdb.patch(['api_key'])}
          onSave={() => persist(tmdb.patch(['api_key']))}
        >
          <Field label={t('settings.apiKey')}>
            {(id) => (
              <SecretInput
                id={id}
                set={view.tmdb.api_key.set}
                value={String(tmdb.values.api_key ?? '')}
                onChange={(v) => tmdb.set('api_key', v)}
              />
            )}
          </Field>
        </Section>

        <Section
          title={t('settings.ai')}
          description={t('settings.aiHint')}
          service="ollama"
          saving={save.isPending}
          testPatch={() => ollama.patch()}
          onSave={() => persist(ollama.patch())}
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
          <Field label={t('settings.model')}>
            {(id) =>
              models.data?.length ? (
                <Select
                  id={id}
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
                  placeholder="qwen3:8b"
                  value={String(ollama.values.model ?? '')}
                  onChange={(e) => ollama.set('model', e.target.value)}
                />
              )
            }
          </Field>
          <Field label={t('settings.aiTimeout')}>
            {(id) => (
              <Input
                id={id}
                type="number"
                min={5}
                max={600}
                value={Number(ollama.values.timeout_s ?? 60)}
                onChange={(e) => ollama.set('timeout_s', Number(e.target.value))}
              />
            )}
          </Field>
        </Section>

        <Section
          title={t('settings.sorting')}
          description={t('settings.sortingHint')}
          saving={save.isPending}
          onSave={() => persist(sorting.patch())}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('settings.threshold')} hint={t('settings.thresholdHint')}>
              {(id, desc) => (
                <Input
                  id={id}
                  type="number"
                  min={50}
                  max={100}
                  aria-describedby={desc}
                  value={Math.round(Number(sorting.values.threshold ?? 0.8) * 100)}
                  onChange={(e) => sorting.set('threshold', Number(e.target.value) / 100)}
                />
              )}
            </Field>
            <Field label={t('settings.margin')} hint={t('settings.marginHint')}>
              {(id, desc) => (
                <Input
                  id={id}
                  type="number"
                  min={0}
                  max={100}
                  aria-describedby={desc}
                  value={Number(sorting.values.margin ?? 20)}
                  onChange={(e) => sorting.set('margin', Number(e.target.value))}
                />
              )}
            </Field>
            <Field label={t('settings.aiWeight')} hint={t('settings.aiWeightHint')}>
              {(id, desc) => (
                <Input
                  id={id}
                  type="number"
                  min={0}
                  max={100}
                  aria-describedby={desc}
                  value={Number(sorting.values.ai_weight ?? 60)}
                  onChange={(e) => sorting.set('ai_weight', Number(e.target.value))}
                />
              )}
            </Field>
            <Field label={t('settings.interval')} hint={t('settings.intervalHint')}>
              {(id, desc) => (
                <Input
                  id={id}
                  type="number"
                  min={1}
                  max={1440}
                  aria-describedby={desc}
                  value={Math.round(Number(sorting.values.poll_interval_s ?? 300) / 60)}
                  onChange={(e) => sorting.set('poll_interval_s', Number(e.target.value) * 60)}
                />
              )}
            </Field>
          </div>
        </Section>

        <Section
          title={t('settings.email')}
          description={t('settings.emailHint')}
          service="smtp"
          saving={save.isPending}
          testPatch={() => smtp.patch(['password'])}
          onSave={() =>
            persist({
              ...smtp.patch(['password']),
              base_url: baseUrl,
              sorting: { link_validity_days: Number(sorting.values.link_validity_days ?? 7) },
            })
          }
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('settings.smtpHost')}>
              {(id) => (
                <Input
                  id={id}
                  placeholder="smtp.example.org"
                  value={String(smtp.values.host ?? '')}
                  onChange={(e) => smtp.set('host', e.target.value)}
                />
              )}
            </Field>
            <Field label={t('settings.smtpPort')}>
              {(id) => (
                <Input
                  id={id}
                  type="number"
                  value={Number(smtp.values.port ?? 587)}
                  onChange={(e) => smtp.set('port', Number(e.target.value))}
                />
              )}
            </Field>
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
            <Field label={t('settings.smtpUser')}>
              {(id) => (
                <Input
                  id={id}
                  autoComplete="off"
                  value={String(smtp.values.username ?? '')}
                  onChange={(e) => smtp.set('username', e.target.value)}
                />
              )}
            </Field>
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
            <Field label={t('settings.smtpFrom')}>
              {(id) => (
                <Input
                  id={id}
                  type="email"
                  value={String(smtp.values.sender ?? '')}
                  onChange={(e) => smtp.set('sender', e.target.value)}
                />
              )}
            </Field>
            <Field label={t('settings.smtpTo')}>
              {(id) => (
                <Input
                  id={id}
                  type="email"
                  value={String(smtp.values.recipient ?? '')}
                  onChange={(e) => smtp.set('recipient', e.target.value)}
                />
              )}
            </Field>
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
            <Field label={t('settings.linkValidity')}>
              {(id) => (
                <Input
                  id={id}
                  type="number"
                  min={1}
                  max={30}
                  value={Number(sorting.values.link_validity_days ?? 7)}
                  onChange={(e) => sorting.set('link_validity_days', Number(e.target.value))}
                />
              )}
            </Field>
          </div>
        </Section>

        <Section
          title={t('settings.seerr')}
          description={t('settings.seerrHint')}
          service="seerr"
          saving={save.isPending}
          testPatch={() => seerr.patch(['api_key'])}
          onSave={() => persist(seerr.patch(['api_key']))}
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
                {view.seerr.webhook_secret.set
                  ? t('settings.webhookRegenerate')
                  : t('settings.webhookGenerate')}
              </Button>
              {webhook.data && (
                <p className="text-xs">
                  {t('settings.webhookSecretOnce')} <code className="break-all">{webhook.data.secret}</code>
                </p>
              )}
            </div>
          </div>
        </Section>
      </div>
    </>
  )
}
