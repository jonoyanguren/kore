/** Markdown → HTML for mission reports (links, tables, headings, lists). */

function esc(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function inlineMarkdown(s: string): string {
  if (!/[\[*`]/.test(s)) return esc(s)
  return s
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, text: string, url: string) => {
      const href = url.trim()
      if (!/^https?:\/\//i.test(href) && !/^mailto:/i.test(href)) {
        return esc(`[${text}](${url})`)
      }
      return `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>`
    })
    .replace(/\*\*(.+?)\*\*/g, (_, t: string) => `<strong>${esc(t)}</strong>`)
    .replace(/\*(.+?)\*/g, (_, t: string) => `<em>${esc(t)}</em>`)
    .replace(/`([^`]+)`/g, (_, t: string) => `<code>${esc(t)}</code>`)
}

function isTableRow(line: string): boolean {
  const t = line.trim()
  return t.includes('|') && t.split('|').filter((c) => c.trim()).length >= 2
}

function isTableSeparator(line: string): boolean {
  const t = line.trim()
  return /^\|?[\s\-:|]+\|?$/.test(t) && t.includes('-')
}

function parseTableCells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim())
}

function renderTable(rows: string[][]): string {
  if (rows.length === 0) return ''
  const [head, ...body] = rows
  const thead = `<thead><tr>${head.map((c) => `<th>${inlineMarkdown(c)}</th>`).join('')}</tr></thead>`
  const tbody =
    body.length > 0
      ? `<tbody>${body
          .map(
            (row) =>
              `<tr>${row.map((c) => `<td>${inlineMarkdown(c)}</td>`).join('')}</tr>`,
          )
          .join('')}</tbody>`
      : ''
  return `<table>${thead}${tbody}</table>`
}

export function renderMissionMarkdown(md: string): string {
  const lines = md.replace(/\r\n/g, '\n').split('\n')
  const out: string[] = []
  let inList = false
  let inQuote = false
  let tableRows: string[][] = []

  function closeList() {
    if (inList) {
      out.push('</ul>')
      inList = false
    }
  }

  function closeQuote() {
    if (inQuote) {
      out.push('</blockquote>')
      inQuote = false
    }
  }

  function flushTable() {
    if (tableRows.length === 0) return
    out.push(renderTable(tableRows))
    tableRows = []
  }

  for (const raw of lines) {
    const line = raw

    if (isTableRow(line)) {
      closeList()
      closeQuote()
      if (isTableSeparator(line)) continue
      tableRows.push(parseTableCells(line))
      continue
    }
    flushTable()

    if (/^---+$|^\*\*\*+$|^___+$/.test(line.trim())) {
      closeList()
      closeQuote()
      out.push('<hr />')
      continue
    }

    if (/^###\s+/.test(line)) {
      closeList()
      closeQuote()
      out.push(`<h3>${inlineMarkdown(line.replace(/^###\s+/, ''))}</h3>`)
      continue
    }
    if (/^##\s+/.test(line)) {
      closeList()
      closeQuote()
      out.push(`<h2>${inlineMarkdown(line.replace(/^##\s+/, ''))}</h2>`)
      continue
    }
    if (/^#\s+/.test(line)) {
      closeList()
      closeQuote()
      out.push(`<h1>${inlineMarkdown(line.replace(/^#\s+/, ''))}</h1>`)
      continue
    }
    if (/^>\s?/.test(line)) {
      closeList()
      if (!inQuote) {
        out.push('<blockquote>')
        inQuote = true
      }
      out.push(`<p>${inlineMarkdown(line.replace(/^>\s?/, ''))}</p>`)
      continue
    }
    if (/^[-*]\s+/.test(line)) {
      closeQuote()
      if (!inList) {
        out.push('<ul>')
        inList = true
      }
      out.push(`<li>${inlineMarkdown(line.replace(/^[-*]\s+/, ''))}</li>`)
      continue
    }
    if (!line.trim()) {
      closeList()
      closeQuote()
      continue
    }
    closeList()
    closeQuote()
    out.push(`<p>${inlineMarkdown(line)}</p>`)
  }

  flushTable()
  closeList()
  closeQuote()
  return out.join('\n')
}
