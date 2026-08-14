/** Citas de motivación que rotan cada día en la vista Día. */

export type Quote = {
  text: string
  author?: string
}

const QUOTES: Quote[] = [
  { text: 'Los pequeños pasos también avanzan', author: 'Kore' },
  { text: 'Hoy es un buen día para empezar', author: 'Kore' },
  { text: 'Constancia sobre intensidad, cada día un poco mejor' },
  { text: 'No compares tu día uno con el día cien de nadie' },
  { text: 'La disciplina gana cuando el ánimo se agota' },
  { text: 'Haz de hoy un ladrillo firme para mañana' },
  { text: 'Primero el primer paso, el resto viene solo' },
  { text: 'Una cosa a la vez, hecha bien', author: 'Kore' },
  { text: 'Los hábitos se notan a la décima repetición' },
  { text: 'Avanza aunque sea un metro, no te quedes quieto' },
  { text: 'El foco es el superpoder de los días normales' },
  { text: 'Terminar lo empezado vale más que empezar lo nuevo' },
  { text: 'La energía sigue a la acción, no al revés' },
  { text: 'Cada tarea cerrada es un poco de despeje mental' },
  { text: 'Confía en el proceso, no en el golpe de suerte' },
]

/** Devuelve la cita del día, estable a lo largo de la misma jornada. */
export function dailyQuote(dayIso: string): Quote {
  let hash = 0
  const s = dayIso || String(new Date().getDate())
  for (let i = 0; i < s.length; i++) {
    hash = (hash << 5) - hash + s.charCodeAt(i)
    hash |= 0
  }
  const idx = ((hash % QUOTES.length) + QUOTES.length) % QUOTES.length
  return QUOTES[idx]
}
