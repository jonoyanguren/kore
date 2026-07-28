import type { Mission, Task, TaskStatus } from './types'

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

export type UsageInfo = {
  usage_usd: number
  total_usd: number
  remaining_usd: number
  pct_used: number
  source: string
}

export async function apiUsage(force = false): Promise<UsageInfo | null> {
  const qs = force ? '?force=true' : ''
  const r = await req<{ ok: boolean; usage: UsageInfo | null }>(`/api/usage${qs}`)
  if (!r.ok || !r.data.ok || !r.data.usage) return null
  return r.data.usage
}

export type LlmRoutingRow = {
  role: string
  model: string
  price_in: string
  price_out: string
  uses: string
}

export type LlmRouting = {
  rows: LlmRoutingRow[]
  notes: string[]
}

export async function apiLlmRouting(): Promise<LlmRouting | null> {
  const r = await req<{ ok: boolean; rows: LlmRoutingRow[]; notes: string[] }>(
    '/api/llm-routing',
  )
  if (!r.ok || !r.data.ok) return null
  return { rows: r.data.rows, notes: r.data.notes ?? [] }
}

export type MemoryItem = { id: number; category: string; text: string }
export type DiaryEntry = { id: number; text: string }

export async function apiMemoryCategories(): Promise<string[]> {
  const r = await req<{ categories: string[] }>('/api/memory/categories')
  if (!r.ok) throw new Error(`memory categories ${r.status}`)
  return r.data.categories
}

export async function apiListMemory(
  category?: string,
  limit = 40,
): Promise<MemoryItem[]> {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (category) qs.set('category', category)
  const r = await req<{ items: MemoryItem[] }>(`/api/memory?${qs}`)
  if (!r.ok) throw new Error(`list memory ${r.status}`)
  return r.data.items
}

export async function apiCreateMemory(input: {
  text: string
  category?: string
}): Promise<MemoryItem> {
  const r = await req<{ item: MemoryItem }>('/api/memory', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  if (!r.ok) throw new Error(`create memory ${r.status}`)
  return r.data.item
}

export async function apiDeleteMemory(id: number): Promise<void> {
  const r = await req(`/api/memory/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`delete memory ${r.status}`)
}

export async function apiDeleteMemoryCategory(category: string): Promise<number> {
  const r = await req<{ deleted: number }>(
    `/api/memory/category/${encodeURIComponent(category)}`,
    { method: 'DELETE' },
  )
  if (!r.ok) throw new Error(`delete category ${r.status}`)
  return r.data.deleted
}

export type PrivacyOverview = {
  memory_categories: { category: string; count: number }[]
  memory_total: number
  diary_today: number
  tasks_open: number
  vault_root: string
}

export async function apiPrivacyOverview(): Promise<PrivacyOverview> {
  const r = await req<PrivacyOverview>('/api/privacy/overview')
  if (!r.ok) throw new Error(`privacy ${r.status}`)
  return r.data
}

/** Download vault zip (cookie auth). Triggers browser save. */
export async function apiVaultExport(): Promise<void> {
  const res = await fetch('/api/vault/export', { credentials: 'include' })
  if (!res.ok) throw new Error(`export ${res.status}`)
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') || ''
  const m = /filename="([^"]+)"/.exec(cd)
  const name = m?.[1] ?? 'kore-vault.zip'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

export async function apiTranscribe(blob: Blob): Promise<string> {
  const fd = new FormData()
  const ext = blob.type.includes('ogg')
    ? 'ogg'
    : blob.type.includes('mp4')
      ? 'm4a'
      : 'webm'
  fd.append('file', blob, `voice.${ext}`)
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 90_000)
  try {
    const res = await fetch('/api/transcribe', {
      method: 'POST',
      credentials: 'include',
      body: fd,
      signal: controller.signal,
    })
    if (!res.ok) {
      let detail = `transcribe ${res.status}`
      try {
        const j = (await res.json()) as { detail?: string }
        if (j.detail) detail = String(j.detail)
      } catch {
        /* ignore */
      }
      throw new Error(detail)
    }
    const data = (await res.json()) as { text: string }
    return (data.text || '').trim()
  } finally {
    window.clearTimeout(timer)
  }
}

export async function apiListDiary(
  day?: string,
): Promise<{ day: string; entries: DiaryEntry[] }> {
  const qs = day ? `?day=${encodeURIComponent(day)}` : ''
  const r = await req<{ day: string; entries: DiaryEntry[] }>(`/api/diary${qs}`)
  if (!r.ok) throw new Error(`list diary ${r.status}`)
  return r.data
}

export async function apiCreateDiary(input: {
  text: string
  day?: string
}): Promise<DiaryEntry & { day: string }> {
  const r = await req<{ entry: DiaryEntry & { day: string } }>('/api/diary', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  if (!r.ok) throw new Error(`create diary ${r.status}`)
  return r.data.entry
}

export async function apiDeleteDiary(id: number): Promise<void> {
  const r = await req(`/api/diary/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`delete diary ${r.status}`)
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

export async function apiDeleteTask(id: number): Promise<void> {
  const r = await req(`/api/tasks/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`delete task ${r.status}`)
}

export async function apiPurgeCompletedTasks(): Promise<number> {
  const r = await req<{ ok: boolean; deleted: number }>('/api/tasks/completed', {
    method: 'DELETE',
  })
  if (!r.ok) throw new Error(`purge completed ${r.status}`)
  return r.data.deleted
}

export type DayBriefing = {
  day: string | null
  has_dream: boolean
  summary: string[]
  in_progress_tasks: {
    id: number
    title: string
    status: string
    project?: string | null
    due_at?: string | null
    priority?: number
  }[]
  must_not_miss: {
    id: number
    title: string
    status: string
    project?: string | null
    due_at?: string | null
    priority?: number
  }[]
  important_tasks: {
    id: number
    title: string
    status: string
    project?: string | null
    due_at?: string | null
    priority?: number
  }[]
  meetings: { id: number; starts_at: string; title: string; status: string }[]
  help: string[]
  inbox?: string[]
}

export type DaySnapshot = {
  today: string
  clock: string
  headline: string
  greeting: string
  owner_name: string
  tasks: { in_progress: number; open: number }
  agenda: { id: number; starts_at: string; title: string; status: string }[]
  briefing: DayBriefing
  dream: { day: string | null; excerpt: string | null } | null
  inbox?: {
    connected: boolean
    email?: string
    gmail_ready?: boolean
    can_send?: boolean
    messages: {
      id: string
      subject: string
      from: string
      snippet: string
      date: string
      permalink: string
    }[]
    error?: string | null
    error_code?: string | null
    marked_read_today?: {
      at: number
      message_id: string
      subject: string
      from: string
      permalink: string
      reason: string
    }[]
  }
  server_now: string
}

export type GmailStatus = {
  configured: boolean
  connected: boolean
  email: string
  scope: string
  gmail_ready?: boolean
  can_send?: boolean
}

export async function apiGmailStatus(): Promise<GmailStatus> {
  const r = await req<GmailStatus>('/api/gmail/status')
  if (!r.ok) {
    return { configured: false, connected: false, email: '', scope: 'gmail.modify' }
  }
  return r.data
}

export async function apiGmailDisconnect(): Promise<boolean> {
  const r = await req<{ ok: boolean }>('/api/gmail/disconnect', { method: 'POST' })
  return r.ok
}

export async function apiGmailMarkRead(messageId: string): Promise<boolean> {
  const r = await req<{ ok: boolean }>(
    `/api/gmail/messages/${encodeURIComponent(messageId)}/read`,
    { method: 'POST' },
  )
  return r.ok
}

export async function apiGmailToTask(
  messageId: string,
): Promise<{ task: Task; email: { id: string; subject: string; from: string } }> {
  const r = await req<{
    ok: boolean
    task: Task
    email: { id: string; subject: string; from: string }
  }>(`/api/gmail/messages/${encodeURIComponent(messageId)}/to-task`, {
    method: 'POST',
  })
  if (!r.ok) throw new Error(`No se pudo crear la tarea (${r.status})`)
  return { task: r.data.task, email: r.data.email }
}

export async function apiListMissions(includeDone = true): Promise<Mission[]> {
  const qs = includeDone ? '' : '?include_done=false'
  const r = await req<{ missions: Mission[] }>(`/api/missions${qs}`)
  if (!r.ok) throw new Error(`missions ${r.status}`)
  return r.data.missions
}

export async function apiGetMission(id: number): Promise<Mission> {
  const r = await req<{ mission: Mission }>(`/api/missions/${id}`)
  if (!r.ok) throw new Error(`mission ${r.status}`)
  return r.data.mission
}

export async function apiCreateMission(input: {
  title: string
  brief?: string
  launch?: boolean
  max_ticks?: number
  tick_seconds?: number
}): Promise<Mission> {
  const r = await req<{ mission: Mission }>('/api/missions', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  if (!r.ok) throw new Error(`create mission ${r.status}`)
  return r.data.mission
}

export type ClarifyHistoryItem = { question: string; answer: string }

export type ClarifyResult = {
  ready: boolean
  questions: string[]
  refined_brief: string
  round: number
  rounds_left: number
}

export async function apiClarifyMission(input: {
  title: string
  brief?: string
  history?: ClarifyHistoryItem[]
  round?: number
}): Promise<ClarifyResult> {
  const r = await req<{
    ok: boolean
    ready: boolean
    questions: string[]
    refined_brief: string
    round: number
    rounds_left: number
  }>('/api/missions/clarify', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  if (!r.ok) throw new Error(`clarify mission ${r.status}`)
  return {
    ready: !!r.data.ready,
    questions: r.data.questions ?? [],
    refined_brief: r.data.refined_brief ?? '',
    round: r.data.round,
    rounds_left: r.data.rounds_left,
  }
}

export async function apiCancelMission(id: number): Promise<Mission> {
  const r = await req<{ mission: Mission }>(`/api/missions/${id}/cancel`, {
    method: 'POST',
  })
  if (!r.ok) throw new Error(`cancel mission ${r.status}`)
  return r.data.mission
}

export async function apiRelaunchMission(id: number): Promise<Mission> {
  const r = await req<{ mission: Mission }>(`/api/missions/${id}/relaunch`, {
    method: 'POST',
  })
  if (!r.ok) throw new Error(`relaunch mission ${r.status}`)
  return r.data.mission
}

export type GmailReplyDraft = {
  message_id: string
  thread_id: string
  to: string
  subject: string
  body: string
  from: string
  permalink: string
}

async function gmailReplyError(res: Response, fallback: string): Promise<Error> {
  try {
    const j = (await res.json()) as {
      detail?: string | { code?: string; message?: string }
    }
    if (typeof j.detail === 'string') return new Error(j.detail)
    if (j.detail?.message) return new Error(j.detail.message)
    if (j.detail?.code === 'needs_send_scope') {
      return new Error(
        'Falta permiso de envío. Desconecta y reconecta Gmail en Más.',
      )
    }
  } catch {
    /* ignore */
  }
  return new Error(`${fallback} (${res.status})`)
}

export async function apiGmailReplyDraft(
  messageId: string,
): Promise<GmailReplyDraft> {
  const res = await fetch(
    `/api/gmail/messages/${encodeURIComponent(messageId)}/reply-draft`,
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    },
  )
  if (!res.ok) throw await gmailReplyError(res, 'No se pudo preparar la respuesta')
  return (await res.json()) as GmailReplyDraft
}

export async function apiGmailReplySend(
  messageId: string,
  body: string,
): Promise<{ ok: boolean; to: string; subject: string }> {
  const res = await fetch(
    `/api/gmail/messages/${encodeURIComponent(messageId)}/reply`,
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body }),
    },
  )
  if (!res.ok) throw await gmailReplyError(res, 'No se pudo enviar')
  return (await res.json()) as { ok: boolean; to: string; subject: string }
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

export type MessagesPage = {
  messages: ChatMessage[]
  has_more: boolean
}

export async function apiListMessages(
  limit = 10,
  before?: number,
): Promise<MessagesPage> {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (before != null) qs.set('before', String(before))
  const r = await req<MessagesPage>(`/api/messages?${qs}`)
  if (!r.ok) throw new Error(`list messages ${r.status}`)
  return {
    messages: r.data.messages,
    has_more: Boolean(r.data.has_more),
  }
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
