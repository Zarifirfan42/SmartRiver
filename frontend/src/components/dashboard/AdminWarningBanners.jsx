import { useEffect, useState } from 'react'
import * as dashboardApi from '../../api/dashboard'

export default function AdminWarningBanners() {
  const [items, setItems] = useState([])

  useEffect(() => {
    let cancelled = false
    dashboardApi
      .getActiveWarnings()
      .then((list) => {
        if (!cancelled) setItems(Array.isArray(list) ? list : [])
      })
      .catch(() => {
        if (!cancelled) setItems([])
      })
    const t = setInterval(() => {
      dashboardApi.getActiveWarnings().then((list) => {
        if (!cancelled) setItems(Array.isArray(list) ? list : [])
      }).catch(() => {})
    }, 120_000)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [])

  if (!items.length) return null

  return (
    <div className="space-y-2 mb-4" role="region" aria-label="Official notices">
      {items.map((w) => (
        <div
          key={w.id}
          className="rounded-xl border-l-4 border-amber-500 bg-gradient-to-r from-amber-50 to-white px-4 py-3 shadow-sm border border-amber-100"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-800 mb-1">Official notice</p>
          <p className="text-sm text-surface-900 leading-relaxed">{w.message}</p>
          {w.created_at && (
            <p className="text-xs text-surface-500 mt-2">Posted {new Date(w.created_at).toLocaleString()}</p>
          )}
        </div>
      ))}
    </div>
  )
}
