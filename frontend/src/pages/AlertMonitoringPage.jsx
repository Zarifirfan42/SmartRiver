import { useState } from 'react'
import RiverHealthIndicator from '../components/dashboard/RiverHealthIndicator'

const mockAlerts = [
  { id: 1, station_code: 'S03', station_name: 'Sungai Pinang', message: 'WQI dropped below 50', date: '2025-03-01T10:30:00', severity: 'critical', wqi: 48, read: false },
  { id: 2, station_code: 'S01', station_name: 'Sungai Klang', message: 'Unusual BOD spike detected', date: '2025-02-28T14:00:00', severity: 'warning', wqi: 65, read: true },
  { id: 3, station_code: 'S05', station_name: 'Sungai Perak', message: 'Anomaly in NH3-N', date: '2025-02-25T09:15:00', severity: 'info', wqi: 62, read: false },
]

const severityStyles = {
  critical: 'border-red-200 bg-red-50',
  warning: 'border-amber-200 bg-amber-50',
  info: 'border-river-200 bg-river-50',
}

export default function AlertMonitoringPage() {
  const [filter, setFilter] = useState('all') // all | unread

  const list = filter === 'unread'
    ? mockAlerts.filter((a) => !a.read)
    : mockAlerts

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

      <div className="space-y-3">
        {list.length === 0 ? (
          <div className="card text-center py-12 text-surface-500">No alerts</div>
        ) : (
          list.map((alert) => (
            <div
              key={alert.id}
              className={`card ${severityStyles[alert.severity]} ${!alert.read ? 'ring-1 ring-river-200' : ''}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-semibold text-surface-800">{alert.station_name} ({alert.station_code})</p>
                  <p className="text-surface-600 mt-1">{alert.message}</p>
                  <p className="text-sm text-surface-500 mt-2">{new Date(alert.date).toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-3">
                  <RiverHealthIndicator wqi={alert.wqi} compact />
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
