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

export type ChatMessage = { role: string; content: string }

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
      tasks_changed: Boolean(r.data.tasks_changed),
    }
  } finally {
    window.clearTimeout(timer)
  }
}
