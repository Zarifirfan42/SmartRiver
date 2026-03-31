/**
 * Pollution Forecast — Historical (2023-2024) + Forecast (2025-2028).
 * User selects Station name and Forecast range (year or All).
 * Chart: Historical WQI (solid), Predicted WQI (dashed). X-axis: chronological 2023 → 2028.
 * Table: Date, Station Name, Predicted WQI, Predicted River Status.
 */
import { useState, useEffect } from 'react'
import ForecastChart from '../components/charts/ForecastChart'
import * as dashboardApi from '../api/dashboard'

const MONTH_RANGE_OPTIONS = [
  { value: 1, label: '1 month (Jan)' },
  { value: 2, label: '2 months (Jan–Feb)' },
  { value: 3, label: '3 months (Jan–Mar)' },
  { value: 4, label: '4 months (Jan–Apr)' },
  { value: 5, label: '5 months (Jan–May)' },
  { value: 6, label: '6 months (Jan–Jun)' },
  { value: 7, label: '7 months (Jan–Jul)' },
  { value: 8, label: '8 months (Jan–Aug)' },
  { value: 9, label: '9 months (Jan–Sep)' },
  { value: 10, label: '10 months (Jan–Oct)' },
  { value: 11, label: '11 months (Jan–Nov)' },
  { value: 12, label: '12 months (Jan–Dec)' },
]

const YEAR_OPTIONS = [
  { value: 2026, label: '2026' },
  { value: 2027, label: '2027' },
  { value: 2028, label: '2028' },
]

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
  const [selectedMonthRange, setSelectedMonthRange] = useState(1)
  const [selectedYear, setSelectedYear] = useState(2027)
  const [historical, setHistorical] = useState([])
  const [forecast, setForecast] = useState([])
  const [today, setToday] = useState(null)
  const [showHistorical, setShowHistorical] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
  }, [])

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
  }, [river, selectedYear])

  const predictionTableRows = forecast.map((f) => ({
    date: f.date || '—',
    riverName: f.river_name || f.station_name || '—',
    stationName: f.station_name || f.station_code || '—',
    predictedWqi: f.wqi != null ? Number(f.wqi) : null,
    predictedStatus: f.river_status ? formatStatus(f.river_status) : (f.wqi >= 81 ? 'Clean' : f.wqi >= 60 ? 'Slightly Polluted' : 'Polluted'),
  }))

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Pollution forecast</h1>
        <p className="text-surface-600 mt-0.5">
          Historical data (up to today) and forecast predictions (from tomorrow onwards). Select year and month range to view predictions; each forecast point uses its original forecast date.
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
          Daily predicted WQI for the selected year and month range (January up to the selected month). Historical data ends at today; forecast starts from tomorrow.
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
            const fcFiltered = forecast.filter((f) => {
              const ds = (f.date || '').slice(0, 10)
              if (!ds.startsWith(yearStr)) return false
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
          Date, River, Station, predicted WQI, and status (WQI ≥81 Clean, 60-80 Slightly Polluted, &lt;60 Polluted).
        </p>
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
                <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">No forecast data. Ensure backend has run forecast (2025-2028) on startup.</td></tr>
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
