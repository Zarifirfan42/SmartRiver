import { useState, useEffect } from 'react'
import RiverHealthIndicator from '../components/dashboard/RiverHealthIndicator'
import AlertsBySeverityChart from '../components/charts/AlertsBySeverityChart'
import * as dashboardApi from '../api/dashboard'

const severityStyles = {
  critical: 'border-red-200 bg-red-50',
  warning: 'border-amber-200 bg-amber-50',
  info: 'border-river-200 bg-river-50',
}

function normalizeAlert(a) {
  return {
    id: a.id,
    station_code: a.station_code,
    station_name: a.station_name || a.station_code,
    message: a.message || 'Anomaly detected',
    date: a.date || a.created_at,
    severity: (a.severity || 'info').toLowerCase(),
    wqi: a.wqi,
    read: a.read ?? a.is_read ?? false,
  }
}

export default function AlertMonitoringPage() {
  const [filter, setFilter] = useState('all') // all | unread
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function fetchAlerts() {
      setLoading(true)
      setError(null)
      try {
        const items = await dashboardApi.getAlerts({ limit: 100 })
        if (!cancelled) setAlerts(Array.isArray(items) ? items.map(normalizeAlert) : [])
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load alerts')
          setAlerts([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchAlerts()
    return () => { cancelled = true }
  }, [])

  const list = filter === 'unread'
    ? alerts.filter((a) => !a.read)
    : alerts

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-900">Alert monitoring</h1>
          <p className="text-surface-600 mt-0.5">Early warnings from anomaly detection</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${filter === 'all' ? 'bg-river-600 text-white' : 'bg-surface-100 text-surface-700'}`}
          >
            All
          </button>
          <button
            type="button"
            onClick={() => setFilter('unread')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${filter === 'unread' ? 'bg-river-600 text-white' : 'bg-surface-100 text-surface-700'}`}
          >
            Unread
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure the backend is running.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading alerts…</p>}

      {/* Alerts by severity — meaningful visualization for FYP demo */}
      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Alerts by severity</h2>
        <AlertsBySeverityChart alerts={alerts} height={220} />
      </div>

      <div className="space-y-3">
        {!loading && list.length === 0 ? (
          <div className="card text-center py-12 text-surface-500">No alerts</div>
        ) : (
          list.map((alert) => (
            <div
              key={alert.id}
              className={`card ${severityStyles[alert.severity] || severityStyles.info} ${!alert.read ? 'ring-1 ring-river-200' : ''}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-semibold text-surface-800">{alert.station_name} ({alert.station_code})</p>
                  <p className="text-surface-600 mt-1">{alert.message}</p>
                  <p className="text-sm text-surface-500 mt-2">{alert.date ? new Date(alert.date).toLocaleString() : '—'}</p>
                </div>
                <div className="flex items-center gap-3">
                  {alert.wqi != null && <RiverHealthIndicator wqi={alert.wqi} compact />}
                  {!alert.read && <span className="text-xs font-medium text-river-600">New</span>}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
