import { useState, useEffect } from 'react'
import * as feedbackApi from '../api/feedback'

export default function FeedbackReportsPage() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    feedbackApi
      .getFeedbackReports()
      .then((list) => {
        if (!cancelled) setReports(list)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message || 'Failed to load reports')
          setReports([])
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Issue reports & feedback</h1>
        <p className="text-sm text-surface-600 mt-1">Submissions from the Report Issue form (newest first).</p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}
        </div>
      )}
      {loading && <p className="text-surface-500 text-sm">Loading…</p>}

      {!loading && !error && reports.length === 0 && (
        <p className="text-surface-500 text-sm">No reports yet.</p>
      )}

      {!loading && reports.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-surface-200 bg-white shadow-sm">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-surface-200 bg-surface-50">
                <th className="px-4 py-3 font-medium text-surface-700">Submitted</th>
                <th className="px-4 py-3 font-medium text-surface-700">User ID</th>
                <th className="px-4 py-3 font-medium text-surface-700">Name</th>
                <th className="px-4 py-3 font-medium text-surface-700">Email</th>
                <th className="px-4 py-3 font-medium text-surface-700">Message</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} className="border-b border-surface-100 align-top">
                  <td className="px-4 py-3 text-surface-800 whitespace-nowrap">{r.created_at || '—'}</td>
                  <td className="px-4 py-3 text-surface-600">{r.user_id != null ? r.user_id : '—'}</td>
                  <td className="px-4 py-3 text-surface-800">{r.name || '—'}</td>
                  <td className="px-4 py-3 text-surface-800">{r.email || '—'}</td>
                  <td className="px-4 py-3 text-surface-700 max-w-md whitespace-pre-wrap break-words">
                    {r.message || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
