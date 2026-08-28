/** Markdown → HTML for mission reports (links, images, tables, headings, lists). */

function esc(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function isSafeHttpUrl(url: string): boolean {
  return /^https?:\/\//i.test(url.trim())
}

export function proxiedMediaSrc(url: string): string {
  const href = url.trim()
  if (href.startsWith('/api/media/proxy')) return href
  return `/api/media/proxy?u=${encodeURIComponent(href)}`
}

export function renderImageHtml(alt: string, url: string): string {
  const href = url.trim()
  if (!isSafeHttpUrl(href)) {
    return esc(`![${alt}](${url})`)
  }
  const caption = alt.trim()
    ? `<figcaption>${esc(alt)}</figcaption>`
    : ''
  const src = proxiedMediaSrc(href)
  return (
    `<figure class="missions__figure">` +
    `<img src="${esc(src)}" alt="${esc(alt)}" decoding="async" />` +
    caption +
    `</figure>`
  )
}

/** Inline formatting; images become figures (block-ish inside paragraphs OK). */
export function inlineMarkdown(s: string): string {
  const slots: string[] = []
  const withSlots = s.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt: string, url: string) => {
    const i = slots.length
    slots.push(renderImageHtml(alt, url))
    return `\u0000IMG${i}\u0000`
  })

  // Escape everything first, then re-apply safe HTML for markdown + restore images.
  // Placeholders survive esc() (\u0000 and digits/letters).
  let html = esc(withSlots)
  html = html
    .replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      (_, text: string, url: string) => {
        // text/url already escaped; unescape for validation then re-esc href
        const hrefRaw = url
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"')
          .trim()
        if (!isSafeHttpUrl(hrefRaw) && !/^mailto:/i.test(hrefRaw)) {
          return `[${text}](${url})`
        }
        return `<a href="${esc(hrefRaw)}" target="_blank" rel="noopener noreferrer">${text}</a>`
      },
    )
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')

  return html.replace(/\u0000IMG(\d+)\u0000/g, (_, n: string) => slots[Number(n)] || '')
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
  return (
    `<div class="missions__table-wrap">` +
    `<table class="missions__table">${thead}${tbody}</table>` +
    `</div>`
  )
}

function sectionBlockClass(title: string): string {
  const t = title.trim().toLowerCase()
  if (
    t.startsWith('decisi') ||
    t.startsWith('juicio') ||
    t.startsWith('veredicto') ||
    t.startsWith('si hubiera')
  ) {
    return 'missions__block--decision'
  }
  if (
    t.startsWith('por qu') ||
    t.startsWith('porque') ||
    t.startsWith('incertidumbre') ||
    t.startsWith('peor caso')
  ) {
    return 'missions__block--why'
  }
  if (
    t.startsWith('opcion') ||
    t.startsWith('opción') ||
    t.startsWith('mapa') ||
    t.startsWith('las más raras') ||
    t.startsWith('las mas raras') ||
    t.startsWith('evidencia') ||
    t.startsWith('contraste') ||
    t.startsWith('qué te comes') ||
    t.startsWith('que te comes')
  ) {
    return 'missions__block--options'
  }
  if (t.startsWith('siguiente') || t.startsWith('si aún así') || t.startsWith('si aun asi')) {
    return 'missions__block--next'
  }
  if (t.startsWith('fuente')) return 'missions__block--sources'
  return 'missions__block--plain'
}

const IMAGE_ONLY = /^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$/

export function renderMissionMarkdown(md: string): string {
  const lines = md.replace(/\r\n/g, '\n').split('\n')
  const out: string[] = []
  let inList = false
  let inQuote = false
  let inSection = false
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

  function closeSection() {
    if (inSection) {
      out.push('</div>')
      inSection = false
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

    const imgOnly = line.match(IMAGE_ONLY)
    if (imgOnly) {
      closeList()
      closeQuote()
      out.push(renderImageHtml(imgOnly[1], imgOnly[2]))
      continue
    }

    if (/^---+$|^\*\*\*+$|^___+$/.test(line.trim())) {
      closeList()
      closeQuote()
      out.push('<hr />')
      continue
    }

    if (/^###\s+/.test(line)) {
      closeList()
      closeQuote()
      closeSection()
      const title = line.replace(/^###\s+/, '')
      const cls = sectionBlockClass(title)
      out.push(
        `<div class="missions__block ${cls}"><h3>${inlineMarkdown(title)}</h3>`,
      )
      inSection = true
      continue
    }
    if (/^##\s+/.test(line)) {
      closeList()
      closeQuote()
      closeSection()
      out.push(`<h2>${inlineMarkdown(line.replace(/^##\s+/, ''))}</h2>`)
      continue
    }
    if (/^#\s+/.test(line)) {
      closeList()
      closeQuote()
      closeSection()
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
  closeSection()
  return out.join('\n')
}
