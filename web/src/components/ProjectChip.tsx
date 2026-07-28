import { spaceColorForProject } from '../spaces'

type Props = {
  project: string | null | undefined
  className?: string
}

export function ProjectChip({ project, className = '' }: Props) {
  const slug = (project || '').trim()
  if (!slug) return null
  const color = spaceColorForProject(slug) || '#5a6570'
  return (
    <span
      className={`project-chip${className ? ` ${className}` : ''}`}
      style={{
        ['--chip' as string]: color,
        background: `color-mix(in srgb, ${color} 18%, white)`,
        color,
        borderColor: `color-mix(in srgb, ${color} 35%, transparent)`,
      }}
    >
      {slug}
    </span>
  )
}
