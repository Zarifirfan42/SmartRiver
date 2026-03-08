/**
 * Dashboard summary cards: stations count, avg WQI, status breakdown.
 */
export default function DashboardSummary({ totalStations = 0, avgWqi = 0, cleanCount = 0, pollutedCount = 0 }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Stations</p>
        <p className="text-2xl font-semibold text-slate-900">{totalStations}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Avg WQI</p>
        <p className="text-2xl font-semibold text-cyan-600">{avgWqi.toFixed(1)}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Clean</p>
        <p className="text-2xl font-semibold text-emerald-600">{cleanCount}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Polluted</p>
        <p className="text-2xl font-semibold text-red-600">{pollutedCount}</p>
      </div>
    </div>
  )
}
