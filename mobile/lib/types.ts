export type Task = {
  id: number
  title: string
  status: string
  due_at: string | null
  priority: number
  notes: string | null
  url: string | null
  project: string | null
}

export type Mission = {
  id: number
  title: string
  status: string
  brief: string
  quality?: string
  mode?: string
  mode_label?: string
  model?: string
  step_index: number
  max_ticks: number
  error: string | null
  markdown?: string
  plan?: {
    tasks: { title: string; goal: string; status: string }[]
    completed: number
    total: number
    cost?: { usd: number; estimated: boolean } | null
  } | null
}

export function missionModeLabel(m: Mission): string {
  if (m.mode_label) return m.mode_label
  const id = (m.mode || m.quality || 'normal').toLowerCase()
  if (id === 'experto' || id === 'pro') return 'A fondo'
  if (id === 'loco') return 'Loco'
  if (id === 'duro') return 'Duro'
  return 'Rápido'
}

export type DaySnapshot = {
  today: string
  clock: string
  headline: string
  greeting: string
  owner_name: string
  tasks: { in_progress: number; open: number }
  agenda: { id: number; starts_at: string; title: string; status: string }[]
  briefing: {
    day: string | null
    summary: string[]
    help: string[]
    tasks: string[]
    meetings: { id: number; starts_at: string; title: string; status: string }[]
    has_dream: boolean
  }
  dream: { day: string | null; excerpt: string | null } | null
  inbox?: {
    connected: boolean
    messages: { id: string; subject: string; from: string; snippet: string }[]
    error?: string | null
  }
}

export type ChatMessage = {
  id?: number
  role: string
  content: string
  created_at?: string
}

export type DiaryEntry = {
  id: number
  text: string
}
