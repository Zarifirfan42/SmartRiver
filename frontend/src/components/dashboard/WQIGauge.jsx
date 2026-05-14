import { getStatusFromWQI } from './RiverHealthIndicator'

export default function WQIGauge({ value = 0, size = 160 }) {
  const wqi = Math.min(100, Math.max(0, Number(value)))
  const status = getStatusFromWQI(wqi)
  const strokeColor =
    status.slug === 'clean'
      ? '#10b981'
      : status.slug === 'slightly_polluted'
        ? '#f59e0b'
        : '#ef4444'

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size / 2 + 20 }}>
        <svg
          viewBox="0 0 200 120"
          className="w-full h-full"
          style={{ width: size, height: size / 2 + 20 }}
        >
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={strokeColor}
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={`${(wqi / 100) * 251.2} 251.2`}
            strokeDashoffset="0"
            className="transition-all duration-700"
          />
        </svg>
        <div
          className="absolute left-1/2 bottom-0 -translate-x-1/2 text-center"
          style={{ bottom: 4 }}
        >
          <span className="font-display text-2xl font-bold text-surface-800">{Math.round(wqi)}</span>
          <span className="block text-xs font-medium text-surface-500">WQI</span>
        </div>
      </div>
      <span className="mt-1 text-sm font-medium text-surface-600">{status.label}</span>
    </div>
  )
}
