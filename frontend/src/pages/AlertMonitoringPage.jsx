import { useState, useEffect, useMemo } from 'react'
import * as dashboardApi from '../api/dashboard'

function formatStatus(s) {
  if (!s) return '—'
  const v = String(s).toLowerCase().replace(/_/g, ' ')
  if (v === 'clean') return 'Clean'
  if (v === 'slightly polluted') return 'Slightly Polluted'
  if (v === 'polluted') return 'Polluted'
  return v
}

export default function AlertMonitoringPage() {
  const [stations, setStations] = useState([])
  const [historicalAlerts, setHistoricalAlerts] = useState([])
  const [forecastAlerts, setForecastAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filters
  const [stationFilter, setStationFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('') // '' | slightly_polluted | polluted
  const [typeFilter, setTypeFilter] = useState('all') // all | historical | forecast

  useEffect(() => {
    let cancelled = false
    async function loadStations() {
      try {
        const list = await dashboardApi.getStations()
        if (!cancelled) setStations(Array.isArray(list) ? list : [])
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
      if (stationFilter && name !== stationFilter) return false
      if (statusFilter && a.river_status !== statusFilter) return false
      return true
    })
  }, [historicalAlerts, stationFilter, statusFilter])

  const filteredForecast = useMemo(() => {
    return forecastAlerts.filter((a) => {
      const name = a.station_name || a.station_code || ''
      if (stationFilter && name !== stationFilter) return false
      if (statusFilter && a.river_status !== statusFilter) return false
      return true
    })
  }, [forecastAlerts, stationFilter, statusFilter])

  const allAlerts = [...filteredHistorical, ...filteredForecast]
  const slightlyCount = allAlerts.filter((a) => a.river_status === 'slightly_polluted').length
  const pollutedCount = allAlerts.filter((a) => a.river_status === 'polluted').length

  const hasNoAlerts = !loading && filteredHistorical.length === 0 && filteredForecast.length === 0

  const showHistorical = typeFilter === 'all' || typeFilter === 'historical'
  const showForecast = typeFilter === 'all' || typeFilter === 'forecast'

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Alert monitoring</h1>
        <p className="text-surface-600 mt-0.5">
          Alerts are generated when the latest monitoring state or forecast prediction is Slightly Polluted or Polluted.
        </p>
        <div className="text-sm text-surface-500 mt-2">
          <div>Data Source: Historical, Simulated Live, Forecast</div>
          <div>Last Updated: {new Date().toLocaleString()}</div>
        </div>
      </div>

      <div className="rounded-lg border border-dashed border-surface-200 bg-surface-50 px-4 py-3">
        <p className="text-sm text-surface-600">
          Message rules: Slightly Polluted → <span className="font-medium">Monitor closely</span>, Polluted → <span className="font-medium">Immediate attention required</span>.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure the backend is running.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading alerts…</p>}

      {/* Filters */}
      <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="label">Station</label>
            <select
              value={stationFilter}
              onChange={(e) => setStationFilter(e.target.value)}
              className="input-field w-auto min-w-[220px]"
            >
              <option value="">All stations</option>
              {stations.map((s) => {
                const v = s.station_name || s.station_code
                return (
                  <option key={s.station_code || s.station_name} value={v}>
                    {v}
                  </option>
                )
              })}
            </select>
          </div>
          <div>
            <label className="label">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input-field w-auto min-w-[180px]"
            >
              <option value="">All statuses</option>
              <option value="slightly_polluted">Slightly Polluted</option>
              <option value="polluted">Polluted</option>
            </select>
          </div>
          <div>
            <label className="label">Type</label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="input-field w-auto min-w-[180px]"
            >
              <option value="all">Historical + Forecast</option>
              <option value="historical">Historical</option>
              <option value="forecast">Forecast</option>
            </select>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm font-medium text-amber-800">Monitor closely</p>
            <p className="text-2xl font-bold text-amber-700 mt-1">{slightlyCount}</p>
            <p className="text-xs text-amber-700/80 mt-1">Slightly Polluted</p>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-sm font-medium text-red-800">Immediate attention</p>
            <p className="text-2xl font-bold text-red-700 mt-1">{pollutedCount}</p>
            <p className="text-xs text-red-700/80 mt-1">Polluted</p>
          </div>
        </div>
      </div>

      {hasNoAlerts && (
        <div className="rounded-xl border border-surface-200 bg-white p-8 text-center">
          <p className="text-surface-600 font-medium">No alerts detected.</p>
          <p className="text-sm text-surface-500 mt-2">Try changing filters.</p>
        </div>
      )}

      {/* Historical Alerts */}
      {showHistorical && (
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
          <h2 className="font-display font-semibold text-surface-800 mb-2">Historical alerts</h2>
          <p className="text-sm text-surface-500 mb-4">From latest monitoring state per station. Sorted by date (newest first).</p>
          <div className="overflow-x-auto rounded-lg border border-surface-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-100 text-left">
                  <th className="px-4 py-2 font-medium text-surface-700">Station name</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                  <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Status</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Message</th>
                </tr>
              </thead>
              <tbody>
                {!loading && filteredHistorical.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">No historical alerts</td></tr>
                ) : (
                  filteredHistorical.map((a, i) => (
                    <tr key={`${a.station_name || a.station_code}-${a.date}-${i}`} className="border-t border-surface-100">
                      <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
                      <td className="px-4 py-2 text-surface-800">{a.date || '—'}</td>
                      <td className="px-4 py-2">{a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}</td>
                      <td className="px-4 py-2">{formatStatus(a.river_status)}</td>
                      <td className="px-4 py-2 text-surface-700 max-w-xs">{a.message || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Forecast Alerts */}
      {showForecast && (
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
          <h2 className="font-display font-semibold text-surface-800 mb-2">Forecast alerts</h2>
          <p className="text-sm text-surface-500 mb-4">From future prediction points. Sorted by forecast date (earliest first).</p>
          <div className="overflow-x-auto rounded-lg border border-surface-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-100 text-left">
                  <th className="px-4 py-2 font-medium text-surface-700">Station name</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Forecast date</th>
                  <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Status</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Message</th>
                </tr>
              </thead>
              <tbody>
                {!loading && filteredForecast.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">No forecast alerts</td></tr>
                ) : (
                  filteredForecast.map((a, i) => (
                    <tr key={`${a.station_name || a.station_code}-${a.date}-${i}`} className="border-t border-surface-100">
                      <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
                      <td className="px-4 py-2 text-surface-800">{a.date || '—'}</td>
                      <td className="px-4 py-2">{a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}</td>
                      <td className="px-4 py-2">{formatStatus(a.river_status)}</td>
                      <td className="px-4 py-2 text-surface-700 max-w-xs">{a.message || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
