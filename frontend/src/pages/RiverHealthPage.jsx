/**
 * River Health — Map + dataset table. All data from dataset.
 * Map shows station name, latest WQI, river status. Table: filter by station, date, status; sort by WQI.
 */
import { useState, useEffect } from 'react'
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

export default function RiverHealthPage() {
  const [filter, setFilter] = useState('all')
  const [stations, setStations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedStation, setSelectedStation] = useState(null)
  const [dataRevision, setDataRevision] = useState(0)

  useEffect(() => {
    const bump = () => setDataRevision((n) => n + 1)
    window.addEventListener(SMARTRIVER_DATASET_CHANGED, bump)
    return () => window.removeEventListener(SMARTRIVER_DATASET_CHANGED, bump)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const list = await dashboardApi.getStations()
        if (!cancelled) setStations(Array.isArray(list) ? list : [])
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load')
          setStations([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [dataRevision])

  const filteredStations =
    filter === 'all'
      ? stations
      : stations.filter((s) => s.river_status === filter)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-900">River health status</h1>
          <p className="text-surface-600 mt-0.5">River monitoring stations and readings from the River Monitoring Dataset</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {['all', 'clean', 'slightly_polluted', 'polluted'].map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                filter === f ? 'bg-river-600 text-white' : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
              }`}
            >
              {f === 'all' ? 'All' : formatStatus(f)}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Ensure the backend is running; monitoring data loads on startup.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading…</p>}

      {/* Map — station name, latest WQI, river status */}
      <div className="card p-0 overflow-hidden">
        <div className="px-5 py-3 border-b border-surface-200">
          <h2 className="font-display font-semibold text-surface-800">River monitoring map</h2>
          <p className="text-sm text-surface-500">Station name, latest WQI, and river status from dataset. Click a marker for details.</p>
        </div>
        {filteredStations.length === 0 && !loading ? (
          <div className="flex items-center justify-center text-surface-500 py-24">No stations in dataset.</div>
        ) : (
          <RiverMap
            stations={filteredStations}
            height={360}
            onStationClick={setSelectedStation}
            useDefaultStations={false}
          />
        )}
      </div>

      <DatasetTable
        title="Dataset table"
        description="Historical monitoring (to today), same slice as the dashboard overview. Switch data type to view ML forecast rows."
        datasetRevision={dataRevision}
      />
    </div>
  )
}