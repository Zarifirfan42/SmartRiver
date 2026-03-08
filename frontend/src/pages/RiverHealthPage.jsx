import { useState } from 'react'
import RiverHealthIndicator from '../components/dashboard/RiverHealthIndicator'
import RiverMap from '../components/map/RiverMap'

const mockStations = [
  { station_code: 'S01', station_name: 'Sungai Klang', latest_wqi: 72, river_status: 'slightly_polluted', last_date: '2025-03-05', latitude: 3.1390, longitude: 101.6869 },
  { station_code: 'S02', station_name: 'Sungai Gombak', latest_wqi: 85, river_status: 'clean', last_date: '2025-03-05', latitude: 3.2569, longitude: 101.7172 },
  { station_code: 'S03', station_name: 'Sungai Pinang', latest_wqi: 48, river_status: 'polluted', last_date: '2025-03-04', latitude: 5.4167, longitude: 100.3333 },
  { station_code: 'S04', station_name: 'Sungai Johor', latest_wqi: 78, river_status: 'clean', last_date: '2025-03-05', latitude: 1.4927, longitude: 103.7414 },
  { station_code: 'S05', station_name: 'Sungai Perak', latest_wqi: 62, river_status: 'slightly_polluted', last_date: '2025-03-03', latitude: 4.5921, longitude: 101.0900 },
]

export default function RiverHealthPage() {
  const [filter, setFilter] = useState('all')

  const filtered = filter === 'all'
    ? mockStations
    : mockStations.filter((s) => s.river_status === filter)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-900">River health status</h1>
          <p className="text-surface-600 mt-0.5">Latest WQI by monitoring station</p>
        </div>
        <div className="flex gap-2">
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

      <div className="card p-0 overflow-hidden">
        <div className="px-5 py-3 border-b border-surface-200">
          <h2 className="font-display font-semibold text-surface-800">Stations on map</h2>
        </div>
        <RiverMap stations={filtered} height={360} />
      </div>

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
              {filtered.map((s) => (
                <tr key={s.station_code} className="border-b border-surface-100">
                  <td className="py-3 pr-4 font-medium text-surface-800">{s.station_name}</td>
                  <td className="py-3 pr-4">{s.latest_wqi}</td>
                  <td className="py-3 pr-4">
                    <RiverHealthIndicator wqi={s.latest_wqi} compact />
                  </td>
                  <td className="py-3 text-surface-600">{s.last_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
