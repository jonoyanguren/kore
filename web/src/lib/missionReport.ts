/** Split mission vault markdown into Resultado + research sections for the panel. */

export type MissionMdSection = {
  title: string
  body: string
  kind: 'encargo' | 'plan' | 'gasto' | 'task' | 'other'
}

export type MissionReportParts = {
  /** Lines before the first ## (title + status blockquote). */
  preamble: string
  sections: MissionMdSection[]
  /** Last task-like section (síntesis / Resultado), if any. */
  result: MissionMdSection | null
  /** Intermediate task sections (research), oldest first. */
  research: MissionMdSection[]
}

function classifyHeading(title: string): MissionMdSection['kind'] {
  const t = title.trim().toLowerCase()
  if (t === 'encargo') return 'encargo'
  if (t === 'plan') return 'plan'
  if (t === 'gasto llm' || t.startsWith('gasto')) return 'gasto'
  if (t === 'resultado' || t.startsWith('síntesis') || t.startsWith('sintesis')) {
    return 'task'
  }
  return 'task'
}

function isMetaSection(kind: MissionMdSection['kind']): boolean {
  return kind === 'encargo' || kind === 'plan' || kind === 'gasto'
}

/**
 * Split vault markdown by `##` headings.
 * Resultado = section titled Resultado, else last non-meta task section.
 */
export function splitMissionMarkdown(md: string): MissionReportParts {
  const text = (md || '').replace(/\r\n/g, '\n').trim()
  if (!text) {
    return { preamble: '', sections: [], result: null, research: [] }
  }

  const lines = text.split('\n')
  const preambleLines: string[] = []
  const sections: MissionMdSection[] = []
  let current: MissionMdSection | null = null

  for (const line of lines) {
    const h2 = line.match(/^##\s+(.+)$/)
    if (h2) {
      if (current) sections.push(current)
      const title = h2[1].trim()
      current = { title, body: '', kind: classifyHeading(title) }
      continue
    }
    if (!current) {
      preambleLines.push(line)
      continue
    }
    current.body += (current.body ? '\n' : '') + line
  }
  if (current) sections.push(current)

  for (const s of sections) {
    s.body = s.body.replace(/^\n+/, '').replace(/\n+$/, '')
  }

  const taskSections = sections.filter((s) => !isMetaSection(s.kind))
  const explicit = taskSections.find(
    (s) => s.title.trim().toLowerCase() === 'resultado',
  )
  const result =
    explicit ??
    (taskSections.length > 0 ? taskSections[taskSections.length - 1] : null)

  const research = taskSections.filter((s) => s !== result)

  return {
    preamble: preambleLines.join('\n').trim(),
    sections,
    result,
    research,
  }
}

/** Markdown for one section including its ## heading. */
export function sectionToMarkdown(section: MissionMdSection): string {
  const body = section.body.trim()
  return body ? `## ${section.title}\n\n${body}` : `## ${section.title}`
}
