import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import AlertsBySeverityChart from '../components/charts/AlertsBySeverityChart'
import * as dashboardApi from '../api/dashboard'

const CATEGORY_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'clean', label: 'Clean' },
  { value: 'slightly_polluted', label: 'Slightly Polluted' },
  { value: 'polluted', label: 'Polluted' },
]

const ALERT_LEVEL_OPTIONS = [
  { value: '', label: 'All levels' },
  { value: 'warning', label: 'Warning' },
  { value: 'critical', label: 'Critical' },
]

function formatStatus(s) {
  if (!s) return '—'
  const v = String(s).toLowerCase().replace(/_/g, ' ')
  if (v === 'clean') return 'Clean'
  if (v === 'slightly polluted' || v === 'slightly_polluted') return 'Slightly Polluted'
  if (v === 'polluted') return 'Polluted'
  return v
}

function normalizeStatusForFilter(s) {
  if (!s) return ''
  const v = String(s).toLowerCase().replace(/\s+/g, '_')
  if (v === 'clean') return 'clean'
  if (v === 'slightly_polluted' || v === 'slightly polluted') return 'slightly_polluted'
  if (v === 'polluted') return 'polluted'
  return v
}

function alertLevel(severity) {
  const s = (severity || '').toLowerCase()
  if (s === 'critical') return 'Critical'
  if (s === 'warning') return 'Warning'
  return severity || '—'
}

/** Human-readable alert message. Uses backend message or builds from fields. */
function alertMessage(alert, isForecast) {
  if (alert.message && String(alert.message).trim()) return alert.message.trim()
  const name = alert.station_name || alert.station_code || 'Unknown'
  const status = formatStatus(alert.river_status)
  const wqi = alert.wqi != null ? Number(alert.wqi).toFixed(1) : '—'
  const dateStr = alert.date || ''
  let when = dateStr
  if (dateStr && dateStr.length >= 7) {
    try {
      const [y, m] = dateStr.split('-')
      const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
      when = `${months[parseInt(m, 10) - 1] || m} ${y}`
    } catch (_) {}
  }
  if (isForecast) {
    return `${name} is predicted to become ${status.toLowerCase()} in ${when || 'future'}.`
  }
  return `${name} is ${status.toLowerCase()} (WQI: ${wqi}) on ${when || dateStr || '—'}.`
}

/** Row background by alert level: Warning = orange, Critical = red */
function rowClassByLevel(severity) {
  const s = (severity || '').toLowerCase()
  if (s === 'critical') return 'bg-red-50 hover:bg-red-100/80 border-l-4 border-red-400'
  if (s === 'warning') return 'bg-amber-50 hover:bg-amber-100/80 border-l-4 border-amber-400'
  return 'hover:bg-surface-50 border-l-4 border-transparent'
}

export default function AlertMonitoringPage() {
  const [stations, setStations] = useState([])
  const [historicalAlerts, setHistoricalAlerts] = useState([])
  const [forecastAlerts, setForecastAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [histStation, setHistStation] = useState('')
  const [histCategory, setHistCategory] = useState('')
  const [histAlertLevel, setHistAlertLevel] = useState('')
  const [fcStation, setFcStation] = useState('')
  const [fcCategory, setFcCategory] = useState('')
  const [fcAlertLevel, setFcAlertLevel] = useState('')

  useEffect(() => {
    let cancelled = false
    async function loadStations() {
      try {
        const list = await dashboardApi.getStations()
        if (!cancelled && Array.isArray(list)) setStations(list)
      } catch {
        if (!cancelled) setStations([])
      }
    }
    loadStations()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function fetchAlerts() {
      setLoading(true)
      setError(null)
      try {
        const { historical, forecast } = await dashboardApi.getAlertsByType({ limit: 500 })
        if (!cancelled) {
          setHistoricalAlerts(Array.isArray(historical) ? historical : [])
          setForecastAlerts(Array.isArray(forecast) ? forecast : [])
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load alerts')
          setHistoricalAlerts([])
          setForecastAlerts([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchAlerts()
    return () => { cancelled = true }
  }, [])

  const filteredHistorical = useMemo(() => {
    return historicalAlerts.filter((a) => {
      const name = a.station_name || a.station_code || ''
      if (histStation && name !== histStation) return false
      const status = normalizeStatusForFilter(a.river_status)
      if (histCategory && status !== histCategory) return false
      const sev = (a.severity || '').toLowerCase()
      if (histAlertLevel && sev !== histAlertLevel) return false
      return true
    })
  }, [historicalAlerts, histStation, histCategory, histAlertLevel])

  const filteredForecast = useMemo(() => {
    return forecastAlerts.filter((a) => {
      const name = a.station_name || a.station_code || ''
      if (fcStation && name !== fcStation) return false
      const status = normalizeStatusForFilter(a.river_status)
      if (fcCategory && status !== fcCategory) return false
      const sev = (a.severity || '').toLowerCase()
      if (fcAlertLevel && sev !== fcAlertLevel) return false
      return true
    })
  }, [forecastAlerts, fcStation, fcCategory, fcAlertLevel])

  const allAlerts = [...filteredHistorical, ...filteredForecast]
  const warningCount = allAlerts.filter((a) => (a.severity || '').toLowerCase() === 'warning').length
  const criticalCount = allAlerts.filter((a) => (a.severity || '').toLowerCase() === 'critical').length
  const hasNoAlerts = !loading && filteredHistorical.length === 0 && filteredForecast.length === 0

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Alert monitoring</h1>
        <p className="text-surface-600 mt-0.5">Historical alerts (latest monitoring) and forecast alerts (predictions). Slightly Polluted → Warning; Polluted → Critical.</p>
      </div>

      <div className="rounded-lg border border-dashed border-surface-200 bg-surface-50 px-4 py-3">
        <p className="text-sm text-surface-600">
          Alerts are automatically generated when river conditions are slightly polluted or polluted based on the latest
          monitoring data and forecast predictions.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure the backend is running.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading alerts…</p>}

      {/* Alert summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 shadow-sm">
          <p className="text-sm font-medium text-amber-800">Warning</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">
            <span className="mr-2" aria-hidden>⚠️</span>
            {warningCount}
          </p>
          <p className="text-xs text-amber-700/80 mt-1">Slightly Polluted</p>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50/80 p-4 shadow-sm">
          <p className="text-sm font-medium text-red-800">Critical</p>
          <p className="text-2xl font-bold text-red-700 mt-1">
            <span className="mr-2" aria-hidden>🚨</span>
            {criticalCount}
          </p>
          <p className="text-xs text-red-700/80 mt-1">Polluted</p>
        </div>
      </div>

      {hasNoAlerts && (
        <div className="rounded-xl border border-surface-200 bg-white p-8 text-center">
          <p className="text-surface-600 font-medium">No alerts detected. All rivers are in good condition.</p>
          <p className="text-sm text-surface-500 mt-2">Alerts will appear here when monitoring or forecast data indicates Slightly Polluted or Polluted status.</p>
        </div>
      )}

      <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Alerts by severity</h2>
        {allAlerts.length > 0 ? (
          <AlertsBySeverityChart alerts={allAlerts} height={220} />
        ) : (
          <div className="h-[220px] flex items-center justify-center text-surface-500 text-sm">No alerts to display.</div>
        )}
      </div>

      {/* Historical Alerts — sorted latest first */}
      <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-2">Historical alerts</h2>
        <p className="text-sm text-surface-500 mb-4">From latest monitoring data per station. Sorted by date (newest first).</p>
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="label">Station name</label>
            <select
              value={histStation}
              onChange={(e) => setHistStation(e.target.value)}
              className="input-field w-auto min-w-[200px]"
            >
              <option value="">All stations</option>
              {stations.map((s) => (
                <option key={s.station_code || s.station_name} value={s.station_name || s.station_code}>
                  {s.station_name || s.station_code}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">River condition</label>
            <select
              value={histCategory}
              onChange={(e) => setHistCategory(e.target.value)}
              className="input-field w-auto min-w-[160px]"
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Alert level</label>
            <select
              value={histAlertLevel}
              onChange={(e) => setHistAlertLevel(e.target.value)}
              className="input-field w-auto min-w-[140px]"
            >
              {ALERT_LEVEL_OPTIONS.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="overflow-x-auto rounded-lg border border-surface-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-100 text-left">
                <th className="px-4 py-2 font-medium text-surface-700">Station name</th>
                <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                <th className="px-4 py-2 font-medium text-surface-700">River status</th>
                <th className="px-4 py-2 font-medium text-surface-700">Alert level</th>
                <th className="px-4 py-2 font-medium text-surface-700">Alert message</th>
              </tr>
            </thead>
            <tbody>
              {!loading && filteredHistorical.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-surface-500">No historical alerts</td></tr>
              ) : (
                filteredHistorical.map((a) => (
                  <tr key={`hist-${a.id}`} className={`border-t border-surface-100 transition-colors ${rowClassByLevel(a.severity)}`}>
                    <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
                    <td className="px-4 py-2 text-surface-800">{a.date || '—'}</td>
                    <td className="px-4 py-2">{a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}</td>
                    <td className="px-4 py-2">{formatStatus(a.river_status)}</td>
                    <td className="px-4 py-2 font-medium">{alertLevel(a.severity)}</td>
                    <td className="px-4 py-2 text-surface-700 max-w-xs">{alertMessage(a, false)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forecast Alerts — sorted earliest first */}
      <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-2">Forecast alerts</h2>
        <p className="text-sm text-surface-500 mb-4">From forecast predictions. Sorted by forecast date (earliest first).</p>
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="label">Station name</label>
            <select
              value={fcStation}
              onChange={(e) => setFcStation(e.target.value)}
              className="input-field w-auto min-w-[200px]"
            >
              <option value="">All stations</option>
              {stations.map((s) => (
                <option key={s.station_code || s.station_name} value={s.station_name || s.station_code}>
                  {s.station_name || s.station_code}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">River condition</label>
            <select
              value={fcCategory}
              onChange={(e) => setFcCategory(e.target.value)}
              className="input-field w-auto min-w-[160px]"
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Alert level</label>
            <select
              value={fcAlertLevel}
              onChange={(e) => setFcAlertLevel(e.target.value)}
              className="input-field w-auto min-w-[140px]"
            >
              {ALERT_LEVEL_OPTIONS.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="overflow-x-auto rounded-lg border border-surface-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-100 text-left">
                <th className="px-4 py-2 font-medium text-surface-700">Station name</th>
                <th className="px-4 py-2 font-medium text-surface-700">Forecast date</th>
                <th className="px-4 py-2 font-medium text-surface-700">Predicted WQI</th>
                <th className="px-4 py-2 font-medium text-surface-700">Predicted status</th>
                <th className="px-4 py-2 font-medium text-surface-700">Alert level</th>
                <th className="px-4 py-2 font-medium text-surface-700">Alert message</th>
              </tr>
            </thead>
            <tbody>
              {!loading && filteredForecast.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-surface-500">No forecast alerts</td></tr>
              ) : (
                filteredForecast.map((a) => (
                  <tr key={`fc-${a.id}`} className={`border-t border-surface-100 transition-colors ${rowClassByLevel(a.severity)}`}>
                    <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
                    <td className="px-4 py-2 text-surface-800">{a.date || '—'}</td>
                    <td className="px-4 py-2">{a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}</td>
                    <td className="px-4 py-2">{formatStatus(a.river_status)}</td>
                    <td className="px-4 py-2 font-medium">{alertLevel(a.severity)}</td>
                    <td className="px-4 py-2 text-surface-700 max-w-xs">{alertMessage(a, true)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
