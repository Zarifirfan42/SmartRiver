/**
 * WQIChart — Water Quality Index chart
 * Displays WQI time series (line or bar). Use Chart.js or Plotly for production.
 */
export default function WQIChart({ data = [], title = 'WQI Trend', height = 280 }) {
  return (
    <div
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      style={{ minHeight: height }}
    >
      <h3 className="mb-3 font-semibold text-slate-800">{title}</h3>
      {data.length > 0 ? (
        <div className="flex items-end gap-1" style={{ height: 200 }}>
          {data.slice(0, 30).map((d, i) => (
            <div
              key={i}
              className="flex-1 min-w-[6px] rounded-t bg-cyan-500 transition-opacity hover:opacity-80"
              style={{
                height: `${Math.min(100, ((d.wqi ?? d.value ?? 0) / 100) * 100)}%`,
              }}
              title={`${d.date ?? i}: ${d.wqi ?? d.value ?? '-'}`}
            />
          ))}
        </div>
      ) : (
        <p className="py-8 text-center text-slate-400">No data yet</p>
      )}
    </div>
  )
}
