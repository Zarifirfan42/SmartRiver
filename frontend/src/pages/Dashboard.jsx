/**
 * Dashboard — River monitoring: KPIs, map, dataset table, historical WQI trend, export.
 * Forecast charts live on the Pollution Forecast page only.
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { DashboardSummary } from '../dashboard'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import WQIAnomalyChart from '../components/charts/WQIAnomalyChart'
import RiverMap from '../components/map/RiverMap'
import DatasetTable from '../components/dataset/DatasetTable'
import * as dashboardApi from '../api/dashboard'
import { SMARTRIVER_DATASET_CHANGED } from '../constants/datasetEvents'

function formatStatus(s) {
  if (!s) return '—'
  const v = String(s).toLowerCase().replace(/_/g, ' ')
  if (v === 'clean') return 'Clean'
  if (v === 'slightly polluted' || v === 'slightly_polluted') return 'Slightly Polluted'
  if (v === 'polluted') return 'Polluted'
  return v
}

function exportCsv(rows) {
  const headers = ['River', 'Station Name', 'Date', 'WQI', 'River Status']
  const csv = [headers.join(',')].concat(
    rows.map((r) =>
      [
        `"${(r.river_name || '').replace(/"/g, '""')}"`,
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
    <thead><tr><th>River</th><th>Station</th><th>Date</th><th>WQI</th><th>River Status</th></tr></thead>
    <tbody>
    ${(rows || []).map((r) => `<tr><td>${(r.river_name || '—').replace(/</g, '&lt;')}</td><td>${(r.station_name || r.station || '—').replace(/</g, '&lt;')}</td><td>${r.date || '—'}</td><td>${r.wqi != null ? Number(r.wqi).toFixed(1) : '—'}</td><td>${formatStatus(r.river_status)}</td></tr>`).join('')}
    </tbody></table></body></html>
  `)
  w.document.close()
  w.print()
  w.close()
}

export default function Dashboard() {
  const { isAdmin } = useAuth()
  const lastUpdated = new Date().toLocaleString()
  const [summary, setSummary] = useState({
    totalStations: 0,
    avgWqi: 0,
    cleanCount: 0,
    pollutedCount: 0,
    slightlyPollutedCount: 0,
  })
  const [stations, setStations] = useState([])
  const [years, setYears] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  /** Primary scope for dashboard: canonical river name (backend `river_name`). Empty = all rivers. */
  const [dashboardRiver, setDashboardRiver] = useState('')

  // Station WQI Trend
  const [trendStation, setTrendStation] = useState('')
  const [trendYear, setTrendYear] = useState('')
  const [timeSeries, setTimeSeries] = useState([])

  // Anomaly
  const [anomalyStation, setAnomalyStation] = useState('')
  const [anomalies, setAnomalies] = useState([])
  const [anomalyTimeSeries, setAnomalyTimeSeries] = useState([])

  // Export — uses filtered dataset table rows (no extra reload)
  const [exportData, setExportData] = useState([])
  const [exportQuery, setExportQuery] = useState(null)

  // Latest critical alert for dashboard panel
  const [latestCriticalAlert, setLatestCriticalAlert] = useState(null)
  const [dataRevision, setDataRevision] = useState(0)

  useEffect(() => {
    const bump = () => setDataRevision((n) => n + 1)
    window.addEventListener(SMARTRIVER_DATASET_CHANGED, bump)
    return () => window.removeEventListener(SMARTRIVER_DATASET_CHANGED, bump)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [stationList, yearList] = await Promise.all([
          dashboardApi.getStations(),
          dashboardApi.getYears(),
        ])
        if (cancelled) return
        const st = Array.isArray(stationList) ? stationList : []
        setStations(st)
        setYears(Array.isArray(yearList) ? yearList : [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load dashboard')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [dataRevision])

  useEffect(() => {
    let cancelled = false
    dashboardApi
      .getSummary({ river_name: dashboardRiver || undefined })
      .then((s) => {
        if (cancelled) return
        setSummary({
          totalStations: s.totalStations ?? 0,
          avgWqi: s.avgWqi ?? 0,
          cleanCount: s.cleanCount ?? 0,
          pollutedCount: s.pollutedCount ?? 0,
          slightlyPollutedCount: s.slightlyPollutedCount ?? 0,
        })
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [dashboardRiver, dataRevision])

  async function handleExportCsv() {
    try {
      const rows = exportQuery
        ? await dashboardApi.getReadingsTable({ ...exportQuery, limit: 100000, offset: 0 })
        : exportData
      exportCsv(rows)
    } catch {
      exportCsv(exportData)
    }
  }

  async function handleExportPrint() {
    try {
      const rows = exportQuery
        ? await dashboardApi.getReadingsTable({ ...exportQuery, limit: 100000, offset: 0 })
        : exportData
      exportPrint(rows)
    } catch {
      exportPrint(exportData)
    }
  }

  useEffect(() => {
    let cancelled = false
    dashboardApi
      .getTimeSeries({
        river_name: dashboardRiver || undefined,
        year: trendYear || undefined,
        limit: 1000,
      })
      .then((res) => {
        if (!cancelled) setTimeSeries(Array.isArray(res?.series) ? res.series : [])
      })
      .catch(() => { if (!cancelled) setTimeSeries([]) })
    return () => { cancelled = true }
  }, [dashboardRiver, trendYear, dataRevision])

  useEffect(() => {
    if (!isAdmin) return
    let cancelled = false
    Promise.all([
      dashboardApi.getTimeSeries({ river_name: dashboardRiver || undefined, limit: 500 }),
      dashboardApi.getAnomalies({ river_name: dashboardRiver || undefined, limit: 500 }),
    ]).then(([tsRes, anom]) => {
      if (!cancelled) {
        setAnomalyTimeSeries(Array.isArray(tsRes?.series) ? tsRes.series : [])
        setAnomalies(Array.isArray(anom) ? anom : [])
      }
    }).catch(() => { if (!cancelled) { setAnomalyTimeSeries([]); setAnomalies([]) } })
    return () => { cancelled = true }
  }, [isAdmin, dashboardRiver, dataRevision])

  useEffect(() => {
    let cancelled = false
    dashboardApi.getAlertsByType({ limit: 200, river_name: dashboardRiver || undefined }).then(({ historical }) => {
      if (cancelled) return
      const combined = Array.isArray(historical) ? historical : []
      const polluted = combined.filter((a) => (a.river_status || '').toLowerCase() === 'polluted')
      const slightly = combined.filter((a) => (a.river_status || '').toLowerCase() === 'slightly_polluted')
      const sortDesc = (arr) => arr.sort((a, b) => (b.date || '').localeCompare(a.date || ''))
      const latestPolluted = sortDesc(polluted)[0]
      const latestSlightly = sortDesc(slightly)[0]
      setLatestCriticalAlert(latestPolluted || latestSlightly || null)
    }).catch(() => { if (!cancelled) setLatestCriticalAlert(null) })
    return () => { cancelled = true }
  }, [dashboardRiver, dataRevision])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
      <div className="flex flex-wrap items-end gap-4 mt-2">
        <div>
          <label className="label">River</label>
          <select
            value={dashboardRiver}
            onChange={(e) => setDashboardRiver(e.target.value)}
            className="input-field w-auto min-w-[220px]"
          >
            <option value="">All rivers</option>
            {dashboardApi.uniqueRiverNamesFromStations(stations).map((rn) => (
              <option key={rn} value={rn}>{rn}</option>
            ))}
          </select>
        </div>
        <p className="text-sm text-surface-500 pb-1">
          Scope KPIs, map, table export, trends, and alerts to one water body — or view all rivers.
        </p>
      </div>
      <div className="text-sm text-surface-500 mt-2">
        <div>Data source: historical and simulated live monitoring</div>
        <div>Last Updated: {lastUpdated}</div>
      </div>
      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure the backend is running; the River Monitoring Dataset loads automatically on startup when placed in the datasets folder.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading…</p>}

      <DashboardSummary
        totalStations={summary.totalStations}
        avgWqi={summary.avgWqi}
        cleanCount={summary.cleanCount}
        pollutedCount={summary.pollutedCount}
        slightlyPollutedCount={summary.slightlyPollutedCount}
        riverName={dashboardRiver}
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
              : `${latestCriticalAlert.station_name || latestCriticalAlert.station_code || 'Unknown'} — ${
                (latestCriticalAlert.river_status || '').toLowerCase() === 'slightly_polluted'
                  ? 'Monitor closely'
                  : 'Immediate attention required'
              }`}
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
        <RiverMap
          stations={
            dashboardRiver
              ? stations.filter((s) => (s.river_name || s.station_name) === dashboardRiver)
              : stations
          }
          height={360}
          useDefaultStations={stations.length === 0}
        />
      </div>

      {/* Export Report — CSV, PDF, Print */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Export Report</h2>
        <p className="text-sm text-surface-500 mb-4">Download or print reports based on the current dataset filters: Station, Date, WQI, and river status.</p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleExportCsv}
            className="btn-primary"
          >
            Download CSV
          </button>
          <button
            type="button"
            onClick={handleExportPrint}
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
          description="Historical monitoring only (to today). Use Pollution Forecast for predicted WQI."
          onDataChange={setExportData}
          onQueryChange={setExportQuery}
          syncedRiverName={dashboardRiver}
          datasetRevision={dataRevision}
        />
      </div>

      {/* WQI Trend Analysis — Line chart, filter by station and year */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-4">WQI trend analysis</h2>
        <p className="text-sm text-surface-500 mb-4">
          Historical and simulated live WQI over time for the river selected above (and optional year).{' '}
          <Link to="/forecast" className="font-medium text-cyan-700 hover:text-cyan-900 underline">
            Open Pollution Forecast
          </Link>
          {' '}for predicted WQI.
        </p>
        <div className="flex flex-wrap gap-4 mb-4">
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

      {isAdmin && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="font-display font-semibold text-surface-800 mb-4">Anomaly Detection</h2>
          <p className="text-sm text-surface-500 mb-4">Uses the river scope from the top of the dashboard. Anomalies are marked on the chart and listed below.</p>
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
                    <th className="px-4 py-2 font-medium text-surface-700">River</th>
                    <th className="px-4 py-2 font-medium text-surface-700">Station</th>
                    <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                    <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                    <th className="px-4 py-2 font-medium text-surface-700">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.length === 0 ? (
                    <tr><td colSpan={5} className="px-4 py-6 text-center text-surface-500">No anomalies for this river.</td></tr>
                  ) : (
                    anomalies.map((a, i) => (
                      <tr key={i} className="border-t border-surface-100">
                        <td className="px-4 py-2 text-surface-800">{a.river_name || '—'}</td>
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