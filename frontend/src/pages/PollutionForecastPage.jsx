/**
 * Pollution Forecast — Historical (to today) + Forecast (2026 only, policy cap to 2026-12-31).
 * Chart: Historical WQI (solid), Predicted WQI (dashed).
 * Table: Date, Station Name, Predicted WQI, Predicted River Status.
 */
import { useState, useEffect } from 'react'
import ForecastChart from '../components/charts/ForecastChart'
import * as dashboardApi from '../api/dashboard'
import { SMARTRIVER_DATASET_CHANGED } from '../constants/datasetEvents'

const MONTH_RANGE_OPTIONS = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  label: `${i + 1} month${i === 0 ? '' : 's'}`,
}))

const YEAR_OPTIONS = [{ value: 2026, label: '2026' }]

/** Table month filter starts at April — Jan–Mar are omitted (no meaningful “after today” forecast rows in the 2026 horizon). */
const FORECAST_TABLE_MONTH_MIN = 4

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

/** YYYY-MM-DD prefix for comparisons (ISO dates sort lexicographically). */
function toYmd(d) {
  if (!d) return ''
  return String(d).trim().slice(0, 10)
}

function formatStatus(s) {
  if (!s) return '—'
  const v = String(s).toLowerCase().replace(/_/g, ' ')
  if (v === 'clean') return 'Clean'
  if (v === 'slightly polluted' || v === 'slightly_polluted') return 'Slightly Polluted'
  if (v === 'polluted') return 'Polluted'
  return v
}

export default function PollutionForecastPage() {
  const [stations, setStations] = useState([])
  /** Canonical river name; scopes historical series + forecast points. */
  const [river, setRiver] = useState('')
  /** Default to full calendar year so early-year month presets do not hide all future forecast points. */
  const [selectedMonthRange, setSelectedMonthRange] = useState(12)
  const [selectedYear, setSelectedYear] = useState(2026)
  const [historical, setHistorical] = useState([])
  const [forecast, setForecast] = useState([])
  const [today, setToday] = useState(null)
  const [showHistorical, setShowHistorical] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dataRevision, setDataRevision] = useState(0)
  /** Table only: '' = chart month range (from April onward in table); '4'..'12' = single month. */
  const [tableMonthOnly, setTableMonthOnly] = useState('')

  useEffect(() => {
    if (['1', '2', '3'].includes(tableMonthOnly)) setTableMonthOnly('')
  }, [tableMonthOnly])

  useEffect(() => {
    const bump = () => setDataRevision((n) => n + 1)
    window.addEventListener(SMARTRIVER_DATASET_CHANGED, bump)
    return () => window.removeEventListener(SMARTRIVER_DATASET_CHANGED, bump)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const list = await dashboardApi.getStations()
        if (!cancelled && Array.isArray(list) && list.length > 0) {
          setStations(list)
          const rivers = dashboardApi.uniqueRiverNamesFromStations(list)
          setRiver((r) => r || rivers[0] || '')
        }
      } catch (e) {
        if (!cancelled) setError(e.message || 'Failed to load stations')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [dataRevision])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      dashboardApi.getTimeSeries({ river_name: river || undefined, limit: 2000 }),
      dashboardApi.getForecast({
        river_name: river || undefined,
        year_from: selectedYear,
        year_to: selectedYear,
        limit: 5000,
      }),
    ])
      .then(([tsRes, fcRes]) => {
        if (cancelled) return
        const series = tsRes?.series ?? (Array.isArray(tsRes) ? tsRes : [])
        const fc = fcRes?.forecast ?? (Array.isArray(fcRes) ? fcRes : [])
        setHistorical(Array.isArray(series) ? series : [])
        setForecast(Array.isArray(fc) ? fc : [])
        setToday(tsRes?.today ?? fcRes?.today ?? null)
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message || 'Failed to load data')
          setHistorical([])
          setForecast([])
        }
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [river, selectedYear, dataRevision])

  const maxMonth = selectedMonthRange
  const yearStrTable = String(selectedYear)
  const todayYmd = toYmd(today)

  /** Forecast points strictly after server “today” (time-series / ML horizon only). */
  const forecastAfterToday = forecast.filter((f) => {
    const ds = toYmd(f.date)
    if (!ds) return false
    if (!todayYmd) return true
    return ds > todayYmd
  })

  const forecastRowsForTable = forecastAfterToday
    .filter((f) => {
      const ds = toYmd(f.date)
      if (!ds.startsWith(yearStrTable)) return false
      const m = Number(ds.slice(5, 7))
      if (m < FORECAST_TABLE_MONTH_MIN) return false
      if (tableMonthOnly !== '') {
        return m === Number(tableMonthOnly)
      }
      return m <= maxMonth
    })
    .sort((a, b) => {
      const c = toYmd(a.date).localeCompare(toYmd(b.date))
      if (c !== 0) return c
      const sa = String(a.station_name || a.station_code || '')
      const sb = String(b.station_name || b.station_code || '')
      return sa.localeCompare(sb)
    })

  const predictionTableRows = forecastRowsForTable.map((f) => ({
    date: f.date || '—',
    riverName: f.river_name || f.station_name || '—',
    stationName: f.station_name || f.station_code || '—',
    predictedWqi: f.wqi != null ? Number(f.wqi) : null,
    predictedStatus: f.river_status
      ? formatStatus(f.river_status)
      : (Number(f.wqi) >= 81 ? 'Clean' : Number(f.wqi) >= 60 ? 'Slightly Polluted' : 'Polluted'),
  }))

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Pollution forecast</h1>
        <p className="text-surface-600 mt-0.5">
          Historical data (up to today) and ML forecast predictions through the end of 2026 only (dates after today). Select month range within 2026 to view predictions.
        </p>
        <div className="text-sm text-surface-500 mt-2">
          <div>Data Source: Historical, Simulated Live, Forecast</div>
          <div>Last Updated: {new Date().toLocaleString()}</div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure backend is running; forecast is generated on startup from historical data.
        </div>
      )}

      <div className="flex flex-wrap gap-4">
        <div>
          <label className="label">River</label>
          <select
            value={river}
            onChange={(e) => setRiver(e.target.value)}
            className="input-field w-auto min-w-[220px]"
            disabled={loading || stations.length === 0}
          >
            <option value="">All rivers</option>
            {dashboardApi.uniqueRiverNamesFromStations(stations).map((rn) => (
              <option key={rn} value={rn}>{rn}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Select year</label>
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            className="input-field w-auto min-w-[120px]"
          >
            {YEAR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Select month range</label>
          <select
            value={selectedMonthRange}
            onChange={(e) => setSelectedMonthRange(Number(e.target.value))}
            className="input-field w-auto min-w-[180px]"
          >
            {MONTH_RANGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <label className="inline-flex items-center gap-2 text-sm text-surface-700 mb-1.5">
            <input
              type="checkbox"
              className="rounded border-surface-300 text-cyan-600 focus:ring-cyan-500"
              checked={showHistorical}
              onChange={(e) => setShowHistorical(e.target.checked)}
            />
            <span>Show historical data</span>
          </label>
        </div>
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Forecast chart</h2>
        <p className="text-sm text-surface-500 mb-4">
          Daily predicted WQI for the selected year and how many months to include from the start of that year. Historical data ends at today; forecast starts after today.
        </p>
        {loading ? (
          <p className="text-surface-500 py-8">Loading…</p>
        ) : (
          (() => {
            // Filter historical and forecast by cumulative month range within the selected year
            const maxMonth = selectedMonthRange
            const yearStr = String(selectedYear)
            const histFiltered = (showHistorical ? historical : []).filter((d) => {
              const ds = (d.date || '').slice(0, 10)
              if (!ds.startsWith(yearStr)) return false
              const m = Number(ds.slice(5, 7))
              return m >= 1 && m <= maxMonth
            })
            const todayCut = toYmd(today)
            const fcFiltered = forecast.filter((f) => {
              const ds = toYmd(f.date)
              if (!ds.startsWith(yearStr)) return false
              if (todayCut && ds <= todayCut) return false
              const m = Number(ds.slice(5, 7))
              return m >= 1 && m <= maxMonth
            })
            if (fcFiltered.length === 0) {
              return <p className="text-surface-500 py-8">No forecast data available for selected month range.</p>
            }
            return (
              <ForecastChart
                historical={histFiltered.map((d) => ({ date: d.date, wqi: d.wqi ?? d.value }))}
                forecast={fcFiltered.map((f) => ({ date: f.date, wqi: f.wqi ?? f.value }))}
                today={today}
                viewMode="daily"
                height={360}
              />
            )
          })()
        )}
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Forecast table</h2>
        <p className="text-sm text-surface-500 mb-4">
          Rows are <span className="font-medium text-surface-700">only dates after server today</span>, in time order.
          January–March are not listed (they do not appear in the forecast table). Filter from April onward without
          changing the chart.
        </p>
        <div className="flex flex-wrap items-end gap-4 mb-4">
          <div>
            <label className="label">Table — month</label>
            <select
              value={tableMonthOnly}
              onChange={(e) => setTableMonthOnly(e.target.value)}
              className="input-field w-auto min-w-[220px]"
              disabled={loading}
            >
              <option value="">All months in chart range</option>
              {MONTH_NAMES.map((name, idx) => {
                const monthNum = idx + 1
                if (monthNum < FORECAST_TABLE_MONTH_MIN) return null
                const v = String(monthNum)
                return (
                  <option key={v} value={v}>
                    {name}
                  </option>
                )
              })}
            </select>
          </div>
        </div>
        <div className="overflow-x-auto rounded-lg border border-surface-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-100 text-left">
                <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                <th className="px-4 py-2 font-medium text-surface-700">River</th>
                <th className="px-4 py-2 font-medium text-surface-700">Station</th>
                <th className="px-4 py-2 font-medium text-surface-700">Predicted WQI</th>
                <th className="px-4 py-2 font-medium text-surface-700">Predicted river status</th>
              </tr>
            </thead>
            <tbody>
              {predictionTableRows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-surface-500">
                    No forecast rows for {selectedYear}
                    {tableMonthOnly ? ` · ${MONTH_NAMES[Number(tableMonthOnly) - 1] || 'selected month'}` : ' · selected range'}
                    . Adjust the table month filter or chart range, or ensure the backend has generated the forecast.
                  </td>
                </tr>
              ) : (
                predictionTableRows.map((row, i) => (
                  <tr key={i} className="border-t border-surface-100">
                    <td className="px-4 py-2 text-surface-800">{row.date}</td>
                    <td className="px-4 py-2 text-surface-800">{row.riverName}</td>
                    <td className="px-4 py-2 font-medium text-surface-800">{row.stationName}</td>
                    <td className="px-4 py-2">{row.predictedWqi != null ? Number(row.predictedWqi).toFixed(1) : '—'}</td>
                    <td className="px-4 py-2">{row.predictedStatus}</td>
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
