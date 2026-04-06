/**
 * Dashboard — River monitoring: KPIs, map, dataset table, historical WQI trend, export.
 * Forecast charts live on the Pollution Forecast page only.
 */
import { useState, useEffect, useMemo } from 'react'
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

/** Stations available for WQI trend dropdown (scoped by selected river, if any). */
function filterStationsForTrend(stations, riverName) {
  const list = Array.isArray(stations) ? stations : []
  const byKey = new Map()
  for (const s of list) {
    const key = (s.station_code || s.station_name || '').trim()
    if (!key) continue
    if (riverName && String(riverName).trim()) {
      if ((s.river_name || '').trim() !== String(riverName).trim()) continue
    }
    if (!byKey.has(key)) byKey.set(key, s)
  }
  return [...byKey.values()].sort((a, b) =>
    String(a.station_name || a.station_code).localeCompare(String(b.station_name || b.station_code), undefined, {
      sensitivity: 'base',
    })
  )
}

function stationApiKey(s) {
  return (s.station_code || s.station_name || '').trim()
}

function stationLabel(s) {
  const name = (s.station_name || '').trim()
  const code = (s.station_code || '').trim()
  if (name && code && name !== code) return `${name} (${code})`
  return name || code || 'Station'
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
    /** YYYY-MM-DD from API — aligns critical-alert filter with summary (server calendar day). */
    serverToday: null,
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
  const [trendSeriesToday, setTrendSeriesToday] = useState(null)
  const [trendRefreshTick, setTrendRefreshTick] = useState(0)

  // Anomaly
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

  /** Periodically refresh WQI time series so simulated live / new uploads show without full reload. */
  useEffect(() => {
    const id = setInterval(() => setTrendRefreshTick((t) => t + 1), 90_000)
    return () => clearInterval(id)
  }, [])

  const trendStationChoices = useMemo(
    () => filterStationsForTrend(stations, dashboardRiver),
    [stations, dashboardRiver],
  )

  /** Default or validate trend station when river/station list changes (one station = one clear trend line). */
  useEffect(() => {
    if (trendStationChoices.length === 0) {
      setTrendStation('')
      return
    }
    setTrendStation((prev) => {
      if (prev && trendStationChoices.some((s) => stationApiKey(s) === prev)) return prev
      return stationApiKey(trendStationChoices[0])
    })
  }, [trendStationChoices])

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
    const params = {
      river_name: dashboardRiver || undefined,
      year: trendYear || undefined,
      limit: 2000,
    }
    if (trendStation) {
      params.station_code = trendStation
    }
    dashboardApi
      .getTimeSeries(params)
      .then((res) => {
        if (cancelled) return
        setTimeSeries(Array.isArray(res?.series) ? res.series : [])
        setTrendSeriesToday(res?.today ?? null)
      })
      .catch(() => {
        if (!cancelled) {
          setTimeSeries([])
          setTrendSeriesToday(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [dashboardRiver, trendYear, trendStation, dataRevision, trendRefreshTick])

  useEffect(() => {
    if (!isAdmin) return
    let cancelled = false
    const tsParams = { river_name: dashboardRiver || undefined, limit: 1500 }
    const anomParams = { river_name: dashboardRiver || undefined, limit: 500 }
    if (trendStation) {
      tsParams.station_code = trendStation
      anomParams.station_code = trendStation
    }
    Promise.all([
      dashboardApi.getTimeSeries(tsParams),
      dashboardApi.getAnomalies(anomParams),
    ])
      .then(([tsRes, anom]) => {
        if (!cancelled) {
          setAnomalyTimeSeries(Array.isArray(tsRes?.series) ? tsRes.series : [])
          setAnomalies(Array.isArray(anom) ? anom : [])
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAnomalyTimeSeries([])
          setAnomalies([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [isAdmin, dashboardRiver, trendStation, dataRevision, trendRefreshTick])

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
          KPIs (stations, average WQI, clean / slightly polluted / polluted counts) use{' '}
          <span className="font-medium text-surface-700">readings dated today</span> on the server only.
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
          Choose a <strong>monitoring station</strong> for one WQI line per chart (same for all users and admins).
          Readings are historical plus simulated live through the server &quot;today&quot;; this section refreshes automatically every 90 seconds and when the dataset changes.{' '}
          <Link to="/forecast" className="font-medium text-cyan-700 hover:text-cyan-900 underline">
            Open Pollution Forecast
          </Link>
          {' '}for predicted WQI.
        </p>
        <div className="flex flex-wrap items-end gap-4 mb-4">
          <div>
            <label className="label">Station</label>
            <select
              value={trendStation}
              onChange={(e) => setTrendStation(e.target.value)}
              className="input-field w-auto min-w-[260px]"
              disabled={trendStationChoices.length === 0}
            >
              {trendStationChoices.length === 0 ? (
                <option value="">No stations for this river</option>
              ) : (
                trendStationChoices.map((s) => {
                  const v = stationApiKey(s)
                  return (
                    <option key={v} value={v}>
                      {stationLabel(s)}
                    </option>
                  )
                })
              )}
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
          <button
            type="button"
            className="btn-secondary text-sm"
            onClick={() => setTrendRefreshTick((t) => t + 1)}
          >
            Refresh WQI trend
          </button>
        </div>
        <p className="text-xs text-surface-500 mb-3">
          {trendSeriesToday
            ? `Series includes readings through ${trendSeriesToday} (server date).`
            : ' '}
        </p>
        {timeSeries.length > 0 ? (
          <TimeSeriesChart
            data={timeSeries}
            height={320}
            title="WQI trend"
            subtitle={(() => {
              const sel = trendStationChoices.find((s) => stationApiKey(s) === trendStation)
              const lab = sel ? stationLabel(sel) : trendStation || '—'
              return dashboardRiver ? `${lab} · ${dashboardRiver}` : lab
            })()}
          />
        ) : (
          <div className="h-[320px] flex items-center justify-center text-surface-500">No data for selected filters.</div>
        )}
      </div>

      {isAdmin && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="font-display font-semibold text-surface-800 mb-4">Anomaly Detection</h2>
          <p className="text-sm text-surface-500 mb-4">
            Uses the same river and <strong>station</strong> selection as WQI trend analysis above.
          </p>
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