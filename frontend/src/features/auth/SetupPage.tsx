import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { ApiError, api } from '../../api/client'
import { Button, Card, Field, Input } from '../../design-system'
import { useLocale, useT } from '../../i18n'

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Card className="w-full max-w-sm p-6">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <img src="/favicon.svg" alt="" className="size-12" />
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="text-sm text-muted">{subtitle}</p>
        </div>
        {children}
      </Card>
    </main>
  )
}

export function SetupPage() {
  const t = useT()
  const { locale } = useLocale()
  const queryClient = useQueryClient()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const mismatch = confirm.length > 0 && password !== confirm
  const setup = useMutation({
    mutationFn: () => api('/setup', { method: 'POST', body: { username, password, locale } }),
    onSuccess: () => queryClient.invalidateQueries(),
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!mismatch) setup.mutate()
  }
  const error = setup.error instanceof ApiError ? setup.error.message : undefined

  return (
    <AuthShell title={t('setup.title')} subtitle={t('setup.subtitle')}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label={t('auth.username')}>
          {(id) => (
            <Input
              id={id}
              autoComplete="username"
              required
              minLength={3}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('auth.password')} hint={t('setup.passwordHint')}>
          {(id, desc) => (
            <Input
              id={id}
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              aria-describedby={desc}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('setup.confirm')} error={mismatch ? t('setup.mismatch') : undefined}>
          {(id, desc) => (
            <Input
              id={id}
              type="password"
              autoComplete="new-password"
              required
              aria-describedby={desc}
              aria-invalid={mismatch}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          )}
        </Field>
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        <Button type="submit" variant="primary" loading={setup.isPending} disabled={mismatch}>
          {t('setup.submit')}
        </Button>
      </form>
    </AuthShell>
  )
}
