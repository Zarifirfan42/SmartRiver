import { useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip)

const mockDatasets = [
  { id: 1, name: 'DOE Klang 2024', size: '2.4 MB', rows: 12500, created: '2025-02-01' },
  { id: 2, name: 'DOE National Q1 2024', size: '8.1 MB', rows: 42000, created: '2025-01-15' },
]

export default function DatasetUploadPage() {
  const [file, setFile] = useState(null)
  const [name, setName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [datasets] = useState(mockDatasets)

  const totalRows = datasets.reduce((s, d) => s + (d.rows || 0), 0)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    setSuccess(false)
    try {
      // TODO: call API POST /datasets/upload
      await new Promise((r) => setTimeout(r, 1500))
      setSuccess(true)
      setFile(null)
      setName('')
    } finally {
      setUploading(false)
    }
  }

  const chartData = {
    labels: datasets.map((d) => d.name.length > 18 ? d.name.slice(0, 18) + '…' : d.name),
    datasets: [
      {
        label: 'Rows',
        data: datasets.map((d) => d.rows),
        backgroundColor: 'rgba(6, 182, 212, 0.7)',
        borderColor: 'rgba(6, 182, 212, 1)',
        borderWidth: 1,
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: { display: true, text: 'Dataset size (rows)', font: { size: 14 } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.raw.toLocaleString()} rows` } },
    },
    scales: {
      x: { grid: { display: false }, ticks: { maxRotation: 25 } },
      y: { min: 0, ticks: { stepSize: 5000 }, grid: { color: '#e2e8f0' } },
    },
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Dataset upload</h1>
        <p className="text-surface-600 mt-0.5">Upload DOE Malaysia CSV for processing (Admin)</p>
      </div>

      {/* Summary + bar chart — meaningful visualization for FYP demo */}
      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Dataset overview</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <div className="rounded-lg border border-surface-200 bg-surface-50 px-4 py-3">
            <p className="text-sm text-surface-500">Datasets</p>
            <p className="text-xl font-semibold text-surface-900">{datasets.length}</p>
          </div>
          <div className="rounded-lg border border-surface-200 bg-surface-50 px-4 py-3">
            <p className="text-sm text-surface-500">Total rows</p>
            <p className="text-xl font-semibold text-surface-900">{totalRows.toLocaleString()}</p>
          </div>
        </div>
        {datasets.length > 0 ? (
          <div style={{ height: 220 }}>
            <Bar data={chartData} options={chartOptions} />
          </div>
        ) : (
          <p className="text-surface-500 py-6 text-sm">No datasets yet. Upload a CSV to see statistics here.</p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="card space-y-5">
        {success && (
          <div className="rounded-lg bg-eco-50 px-3 py-2 text-sm text-eco-800">Dataset uploaded successfully.</div>
        )}
        <div>
          <label className="label">Dataset name (optional)</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input-field"
            placeholder="e.g. DOE Klang 2024"
          />
        </div>
        <div>
          <label className="label">CSV file</label>
          <div className="mt-1 flex items-center gap-4">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-surface-600 file:mr-4 file:rounded-lg file:border-0 file:bg-river-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-river-700 hover:file:bg-river-100"
            />
          </div>
          <p className="mt-1 text-xs text-surface-500">DOE format: station, date, DO, BOD, COD, NH3-N, TSS, pH</p>
        </div>
        <button type="submit" disabled={!file || uploading} className="btn-primary">
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
      </form>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-3">Recent datasets</h2>
        <div className="space-y-2">
          {datasets.map((d) => (
            <div key={d.id} className="flex items-center justify-between rounded-lg border border-surface-200 px-4 py-3">
              <span className="font-medium text-surface-800">{d.name}</span>
              <span className="text-sm text-surface-500">{d.rows.toLocaleString()} rows · {d.size}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
