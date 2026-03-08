import { Link } from 'react-router-dom'
import RiverHealthIndicator from './RiverHealthIndicator'

const severityStyles = {
  critical: 'border-red-200 bg-red-50',
  warning: 'border-amber-200 bg-amber-50',
  info: 'border-river-200 bg-river-50',
}

export default function AnomalyAlerts({ alerts = [], maxItems = 5 }) {
  const list = alerts.slice(0, maxItems)

  return (
    <div className="space-y-2">
      {list.length === 0 ? (
        <p className="text-sm text-surface-500 py-2">No recent anomalies</p>
      ) : (
        list.map((alert) => (
          <div
            key={alert.id || alert.date + alert.station_code}
            className={`rounded-lg border p-3 text-sm ${severityStyles[alert.severity] || severityStyles.info}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-medium text-surface-800">{alert.station_code || 'Station'}</p>
                <p className="text-surface-600 mt-0.5">{alert.message || 'Unusual WQI detected'}</p>
                <p className="text-surface-500 text-xs mt-1">{alert.date || alert.created_at}</p>
              </div>
              <RiverHealthIndicator wqi={alert.wqi} compact />
            </div>
          </div>
        ))
      )}
      {alerts.length > maxItems && (
        <Link
          to="/alerts"
          className="block text-center text-sm font-medium text-river-600 hover:text-river-700 py-1"
        >
          View all alerts →
        </Link>
      )}
    </div>
  )
}
