/**
 * Dashboard summary: historical (dataset) + Predicted Average WQI (2025-2028).
 */
export default function DashboardSummary({
  totalStations = 0,
  avgWqi = 0,
  cleanCount = 0,
  slightlyPollutedCount = 0,
  pollutedCount = 0,
  predictedAvgWqi2025_2028 = 0,
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Number of monitoring stations</p>
        <p className="text-2xl font-semibold text-slate-900">{totalStations}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Average WQI (latest monitoring)</p>
        <p className="text-2xl font-semibold text-cyan-600">{Number(avgWqi).toFixed(1)}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Predicted Average WQI (2026-2028)</p>
        <p className="text-2xl font-semibold text-blue-600">{Number(predictedAvgWqi2025_2028).toFixed(1)}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Status distribution (latest monitoring) — Clean</p>
        <p className="text-2xl font-semibold text-emerald-600">{cleanCount}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Slightly Polluted / Polluted</p>
        <p className="text-lg font-semibold text-amber-600">{slightlyPollutedCount} / <span className="text-red-600">{pollutedCount}</span></p>
      </div>
    </div>
  )
}
