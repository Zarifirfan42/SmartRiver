import { useState, useEffect } from 'react'
import WQIGauge from '../components/dashboard/WQIGauge'
import RiverHealthIndicator from '../components/dashboard/RiverHealthIndicator'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import ForecastChart from '../components/charts/ForecastChart'
import AnomalyAlerts from '../components/dashboard/AnomalyAlerts'
import RiverMap from '../components/map/RiverMap'
import * as dashboardApi from '../api/dashboard'

export default function DashboardPage() {
  const [summary, setSummary] = useState({
    totalStations: 0,
    cleanCount: 0,
    slightlyPollutedCount: 0,
    pollutedCount: 0,
    latestWqi: 0,
    recentAnomaliesCount: 0,
  })
  const [timeSeries, setTimeSeries] = useState([])
  const [forecast, setForecast] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const [s, series, fc, al] = await Promise.all([
          dashboardApi.getSummary(),
          dashboardApi.getTimeSeries({ limit: 100 }),
          dashboardApi.getForecast({ limit: 30 }),
          dashboardApi.getAlerts({ limit: 10 }),
        ])
        if (cancelled) return
        setSummary({
          totalStations: s.totalStations ?? 0,
          cleanCount: s.cleanCount ?? 0,
          slightlyPollutedCount: s.slightlyPollutedCount ?? 0,
          pollutedCount: s.pollutedCount ?? 0,
          latestWqi: s.avgWqi ?? 0,
          recentAnomaliesCount: s.recentAnomaliesCount ?? 0,
        })
        setTimeSeries(Array.isArray(series?.series) ? series.series : (Array.isArray(series) ? series : []))
        setForecast(Array.isArray(fc?.forecast) ? fc.forecast : (Array.isArray(fc) ? fc : []))
        setAlerts(Array.isArray(al) ? al : [])
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load dashboard')
          setTimeSeries([])
          setForecast([])
          setAlerts([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchData()
    return () => { cancelled = true }
  }, [])
  return (
    <div className="space-y-6 animate-fade-in">
      {error && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-2 text-sm text-amber-800">
          {error}. Run preprocessing and upload data to see dashboard.
        </div>
      )}
      {loading && (
        <p className="text-surface-500">Loading dashboard…</p>
      )}
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Dashboard</h1>
        <p className="text-surface-600 mt-0.5">River water quality overview</p>
      </div>

      {/* Summary cards + River health indicator + WQI gauge */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <p className="text-sm font-medium text-surface-500">Stations</p>
          <p className="text-2xl font-display font-semibold text-surface-900">{summary.totalStations}</p>
        </div>
        <div className="card flex flex-col justify-center">
          <p className="text-sm font-medium text-surface-500">Overall status</p>
          <RiverHealthIndicator wqi={summary.latestWqi} />
        </div>
        <div className="card flex flex-col justify-center">
          <p className="text-sm font-medium text-surface-500 mb-2">Current WQI</p>
          <WQIGauge value={summary.latestWqi} size={120} />
        </div>
        <div className="card">
          <p className="text-sm font-medium text-surface-500">Status breakdown</p>
          <div className="mt-2 space-y-1 text-sm">
            <p><span className="inline-block w-2 h-2 rounded-full bg-eco-500 mr-2" />Clean: {summary.cleanCount}</p>
            <p><span className="inline-block w-2 h-2 rounded-full bg-amber-500 mr-2" />Slightly polluted: {summary.slightlyPollutedCount}</p>
            <p><span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-2" />Polluted: {summary.pollutedCount}</p>
          </div>
        </div>
      </div>

      {/* WQI trend + Forecast */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-display font-semibold text-surface-800 mb-4">WQI trend</h2>
          <TimeSeriesChart data={timeSeries} height={280} />
        </div>
        <div className="card">
          <h2 className="font-display font-semibold text-surface-800 mb-4">7–30 day forecast</h2>
          <ForecastChart
            historical={timeSeries.slice(-14)}
            forecast={forecast.map((f) => ({ date: f.date || '', wqi: typeof f === 'number' ? f : (f.wqi ?? null) }))}
            height={280}
          />
        </div>
      </div>

      {/* Anomaly alerts + Map */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-display font-semibold text-surface-800 mb-4">Anomaly alerts</h2>
          <AnomalyAlerts alerts={alerts} maxItems={5} />
        </div>
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-3 border-b border-surface-200">
            <h2 className="font-display font-semibold text-surface-800">Map</h2>
            <p className="text-sm text-surface-500">Monitoring stations</p>
          </div>
          <RiverMap height={320} />
        </div>
      </div>
    </div>
  )
}
