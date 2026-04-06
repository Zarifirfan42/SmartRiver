import { useState, useEffect, useCallback } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'
import * as datasetsApi from '../api/datasets'
import { notifyDatasetChanged } from '../constants/datasetEvents'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip)

export default function DatasetUploadPage() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)
  const [datasets, setDatasets] = useState([])
  const [deletingId, setDeletingId] = useState(null)
  const [trainingSummary, setTrainingSummary] = useState(null)

  const loadList = useCallback(async () => {
    setError(null)
    try {
      const res = await datasetsApi.listDatasets()
      const items = res?.items || res?.data?.items || []
      setDatasets(Array.isArray(items) ? items : [])
    } catch (e) {
      setDatasets([])
      setError(e.response?.data?.detail || e.message || 'Failed to list datasets')
    }
  }, [])

  useEffect(() => {
    loadList()
  }, [loadList])

  const totalRows = datasets.reduce((s, d) => s + (Number(d.row_count) || 0), 0)
  const sortedDatasets = datasets
    .slice()
    .sort((a, b) => {
      const ai = Number.isFinite(Number(a.id)) ? Number(a.id) : -1
      const bi = Number.isFinite(Number(b.id)) ? Number(b.id) : -1
      if (bi !== ai) return bi - ai
      const as = String(a.name || '')
      const bs = String(b.name || '')
      return as.localeCompare(bs)
    })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    setSuccess(false)
    setTrainingSummary(null)
    setError(null)
    try {
      const up = await datasetsApi.uploadDataset(file)
      if (up.error) {
        setError(typeof up.error === 'string' ? up.error : JSON.stringify(up))
        return
      }
      setSuccess(true)
      setFile(null)
      await loadList()
      notifyDatasetChanged({ reason: 'upload' })
    } catch (err) {
      const d = err.response?.data?.detail
      setError(typeof d === 'string' ? d : d ? JSON.stringify(d) : err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteDataset = async (d) => {
    const ok = window.confirm(`Delete dataset "${d.name || `Dataset ${d.id}`}"?`)
    if (!ok) return
    setDeletingId(d.id)
    setError(null)
    try {
      if (d.source === 'uploaded') {
        await datasetsApi.deleteDataset(d.id)
      } else if (d.source === 'filesystem') {
        await datasetsApi.deleteFilesystemDataset(d.file_path)
      } else {
        throw new Error('Unknown dataset source')
      }
      await loadList()
      notifyDatasetChanged({ reason: 'delete' })
    } catch (err) {
      const dmsg = err.response?.data?.detail
      setError(typeof dmsg === 'string' ? dmsg : err.message || 'Failed to delete dataset')
    } finally {
      setDeletingId(null)
    }
  }

  const chartData = {
    labels: datasets.map((d) => {
      const n = d.name || d.filename || `Dataset ${d.id}`
      return n.length > 22 ? `${n.slice(0, 22)}…` : n
    }),
    datasets: [
      {
        label: 'Rows (registered)',
        data: datasets.map((d) => Number(d.row_count) || 0),
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
      title: { display: true, text: 'Dataset size (row_count from upload)', font: { size: 14 } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.raw.toLocaleString()} rows` } },
    },
    scales: {
      x: { grid: { display: false }, ticks: { maxRotation: 25 } },
      y: { min: 0, ticks: { stepSize: 500 }, grid: { color: '#e2e8f0' } },
    },
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Dataset upload</h1>
        <p className="text-surface-600 mt-0.5">
          Upload a CSV: the server saves it, loads WQI into the dashboard, registers stations, refreshes forecast, and queues ML training. Re-uploading the same filename replaces the previous dataset (no duplicates).
          Supported: simplified format (<code className="text-xs bg-surface-100 px-1 rounded">date</code>,{' '}
          <code className="text-xs bg-surface-100 px-1 rounded">station_code</code>, parameters) or DOE-style exports (
          <code className="text-xs bg-surface-100 px-1 rounded">SMP-DAT</code>,{' '}
          <code className="text-xs bg-surface-100 px-1 rounded">ID STN BARU</code>, etc.).
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          {String(error)}
        </div>
      )}

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Dataset overview</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <div className="rounded-lg border border-surface-200 bg-surface-50 px-4 py-3">
            <p className="text-sm text-surface-500">Datasets</p>
            <p className="text-xl font-semibold text-surface-900">{datasets.length}</p>
          </div>
          <div className="rounded-lg border border-surface-200 bg-surface-50 px-4 py-3">
            <p className="text-sm text-surface-500">Total rows (upload metadata)</p>
            <p className="text-xl font-semibold text-surface-900">{totalRows.toLocaleString()}</p>
          </div>
        </div>
        {datasets.length > 0 ? (
          <div style={{ height: 220 }}>
            <Bar data={chartData} options={chartOptions} />
          </div>
        ) : (
          <p className="text-surface-500 py-6 text-sm">No datasets registered yet. Upload a CSV after signing in as admin.</p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="card space-y-5">
        {success && (
          <div className="rounded-lg bg-eco-50 px-3 py-2 text-sm text-eco-800 space-y-1">
            <p className="font-medium">Upload successful</p>
            <p>Dataset is saved, readings are loaded into the dashboard, and models were trained (Random Forest + anomaly; LSTM if TensorFlow is installed).</p>
            {trainingSummary?.error && (
              <p className="text-amber-800">Training note: {String(trainingSummary.error)}</p>
            )}
            {trainingSummary?.metrics?.random_forest_classification?.accuracy != null && (
              <p className="text-eco-900">
                RF accuracy: {(Number(trainingSummary.metrics.random_forest_classification.accuracy) * 100).toFixed(1)}%
                {trainingSummary.lstm_trained === false ? ' · LSTM skipped (install TensorFlow for full forecast training)' : ''}
              </p>
            )}
          </div>
        )}
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
          <p className="mt-1 text-xs text-surface-500">
            Required for dashboard: parsable date column, station identifier (station_code or DOE ID columns), and either
            WQI or raw parameters (DO, BOD, COD, NH3-N / AN, SS / TSS, pH). Optional: river_name column; else inferred from
            SUNGAI or station_code mapping.
          </p>
        </div>
        <button type="submit" disabled={!file || uploading} className="btn-primary">
            {uploading ? 'Uploading & loading…' : 'Upload & load into dashboard'}
        </button>
      </form>

      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-3">Recent datasets</h2>
        <div className="space-y-2">
          {datasets.length === 0 ? (
            <p className="text-sm text-surface-500">None yet.</p>
          ) : (
            sortedDatasets.map((d) => (
                <div key={d.id} className="rounded-lg border border-surface-200 px-4 py-3">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <span className="font-medium text-surface-800">{d.name || `Dataset ${d.id}`}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-surface-500">
                        {(Number(d.row_count) || 0).toLocaleString()} rows
                        {d.river_name ? ` · ${d.river_name}` : ''}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeleteDataset(d)}
                        disabled={deletingId === d.id}
                        className="rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-60"
                      >
                        {deletingId === d.id ? 'Deleting…' : 'Delete'}
                      </button>
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-surface-500">
                    <span>ID: {d.id}</span>
                    {d.source ? <span> · Source: {d.source}</span> : null}
                    {d.file_path ? <span> · Path: {d.file_path}</span> : null}
                    {d.created_at ? <span> · Uploaded: {String(d.created_at).replace('T', ' ').slice(0, 19)}</span> : null}
                  </div>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  )
}
