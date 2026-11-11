import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'

type Secret = { set: boolean }

export type SettingsView = {
  wizard_completed: boolean
  base_url: string
  webhook_url: string
  radarr: { url: string; api_key: Secret; intake_root_folders: string[] }
  tmdb: { api_key: Secret; language: string }
  ollama: { url: string; model: string; timeout_s: number; ask: 'when_unsure' | 'always' | 'never' }
  seerr: { url: string; api_key: Secret; webhook_secret: Secret }
  smtp: {
    host: string
    port: number
    security: 'starttls' | 'ssl' | 'none'
    username: string
    password: Secret
    sender: string
    recipient: string
  }
  sorting: {
    mode: 'preview' | 'automatic'
    threshold: number
    margin: number
    ai_weight: number
    poll_interval_s: number
    link_validity_days: number
  }
  wiki: { enabled: boolean }
}

export type Service = 'radarr' | 'tmdb' | 'ollama' | 'seerr' | 'smtp'
export type Check = { ok: boolean; detail: string; latency_ms: number; models?: string[] }
export type SettingsPatch = Record<string, unknown>

export const useSettings = () =>
  useQuery({ queryKey: ['settings'], queryFn: () => api<SettingsView>('/settings') })

export function useSaveSettings() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (patch: SettingsPatch) => api<SettingsView>('/settings', { method: 'PATCH', body: patch }),
    onSuccess: (data) => {
      client.setQueryData(['settings'], data)
      return client.invalidateQueries({ predicate: (q) => q.queryKey[0] !== 'settings' })
    },
  })
}

export function useTestService() {
  return useMutation({
    mutationFn: ({ service, patch }: { service: Service; patch: SettingsPatch }) =>
      api<Check>(`/settings/test/${service}`, { method: 'POST', body: patch }),
  })
}

export const useOllamaModels = (enabled: boolean) =>
  useQuery({
    queryKey: ['ollama-models'],
    queryFn: () => api<string[]>('/ollama/models'),
    enabled,
    retry: false,
  })

export function useRegenerateWebhookSecret() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api<{ secret: string }>('/settings/webhook-secret', { method: 'POST' }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['settings'] }),
  })
}
