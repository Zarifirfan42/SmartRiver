import { useState, useEffect, useMemo } from 'react'
import AlertsBySeverityChart from '../components/charts/AlertsBySeverityChart'
import * as dashboardApi from '../api/dashboard'

const CATEGORY_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'clean', label: 'Clean' },
  { value: 'slightly_polluted', label: 'Slightly Polluted' },
  { value: 'polluted', label: 'Polluted' },
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

export default function AlertMonitoringPage() {
  const [stations, setStations] = useState([])
  const [historicalAlerts, setHistoricalAlerts] = useState([])
  const [forecastAlerts, setForecastAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [histStation, setHistStation] = useState('')
  const [histCategory, setHistCategory] = useState('')
  const [fcStation, setFcStation] = useState('')
  const [fcCategory, setFcCategory] = useState('')

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
      return true
    })
  }, [historicalAlerts, histStation, histCategory])

  const filteredForecast = useMemo(() => {
    return forecastAlerts.filter((a) => {
      const name = a.station_name || a.station_code || ''
      if (fcStation && name !== fcStation) return false
      const status = normalizeStatusForFilter(a.river_status)
      if (fcCategory && status !== fcCategory) return false
      return true
    })
  }, [forecastAlerts, fcStation, fcCategory])

  const allAlerts = [...filteredHistorical, ...filteredForecast]

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Alert monitoring</h1>
        <p className="text-surface-600 mt-0.5">Historical alerts (latest monitoring) and forecast alerts (predictions)</p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure the backend is running.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading alerts…</p>}

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Alerts by severity</h2>
        <AlertsBySeverityChart alerts={allAlerts} height={220} />
      </div>

      {/* Historical Alerts — latest monitoring; filters + table */}
      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Historical alerts</h2>
        <p className="text-sm text-surface-500 mb-4">From latest monitoring data per station. Triggered when status is Slightly Polluted or Polluted. Sorted by date (newest first).</p>
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
              className="input-field w-auto min-w-[180px]"
            >
              {CATEGORY_OPTIONS.map((opt) => (
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
              </tr>
            </thead>
            <tbody>
              {!loading && filteredHistorical.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">No historical alerts</td></tr>
              ) : (
                filteredHistorical.map((a) => (
                  <tr key={`hist-${a.id}`} className="border-t border-surface-100">
                    <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
                    <td className="px-4 py-2 text-surface-800">{a.date || '—'}</td>
                    <td className="px-4 py-2">{a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}</td>
                    <td className="px-4 py-2">{formatStatus(a.river_status)}</td>
                    <td className="px-4 py-2">{alertLevel(a.severity)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forecast Alerts — filters + table */}
      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Forecast alerts</h2>
        <p className="text-sm text-surface-500 mb-4">From forecast predictions. Triggered when predicted status is Slightly Polluted or Polluted. Sorted by forecast date (earliest first).</p>
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
              className="input-field w-auto min-w-[180px]"
            >
              {CATEGORY_OPTIONS.map((opt) => (
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
              </tr>
            </thead>
            <tbody>
              {!loading && filteredForecast.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">No forecast alerts</td></tr>
              ) : (
                filteredForecast.map((a) => (
                  <tr key={`fc-${a.id}`} className="border-t border-surface-100">
                    <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
                    <td className="px-4 py-2 text-surface-800">{a.date || '—'}</td>
                    <td className="px-4 py-2">{a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}</td>
                    <td className="px-4 py-2">{formatStatus(a.river_status)}</td>
                    <td className="px-4 py-2">{alertLevel(a.severity)}</td>
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
