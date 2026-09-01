export type TaskStatus = 'open' | 'in_progress' | 'done' | 'cancelled'

export type Task = {
  id: number
  title: string
  status: TaskStatus | string
  due_at: string | null
  priority: number
  notes: string | null
  url: string | null
  project: string | null
}

export type BoardColumnId = 'in_progress' | 'open' | 'done'

export type MissionStatus =
  | 'draft'
  | 'clarifying'
  | 'queued'
  | 'running'
  | 'waiting'
  | 'done'
  | 'failed'
  | 'cancelled'

export type MissionMode = 'normal' | 'loco' | 'experto' | 'duro'

export type MissionTaskItem = {
  title: string
  goal: string
  status: string
}

export type MissionPlanView = {
  tasks: MissionTaskItem[]
  handoff: string | null
  completed: number
  total: number
  cost?: MissionCostInfo | null
}

export type MissionCostInfo = {
  usd: number
  prompt_tokens: number
  completion_tokens: number
  llm_calls: number
  estimated: boolean
  account_delta_usd?: number | null
}

export type Mission = {
  id: number
  title: string
  status: MissionStatus | string
  brief: string
  quality?: MissionMode | 'pro' | string
  mode?: MissionMode | string
  mode_label?: string
  model?: string
  step_index: number
  max_ticks: number
  tick_seconds: number
  next_run_at: string | null
  result_path: string | null
  error: string | null
  created_at: string
  updated_at: string
  markdown?: string
  asks?: { q: string; a: string }[]
  plan?: MissionPlanView | null
}

export type MissionModeOption = {
  id: MissionMode | string
  label: string
  when: string
  legend: string
  outcome?: string
  blurb: string
  model: string
  approx_usd: number
  approx_label: string
}

/** @deprecated use MissionModeOption */
export type MissionQualityOption = MissionModeOption

export type VoiceProfile = {
  address: 'tu' | 'usted' | 'da_igual' | string
  length: 'telegrafico' | 'corto' | 'normal' | string
  warmth: 'directo' | 'neutro' | 'cercano' | string
  humor: 'cero' | 'seco' | 'si' | string
  signoff: 'nada' | 'nombre' | 'saludo' | string
  notes: string
}

export type BillingInfo = {
  needed: boolean
  status: string
  plan?: string | null
  enforced: boolean
  has_customer: boolean
  legacy: boolean
}

export type MeUser = {
  id: number
  email: string
  owner_name: string
  companion_name: string
  companion_tone: string
  voice?: VoiceProfile
  onboarded: boolean
  legacy: boolean
  billing?: BillingInfo
}
