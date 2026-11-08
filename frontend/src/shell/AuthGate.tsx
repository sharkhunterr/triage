import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { api, isUnauthorized } from '../api/client'
import { Spinner } from '../design-system'
import { LoginPage } from '../features/auth/LoginPage'
import { SetupPage } from '../features/auth/SetupPage'
import { useT } from '../i18n'

type SetupStatus = { needs_setup: boolean }
export type Me = { username: string; locale: string }

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/auth/me') })
}

/** Shows setup on first start, sign-in when signed out, the app otherwise. */
export function AuthGate({ children }: { children: ReactNode }) {
  const t = useT()
  const setup = useQuery({ queryKey: ['setup'], queryFn: () => api<SetupStatus>('/setup/status') })
  const me = useQuery({
    queryKey: ['me'],
    queryFn: () => api<Me>('/auth/me'),
    enabled: setup.data?.needs_setup === false,
  })

  if (setup.isPending) return <Spinner label={t('common.loading')} />
  if (setup.data?.needs_setup) return <SetupPage />
  if (me.isPending) return <Spinner label={t('common.loading')} />
  if (me.isError && isUnauthorized(me.error)) return <LoginPage />
  return <>{children}</>
}
