/**
 * WQI gauge (0–100). Replace with custom SVG or chart library for production.
 */
export default function WQIGauge({ value = 0, label = 'WQI', size = 120 }) {
  const v = Math.min(100, Math.max(0, Number(value)))
  const color = v >= 81 ? '#10b981' : v >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex flex-col items-center">
      <div
        className="rounded-full border-4 flex items-center justify-center font-bold text-slate-800"
        style={{
          width: size,
          height: size,
          borderColor: color,
          fontSize: size * 0.3,
        }}
      >
        {Math.round(v)}
      </div>
      <span className="text-sm text-slate-500 mt-1">{label}</span>
    </div>
  )
}
