/** Hide broken/pending mission images so they never jump the layout. */

function markFigure(img: HTMLImageElement, ok: boolean) {
  const fig = img.closest('.missions__figure')
  if (!(fig instanceof HTMLElement)) return
  fig.classList.toggle('missions__figure--ready', ok)
  fig.classList.toggle('missions__figure--broken', !ok)
}

function syncImage(img: HTMLImageElement) {
  if (!img.complete) return
  markFigure(img, img.naturalWidth > 0)
}

export function bindMissionImages(root: HTMLElement): () => void {
  function onLoad(e: Event) {
    const t = e.target
    if (!(t instanceof HTMLImageElement)) return
    if (!t.closest('.missions__figure')) return
    markFigure(t, t.naturalWidth > 0)
  }

  function onError(e: Event) {
    const t = e.target
    if (!(t instanceof HTMLImageElement)) return
    if (!t.closest('.missions__figure')) return
    markFigure(t, false)
  }

  function syncExisting() {
    root
      .querySelectorAll<HTMLImageElement>('.missions__figure img')
      .forEach(syncImage)
  }

  root.addEventListener('load', onLoad, true)
  root.addEventListener('error', onError, true)
  syncExisting()
  const mo = new MutationObserver(syncExisting)
  mo.observe(root, { childList: true, subtree: true })
  return () => {
    root.removeEventListener('load', onLoad, true)
    root.removeEventListener('error', onError, true)
    mo.disconnect()
  }
}
