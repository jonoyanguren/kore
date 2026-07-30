import { API_BASE } from './config'

export class ApiError extends Error {
  status: number
  constructor(status: number, message?: string) {
    super(message || `API ${status}`)
    this.status = status
  }
}

async function request<T>(
  path: string,
  opts: {
    method?: string
    token: string
    body?: unknown
    formData?: FormData
  },
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${opts.token}`,
  }
  let body: BodyInit | undefined
  if (opts.formData) {
    body = opts.formData
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method || 'GET',
    headers,
    body,
  })
  if (!res.ok) {
    throw new ApiError(res.status)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export async function apiMe(token: string): Promise<boolean> {
  try {
    const ctrl = new AbortController()
    const t = setTimeout(() => ctrl.abort(), 12_000)
    try {
      const res = await fetch(`${API_BASE}/api/me`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: ctrl.signal,
      })
      return res.ok
    } finally {
      clearTimeout(t)
    }
  } catch {
    return false
  }
}

export async function apiDay(token: string): Promise<unknown> {
  return request('/api/day', { token })
}

export async function apiTasks(token: string): Promise<unknown> {
  return request('/api/tasks', { token })
}

export async function apiMissions(token: string): Promise<unknown> {
  return request('/api/missions', { token })
}
