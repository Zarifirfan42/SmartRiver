/**
 * Pollution Forecast — Historical (2023-2024) + Forecast (2025-2028).
 * User selects Station name and Forecast range (year or All).
 * Chart: Historical WQI (solid), Predicted WQI (dashed). X-axis: chronological 2023 → 2028.
 * Table: Date, Station Name, Predicted WQI, Predicted River Status.
 */
import { useState, useEffect } from 'react'
import ForecastChart from '../components/charts/ForecastChart'
import * as dashboardApi from '../api/dashboard'

const FORECAST_YEAR_OPTIONS = [
  { value: 'all', label: 'All (2025-2028)', yearFrom: 2025, yearTo: 2028 },
  { value: '2025', label: '2025', yearFrom: 2025, yearTo: 2025 },
  { value: '2026', label: '2026', yearFrom: 2026, yearTo: 2026 },
  { value: '2027', label: '2027', yearFrom: 2027, yearTo: 2027 },
  { value: '2028', label: '2028', yearFrom: 2028, yearTo: 2028 },
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
  const [station, setStation] = useState('')
  const [forecastRange, setForecastRange] = useState('all')
  const [historical, setHistorical] = useState([])
  const [forecast, setForecast] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const rangeOption = FORECAST_YEAR_OPTIONS.find((o) => o.value === forecastRange) || FORECAST_YEAR_OPTIONS[0]

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const list = await dashboardApi.getStations()
        if (!cancelled && Array.isArray(list) && list.length > 0) {
          setStations(list)
          setStation((s) => s || list[0].station_name || list[0].station_code)
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
    if (!station) return
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      dashboardApi.getTimeSeries({ station_name: station, limit: 2000 }),
      dashboardApi.getForecast({
        station_code: station,
        year_from: rangeOption.yearFrom,
        year_to: rangeOption.yearTo,
        limit: 5000,
      }),
    ])
      .then(([series, fc]) => {
        if (cancelled) return
        setHistorical(Array.isArray(series) ? series : [])
        setForecast(Array.isArray(fc) ? fc : [])
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
  }, [station, forecastRange, rangeOption.yearFrom, rangeOption.yearTo])

  const predictionTableRows = forecast.map((f) => ({
    date: f.date || '—',
    stationName: f.station_name || f.station_code || station || '—',
    predictedWqi: f.wqi != null ? Number(f.wqi) : null,
    predictedStatus: f.river_status ? formatStatus(f.river_status) : (f.wqi >= 81 ? 'Clean' : f.wqi >= 60 ? 'Slightly Polluted' : 'Polluted'),
  }))

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Pollution forecast</h1>
        <p className="text-surface-600 mt-0.5">
          Historical data (2023-2024) and forecast predictions (2025-2028). Select station and forecast range. Chart: Historical (solid) vs Forecast (dashed).
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure backend is running; forecast is generated on startup from historical data.
        </div>
      )}

      <div className="flex flex-wrap gap-4">
        <div>
          <label className="label">Station name</label>
          <select
            value={station}
            onChange={(e) => setStation(e.target.value)}
            className="input-field w-auto min-w-[200px]"
            disabled={loading || stations.length === 0}
          >
            {stations.length === 0 && <option value="">No stations</option>}
            {stations.map((s) => (
              <option key={s.station_code} value={s.station_name || s.station_code}>
                {s.station_name || s.station_code}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Forecast range</label>
          <select
            value={forecastRange}
            onChange={(e) => setForecastRange(e.target.value)}
            className="input-field w-auto min-w-[160px]"
          >
            {FORECAST_YEAR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Forecast chart</h2>
        <p className="text-sm text-surface-500 mb-4">
          X-axis: chronological date (2023 → 2028). <strong>Historical Data</strong> (solid line, 2023-2024). <strong>Forecast Prediction</strong> (dashed line, 2025-2028).
        </p>
        {loading ? (
          <p className="text-surface-500 py-8">Loading…</p>
        ) : (
          <ForecastChart
            historical={historical.map((d) => ({ date: d.date, wqi: d.wqi ?? d.value }))}
            forecast={forecast.map((f) => ({ date: f.date, wqi: f.wqi ?? f.value }))}
            height={360}
          />
        )}
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Forecast table</h2>
        <p className="text-sm text-surface-500 mb-4">
          Date, Station Name, Predicted WQI, Predicted River Status (WQI ≥81 Clean, 60-80 Slightly Polluted, &lt;60 Polluted).
        </p>
        <div className="overflow-x-auto rounded-lg border border-surface-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-100 text-left">
                <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                <th className="px-4 py-2 font-medium text-surface-700">Station name</th>
                <th className="px-4 py-2 font-medium text-surface-700">Predicted WQI</th>
                <th className="px-4 py-2 font-medium text-surface-700">Predicted river status</th>
              </tr>
            </thead>
            <tbody>
              {predictionTableRows.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-surface-500">No forecast data. Ensure backend has run forecast (2025-2028) on startup.</td></tr>
              ) : (
                predictionTableRows.map((row, i) => (
                  <tr key={i} className="border-t border-surface-100">
                    <td className="px-4 py-2 text-surface-800">{row.date}</td>
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
