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
}

export type Mission = {
  id: number
  title: string
  status: MissionStatus | string
  brief: string
  step_index: number
  max_ticks: number
  tick_seconds: number
  next_run_at: string | null
  result_path: string | null
  error: string | null
  created_at: string
  updated_at: string
  markdown?: string
  plan?: MissionPlanView | null
}
