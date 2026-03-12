import { useState, useEffect, useMemo } from 'react'
import RiverHealthIndicator from '../components/dashboard/RiverHealthIndicator'
import RiverMap from '../components/map/RiverMap'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import * as dashboardApi from '../api/dashboard'

function getRiverStatusSlug(wqi) {
  if (wqi == null || Number.isNaN(wqi)) return 'unknown'
  if (wqi >= 81) return 'clean'
  if (wqi >= 60) return 'slightly_polluted'
  return 'polluted'
}

function formatDate(d) {
  if (!d) return '—'
  if (typeof d === 'string') return d
  return d
}

export default function RiverHealthPage() {
  const [filter, setFilter] = useState('all')
  const [stations, setStations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [selectedStation, setSelectedStation] = useState(null)
  const [historyData, setHistoryData] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState(null)

  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  useEffect(() => {
    let cancelled = false
    async function fetchStations() {
      setLoading(true)
      setError(null)
      try {
        const list = await dashboardApi.getStations()
        if (!cancelled) setStations(Array.isArray(list) ? list : [])
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load stations')
          setStations([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchStations()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!selectedStation) {
      setHistoryData([])
      return
    }
    let cancelled = false
    setHistoryLoading(true)
    setHistoryError(null)
    dashboardApi
      .getTimeSeries({ station_code: selectedStation.station_code, limit: 500 })
      .then((series) => {
        if (cancelled) return
        const withStatus = (series || []).map((d) => ({
          date: d.date,
          wqi: d.wqi ?? d.value,
          river_status: getRiverStatusSlug(d.wqi ?? d.value),
        }))
        setHistoryData(withStatus)
      })
      .catch((err) => {
        if (!cancelled) {
          setHistoryError(err.message || 'Failed to load history')
          setHistoryData([])
        }
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false)
      })
    return () => { cancelled = true }
  }, [selectedStation])

  const filteredStations =
    filter === 'all'
      ? stations
      : stations.filter((s) => s.river_status === filter)

  const filteredHistory = useMemo(() => {
    let list = [...historyData]
    if (dateFrom) {
      list = list.filter((r) => formatDate(r.date) >= dateFrom)
    }
    if (dateTo) {
      list = list.filter((r) => formatDate(r.date) <= dateTo)
    }
    return list.sort((a, b) => String(a.date).localeCompare(String(b.date)))
  }, [historyData, dateFrom, dateTo])

  const handleSelectStation = (station) => {
    setSelectedStation(station)
    setDateFrom('')
    setDateTo('')
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-900">River health status</h1>
          <p className="text-surface-600 mt-0.5">Latest WQI by monitoring station — select a station to view full history</p>
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
              {f === 'all' ? 'All' : f.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}. Upload a dataset and run preprocessing to see stations.
        </div>
      )}
      {loading && <p className="text-surface-500">Loading stations…</p>}

      {/* Map — stations from dataset only */}
      <div className="card p-0 overflow-hidden">
        <div className="px-5 py-3 border-b border-surface-200">
          <h2 className="font-display font-semibold text-surface-800">Stations on map</h2>
          <p className="text-sm text-surface-500">Click a marker or “View history” to see full records</p>
        </div>
        {filteredStations.length === 0 && !loading ? (
          <div className="flex items-center justify-center text-surface-500 py-24">
            No stations in dataset. Upload a CSV and run preprocessing to see the map.
          </div>
        ) : (
          <RiverMap
            stations={filteredStations}
            height={360}
            onStationClick={handleSelectStation}
            useDefaultStations={false}
          />
        )}
      </div>

      {/* Station list — clickable, matches dataset */}
      <div className="card">
        <h2 className="font-display font-semibold text-surface-800 mb-4">Station list</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-200 text-left text-surface-500">
                <th className="pb-3 pr-4 font-medium">Station</th>
                <th className="pb-3 pr-4 font-medium">WQI</th>
                <th className="pb-3 pr-4 font-medium">Status</th>
                <th className="pb-3 font-medium">Last reading</th>
              </tr>
            </thead>
            <tbody>
              {filteredStations.length === 0 && !loading && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-surface-500">
                    No stations yet. Upload a dataset and run preprocessing.
                  </td>
                </tr>
              )}
              {filteredStations.map((s) => (
                <tr
                  key={s.station_code}
                  className={`border-b border-surface-100 ${selectedStation?.station_code === s.station_code ? 'bg-river-50' : ''} cursor-pointer hover:bg-surface-50`}
                  onClick={() => handleSelectStation(s)}
                >
                  <td className="py-3 pr-4 font-medium text-surface-800">{s.station_name || s.station_code}</td>
                  <td className="py-3 pr-4">{s.latest_wqi != null ? Number(s.latest_wqi).toFixed(1) : '—'}</td>
                  <td className="py-3 pr-4">
                    <RiverHealthIndicator wqi={s.latest_wqi} compact />
                  </td>
                  <td className="py-3 text-surface-600">{s.last_reading_date || s.last_date || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected station: full historical records + table + line chart + date filter */}
      {selectedStation && (
        <div className="card space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-lg font-semibold text-surface-900">
                {selectedStation.station_name || selectedStation.station_code} — Historical records
              </h2>
              <p className="text-sm text-surface-500">Date, WQI, and river status from the dataset</p>
            </div>
            <button
              type="button"
              onClick={() => setSelectedStation(null)}
              className="btn-secondary text-sm"
            >
              ← Back to list
            </button>
          </div>

          {/* Date filter */}
          <div className="flex flex-wrap items-center gap-4 py-2 border-y border-surface-200">
            <span className="text-sm font-medium text-surface-700">Filter by date</span>
            <label className="flex items-center gap-2 text-sm">
              From
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="input-field w-auto py-1.5"
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              To
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="input-field w-auto py-1.5"
              />
            </label>
            {(dateFrom || dateTo) && (
              <button
                type="button"
                onClick={() => { setDateFrom(''); setDateTo('') }}
                className="text-sm text-river-600 hover:underline"
              >
                Clear filter
              </button>
            )}
          </div>

          {historyError && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
              {historyError}
            </div>
          )}
          {historyLoading && <p className="text-surface-500">Loading history…</p>}

          {!historyLoading && !historyError && (
            <>
              {/* Table view */}
              <div>
                <h3 className="font-display font-medium text-surface-800 mb-2">Table view</h3>
                <div className="overflow-x-auto rounded-lg border border-surface-200">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-surface-50 text-left text-surface-600">
                        <th className="px-4 py-2.5 font-medium">Date</th>
                        <th className="px-4 py-2.5 font-medium">WQI</th>
                        <th className="px-4 py-2.5 font-medium">River status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredHistory.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="px-4 py-8 text-center text-surface-500">
                            No records in this range.
                          </td>
                        </tr>
                      ) : (
                        filteredHistory.map((r, i) => (
                          <tr key={i} className="border-t border-surface-100">
                            <td className="px-4 py-2.5 text-surface-800">{formatDate(r.date)}</td>
                            <td className="px-4 py-2.5">{r.wqi != null ? Number(r.wqi).toFixed(1) : '—'}</td>
                            <td className="px-4 py-2.5">
                              <RiverHealthIndicator wqi={r.wqi} compact />
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Line chart — WQI trend */}
              <div>
                <h3 className="font-display font-medium text-surface-800 mb-2">WQI trend</h3>
                <div className="rounded-lg border border-surface-200 bg-white p-4">
                  {filteredHistory.length > 0 ? (
                    <TimeSeriesChart
                      data={filteredHistory.map((r) => ({ date: formatDate(r.date), wqi: r.wqi }))}
                      height={280}
                    />
                  ) : (
                    <div className="h-[280px] flex items-center justify-center text-surface-500">
                      No data to display for the selected date range.
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
