import { useState, useEffect, useCallback } from 'react'
import * as warningsApi from '../api/warnings'

export default function AdminWarningsPage() {
  const [message, setMessage] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const list = await warningsApi.listAdminWarnings()
      setItems(Array.isArray(list) ? list : [])
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const m = message.trim()
    if (m.length < 3) {
      setError('Message must be at least 3 characters.')
      return
    }
    setSaving(true)
    try {
      await warningsApi.postAdminWarning(m)
      setMessage('')
      await load()
    } catch (err) {
      const d = err.response?.data?.detail
      setError(Array.isArray(d) ? d[0] : d || err.message || 'Failed to post')
    } finally {
      setSaving(false)
    }
  }

  const handleDeactivate = async (id) => {
    try {
      await warningsApi.deactivateWarning(id)
      await load()
    } catch {
      setError('Could not deactivate notice.')
    }
  }

  return (
    <div className="space-y-6 max-w-3xl animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Public notices</h1>
        <p className="text-surface-600 mt-1 text-sm">
          Post a short official message (e.g. pollution incident). It appears as a banner at the top of every page for all signed-in users until you deactivate it.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-4">
        {error && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        <div>
          <label htmlFor="notice" className="label">Notice text</label>
          <textarea
            id="notice"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="input-field min-h-[120px]"
            placeholder="e.g. Pollution incident reported at Sungai Klang — avoid water contact until further notice."
            maxLength={2000}
          />
        </div>
        <button type="submit" disabled={saving} className="btn-primary">
          {saving ? 'Publishing…' : 'Publish notice'}
        </button>
      </form>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-3">All notices</h2>
        {loading ? <p className="text-surface-500 text-sm">Loading…</p> : null}
        {!loading && items.length === 0 ? (
          <p className="text-surface-500 text-sm">No notices yet.</p>
        ) : (
          <ul className="divide-y divide-surface-100">
            {items.map((w) => (
              <li key={w.id} className="py-3 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                <div>
                  <p className="text-surface-900 text-sm">{w.message}</p>
                  <p className="text-xs text-surface-500 mt-1">
                    {w.created_at ? new Date(w.created_at).toLocaleString() : ''}
                    {' · '}
                    <span className={w.is_active ? 'text-amber-700 font-medium' : 'text-surface-400'}>
                      {w.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </p>
                </div>
                {w.is_active ? (
                  <button
                    type="button"
                    onClick={() => handleDeactivate(w.id)}
                    className="text-sm font-medium text-red-600 hover:text-red-700 shrink-0"
                  >
                    Deactivate
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
