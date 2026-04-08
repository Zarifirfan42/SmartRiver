/**
 * Dashboard — River monitoring: KPIs, map, dataset table, WQI trend + ML forecast, export.
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { DashboardSummary } from '../dashboard'
import RiverMap from '../components/map/RiverMap'
import DatasetTable from '../components/dataset/DatasetTable'
import WqiHistoricalForecastCard from '../components/dashboard/WqiHistoricalForecastCard'
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
  const headers = ['River', 'Date', 'Station Name', 'WQI', 'River Status']
  const csv = [headers.join(',')].concat(
    rows.map((r) =>
      [
        `"${(r.river_name || '').replace(/"/g, '""')}"`,
        r.date || '',
        `"${(r.station_name || r.station || '').replace(/"/g, '""')}"`,
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

function exportPrint(rows, targetWindow = null) {
  const w = targetWindow || window.open('', '_blank')
  if (!w) return false
  w.document.write(`
    <!DOCTYPE html><html><head><title>SmartRiver Report</title>
    <style>table{border-collapse:collapse;width:100%} th,td{border:1px solid #ccc;padding:6px 10px;text-align:left} th{background:#f1f5f9}</style>
    </head><body>
    <h1>SmartRiver — Dataset Report</h1>
    <p>Generated: ${new Date().toLocaleString()}</p>
    <table>
    <thead><tr><th>River</th><th>Date</th><th>Station</th><th>WQI</th><th>River Status</th></tr></thead>
    <tbody>
    ${(rows || []).map((r) => `<tr><td>${(r.river_name || '—').replace(/</g, '&lt;')}</td><td>${r.date || '—'}</td><td>${(r.station_name || r.station || '—').replace(/</g, '&lt;')}</td><td>${r.wqi != null ? Number(r.wqi).toFixed(1) : '—'}</td><td>${formatStatus(r.river_status)}</td></tr>`).join('')}
    </tbody></table></body></html>
  `)
  w.document.close()
  // Wait for the popup document to finish rendering before printing.
  // Printing immediately can fail on some browsers.
  const runPrint = () => {
    try {
      w.focus()
      w.print()
      // Auto-close after the print dialog completes when supported.
      w.onafterprint = () => {
        try { w.close() } catch {}
      }
    } catch {}
  }
  if (w.document.readyState === 'complete') {
    setTimeout(runPrint, 50)
  } else {
    w.onload = () => setTimeout(runPrint, 50)
  }
  return true
}

export default function Dashboard() {
  const lastUpdated = new Date().toLocaleString()
  const [summary, setSummary] = useState({
    totalStations: 0,
    avgWqi: 0,
    cleanCount: 0,
    pollutedCount: 0,
    slightlyPollutedCount: 0,
    /** YYYY-MM-DD from API — aligns critical-alert filter with summary (server calendar day). */
    serverToday: null,
  })
  const [stations, setStations] = useState([])
  const [years, setYears] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  /** Primary scope for dashboard: canonical river name (backend `river_name`). Empty = all rivers. */
  const [dashboardRiver, setDashboardRiver] = useState('')

  // Export — full fetch uses DatasetTable filter query + top-level river (same for all logged-in users)
  const [exportData, setExportData] = useState([])
  const [exportQuery, setExportQuery] = useState(null)
  const [exportBusy, setExportBusy] = useState(false)

  // Latest critical alert for dashboard panel
  const [latestCriticalAlert, setLatestCriticalAlert] = useState(null)
  const [forecastPollutionAlertCount, setForecastPollutionAlertCount] = useState(0)
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
          serverToday: s.today ?? null,
        })
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [dashboardRiver, dataRevision])

  /** Merge dashboard river scope with table filters so export always matches what users set on the page. */
  function buildExportQuery() {
    const q = exportQuery && typeof exportQuery === 'object' ? { ...exportQuery } : {}
    if (dashboardRiver) q.river_name = dashboardRiver
    else delete q.river_name
    return q
  }

  async function handleExportCsv() {
    setExportBusy(true)
    try {
      const q = buildExportQuery()
      const hasFilters = Object.keys(q).length > 0
      const rows = hasFilters
        ? await dashboardApi.getReadingsTable({ ...q, limit: 100000, offset: 0 })
        : await dashboardApi.getReadingsTable({ limit: 100000, offset: 0 })
      exportCsv(Array.isArray(rows) ? rows : exportData)
    } catch {
      exportCsv(exportData)
    } finally {
      setExportBusy(false)
    }
  }

  async function handleExportPrint() {
    // Open popup synchronously on click to avoid browser popup blockers.
    const popup = window.open('', '_blank')
    if (!popup) {
      alert('Pop-up blocked. Please allow pop-ups for this site to export PDF/Print.')
      return
    }
    setExportBusy(true)
    try {
      const q = buildExportQuery()
      const rows = await dashboardApi.getReadingsTable({ ...q, limit: 100000, offset: 0 })
      exportPrint(Array.isArray(rows) ? rows : exportData, popup)
    } catch {
      exportPrint(exportData, popup)
    } finally {
      setExportBusy(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const today = summary.serverToday ? String(summary.serverToday).slice(0, 10) : ''
    if (!today) {
      setLatestCriticalAlert(null)
      return
    }
    dashboardApi.getAlertsByType({ limit: 200, river_name: dashboardRiver || undefined }).then(({ historical }) => {
      if (cancelled) return
      const combined = (Array.isArray(historical) ? historical : []).filter(
        (a) => String(a.date || '').slice(0, 10) === today,
      )
      const polluted = combined.filter((a) => (a.river_status || '').toLowerCase() === 'polluted')
      const slightly = combined.filter((a) => (a.river_status || '').toLowerCase() === 'slightly_polluted')
      const sortDesc = (arr) => [...arr].sort((a, b) => (b.date || '').localeCompare(a.date || ''))
      const latestPolluted = sortDesc(polluted)[0]
      const latestSlightly = sortDesc(slightly)[0]
      // Prioritize slightly polluted for the banner — primary operational focus; polluted shown when no slight alert
      setLatestCriticalAlert(latestSlightly || latestPolluted || null)
    }).catch(() => { if (!cancelled) setLatestCriticalAlert(null) })
    return () => { cancelled = true }
  }, [dashboardRiver, dataRevision, summary.serverToday])

  /** Forecast-side pollution flags (slightly polluted / polluted only) — same source as Alert monitoring → Forecast. */
  useEffect(() => {
    let cancelled = false
    dashboardApi
      .getAlertsByType({ limit: 500, river_name: dashboardRiver || undefined })
      .then(({ forecast }) => {
        if (!cancelled) setForecastPollutionAlertCount(Array.isArray(forecast) ? forecast.length : 0)
      })
      .catch(() => {
        if (!cancelled) setForecastPollutionAlertCount(0)
      })
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
        <div>
          KPIs use <span className="font-medium text-surface-700">one reading per station</span>: the server
          prefers <span className="font-medium text-surface-700">today’s</span> date when a row exists; otherwise
          the <span className="font-medium text-surface-700">latest historical</span> reading (same rule as the map).
        </div>
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

      {/* Today’s alert panel — slightly polluted first (primary); polluted when no slight */}
      {latestCriticalAlert && (
        <div
          className={`rounded-xl border p-4 shadow-sm ${
            (latestCriticalAlert.river_status || '').toLowerCase() === 'slightly_polluted'
              ? 'border-amber-200 bg-amber-50'
              : 'border-red-200 bg-red-50'
          }`}
        >
          <h2
            className={`font-display text-base font-semibold mb-2 ${
              (latestCriticalAlert.river_status || '').toLowerCase() === 'slightly_polluted'
                ? 'text-amber-900'
                : 'text-red-800'
            }`}
          >
            {(latestCriticalAlert.river_status || '').toLowerCase() === 'slightly_polluted'
              ? "Today's attention — slightly polluted"
              : "Today's critical alert — polluted"}
          </h2>
          <p
            className={`text-sm ${
              (latestCriticalAlert.river_status || '').toLowerCase() === 'slightly_polluted'
                ? 'text-amber-950'
                : 'text-red-900'
            }`}
          >
            <span aria-hidden>{(latestCriticalAlert.river_status || '').toLowerCase() === 'slightly_polluted' ? '⚠️' : '🚨'}</span>{' '}
            {latestCriticalAlert.message && String(latestCriticalAlert.message).trim()
              ? latestCriticalAlert.message.trim()
              : `${latestCriticalAlert.station_name || latestCriticalAlert.station_code || 'Unknown'} — ${
                (latestCriticalAlert.river_status || '').toLowerCase() === 'slightly_polluted'
                  ? 'Monitor closely'
                  : 'Immediate attention required'
              }`}
          </p>
          <Link
            to="/alerts"
            className={`inline-block mt-2 text-sm font-medium underline ${
              (latestCriticalAlert.river_status || '').toLowerCase() === 'slightly_polluted'
                ? 'text-amber-800 hover:text-amber-950'
                : 'text-red-700 hover:text-red-900'
            }`}
          >
            View all alerts →
          </Link>
        </div>
      )}

      {forecastPollutionAlertCount > 0 && (
        <div className="rounded-xl border border-cyan-200 bg-cyan-50/90 p-4 shadow-sm">
          <h2 className="font-display text-base font-semibold text-cyan-900 mb-1">Forecast pollution warnings</h2>
          <p className="text-sm text-cyan-950">
            The ML horizon (through end of 2026) includes{' '}
            <span className="font-semibold tabular-nums">{forecastPollutionAlertCount}</span> future point
            {forecastPollutionAlertCount === 1 ? '' : 's'} flagged as slightly polluted or polluted (same list as
            Alert monitoring).
          </p>
          <Link
            to="/alerts"
            className="inline-block mt-2 text-sm font-medium text-cyan-800 underline hover:text-cyan-950"
          >
            Open Alert monitoring (use Forecast filter) →
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

      <div className="mt-6">
        <DatasetTable
          title="Dataset overview"
          description="Default: historical monitoring (to server today). Switch Data type to Forecast for ML daily predictions (through end of 2026). The WQI trend section below also overlays forecast on the chart. Set filters here, then Export below. Default sort is date (earliest first)."
          onDataChange={setExportData}
          onQueryChange={setExportQuery}
          syncedRiverName={dashboardRiver}
          datasetRevision={dataRevision}
        />
      </div>

      {/* Export after table so filters are set first; query = river (top) + table filters */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Export report</h2>
        <p className="text-sm text-surface-500 mb-4">
          Download or print using the <strong>River</strong> selector at the top of the dashboard plus every filter in{' '}
          <strong>Dataset overview</strong> above (station, year/month or date range, status, historical vs forecast, sort).
          All logged-in users and admins use the same export rules.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={exportBusy}
            className="btn-primary disabled:opacity-50"
          >
            {exportBusy ? 'Preparing…' : 'Download CSV'}
          </button>
          <button
            type="button"
            onClick={handleExportPrint}
            disabled={exportBusy}
            className="btn-secondary disabled:opacity-50"
          >
            Print report
          </button>
          <span className="text-sm text-surface-500 self-center">PDF: use Print → Save as PDF in the print dialog.</span>
        </div>
      </div>

      <WqiHistoricalForecastCard
        stations={stations}
        years={years}
        dataRevision={dataRevision}
        riverName={dashboardRiver}
        pickRiver={false}
      />
    </div>
  )
}