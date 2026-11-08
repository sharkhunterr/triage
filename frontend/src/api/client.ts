import type { components } from './generated/schema'

export type Schemas = components['schemas']

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message)
  }
}

type Options = { method?: string; body?: unknown; signal?: AbortSignal }

/** Calls `/api/v1{path}` with the session cookie; writes carry the CSRF header (Constitution VII). */
export async function api<T>(path: string, { method = 'GET', body, signal }: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (method !== 'GET') headers['X-Triage-CSRF'] = '1'
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = data?.error ?? {}
    throw new ApiError(
      response.status,
      error.code ?? 'error',
      error.message ?? response.statusText,
      error.details,
    )
  }
  return data as T
}

export const isUnauthorized = (error: unknown) => error instanceof ApiError && error.status === 401
