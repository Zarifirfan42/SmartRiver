/**
 * Dashboard — Main dashboard page
 * Shows river health summary and WQI bar chart by station (data from API).
 */
import { useState, useEffect } from 'react'
import { DashboardSummary } from '../dashboard'
import WQIByStationChart from '../components/charts/WQIByStationChart'
import * as dashboardApi from '../api/dashboard'

export default function Dashboard() {
  const [summary, setSummary] = useState({
    totalStations: 0,
    avgWqi: 0,
    cleanCount: 0,
    pollutedCount: 0,
  })
  const [stations, setStations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const [s, stationList] = await Promise.all([
          dashboardApi.getSummary(),
          dashboardApi.getStations(),
        ])
        if (cancelled) return
        setSummary({
          totalStations: s.totalStations ?? 0,
          avgWqi: s.avgWqi ?? 0,
          cleanCount: s.cleanCount ?? 0,
          pollutedCount: s.pollutedCount ?? 0,
        })
        setStations(Array.isArray(stationList) ? stationList : [])
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load dashboard')
          setStations([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchData()
    return () => { cancelled = true }
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Upload a dataset and run preprocessing to see data.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading…</p>}
      <DashboardSummary
        totalStations={summary.totalStations}
        avgWqi={summary.avgWqi}
        cleanCount={summary.cleanCount}
        pollutedCount={summary.pollutedCount}
      />
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <WQIByStationChart stations={stations} height={320} />
      </div>
    </div>
  )
}
