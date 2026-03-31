/**
 * Anomaly Detection — Per station. Select station name; display anomaly chart + table.
 * Table: Station, Date, WQI, Reason (Abnormal spike). All data from dataset.
 */
import { useState, useEffect, useCallback } from 'react'
import WQIAnomalyChart from '../components/charts/WQIAnomalyChart'
import * as dashboardApi from '../api/dashboard'
import * as datasetsApi from '../api/datasets'

export default function AnomalyDetectionPage() {
  const [stations, setStations] = useState([])
  const [river, setRiver] = useState('')
  const [timeSeries, setTimeSeries] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    if (stations.length === 0) {
      setTimeSeries([])
      setAnomalies([])
      return
    }
    setError(null)
    try {
      const [series, list] = await Promise.all([
        dashboardApi.getTimeSeries({ river_name: river || undefined, limit: 500 }),
        dashboardApi.getAnomalies({ river_name: river || undefined, limit: 500 }),
      ])
      setTimeSeries(Array.isArray(series?.series) ? series.series : (Array.isArray(series) ? series : []))
      setAnomalies(Array.isArray(list) ? list : [])
    } catch (e) {
      setError(e.message || 'Failed to load data')
      setTimeSeries([])
      setAnomalies([])
    }
  }, [river, stations.length])

  useEffect(() => {
    let cancelled = false
    async function loadStations() {
      try {
        const list = await dashboardApi.getStations()
        if (!cancelled && Array.isArray(list) && list.length > 0) {
          setStations(list)
          const rivers = dashboardApi.uniqueRiverNamesFromStations(list)
          setRiver((prev) => prev || rivers[0] || '')
        }
      } catch (e) {
        if (!cancelled) setError(e.message || 'Failed to load stations')
      }
    }
    loadStations()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    if (stations.length === 0) {
      setLoading(false)
      return
    }
    setLoading(true)
    fetchData()
      .then(() => { if (!cancelled) setLoading(false) })
      .catch(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [fetchData, stations.length])

  const runAnomalyDetection = async () => {
    setRunning(true)
    setError(null)
    try {
      await datasetsApi.predictAnomaly(null)
      await fetchData()
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Anomaly detection failed. Ensure dataset is loaded and model is trained.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Anomaly detection</h1>
        <p className="text-surface-600 mt-0.5">
          Isolation Forest on WQI. Select a river to scope anomalies. Chart and table show river, station, date, WQI, and reason.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-4">
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
        <div className="pt-6">
          <button
            type="button"
            onClick={runAnomalyDetection}
            disabled={loading || running}
            className="btn-primary"
          >
            {running ? 'Running…' : 'Run anomaly detection (dataset)'}
          </button>
        </div>
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Anomaly chart</h2>
        <p className="text-sm text-surface-500 mb-4">WQI time series with anomaly points (red). Title and labels from dataset.</p>
        {loading ? (
          <p className="text-surface-500 py-8">Loading…</p>
        ) : timeSeries.length === 0 ? (
          <div className="h-[340px] flex items-center justify-center text-surface-500">No time series for this river. Ensure backend and dataset are loaded.</div>
        ) : (
          <WQIAnomalyChart data={timeSeries} anomalies={anomalies} height={340} />
        )}
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Anomaly table</h2>
        <p className="text-sm text-surface-500 mb-4">River, station, date, WQI, reason (abnormal spike).</p>
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
                <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">No anomalies for this river.</td></tr>
              ) : (
                anomalies.map((a, i) => (
                  <tr key={i} className="border-t border-surface-100 hover:bg-surface-50">
                    <td className="px-4 py-2 text-surface-800">{a.river_name || '—'}</td>
                    <td className="px-4 py-2 font-medium text-surface-800">{a.station_name || a.station_code || '—'}</td>
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
  )
}