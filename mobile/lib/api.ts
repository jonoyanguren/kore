import { API_BASE } from './config'
import type {
  ChatMessage,
  DaySnapshot,
  DiaryEntry,
  Mission,
  Task,
} from './types'

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
  },
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${opts.token}`,
  }
  let body: string | undefined
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method || 'GET',
    headers,
    body,
  })
  if (!res.ok) throw new ApiError(res.status)
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

export async function apiDay(token: string): Promise<DaySnapshot> {
  return request('/api/day', { token })
}

export async function apiTasks(
  token: string,
  status = 'all',
): Promise<Task[]> {
  const data = await request<{ tasks: Task[] }>(
    `/api/tasks?status=${encodeURIComponent(status)}&limit=100`,
    { token },
  )
  return data.tasks
}

export async function apiCompleteTask(
  token: string,
  id: number,
): Promise<Task> {
  const data = await request<{ task: Task }>(`/api/tasks/${id}/complete`, {
    token,
    method: 'POST',
  })
  return data.task
}

export async function apiMissions(token: string): Promise<Mission[]> {
  const data = await request<{ missions: Mission[] }>('/api/missions', {
    token,
  })
  return data.missions
}

export async function apiMission(
  token: string,
  id: number,
): Promise<Mission> {
  const data = await request<{ mission: Mission }>(`/api/missions/${id}`, {
    token,
  })
  return data.mission
}

export async function apiDiary(
  token: string,
  day?: string,
): Promise<{ day: string; entries: DiaryEntry[] }> {
  const q = day ? `?day=${encodeURIComponent(day)}` : ''
  return request(`/api/diary${q}`, { token })
}

export async function apiAddDiary(
  token: string,
  text: string,
): Promise<DiaryEntry & { day: string }> {
  const data = await request<{ entry: DiaryEntry & { day: string } }>(
    '/api/diary',
    { token, method: 'POST', body: { text } },
  )
  return data.entry
}

export async function apiMessages(
  token: string,
  limit = 30,
): Promise<ChatMessage[]> {
  const data = await request<{ messages: ChatMessage[] }>(
    `/api/messages?limit=${limit}`,
    { token },
  )
  return data.messages
}

export async function apiChat(
  token: string,
  text: string,
): Promise<{ reply: string }> {
  return request('/api/chat', {
    token,
    method: 'POST',
    body: { text },
  })
}
