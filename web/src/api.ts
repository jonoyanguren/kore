import type { Task, TaskStatus } from './types'

async function req<T>(
  path: string,
  init: RequestInit = {},
): Promise<{ ok: true; data: T } | { ok: false; status: number }> {
  const { headers: initHeaders, ...rest } = init
  const res = await fetch(path, {
    credentials: 'include',
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...(initHeaders ?? {}),
    },
  })
  if (!res.ok) return { ok: false, status: res.status }
  const data = (await res.json()) as T
  return { ok: true, data }
}

export async function apiMe(): Promise<boolean> {
  const r = await req<{ ok: boolean }>('/api/me')
  return r.ok
}

export async function apiLogin(secret: string): Promise<boolean> {
  const r = await req<{ ok: boolean }>('/api/login', {
    method: 'POST',
    body: JSON.stringify({ secret }),
  })
  return r.ok
}

export async function apiLogout(): Promise<void> {
  await req('/api/logout', { method: 'POST' })
}

export async function apiListTasks(): Promise<Task[]> {
  const r = await req<{ tasks: Task[] }>('/api/tasks?status=all&limit=100')
  if (!r.ok) throw new Error(`list tasks ${r.status}`)
  return r.data.tasks
}

export async function apiCreateTask(input: {
  title: string
  status?: TaskStatus
  project?: string
  url?: string
}): Promise<Task> {
  const r = await req<{ task: Task }>('/api/tasks', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  if (!r.ok) throw new Error(`create task ${r.status}`)
  return r.data.task
}

export async function apiPatchTask(
  id: number,
  body: Record<string, unknown>,
): Promise<Task> {
  const r = await req<{ task: Task }>(`/api/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`patch task ${r.status}`)
  return r.data.task
}

export async function apiCompleteTask(id: number): Promise<Task> {
  const r = await req<{ task: Task }>(`/api/tasks/${id}/complete`, {
    method: 'POST',
  })
  if (!r.ok) throw new Error(`complete task ${r.status}`)
  return r.data.task
}

export type DaySnapshot = {
  today: string
  clock: string
  headline: string
  tasks: { in_progress: number; open: number }
  agenda: { id: number; starts_at: string; title: string; status: string }[]
  dream: { day: string; excerpt: string } | null
  server_now: string
}

export async function apiDay(): Promise<DaySnapshot> {
  const r = await req<DaySnapshot>('/api/day')
  if (!r.ok) throw new Error(`day ${r.status}`)
  return r.data
}

export type ChatMessage = {
  id?: number
  role: string
  content: string
  created_at?: string
  relative?: string
  tasks?: Task[]
}

export async function apiListMessages(limit = 100): Promise<ChatMessage[]> {
  const r = await req<{ messages: ChatMessage[] }>(
    `/api/messages?limit=${limit}`,
  )
  if (!r.ok) throw new Error(`list messages ${r.status}`)
  return r.data.messages
}

export type ChatResult = {
  reply: string
  tasks_created: Task[]
  tasks_listed: Task[]
  tasks_changed: boolean
}

export async function apiChat(text: string): Promise<ChatResult> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 180_000)
  try {
    const r = await req<ChatResult>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ text }),
      signal: controller.signal,
    })
    if (!r.ok) throw new Error(`chat ${r.status}`)
    return {
      reply: r.data.reply,
      tasks_created: r.data.tasks_created ?? [],
      tasks_listed: r.data.tasks_listed ?? r.data.tasks_created ?? [],
      tasks_changed: Boolean(r.data.tasks_changed),
    }
  } finally {
    window.clearTimeout(timer)
  }
}

export type ChatStreamHandlers = {
  onStatus?: (text: string) => void
}

/** Live chat via SSE (`/api/chat/stream`). Falls back to JSON `/api/chat` if needed. */
export async function apiChatLive(
  text: string,
  handlers: ChatStreamHandlers = {},
): Promise<ChatResult> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 180_000)
  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    })
    if (!res.ok || !res.body) {
      return apiChat(text)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let result: ChatResult | null = null
    let err: string | null = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        const line = part
          .split('\n')
          .map((l) => l.trim())
          .find((l) => l.startsWith('data:'))
        if (!line) continue
        const raw = line.slice(5).trim()
        if (!raw) continue
        let ev: {
          type?: string
          text?: string
          reply?: string
          tasks_created?: Task[]
          tasks_listed?: Task[]
          tasks_changed?: boolean
          detail?: string
        }
        try {
          ev = JSON.parse(raw) as typeof ev
        } catch {
          continue
        }
        if (ev.type === 'status' && ev.text) {
          handlers.onStatus?.(ev.text)
        } else if (ev.type === 'done' && typeof ev.reply === 'string') {
          result = {
            reply: ev.reply,
            tasks_created: ev.tasks_created ?? [],
            tasks_listed: ev.tasks_listed ?? ev.tasks_created ?? [],
            tasks_changed: Boolean(ev.tasks_changed),
          }
        } else if (ev.type === 'error') {
          err = String(ev.detail ?? 'error')
        }
      }
    }
    if (err) throw new Error(err)
    if (result) return result
    return apiChat(text)
  } finally {
    window.clearTimeout(timer)
  }
}
