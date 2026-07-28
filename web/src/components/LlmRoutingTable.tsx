import { useEffect, useState } from 'react'
import { apiLlmRouting, type LlmRouting } from '../api'

/** Short slug for display (last segment). */
function shortModel(slug: string): string {
  const parts = slug.split('/')
  return parts[parts.length - 1] || slug
}

export function LlmRoutingTable() {
  const [data, setData] = useState<LlmRouting | null>(null)

  useEffect(() => {
    let cancelled = false
    void apiLlmRouting().then((d) => {
      if (!cancelled) setData(d)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (!data) {
    return <p className="muted more-drawer__usage-empty">…</p>
  }

  return (
    <div className="llm-routing">
      <table className="llm-routing__table">
        <thead>
          <tr>
            <th>Rol</th>
            <th>Modelo</th>
            <th>Precio ~/1M</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.role}>
              <td>
                <span className="llm-routing__role">{row.role}</span>
                <span className="llm-routing__uses muted">{row.uses}</span>
              </td>
              <td>
                <code className="llm-routing__model" title={row.model}>
                  {shortModel(row.model)}
                </code>
              </td>
              <td className="llm-routing__price">
                {row.price_in} / {row.price_out}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.notes.length > 0 ? (
        <ul className="llm-routing__notes muted">
          {data.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
