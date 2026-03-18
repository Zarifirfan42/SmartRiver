/**
 * Dashboard — All data from dataset (Lampiran A - Sungai Kulim.xlsx).
 * Summary, Station WQI Trend (line), Forecast, Anomaly, Dataset table, Map, Export.
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { DashboardSummary } from '../dashboard'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import ForecastChart from '../components/charts/ForecastChart'
import WQIAnomalyChart from '../components/charts/WQIAnomalyChart'
import RiverMap from '../components/map/RiverMap'
import DatasetTable from '../components/dataset/DatasetTable'
import * as dashboardApi from '../api/dashboard'

function formatStatus(s) {
  if (!s) return '—'
  const v = String(s).toLowerCase().replace(/_/g, ' ')
  if (v === 'clean') return 'Clean'
  if (v === 'slightly polluted' || v === 'slightly_polluted') return 'Slightly Polluted'
  if (v === 'polluted') return 'Polluted'
  return v
}

function exportCsv(rows) {
  const headers = ['Station Name', 'Date', 'WQI', 'River Status']
  const csv = [headers.join(',')].concat(
    rows.map((r) =>
      [
        `"${(r.station_name || r.station || '').replace(/"/g, '""')}"`,
        r.date || '',
        r.wqi != null ? Number(r.wqi) : '',
        `"${formatStatus(r.river_status)}"`,
      ].join(',')
    )
  ).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `smartriver-report-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

function exportPrint(rows) {
  const w = window.open('', '_blank')
  if (!w) return
  w.document.write(`
    <!DOCTYPE html><html><head><title>SmartRiver Report</title>
    <style>table{border-collapse:collapse;width:100%} th,td{border:1px solid #ccc;padding:6px 10px;text-align:left} th{background:#f1f5f9}</style>
    </head><body>
    <h1>SmartRiver — Dataset Report</h1>
    <p>Generated: ${new Date().toLocaleString()}</p>
    <table>
    <thead><tr><th>Station Name</th><th>Date</th><th>WQI</th><th>River Status</th></tr></thead>
    <tbody>
    ${(rows || []).map((r) => `<tr><td>${(r.station_name || r.station || '—').replace(/</g, '&lt;')}</td><td>${r.date || '—'}</td><td>${r.wqi != null ? Number(r.wqi).toFixed(1) : '—'}</td><td>${formatStatus(r.river_status)}</td></tr>`).join('')}
    </tbody></table></body></html>
  `)
  w.document.close()
  w.print()
  w.close()
}

export default function Dashboard() {
  const { isAdmin } = useAuth()
  const [summary, setSummary] = useState({
    totalStations: 0,
    avgWqi: 0,
    cleanCount: 0,
    pollutedCount: 0,
    slightlyPollutedCount: 0,
    predictedAvgWqi2025_2028: 0,
  })
  const [stations, setStations] = useState([])
  const [years, setYears] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Station WQI Trend
  const [trendStation, setTrendStation] = useState('')
  const [trendYear, setTrendYear] = useState('')
  const [timeSeries, setTimeSeries] = useState([])

  // Forecast
  const [forecastStation, setForecastStation] = useState('')
  const [forecastRange, setForecastRange] = useState(14)
  const [historicalSeries, setHistoricalSeries] = useState([])
  const [forecast, setForecast] = useState([])

  // Anomaly
  const [anomalyStation, setAnomalyStation] = useState('')
  const [anomalies, setAnomalies] = useState([])
  const [anomalyTimeSeries, setAnomalyTimeSeries] = useState([])

  // Export — uses filtered dataset table rows (no extra reload)
  const [exportData, setExportData] = useState([])

  // Latest critical alert for dashboard panel
  const [latestCriticalAlert, setLatestCriticalAlert] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [s, stationList, yearList] = await Promise.all([
          dashboardApi.getSummary(),
          dashboardApi.getStations(),
          dashboardApi.getYears(),
        ])
        if (cancelled) return
        setSummary({
          totalStations: s.totalStations ?? 0,
          avgWqi: s.avgWqi ?? 0,
          cleanCount: s.cleanCount ?? 0,
          pollutedCount: s.pollutedCount ?? 0,
          slightlyPollutedCount: s.slightlyPollutedCount ?? 0,
          predictedAvgWqi2025_2028: s.predictedAvgWqi2025_2028 ?? 0,
        })
        const st = Array.isArray(stationList) ? stationList : []
        setStations(st)
        setYears(Array.isArray(yearList) ? yearList : [])
        if (st.length > 0 && !trendStation) setTrendStation(st[0].station_name || st[0].station_code)
        if (st.length > 0 && !forecastStation) setForecastStation(st[0].station_name || st[0].station_code)
        if (isAdmin && st.length > 0 && !anomalyStation) setAnomalyStation(st[0].station_name || st[0].station_code)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load dashboard')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    const station = trendStation || (stations[0]?.station_name || stations[0]?.station_code)
    if (!station) return
    dashboardApi.getTimeSeries({ station_name: station, year: trendYear || undefined, limit: 1000 }).then((res) => {
      if (!cancelled) setTimeSeries(Array.isArray(res?.series) ? res.series : [])
    }).catch(() => { if (!cancelled) setTimeSeries([]) })
    return () => { cancelled = true }
  }, [trendStation, trendYear, stations.length])

  useEffect(() => {
    let cancelled = false
    const station = forecastStation || (stations[0]?.station_name || stations[0]?.station_code)
    if (!station) return
    Promise.all([
      dashboardApi.getTimeSeries({ station_name: station, limit: 60 }),
      dashboardApi.getForecast({ station_code: station, limit: forecastRange }),
    ]).then(([tsRes, fcRes]) => {
      if (!cancelled) {
        setHistoricalSeries(Array.isArray(tsRes?.series) ? tsRes.series : [])
        setForecast(Array.isArray(fcRes?.forecast) ? fcRes.forecast : [])
      }
    }).catch(() => { if (!cancelled) { setHistoricalSeries([]); setForecast([]) } })
    return () => { cancelled = true }
  }, [forecastStation, forecastRange, stations.length])

  useEffect(() => {
    if (!isAdmin) return
    let cancelled = false
    const station = anomalyStation || (stations[0]?.station_name || stations[0]?.station_code)
    if (!station) return
    Promise.all([
      dashboardApi.getTimeSeries({ station_name: station, limit: 500 }),
      dashboardApi.getAnomalies({ station_code: station, limit: 500 }),
    ]).then(([tsRes, anom]) => {
      if (!cancelled) {
        setAnomalyTimeSeries(Array.isArray(tsRes?.series) ? tsRes.series : [])
        setAnomalies(Array.isArray(anom) ? anom : [])
      }
    }).catch(() => { if (!cancelled) { setAnomalyTimeSeries([]); setAnomalies([]) } })
    return () => { cancelled = true }
  }, [isAdmin, anomalyStation, stations.length])

  useEffect(() => {
    let cancelled = false
    dashboardApi.getAlertsByType({ limit: 200 }).then(({ historical, forecast }) => {
      if (cancelled) return
      const combined = [...(Array.isArray(historical) ? historical : []), ...(Array.isArray(forecast) ? forecast : [])]
      const critical = combined.filter((a) => (a.severity || '').toLowerCase() === 'critical')
      const sorted = critical.sort((a, b) => {
        const da = a.date || ''
        const db = b.date || ''
        return db.localeCompare(da)
      })
      setLatestCriticalAlert(sorted[0] || null)
    }).catch(() => { if (!cancelled) setLatestCriticalAlert(null) })
    return () => { cancelled = true }
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure the backend is running; dataset loads from datasets/Lampiran A - Sungai Kulim.xlsx on startup.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading…</p>}

      <DashboardSummary
        totalStations={summary.totalStations}
        avgWqi={summary.avgWqi}
        cleanCount={summary.cleanCount}
        pollutedCount={summary.pollutedCount}
        slightlyPollutedCount={summary.slightlyPollutedCount}
        predictedAvgWqi2025_2028={summary.predictedAvgWqi2025_2028}
      />

      {/* WQI classification panel */}
      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-display text-base font-semibold text-surface-800 mb-2">WQI classification</h2>
        <p className="text-sm text-surface-500 mb-3">
          Water Quality Index (WQI) classification used across charts, tables, alerts, and the map.
        </p>
        <dl className="space-y-2 text-sm">
          <div className="flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2">
            <dt className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500" />
              <span className="font-medium text-emerald-800">Clean</span>
            </dt>
            <dd className="text-surface-700 font-mono text-xs sm:text-sm">81–100</dd>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2">
            <dt className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-500" />
              <span className="font-medium text-amber-800">Slightly Polluted</span>
            </dt>
            <dd className="text-surface-700 font-mono text-xs sm:text-sm">60–80</dd>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-red-50 px-3 py-2">
            <dt className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" />
              <span className="font-medium text-red-800">Polluted</span>
            </dt>
            <dd className="text-surface-700 font-mono text-xs sm:text-sm">&lt;60</dd>
          </div>
        </dl>
      </div>

      {/* Latest critical alert panel */}
      {latestCriticalAlert && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 shadow-sm">
          <h2 className="font-display text-base font-semibold text-red-800 mb-2">Latest critical alert</h2>
          <p className="text-sm text-red-900">
            <span aria-hidden>🚨</span>{' '}
            {latestCriticalAlert.message && String(latestCriticalAlert.message).trim()
              ? latestCriticalAlert.message.trim()
              : `${latestCriticalAlert.station_name || latestCriticalAlert.station_code || 'Unknown'} is polluted${latestCriticalAlert.wqi != null ? ` (WQI: ${Number(latestCriticalAlert.wqi).toFixed(0)})` : ''}.`}
          </p>
          <Link to="/alerts" className="inline-block mt-2 text-sm font-medium text-red-700 hover:text-red-900 underline">
            View all alerts →
          </Link>
        </div>
      )}

      {/* Monitoring Stations Map */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-0 overflow-hidden shadow-sm">
        <div className="px-5 py-3 border-b border-slate-200">
          <h2 className="font-display font-semibold text-surface-800">Monitoring Stations Map</h2>
          <p className="text-sm text-surface-500">Visual overview of monitoring stations with their latest WQI and river status from the dataset.</p>
        </div>
        <RiverMap stations={stations} height={360} useDefaultStations={stations.length === 0} />
      </div>

      {/* Export Report — CSV, PDF, Print */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Export Report</h2>
        <p className="text-sm text-surface-500 mb-4">Download or print reports based on the current dataset filters: Station, Date, WQI, and river status.</p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => exportCsv(exportData)}
            className="btn-primary"
          >
            Download CSV
          </button>
          <button
            type="button"
            onClick={() => exportPrint(exportData)}
            className="btn-secondary"
          >
            Print Report
          </button>
          <span className="text-sm text-surface-500 self-center">PDF: use Print → Save as PDF in the print dialog.</span>
        </div>
      </div>

      <div className="mt-6">
        <DatasetTable
          title="Dataset overview"
          description="Filtered view of dataset records: Station Name, Date, WQI, and River Status, with sorting and pagination."
          onDataChange={setExportData}
        />
      </div>

      {/* WQI Trend Analysis — Line chart, filter by station and year */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-4">WQI Trend Analysis</h2>
        <p className="text-sm text-surface-500 mb-4">Shows how river water quality (WQI) changes over time for the selected station and year.</p>
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="label">Station</label>
            <select
              value={trendStation}
              onChange={(e) => setTrendStation(e.target.value)}
              className="input-field w-auto min-w-[200px]"
            >
              <option value="">All stations</option>
              {stations.map((s) => (
                <option key={s.station_code} value={s.station_name || s.station_code}>
                  {s.station_name || s.station_code}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Year</label>
            <select
              value={trendYear}
              onChange={(e) => setTrendYear(e.target.value)}
              className="input-field w-auto min-w-[120px]"
            >
              <option value="">All</option>
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>
        {timeSeries.length > 0 ? (
          <TimeSeriesChart data={timeSeries} height={320} />
        ) : (
          <div className="h-[320px] flex items-center justify-center text-surface-500">No data for selected filters.</div>
        )}
      </div>

      {/* Forecast Prediction — Station + range; Historical (solid) + Forecast (dashed) */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Forecast Prediction</h2>
        <p className="text-sm text-surface-500 mb-4">Compares historical WQI (solid line) with predicted WQI (dashed line) for the selected station and forecast range.</p>
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="label">Station name</label>
            <select
              value={forecastStation}
              onChange={(e) => setForecastStation(e.target.value)}
              className="input-field w-auto min-w-[200px]"
            >
              {stations.map((s) => (
                <option key={s.station_code} value={s.station_name || s.station_code}>
                  {s.station_name || s.station_code}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Forecast range (days)</label>
            <select
              value={forecastRange}
              onChange={(e) => setForecastRange(Number(e.target.value))}
              className="input-field w-auto min-w-[120px]"
            >
              <option value={7}>7</option>
              <option value={14}>14</option>
              <option value={30}>30</option>
            </select>
          </div>
        </div>
        {(historicalSeries.length > 0 || forecast.length > 0) ? (
          <ForecastChart
            historical={historicalSeries.map((d) => ({ date: d.date, wqi: d.wqi ?? d.value }))}
            forecast={forecast.map((f) => ({ date: f?.date || '', wqi: typeof f === 'number' ? f : (f?.wqi ?? f?.value ?? null) }))}
            height={320}
          />
        ) : (
          <div className="h-[320px] flex items-center justify-center text-surface-500">No forecast data. Run model to generate predictions.</div>
        )}
      </div>

      {isAdmin && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="font-display font-semibold text-surface-800 mb-4">Anomaly Detection</h2>
          <p className="text-sm text-surface-500 mb-4">Select station. Anomalies (abnormal spikes) are marked on the chart and listed in the table.</p>
          <div className="mb-4">
            <label className="label">Station name</label>
            <select
              value={anomalyStation}
              onChange={(e) => setAnomalyStation(e.target.value)}
              className="input-field w-auto min-w-[200px]"
            >
              {stations.map((s) => (
                <option key={s.station_code} value={s.station_name || s.station_code}>
                  {s.station_name || s.station_code}
                </option>
              ))}
            </select>
          </div>
          <div className="mb-4">
            <h3 className="font-medium text-surface-700 mb-2">Anomaly Chart</h3>
            {anomalyTimeSeries.length > 0 ? (
              <WQIAnomalyChart data={anomalyTimeSeries} anomalies={anomalies} height={300} />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-surface-500">No time series for this station.</div>
            )}
          </div>
          <div>
            <h3 className="font-medium text-surface-700 mb-2">Anomaly Table</h3>
            <div className="overflow-x-auto rounded-lg border border-surface-200">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-surface-100 text-left">
                    <th className="px-4 py-2 font-medium text-surface-700">Station</th>
                    <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                    <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                    <th className="px-4 py-2 font-medium text-surface-700">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.length === 0 ? (
                    <tr><td colSpan={4} className="px-4 py-6 text-center text-surface-500">No anomalies for this station.</td></tr>
                  ) : (
                    anomalies.map((a, i) => (
                      <tr key={i} className="border-t border-surface-100">
                        <td className="px-4 py-2 text-surface-800">{a.station_name || a.station_code || '—'}</td>
                        <td className="px-4 py-2 text-surface-800">{a.date || '—'}</td>
                        <td className="px-4 py-2">{a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}</td>
                        <td className="px-4 py-2 text-amber-700">{a.reason || 'Abnormal spike'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}