import { useState } from 'react'

const mockDatasets = [
  { id: 1, name: 'DOE Klang 2024', size: '2.4 MB', rows: 12500, created: '2025-02-01' },
  { id: 2, name: 'DOE National Q1 2024', size: '8.1 MB', rows: 42000, created: '2025-01-15' },
]

export default function DatasetUploadPage() {
  const [file, setFile] = useState(null)
  const [name, setName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState(false)

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

  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">Dataset upload</h1>
        <p className="text-surface-600 mt-0.5">Upload DOE Malaysia CSV for processing (Admin)</p>
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
          {mockDatasets.map((d) => (
            <div key={d.id} className="flex items-center justify-between rounded-lg border border-surface-200 px-4 py-3">
              <span className="font-medium text-surface-800">{d.name}</span>
              <span className="text-sm text-surface-500">{d.rows} rows · {d.size}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
