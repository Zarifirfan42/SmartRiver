import { useState, useEffect } from 'react'
import * as feedbackApi from '../api/feedback'

export default function FeedbackReportsPage() {
  const [reports, setReports] = useState([])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [readStatus, setReadStatus] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const loadReports = async (
    cancelledRef = { value: false },
    filters = { dateFrom, dateTo, name, email, readStatus }
  ) => {
    setLoading(true)
    setError(null)
    try {
      const list = await feedbackApi.getFeedbackReportsFiltered({
        dateFrom: filters.dateFrom,
        dateTo: filters.dateTo,
        name: filters.name,
        email: filters.email,
        readStatus: filters.readStatus,
        limit: 1000,
      })
      if (!cancelledRef.value) setReports(list)
    } catch (err) {
      if (!cancelledRef.value) {
        setError(err.response?.data?.detail || err.message || 'Failed to load reports')
        setReports([])
      }
    } finally {
      if (!cancelledRef.value) setLoading(false)
    }
  }

  useEffect(() => {
    const cancelledRef = { value: false }
    loadReports(cancelledRef)
    return () => {
      cancelledRef.value = true
    }
  }, [])

  const onSearch = async (e) => {
    e.preventDefault()
    await loadReports()
  }

  const onReset = async () => {
    setDateFrom('')
    setDateTo('')
    setName('')
    setEmail('')
    setReadStatus('all')
    await loadReports({ value: false }, {
      dateFrom: '',
      dateTo: '',
      name: '',
      email: '',
      readStatus: 'all',
    })
  }

  const onToggleRead = async (report) => {
    setBusyId(report.id)
    setError(null)
    try {
      const updated = await feedbackApi.markFeedbackRead(report.id, !report.is_read)
      setReports((prev) => prev.map((r) => (r.id === report.id ? { ...r, ...updated } : r)))
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to update read status')
    } finally {
      setBusyId(null)
    }
  }

  const onDelete = async (report) => {
    const ok = window.confirm(`Delete issue report #${report.id}? This cannot be undone.`)
    if (!ok) return
    setBusyId(report.id)
    setError(null)
    try {
      await feedbackApi.deleteFeedbackReport(report.id)
      setReports((prev) => prev.filter((r) => r.id !== report.id))
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete report')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Issue reports & feedback</h1>
        <p className="text-sm text-surface-600 mt-1">Submissions from the Report Issue form. Filter, mark as read, and delete.</p>
      </div>

      <form onSubmit={onSearch} className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          <div>
            <label className="label">From date</label>
            <input type="date" className="input-field w-full" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <label className="label">To date</label>
            <input type="date" className="input-field w-full" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div>
            <label className="label">Name</label>
            <input type="text" className="input-field w-full" placeholder="Search name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Email</label>
            <input type="text" className="input-field w-full" placeholder="Search email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label">Status</label>
            <select className="input-field w-full" value={readStatus} onChange={(e) => setReadStatus(e.target.value)}>
              <option value="all">All</option>
              <option value="unread">Unread</option>
              <option value="read">Read</option>
            </select>
          </div>
        </div>
        <div className="mt-3 flex gap-2">
          <button type="submit" className="btn-primary" disabled={loading}>Apply filters</button>
          <button type="button" className="btn-secondary" onClick={onReset} disabled={loading}>Reset</button>
        </div>
      </form>

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
                <th className="px-4 py-3 font-medium text-surface-700">Status</th>
                <th className="px-4 py-3 font-medium text-surface-700">Actions</th>
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
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${r.is_read ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                      {r.is_read ? 'Read' : 'Unread'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn-secondary text-xs px-2 py-1"
                        onClick={() => onToggleRead(r)}
                        disabled={busyId === r.id}
                      >
                        {r.is_read ? 'Mark unread' : 'Mark read'}
                      </button>
                      <button
                        type="button"
                        className="text-xs rounded-md border border-red-200 bg-red-50 px-2 py-1 font-medium text-red-700 hover:bg-red-100 disabled:opacity-60"
                        onClick={() => onDelete(r)}
                        disabled={busyId === r.id}
                      >
                        Delete
                      </button>
                    </div>
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
