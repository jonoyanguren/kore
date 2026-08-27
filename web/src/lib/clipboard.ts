/** Collapse copy artifacts from card/table layouts. */
export function cleanCopiedText(s: string): string {
  return (s || '')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/** Copy text to clipboard; returns true on success. */
export async function copyToClipboard(text: string): Promise<boolean> {
  const t = cleanCopiedText(text)
  if (!t) return false
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(t)
      return true
    }
  } catch {
    /* fall through */
  }
  try {
    const ta = document.createElement('textarea')
    ta.value = t
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}

export function shortUrlLabel(url: string, max = 48): string {
  return url.replace(/^https?:\/\//, '').slice(0, max)
}
