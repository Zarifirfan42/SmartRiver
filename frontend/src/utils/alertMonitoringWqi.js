/**
 * Alert monitoring WQI bands (single source of truth for today’s summary counts).
 * Slightly polluted: 60 ≤ WQI ≤ 80. Polluted: WQI < 60.
 */

export function isWqiSlightlyPolluted(w) {
  const x = Number(w)
  return Number.isFinite(x) && x >= 60 && x <= 80
}

export function isWqiPolluted(w) {
  const x = Number(w)
  return Number.isFinite(x) && x < 60
}

export function countSlightlyPollutedStations(readings) {
  return (readings || []).filter((r) => isWqiSlightlyPolluted(r.wqi)).length
}

export function countPollutedStations(readings) {
  return (readings || []).filter((r) => isWqiPolluted(r.wqi)).length
}
