import { useState, useEffect, useMemo } from 'react'
import * as dashboardApi from '../api/dashboard'
import { SMARTRIVER_DATASET_CHANGED } from '../constants/datasetEvents'
import {
  countPollutedStations,
  countSlightlyPollutedStations,
} from '../utils/alertMonitoringWqi'

function formatStatus(s) {
  if (!s) return '—'
  const v = String(s).toLowerCase().replace(/_/g, ' ')
  if (v === 'clean') return 'Clean'
  if (v === 'slightly polluted') return 'Slightly Polluted'
  if (v === 'polluted') return 'Polluted'
  return v
}

/** Parse alert date to YYYY-MM-DD prefix when possible */
function alertDateYmd(dateStr) {
  if (!dateStr) return null
  const s = String(dateStr).trim().slice(0, 10)
  if (s.length < 10 || s[4] !== '-' || s[7] !== '-') return null
  return s
}

/** Chronological order for WQI alert rows: date ascending, then station (time-series friendly). */
function compareAlertsChronological(a, b) {
  const da = String(a.date || '').slice(0, 10)
  const db = String(b.date || '').slice(0, 10)
  if (da !== db) return da.localeCompare(db)
  const sa = String(a.station_name || a.station_code || '')
  const sb = String(b.station_name || b.station_code || '')
  return sa.localeCompare(sb)
}

/** Local calendar date as YYYY-MM-DD (matches typical backend reading_date strings). */
function localTodayYmd() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export default function AlertMonitoringPage() {
  const [stations, setStations] = useState([])
  const [historicalAlerts, setHistoricalAlerts] = useState([])
  const [forecastAlerts, setForecastAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filters — river aligned with backend river_name
  const [riverFilter, setRiverFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('') // '' | slightly_polluted | polluted
  const [typeFilter, setTypeFilter] = useState('all') // all | historical | forecast

  /** Forecast-only filters (full forecast list, not limited to today) */
  const [forecastStationFilter, setForecastStationFilter] = useState('')
  const [forecastYearFilter, setForecastYearFilter] = useState('')
  const [forecastMonthFilter, setForecastMonthFilter] = useState('') // '' or '1'..'12'
  /** Forecast alerts only: slightly polluted vs polluted */
  const [forecastStatusFilter, setForecastStatusFilter] = useState('')

  /** Re-render periodically so "today" rolls over at local midnight without a full refresh */
  const [clockTick, setClockTick] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setClockTick((t) => t + 1), 60_000)
    return () => window.clearInterval(id)
  }, [])

  /** Today's readings for WQI summary counts (local date, optional river filter) */
  const [todayReadings, setTodayReadings] = useState([])
  const [todayReadingsLoading, setTodayReadingsLoading] = useState(false)
  const [dataRevision, setDataRevision] = useState(0)

  const todayYmd = localTodayYmd()

  useEffect(() => {
    const bump = () => setDataRevision((n) => n + 1)
    window.addEventListener(SMARTRIVER_DATASET_CHANGED, bump)
    return () => window.removeEventListener(SMARTRIVER_DATASET_CHANGED, bump)
  }, [])

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
  }, [dataRevision])

  useEffect(() => {
    let cancelled = false
    async function fetchAlerts() {
      setLoading(true)
      setError(null)
      try {
        const { historical, forecast } = await dashboardApi.getAlertsByType({
          limit: 500,
          river_name: riverFilter || undefined,
        })
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
  }, [riverFilter, dataRevision])

  useEffect(() => {
    let cancelled = false
    setTodayReadingsLoading(true)
    dashboardApi
      .getReadingsTable({
        date_from: todayYmd,
        date_to: todayYmd,
        river_name: riverFilter || undefined,
        limit: 10000,
        offset: 0,
      })
      .then((rows) => {
        if (!cancelled) setTodayReadings(Array.isArray(rows) ? rows : [])
      })
      .catch(() => {
        if (!cancelled) setTodayReadings([])
      })
      .finally(() => {
        if (!cancelled) setTodayReadingsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [riverFilter, todayYmd, clockTick])

  const historicalToday = useMemo(() => {
    return historicalAlerts.filter((a) => alertDateYmd(a.date) === todayYmd)
  }, [historicalAlerts, todayYmd])

  const filteredHistorical = useMemo(() => {
    const filtered = historicalToday.filter((a) => {
      if (statusFilter) {
        const st = String(a.river_status || '').toLowerCase().replace(/\s+/g, '_')
        if (st !== statusFilter) return false
      }
      return true
    })
    return [...filtered].sort(compareAlertsChronological)
  }, [historicalToday, statusFilter])

  const forecastStationOptions = useMemo(() => {
    const map = new Map()
    forecastAlerts.forEach((a) => {
      const code = String(a.station_code || '').trim()
      const name = String(a.station_name || '').trim()
      const value = code || name
      if (!value) return
      const label =
        name && code && name !== code ? `${name} (${code})` : name || code
      if (!map.has(value)) map.set(value, label)
    })
    return [...map.entries()]
      .map(([value, label]) => ({ value, label }))
      .sort((x, y) => x.label.localeCompare(y.label))
  }, [forecastAlerts])

  /** Forecast horizon is capped at end of 2026 (no 2027+ in product policy). */
  const forecastYearOptions = useMemo(() => {
    const years = new Set(['2026'])
    forecastAlerts.forEach((a) => {
      const ymd = alertDateYmd(a.date)
      if (ymd) {
        const y = ymd.slice(0, 4)
        if (y <= '2026') years.add(y)
      }
    })
    return [...years].sort((a, b) => b.localeCompare(a))
  }, [forecastAlerts])

  const filteredForecast = useMemo(() => {
    const monthPadded =
      forecastMonthFilter === ''
        ? ''
        : String(Number(forecastMonthFilter)).padStart(2, '0')

    const list = forecastAlerts.filter((a) => {
      if (forecastStatusFilter) {
        const st = String(a.river_status || '').toLowerCase().replace(/\s+/g, '_')
        if (st !== forecastStatusFilter) return false
      }
      if (forecastStationFilter) {
        const key = String(a.station_code || a.station_name || '').trim()
        if (key !== forecastStationFilter) return false
      }
      const ymd = alertDateYmd(a.date)
      if (forecastYearFilter && (!ymd || ymd.slice(0, 4) !== forecastYearFilter)) return false
      if (monthPadded && (!ymd || ymd.slice(5, 7) !== monthPadded)) return false
      return true
    })
    return [...list].sort(compareAlertsChronological)
  }, [
    forecastAlerts,
    forecastStatusFilter,
    forecastStationFilter,
    forecastYearFilter,
    forecastMonthFilter,
  ])

  /** WQI-based counts: 60 ≤ WQI ≤ 80 vs WQI < 60 (from today’s readings). */
  const slightlyPollutedTodayCount = useMemo(
    () => countSlightlyPollutedStations(todayReadings),
    [todayReadings],
  )
  const pollutedTodayCount = useMemo(() => countPollutedStations(todayReadings), [todayReadings])

  const filtersActive = Boolean(
    riverFilter ||
      statusFilter ||
      forecastStationFilter ||
      forecastYearFilter ||
      forecastMonthFilter ||
      forecastStatusFilter,
  )
  const forecastFiltersActive = Boolean(
    forecastStationFilter ||
      forecastYearFilter ||
      forecastMonthFilter ||
      forecastStatusFilter,
  )
  const hasNoAlerts = !loading && filteredHistorical.length === 0 && filteredForecast.length === 0

  const showHistorical = typeFilter === 'all' || typeFilter === 'historical'
  const showForecast = typeFilter === 'all' || typeFilter === 'forecast'

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Alert monitoring</h1>
        <p className="text-surface-600 mt-0.5">
          <span className="font-medium text-surface-800">Monitoring (historical)</span> shows{' '}
          <span className="font-medium text-surface-800">today only</span> — alerts dated{' '}
          <span className="font-mono">{todayYmd}</span> (local date).{' '}
          <span className="font-medium text-surface-800">Forecast</span> lists future dates where the model predicts{' '}
          <span className="font-medium text-surface-800">slightly polluted or polluted</span> WQI only (clean forecast days
          do not appear here). Use station / year / month / forecast status filters on that table. Data refreshes when the
          dataset or forecast run changes.
        </p>
        <div className="text-sm text-surface-500 mt-2">
          <div>Data source: historical / simulated live (today) · forecast (through end of 2026)</div>
          <div>Page time: {new Date().toLocaleString()}</div>
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
            <label className="label">River</label>
            <select
              value={riverFilter}
              onChange={(e) => setRiverFilter(e.target.value)}
              className="input-field w-auto min-w-[220px]"
            >
              <option value="">All rivers</option>
              {dashboardApi.uniqueRiverNamesFromStations(stations).map((rn) => (
                <option key={rn} value={rn}>{rn}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Monitoring status (today)</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input-field w-auto min-w-[200px]"
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

        <div className="mt-4 max-w-lg mx-auto">
          <p className="text-xs text-surface-500 mb-3 text-center">
            Today&apos;s station counts from WQI readings ({todayYmd}, respecting the river filter). Slightly polluted =
            60–80; polluted = under 60.
            {todayReadingsLoading ? (
              <span className="block mt-1 text-amber-800/90">Updating counts…</span>
            ) : null}
          </p>
          <div className="rounded-xl border-2 border-surface-300 bg-white px-5 py-5 shadow-md flex flex-col justify-center min-h-[200px]">
            <p className="text-center text-[11px] font-bold tracking-[0.2em] text-surface-600 border-b border-surface-200 pb-3 mb-4">
              WATER QUALITY ALERT (TODAY)
            </p>
            <div className="space-y-5">
              <div className="rounded-lg border-l-4 border-orange-500 bg-orange-50/90 pl-3 pr-2 py-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-orange-900 uppercase tracking-wide">
                      🟠 Slightly polluted
                    </p>
                    <p className="text-xs text-orange-800 mt-0.5 font-medium">WQI 60–80 — caution level</p>
                  </div>
                  <p className="text-3xl font-extrabold text-orange-600 tabular-nums shrink-0">
                    {slightlyPollutedTodayCount}
                  </p>
                </div>
              </div>
              <div className="rounded-lg border-l-4 border-red-600 bg-red-50 pl-3 pr-2 py-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-red-900 uppercase tracking-wide">🔴 Polluted</p>
                    <p className="text-xs text-red-800 mt-0.5 font-medium">WQI under 60 — immediate attention</p>
                  </div>
                  <p className="text-3xl font-extrabold text-red-600 tabular-nums shrink-0">{pollutedTodayCount}</p>
                </div>
              </div>
            </div>
            <p className="text-[10px] text-surface-500 text-center mt-4 pt-3 border-t border-surface-100">
              {slightlyPollutedTodayCount + pollutedTodayCount} station
              {slightlyPollutedTodayCount + pollutedTodayCount === 1 ? '' : 's'} in alert bands today (🟠 + 🔴)
            </p>
          </div>
        </div>
      </div>

      {hasNoAlerts && (
        <div className="rounded-xl border border-surface-200 bg-white p-8 text-center">
          <p className="text-surface-600 font-medium">
            {filtersActive
              ? 'No alerts match the selected filters.'
              : `Nothing to show: no monitoring alerts for today (${todayYmd}) and no forecast pollution alerts.`}
          </p>
          {filtersActive && (
            <p className="text-sm text-surface-500 mt-2">
              Try changing river, monitoring status, or forecast filters (station / year / month / forecast status).
              Monitoring stays today-only; if
              today has no readings, that section stays empty until data exists (e.g. simulated live).
            </p>
          )}
        </div>
      )}

      {/* Historical Alerts */}
      {showHistorical && (
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
          <h2 className="font-display font-semibold text-surface-800 mb-2">Today&apos;s monitoring alerts</h2>
          <p className="text-sm text-surface-500 mb-4">
            Latest monitoring or simulated live per station, only when the alert date is today ({todayYmd}). Rows are in{' '}
            <strong>time-series order</strong> (date, then station).
          </p>
          <div className="overflow-x-auto rounded-lg border border-surface-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-100 text-left">
                  <th className="px-4 py-2 font-medium text-surface-700">River</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Station</th>
                  <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Status</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Message</th>
                </tr>
              </thead>
              <tbody>
                {!loading && filteredHistorical.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-surface-500">
                      {filtersActive
                        ? 'No monitoring alerts match the selected filters for today.'
                        : `No monitoring alerts for today (${todayYmd}) — either all stations are clean or there is no reading dated today.`}
                    </td>
                  </tr>
                ) : (
                  filteredHistorical.map((a, i) => (
                    <tr key={`${a.station_name || a.station_code}-${a.date}-${i}`} className="border-t border-surface-100">
                      <td className="px-4 py-2 text-surface-800">{a.river_name || '—'}</td>
                      <td className="px-4 py-2 text-surface-800 font-mono text-xs sm:text-sm">{a.date || '—'}</td>
                      <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
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
          <p className="text-sm text-surface-500 mb-4">
            From future prediction points. Table is in <strong>time-series order</strong> (forecast date, then station).
            Use filters below — including slightly polluted / polluted for forecast only.
          </p>
          <div className="flex flex-wrap items-end gap-4 mb-4 pb-4 border-b border-surface-100">
            <div>
              <label className="label">Forecast status</label>
              <select
                value={forecastStatusFilter}
                onChange={(e) => setForecastStatusFilter(e.target.value)}
                className="input-field w-auto min-w-[200px]"
              >
                <option value="">All forecast alert statuses</option>
                <option value="slightly_polluted">Slightly Polluted</option>
                <option value="polluted">Polluted</option>
              </select>
            </div>
            <div>
              <label className="label">Forecast station</label>
              <select
                value={forecastStationFilter}
                onChange={(e) => setForecastStationFilter(e.target.value)}
                className="input-field w-auto min-w-[200px]"
              >
                <option value="">All stations</option>
                {forecastStationOptions.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Forecast year</label>
              <select
                value={forecastYearFilter}
                onChange={(e) => setForecastYearFilter(e.target.value)}
                className="input-field w-auto min-w-[140px]"
              >
                <option value="">All years</option>
                {forecastYearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Forecast month</label>
              <select
                value={forecastMonthFilter}
                onChange={(e) => setForecastMonthFilter(e.target.value)}
                className="input-field w-auto min-w-[160px]"
              >
                <option value="">All months</option>
                <option value="1">January</option>
                <option value="2">February</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
              </select>
            </div>
          </div>
          <div className="overflow-x-auto rounded-lg border border-surface-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-100 text-left">
                  <th className="px-4 py-2 font-medium text-surface-700">River</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Forecast date</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Station</th>
                  <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Status</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Message</th>
                </tr>
              </thead>
              <tbody>
                {!loading && filteredForecast.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-surface-500">
                      {forecastAlerts.length === 0
                        ? 'No forecast alerts.'
                        : forecastFiltersActive
                          ? 'No forecast alerts match the selected station, year, month, or forecast status.'
                          : 'No forecast alerts.'}
                    </td>
                  </tr>
                ) : (
                  filteredForecast.map((a, i) => (
                    <tr key={`${a.station_name || a.station_code}-${a.date}-${i}`} className="border-t border-surface-100">
                      <td className="px-4 py-2 text-surface-800">{a.river_name || '—'}</td>
                      <td className="px-4 py-2 text-surface-800 font-mono text-xs sm:text-sm">{a.date || '—'}</td>
                      <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
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
