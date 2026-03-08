/**
 * Dashboard — Main dashboard page
 * Shows river health summary, WQI gauge, time-series and forecast charts.
 */
import { useState, useEffect } from 'react'
import { DashboardSummary } from '../dashboard'
import WQIChart from '../charts/WQIChart'

export default function Dashboard() {
  const [summary, setSummary] = useState({
    totalStations: 0,
    avgWqi: 0,
    cleanCount: 0,
    pollutedCount: 0,
  })
  const [wqiData, setWqiData] = useState([])

  // TODO: fetch from API GET /api/v1/dashboard/summary and /dashboard/time-series
  useEffect(() => {
    setSummary({
      totalStations: 12,
      avgWqi: 68.5,
      cleanCount: 5,
      pollutedCount: 3,
    })
    setWqiData([
      { date: '01 Jan', wqi: 72 },
      { date: '05 Jan', wqi: 68 },
      { date: '10 Jan', wqi: 71 },
      { date: '15 Jan', wqi: 65 },
      { date: '20 Jan', wqi: 69 },
    ])
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
      <DashboardSummary
        totalStations={summary.totalStations}
        avgWqi={summary.avgWqi}
        cleanCount={summary.cleanCount}
        pollutedCount={summary.pollutedCount}
      />
      <WQIChart data={wqiData} title="WQI Trend" />
    </div>
  )
}
