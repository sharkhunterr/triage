import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { ApiError, api } from '../../api/client'
import { Button, Field, Input } from '../../design-system'
import { useT } from '../../i18n'
import { AuthShell } from './SetupPage'

export function LoginPage() {
  const t = useT()
  const queryClient = useQueryClient()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const login = useMutation({
    mutationFn: () => api('/auth/login', { method: 'POST', body: { username, password } }),
    onSuccess: () => queryClient.invalidateQueries(),
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    login.mutate()
  }
  const error =
    login.error instanceof ApiError
      ? login.error.status === 429
        ? t('login.throttled')
        : t('login.failed')
      : undefined

  return (
    <AuthShell title={t('login.title')} subtitle={t('login.subtitle')}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label={t('auth.username')}>
          {(id) => (
            <Input
              id={id}
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('auth.password')}>
          {(id) => (
            <Input
              id={id}
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
        </Field>
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        <Button type="submit" variant="primary" loading={login.isPending}>
          {t('login.submit')}
        </Button>
      </form>
    </AuthShell>
  )
}
