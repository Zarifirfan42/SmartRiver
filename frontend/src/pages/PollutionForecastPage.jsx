/**
 * Pollution Forecast — Station name + prediction range. Forecast chart + prediction table.
 * Historical WQI (solid), Predicted WQI (dashed). Table: Date, Station, Predicted WQI, Predicted Status.
 */
import { useState, useEffect } from 'react'
import ForecastChart from '../components/charts/ForecastChart'
import RiverHealthIndicator from '../components/dashboard/RiverHealthIndicator'
import * as dashboardApi from '../api/dashboard'

function predictedStatus(wqi) {
  if (wqi == null || Number.isNaN(wqi)) return '—'
  if (wqi >= 81) return 'Clean'
  if (wqi >= 60) return 'Slightly Polluted'
  return 'Polluted'
}

export default function PollutionForecastPage() {
  const [stations, setStations] = useState([])
  const [station, setStation] = useState('')
  const [predictionRange, setPredictionRange] = useState(14)
  const [historical, setHistorical] = useState([])
  const [forecast, setForecast] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
      dashboardApi.getTimeSeries({ station_name: station, limit: 60 }),
      dashboardApi.getForecast({ station_code: station, limit: Math.max(predictionRange, 30) }),
    ])
      .then(([series, fc]) => {
        if (cancelled) return
        setHistorical(Array.isArray(series) ? series : [])
        setForecast(Array.isArray(fc) ? fc.slice(0, predictionRange) : [])
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
  }, [station, predictionRange])

  // Build prediction table rows: Date, Station, Predicted WQI, Predicted Status
  const lastHistDate = historical.length > 0 ? historical[historical.length - 1].date : null
  const predictionTableRows = forecast.map((f, i) => {
    const wqi = typeof f === 'number' ? f : (f?.wqi ?? f?.value)
    let dateStr = typeof f === 'object' && f?.date ? f.date : ''
    if (!dateStr && lastHistDate) {
      const d = new Date(lastHistDate)
      d.setDate(d.getDate() + i + 1)
      dateStr = d.toISOString().slice(0, 10)
    }
    return {
      date: dateStr,
      station: station || (stations[0]?.station_name || stations[0]?.station_code),
      predictedWqi: wqi,
      predictedStatus: predictedStatus(wqi),
    }
  })

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Pollution forecast</h1>
        <p className="text-surface-600 mt-0.5">Select station and prediction range. Historical WQI (solid line), Predicted WQI (dashed line).</p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure backend is running; train LSTM model for forecasts.
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
          <label className="label">Prediction range</label>
          <select
            value={predictionRange}
            onChange={(e) => setPredictionRange(Number(e.target.value))}
            className="input-field w-auto min-w-[120px]"
          >
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
        </div>
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Forecast chart</h2>
        <p className="text-sm text-surface-500 mb-4">X-axis: chronological dates. Legend: Historical Data (solid), Forecast Prediction (dashed).</p>
        {loading ? (
          <p className="text-surface-500 py-8">Loading…</p>
        ) : (
          <ForecastChart
            historical={historical.map((d) => ({ date: d.date, wqi: d.wqi ?? d.value }))}
            forecast={forecast.map((f) => (typeof f === 'number' ? { wqi: f } : { date: f?.date, wqi: f?.wqi ?? f?.value }))}
            height={340}
          />
        )}
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Prediction table</h2>
        <p className="text-sm text-surface-500 mb-4">Date, Station, Predicted WQI, Predicted Status.</p>
        <div className="overflow-x-auto rounded-lg border border-surface-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-100 text-left">
                <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                <th className="px-4 py-2 font-medium text-surface-700">Station</th>
                <th className="px-4 py-2 font-medium text-surface-700">Predicted WQI</th>
                <th className="px-4 py-2 font-medium text-surface-700">Predicted Status</th>
              </tr>
            </thead>
            <tbody>
              {predictionTableRows.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-surface-500">No forecast data. Run model to generate predictions.</td></tr>
              ) : (
                predictionTableRows.map((row, i) => (
                  <tr key={i} className="border-t border-surface-100">
                    <td className="px-4 py-2 text-surface-800">{row.date || '—'}</td>
                    <td className="px-4 py-2 font-medium text-surface-800">{row.station || '—'}</td>
                    <td className="px-4 py-2">{row.predictedWqi != null ? Number(row.predictedWqi).toFixed(1) : '—'}</td>
                    <td className="px-4 py-2"><RiverHealthIndicator wqi={row.predictedWqi} compact /></td>
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