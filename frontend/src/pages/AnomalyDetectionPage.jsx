import { useState, useEffect } from 'react'
import WQIAnomalyChart from '../components/charts/WQIAnomalyChart'
import * as dashboardApi from '../api/dashboard'
import * as datasetsApi from '../api/datasets'

export default function AnomalyDetectionPage() {
  const [timeSeries, setTimeSeries] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

  const fetchData = async () => {
    setError(null)
    try {
      const [series, list] = await Promise.all([
        dashboardApi.getTimeSeries({ limit: 500 }),
        dashboardApi.getAnomalies({ limit: 500 }),
      ])
      setTimeSeries(Array.isArray(series) ? series : [])
      setAnomalies(Array.isArray(list) ? list : [])
    } catch (e) {
      setError(e.message || 'Failed to load data')
      setTimeSeries([])
      setAnomalies([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchData().then(() => {
      if (!cancelled) setLoading(false)
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  const runAnomalyDetection = async () => {
    setRunning(true)
    setError(null)
    try {
      await datasetsApi.predictAnomaly(null)
      await fetchData()
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Anomaly detection failed. Train the model first (ML Train) or upload a dataset.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Anomaly detection</h1>
        <p className="text-surface-600 mt-0.5">
          Isolation Forest on the latest uploaded dataset. Anomalies are marked on the chart and listed below.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-4">
        <button
          type="button"
          onClick={runAnomalyDetection}
          disabled={loading || running}
          className="btn-primary"
        >
          {running ? 'Running…' : 'Run anomaly detection (latest dataset)'}
        </button>
        <p className="text-sm text-surface-500 self-center">
          Detection runs automatically when you run preprocessing after uploading new data.
        </p>
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-2">WQI with anomalies</h2>
        <p className="text-sm text-surface-500 mb-4">
          Red points indicate abnormal spikes detected by the model.
        </p>
        {loading ? (
          <p className="text-surface-500 py-8">Loading…</p>
        ) : timeSeries.length === 0 ? (
          <p className="text-surface-500 py-8">No time series data. Upload a dataset and run preprocessing.</p>
        ) : (
          <WQIAnomalyChart data={timeSeries} anomalies={anomalies} height={340} />
        )}
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Anomaly table</h2>
        <p className="text-sm text-surface-500 mb-4">Date, station, WQI, and reason for each detected anomaly.</p>
        {anomalies.length === 0 ? (
          <p className="text-surface-500 py-4">No anomalies in the latest run.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border border-surface-200 rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-surface-100 text-left">
                  <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Station</th>
                  <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                  <th className="px-4 py-2 font-medium text-surface-700">Reason</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a, i) => (
                  <tr key={i} className="border-t border-surface-200 hover:bg-surface-50">
                    <td className="px-4 py-2 text-surface-800">{a.date || '—'}</td>
                    <td className="px-4 py-2 text-surface-800">{a.station_code || '—'}</td>
                    <td className="px-4 py-2 text-surface-800">{a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}</td>
                    <td className="px-4 py-2 text-amber-700">{a.reason || 'Abnormal spike'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
