/**
 * Simple placeholder time-series chart. Replace with Chart.js or Plotly implementation.
 */
export default function TimeSeriesChart({ data = [], title = 'WQI Trend', height = 280 }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm" style={{ minHeight: height }}>
      <h3 className="font-semibold text-slate-800 mb-3">{title}</h3>
      <div className="flex items-end gap-1 h-48">
        {data.length
          ? data.slice(0, 30).map((d, i) => (
              <div
                key={i}
                className="flex-1 bg-cyan-500 rounded-t min-w-[4px]"
                style={{ height: `${(d?.value ?? d?.wqi ?? 50) / 100 * 100}%` }}
                title={d?.date || `${i}`}
              />
            ))
          : <p className="text-slate-400 text-sm">No data</p>}
      </div>
    </div>
  )
}
