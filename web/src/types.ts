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
