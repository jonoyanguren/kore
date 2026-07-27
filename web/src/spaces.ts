/** Canonical project spaces for the console. */

export type SpaceId = 'all' | 'personal' | 'kimay' | 'kore'

export type SpaceDef = {
  id: SpaceId
  label: string
  /** CSS accent (hex) */
  color: string
  /** Task.project value; null = no filter */
  project: string | null
}

export const SPACES: SpaceDef[] = [
  { id: 'all', label: 'Todo', color: '#5a6570', project: null },
  { id: 'personal', label: 'Personal', color: '#2f6f5e', project: 'personal' },
  { id: 'kimay', label: 'Kimay', color: '#b45309', project: 'kimay' },
  { id: 'kore', label: 'Kore', color: '#2b6cb0', project: 'kore' },
]

const STORAGE_KEY = 'kore.space'

export function readSpace(): SpaceId {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v && SPACES.some((s) => s.id === v)) return v as SpaceId
  } catch {
    /* ignore */
  }
  return 'all'
}

export function writeSpace(id: SpaceId): void {
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
}

export function spaceDef(id: SpaceId): SpaceDef {
  return SPACES.find((s) => s.id === id) ?? SPACES[0]
}

export function spaceColorForProject(project: string | null | undefined): string | null {
  if (!project) return null
  const hit = SPACES.find((s) => s.project === project)
  return hit?.color ?? null
}
