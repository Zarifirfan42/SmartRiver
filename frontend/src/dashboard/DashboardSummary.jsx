/**
 * Dashboard summary KPIs: stations, average WQI, status distribution (today's readings per station only).
 */
export default function DashboardSummary({
  totalStations = 0,
  avgWqi = 0,
  cleanCount = 0,
  slightlyPollutedCount = 0,
  pollutedCount = 0,
  /** When set, KPIs are scoped to this river (entity-centric view). */
  riverName = '',
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-6">
      {riverName ? (
        <div className="col-span-full rounded-lg border border-cyan-100 bg-cyan-50/80 px-4 py-2 text-sm text-cyan-900">
          Showing metrics for: <span className="font-semibold">{riverName}</span>
        </div>
      ) : null}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Stations with a reading today</p>
        <p className="text-2xl font-semibold text-slate-900">{totalStations}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Average WQI (today only)</p>
        <p className="text-2xl font-semibold text-cyan-600">{Number(avgWqi).toFixed(1)}</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-sm text-slate-500">Clean (today)</p>
        <p className="text-2xl font-semibold text-emerald-600">{cleanCount}</p>
      </div>
      <div className="rounded-xl border-2 border-amber-200 bg-amber-50/80 p-4 shadow-sm ring-1 ring-amber-100">
        <p className="text-sm font-medium text-amber-900">Slightly polluted (today)</p>
        <p className="text-xs text-amber-800/90 mt-0.5 mb-2">WQI 60–80 — monitor closely</p>
        <p className="text-3xl font-bold text-amber-700 tabular-nums">{slightlyPollutedCount}</p>
      </div>
      <div
        className={`rounded-xl border p-4 shadow-sm ${
          pollutedCount > 0
            ? 'border-red-200 bg-red-50/60'
            : 'border-slate-200 bg-slate-50/80'
        }`}
      >
        <p className={`text-sm ${pollutedCount > 0 ? 'font-medium text-red-900' : 'text-slate-500'}`}>
          Polluted (today)
        </p>
        <p className={`text-xs mt-0.5 mb-2 ${pollutedCount > 0 ? 'text-red-800/90' : 'text-slate-500'}`}>
          {pollutedCount === 0 ? 'None — within acceptable range' : 'WQI under 60 — immediate attention'}
        </p>
        <p
          className={`text-2xl font-semibold tabular-nums ${
            pollutedCount > 0 ? 'text-red-700' : 'text-slate-400'
          }`}
        >
          {pollutedCount}
        </p>
      </div>
    </div>
  )
}
