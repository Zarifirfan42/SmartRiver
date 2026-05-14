export function getStatusFromWQI(wqi) {
  if (wqi == null || Number.isNaN(wqi)) return { label: 'Unknown', color: 'surface', slug: 'unknown' }
  if (wqi >= 81) return { label: 'Clean', color: 'eco', slug: 'clean' }
  if (wqi >= 60) return { label: 'Slightly Polluted', color: 'amber', slug: 'slightly_polluted' }
  return { label: 'Polluted', color: 'red', slug: 'polluted' }
}

const colorClasses = {
  eco: 'bg-eco-500 text-white',
  amber: 'bg-amber-500 text-white',
  red: 'bg-red-500 text-white',
  surface: 'bg-surface-400 text-white',
}

export default function RiverHealthIndicator({ wqi, stationName, compact }) {
  const status = getStatusFromWQI(wqi)
  const cls = colorClasses[status.color] || colorClasses.surface

  if (compact) {
    return (
      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
        {status.label}
      </span>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <span className={`inline-flex rounded-lg px-3 py-1.5 text-sm font-medium ${cls}`}>
        {status.label}
      </span>
      {stationName && <span className="text-sm text-surface-600">{stationName}</span>}
      {wqi != null && !Number.isNaN(wqi) && (
        <span className="text-sm text-surface-500">WQI {Number(wqi).toFixed(1)}</span>
      )}
    </div>
  )
}
