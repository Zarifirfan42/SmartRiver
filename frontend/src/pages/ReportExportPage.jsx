import { useState, useEffect } from 'react'
import * as dashboardApi from '../api/dashboard'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import RiverHealthIndicator from '../components/dashboard/RiverHealthIndicator'

const formats = [
  { id: 'csv', label: 'CSV' },
  { id: 'pdf', label: 'PDF' },
]

export default function ReportExportPage() {
  const [format, setFormat] = useState('csv')
  const [dateFrom, setDateFrom] = useState('2025-01-01')
  const [dateTo, setDateTo] = useState('2025-03-05')
  const [exporting, setExporting] = useState(false)
  const [done, setDone] = useState(false)
  const [previewData, setPreviewData] = useState([])
  const [previewLoading, setPreviewLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function fetchPreview() {
      setPreviewLoading(true)
      try {
        const data = await dashboardApi.getWqiData({ limit: 1000 })
        if (!cancelled && Array.isArray(data)) setPreviewData(data)
      } catch {
        if (!cancelled) setPreviewData([])
      } finally {
        if (!cancelled) setPreviewLoading(false)
      }
    }
    fetchPreview()
    return () => { cancelled = true }
  }, [])

  const filtered = previewData.filter((r) => {
    const d = r.date || ''
    if (dateFrom && d < dateFrom) return false
    if (dateTo && d > dateTo) return false
    return true
  })
  const avgWqi = filtered.length
    ? filtered.reduce((s, r) => s + Number(r.wqi || 0), 0) / filtered.length
    : 0
  const stationsInRange = [...new Set(filtered.map((r) => r.station_code || r.station))].length

  const handleExport = async (e) => {
    e.preventDefault()
    setExporting(true)
    setDone(false)
    try {
      // TODO: call API POST /reports/export
      await new Promise((r) => setTimeout(r, 1200))
      setDone(true)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Report export</h1>
        <p className="text-surface-600 mt-0.5">Download WQI and status data as CSV or PDF. Preview data in the selected date range below.</p>
      </div>

      {/* Preview visualization — meaningful for FYP demo */}
      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Data preview (selected date range)</h2>
        {previewLoading ? (
          <p className="text-surface-500 py-6">Loading preview…</p>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
              <div className="rounded-lg border border-surface-200 bg-surface-50 px-4 py-3">
                <p className="text-sm text-surface-500">Records</p>
                <p className="text-xl font-semibold text-surface-900">{filtered.length}</p>
              </div>
              <div className="rounded-lg border border-surface-200 bg-surface-50 px-4 py-3">
                <p className="text-sm text-surface-500">Stations</p>
                <p className="text-xl font-semibold text-surface-900">{stationsInRange}</p>
              </div>
              <div className="rounded-lg border border-surface-200 bg-surface-50 px-4 py-3">
                <p className="text-sm text-surface-500">Avg WQI</p>
                <p className="text-xl font-semibold text-surface-900">{filtered.length ? avgWqi.toFixed(1) : '—'}</p>
              </div>
              <div className="rounded-lg border border-surface-200 bg-surface-50 px-4 py-3 flex items-center gap-2">
                <p className="text-sm text-surface-500">Status</p>
                <RiverHealthIndicator wqi={avgWqi} compact />
              </div>
            </div>
            {filtered.length > 0 ? (
              <div>
                <p className="text-sm text-surface-500 mb-2">WQI trend in range (sample)</p>
                <TimeSeriesChart
                  data={filtered
                    .sort((a, b) => String(a.date).localeCompare(String(b.date)))
                    .map((r) => ({ date: r.date, wqi: r.wqi }))}
                  height={220}
                />
              </div>
            ) : (
              <p className="text-surface-500 py-6">No data in the selected date range. Adjust dates or ensure the backend has loaded data.</p>
            )}
          </>
        )}
      </div>

      <form onSubmit={handleExport} className="card space-y-5">
        {done && (
          <div className="rounded-lg bg-eco-50 px-3 py-2 text-sm text-eco-800">Report generated. Download will start shortly.</div>
        )}
        <div>
          <label className="label">Format</label>
          <div className="flex gap-4">
            {formats.map((f) => (
              <label key={f.id} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="format"
                  value={f.id}
                  checked={format === f.id}
                  onChange={() => setFormat(f.id)}
                  className="text-river-600 focus:ring-river-500"
                />
                <span>{f.label}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">From date</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label className="label">To date</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="input-field"
            />
          </div>
        </div>
        <button type="submit" disabled={exporting} className="btn-primary">
          {exporting ? 'Generating…' : 'Export report'}
        </button>
      </form>
    </div>
  )
}
