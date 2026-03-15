/**
 * River Health — Map + dataset table. All data from dataset.
 * Map shows station name, latest WQI, river status. Table: filter by station, date, status; sort by WQI.
 */
import { useState, useEffect } from 'react'
import RiverHealthIndicator from '../components/dashboard/RiverHealthIndicator'
import RiverMap from '../components/map/RiverMap'
import * as dashboardApi from '../api/dashboard'

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

  // Dataset table filters
  const [tableStation, setTableStation] = useState('')
  const [tableDateFrom, setTableDateFrom] = useState('')
  const [tableDateTo, setTableDateTo] = useState('')
  const [tableStatus, setTableStatus] = useState('')
  const [tableSortOrder, setTableSortOrder] = useState('asc')
  const [tableData, setTableData] = useState([])
  const [years, setYears] = useState([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [list, yearList] = await Promise.all([
          dashboardApi.getStations(),
          dashboardApi.getYears(),
        ])
        if (!cancelled) {
          setStations(Array.isArray(list) ? list : [])
          setYears(Array.isArray(yearList) ? yearList : [])
        }
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
  }, [])

  useEffect(() => {
    let cancelled = false
    dashboardApi.getReadingsTable({
      station_name: tableStation || undefined,
      date_from: tableDateFrom || undefined,
      date_to: tableDateTo || undefined,
      status: tableStatus || undefined,
      sort_by: 'wqi',
      sort_order: tableSortOrder,
      limit: 2000,
    }).then((data) => {
      if (!cancelled) setTableData(Array.isArray(data) ? data : [])
    }).catch(() => { if (!cancelled) setTableData([]) })
    return () => { cancelled = true }
  }, [tableStation, tableDateFrom, tableDateTo, tableStatus, tableSortOrder])

  const filteredStations =
    filter === 'all'
      ? stations
      : stations.filter((s) => s.river_status === filter)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-900">River health status</h1>
          <p className="text-surface-600 mt-0.5">Monitoring stations and dataset from Lampiran A - Sungai Kulim</p>
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
          {error}. Ensure the backend is running; dataset loads on startup.
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

      {/* Dataset table — filter by station, date, status; sort by WQI */}
      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Dataset table</h2>
        <p className="text-sm text-surface-500 mb-4">Station Name, Date, WQI, River Status. Filter by station, date range, status; sort by WQI.</p>
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="label">Filter by station</label>
            <select
              value={tableStation}
              onChange={(e) => setTableStation(e.target.value)}
              className="input-field w-auto min-w-[180px]"
            >
              <option value="">All</option>
              {stations.map((s) => (
                <option key={s.station_code} value={s.station_name || s.station_code}>
                  {s.station_name || s.station_code}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">From date</label>
            <input
              type="date"
              value={tableDateFrom}
              onChange={(e) => setTableDateFrom(e.target.value)}
              className="input-field w-auto"
            />
          </div>
          <div>
            <label className="label">To date</label>
            <input
              type="date"
              value={tableDateTo}
              onChange={(e) => setTableDateTo(e.target.value)}
              className="input-field w-auto"
            />
          </div>
          <div>
            <label className="label">Filter by status</label>
            <select
              value={tableStatus}
              onChange={(e) => setTableStatus(e.target.value)}
              className="input-field w-auto min-w-[140px]"
            >
              <option value="">All</option>
              <option value="clean">Clean</option>
              <option value="slightly_polluted">Slightly Polluted</option>
              <option value="polluted">Polluted</option>
            </select>
          </div>
          <div>
            <label className="label">Sort by WQI</label>
            <select
              value={tableSortOrder}
              onChange={(e) => setTableSortOrder(e.target.value)}
              className="input-field w-auto min-w-[120px]"
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto rounded-lg border border-surface-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-100 text-left">
                <th className="px-4 py-2 font-medium text-surface-700">Station Name</th>
                <th className="px-4 py-2 font-medium text-surface-700">Date</th>
                <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
                <th className="px-4 py-2 font-medium text-surface-700">River Status</th>
              </tr>
            </thead>
            <tbody>
              {tableData.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-surface-500">No data for selected filters.</td></tr>
              ) : (
                tableData.map((r, i) => (
                  <tr key={i} className="border-t border-surface-100">
                    <td className="px-4 py-2 font-medium text-surface-800">{r.station_name || '—'}</td>
                    <td className="px-4 py-2 text-surface-800">{r.date || '—'}</td>
                    <td className="px-4 py-2">{r.wqi != null ? Number(r.wqi).toFixed(1) : '—'}</td>
                    <td className="px-4 py-2"><RiverHealthIndicator wqi={r.wqi} compact /></td>
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