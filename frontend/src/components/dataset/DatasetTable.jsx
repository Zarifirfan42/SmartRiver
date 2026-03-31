/**
 * Shared dataset table: Station Name, Date, WQI, River Status.
 * Used on Dashboard and River Health. Pagination (10/25/50), filters, sorting.
 * Data from API only (all dataset records).
 */
import { useState, useEffect } from 'react'
import RiverHealthIndicator from '../dashboard/RiverHealthIndicator'
import * as dashboardApi from '../../api/dashboard'

const PAGE_SIZES = [10, 25, 50]
const SORT_OPTIONS = [
  { value: 'wqi_asc', sort_by: 'wqi', sort_order: 'asc', label: 'WQI ascending' },
  { value: 'wqi_desc', sort_by: 'wqi', sort_order: 'desc', label: 'WQI descending' },
  { value: 'date_asc', sort_by: 'date', sort_order: 'asc', label: 'Date (earliest first)' },
  { value: 'date_desc', sort_by: 'date', sort_order: 'desc', label: 'Date (latest first)' },
]

const DATA_TYPE_OPTIONS = [
  { value: '', label: 'All data' },
  { value: 'historical', label: 'Historical (up to today)' },
  { value: 'forecast', label: 'Forecast (after today)' },
]

/**
 * @param {{ syncedRiverName?: string }} props When set, river filter is controlled (e.g. dashboard-wide selector); table skips its own river dropdown.
 */
export default function DatasetTable({
  title = 'Dataset table',
  description = 'River, station, date, WQI, and status. Filter and sort from dataset.',
  onDataChange,
  onQueryChange,
  syncedRiverName,
}) {
  const [stations, setStations] = useState([])
  const [years, setYears] = useState([])
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  /** River entity filter (canonical name, e.g. Sungai Klang). Empty = all rivers. */
  const [riverName, setRiverName] = useState('')
  const effectiveRiver =
    syncedRiverName !== undefined && syncedRiverName !== null ? syncedRiverName : riverName

  const [stationName, setStationName] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [monthYear, setMonthYear] = useState('')
  const [monthFilter, setMonthFilter] = useState('')
  const [status, setStatus] = useState('')
  const [dataType, setDataType] = useState('')
  const [sortValue, setSortValue] = useState('date_asc')
  const [pageSize, setPageSize] = useState(10)
  const [page, setPage] = useState(1)

  const sortOption = SORT_OPTIONS.find((o) => o.value === sortValue) || SORT_OPTIONS[2]

  useEffect(() => {
    let cancelled = false
    dashboardApi.getStations().then((list) => {
      if (!cancelled) setStations(Array.isArray(list) ? list : [])
    }).catch(() => { if (!cancelled) setStations([]) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    dashboardApi.getYears().then((res) => {
      if (!cancelled) setYears(Array.isArray(res) ? res : [])
    }).catch(() => { if (!cancelled) setYears([]) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    const offset = (page - 1) * pageSize
    const effYear = monthYear || undefined
    const effMonth = monthFilter !== '' ? Number(monthFilter) : undefined
    const effectiveDateFrom =
      effYear && effMonth
        ? `${effYear}-${String(effMonth).padStart(2, '0')}-01`
        : (dateFrom || undefined)
    const effectiveDateTo =
      effYear && effMonth
        ? `${effYear}-${String(effMonth).padStart(2, '0')}-${new Date(Number(effYear), effMonth, 0).getDate()}`
        : (dateTo || undefined)

    // Build query without sending "undefined"/empty-string values.
    // This prevents backend filters from accidentally excluding all rows.
    const query = { sort_by: sortOption.sort_by, sort_order: sortOption.sort_order }
    if (effectiveRiver) query.river_name = effectiveRiver
    if (stationName) query.station_name = stationName
    if (effectiveDateFrom) query.date_from = effectiveDateFrom
    if (effectiveDateTo) query.date_to = effectiveDateTo
    if (status) query.status = status
    if (dataType) query.data_type = dataType
    if (typeof onQueryChange === 'function') {
      onQueryChange(query)
    }

    const params = {
      ...query,
      limit: pageSize,
      offset,
    }

    if (import.meta.env.DEV) {
      console.debug('[SmartRiver] DatasetTable query:', { params })
    }

    const countParams = {}
    if (query.river_name) countParams.river_name = query.river_name
    if (query.station_name) countParams.station_name = query.station_name
    if (query.date_from) countParams.date_from = query.date_from
    if (query.date_to) countParams.date_to = query.date_to
    if (query.status) countParams.status = query.status
    if (query.data_type) countParams.data_type = query.data_type

    Promise.all([
      dashboardApi.getReadingsTable(params),
      dashboardApi.getReadingsCount({
        ...countParams,
      }),
    ])
      .then(([rows, count]) => {
        if (!cancelled) {
          const safeRows = Array.isArray(rows) ? rows : []
          if (import.meta.env.DEV) {
            console.log('Before filter:', Number(count) || 0)
            console.log('After filter:', safeRows.length)
            console.debug('[SmartRiver] DatasetTable rows (after backend filter):', {
              received: safeRows.length,
              total: count,
            })
          }
          setData(safeRows)
          setTotal(Number(count) || 0)
          setError(null)
          if (typeof onDataChange === 'function') {
            onDataChange(safeRows)
          }
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load table')
          setData([])
          setTotal(0)
          if (typeof onDataChange === 'function') {
            onDataChange([])
          }
        }
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [stationName, dateFrom, dateTo, monthYear, monthFilter, status, dataType, sortValue, pageSize, page])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const startRow = total === 0 ? 0 : (page - 1) * pageSize + 1
  const endRow = Math.min(page * pageSize, total)

  const totalRecords = total
  const totalStationsCurrentPage = new Set((data || []).map((r) => r.station_name || r.station || '')).size
  const avgWqiCurrentPage =
    data && data.length > 0
      ? data.reduce((sum, r) => sum + (r.wqi != null ? Number(r.wqi) : 0), 0) / data.length
      : 0
  const latestDateCurrentPage =
    data && data.length > 0
      ? data
          .map((r) => r.date || '')
          .filter(Boolean)
          .sort()
          .slice(-1)[0]
      : null

  const rowStatusClass = (riverStatus) => {
    const s = (riverStatus || '').toString().toLowerCase().replace(/\s+/g, '_')
    if (s === 'clean') return 'bg-emerald-50 hover:bg-emerald-100/70'
    if (s === 'slightly_polluted') return 'bg-amber-50 hover:bg-amber-100/70'
    if (s === 'polluted') return 'bg-red-50 hover:bg-red-100/70'
    return 'hover:bg-surface-50'
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-display font-semibold text-surface-800 mb-4">{title}</h2>
      <p className="text-sm text-surface-500 mb-4">{description}</p>

      {/* Summary for current filtered view (page-based for WQI/date) */}
      <div className="mb-4 flex flex-wrap gap-4 text-xs sm:text-sm text-surface-600">
        <div className="rounded-lg bg-surface-50 px-3 py-2 border border-surface-200">
          <p className="font-medium text-surface-800">Total records</p>
          <p>{totalRecords}</p>
        </div>
        <div className="rounded-lg bg-surface-50 px-3 py-2 border border-surface-200">
          <p className="font-medium text-surface-800">Stations (current page)</p>
          <p>{totalStationsCurrentPage}</p>
        </div>
        <div className="rounded-lg bg-surface-50 px-3 py-2 border border-surface-200">
          <p className="font-medium text-surface-800">Average WQI (current page)</p>
          <p>{data.length > 0 ? avgWqiCurrentPage.toFixed(1) : '—'}</p>
        </div>
        <div className="rounded-lg bg-surface-50 px-3 py-2 border border-surface-200">
          <p className="font-medium text-surface-800">Latest date (current page)</p>
          <p>{latestDateCurrentPage || '—'}</p>
        </div>
      </div>

      {/* Filters — river is the primary user-facing scope; optional fine station filter */}
      <div className="flex flex-wrap gap-4 mb-4">
        {syncedRiverName === undefined && (
          <div>
            <label className="label">River</label>
            <select
              value={riverName}
              onChange={(e) => { setRiverName(e.target.value); setPage(1) }}
              className="input-field w-auto min-w-[200px]"
            >
              <option value="">All rivers</option>
              {dashboardApi.uniqueRiverNamesFromStations(stations).map((rn) => (
                <option key={rn} value={rn}>{rn}</option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label className="label">Station (optional)</label>
          <select
            value={stationName}
            onChange={(e) => { setStationName(e.target.value); setPage(1) }}
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
          <label className="label">Year</label>
          <select
            value={monthYear}
            onChange={(e) => { setMonthYear(e.target.value); setPage(1) }}
            className="input-field w-auto min-w-[140px]"
          >
            <option value="">All years</option>
            {years.map((y) => (
              <option key={y} value={String(y)}>{y}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Month</label>
          <select
            value={monthFilter}
            onChange={(e) => { setMonthFilter(e.target.value); setPage(1) }}
            className="input-field w-auto min-w-[140px]"
          >
            <option value="">All months</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={String(m)}>{m}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">From date</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
            className="input-field w-auto"
          />
        </div>
        <div>
          <label className="label">To date</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
            className="input-field w-auto"
          />
        </div>
        <div>
          <label className="label">River status</label>
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1) }}
            className="input-field w-auto min-w-[140px]"
          >
            <option value="">All</option>
            <option value="clean">Clean</option>
            <option value="slightly_polluted">Slightly Polluted</option>
            <option value="polluted">Polluted</option>
          </select>
        </div>
        <div>
          <label className="label">Data type</label>
          <select
            value={dataType}
            onChange={(e) => { setDataType(e.target.value); setPage(1) }}
            className="input-field w-auto min-w-[160px]"
          >
            {DATA_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Sort by</label>
          <select
            value={sortValue}
            onChange={(e) => { setSortValue(e.target.value); setPage(1) }}
            className="input-field w-auto min-w-[180px]"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Rows per page</label>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
            className="input-field w-auto min-w-[100px]"
          >
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800 mb-4">
          {error}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-surface-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-100 text-left">
              <th className="px-4 py-2 font-medium text-surface-700">River</th>
              <th className="px-4 py-2 font-medium text-surface-700">Station</th>
              <th className="px-4 py-2 font-medium text-surface-700">Date</th>
              <th className="px-4 py-2 font-medium text-surface-700">WQI</th>
              <th className="px-4 py-2 font-medium text-surface-700">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">Loading…</td></tr>
            ) : data.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">No data available for selected filters.</td></tr>
            ) : (
              data.map((r, i) => (
                <tr
                  key={`${r.station_name}-${r.date}-${i}`}
                  className={`border-t border-surface-100 transition-colors ${rowStatusClass(r.river_status)}`}
                >
                  <td className="px-4 py-2 font-medium text-surface-800">{r.river_name || '—'}</td>
                  <td className="px-4 py-2 text-surface-800">{r.station_name || r.station_code || '—'}</td>
                  <td className="px-4 py-2 text-surface-800">{r.date || '—'}</td>
                  <td className="px-4 py-2">{r.wqi != null ? Number(r.wqi).toFixed(1) : '—'}</td>
                  <td className="px-4 py-2">
                    <RiverHealthIndicator wqi={r.wqi} compact />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex flex-wrap items-center justify-between gap-4 mt-4">
        <p className="text-sm text-surface-500">
          Showing {startRow}–{endRow} of {total} records
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || loading}
            className="rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-sm font-medium text-surface-700 hover:bg-surface-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-surface-600">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || loading}
            className="rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-sm font-medium text-surface-700 hover:bg-surface-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
