import { useState } from 'react'

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
    <div className="space-y-6 animate-fade-in max-w-xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Report export</h1>
        <p className="text-surface-600 mt-0.5">Download WQI and status data as CSV or PDF</p>
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
