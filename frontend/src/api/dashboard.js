/**
 * Dashboard API — All data from dataset (no hardcoding).
 * Summary, time-series, forecast, stations, anomalies, readings table, years.
 */
import api from './client'

export async function getSummary(params = {}) {
  const { data } = await api.get('/dashboard/summary', { params })
  return data
}

export async function getDatasetOverview() {
  const { data } = await api.get('/dashboard/overview')
  return data
}

export async function getRivers() {
  const { data } = await api.get('/dashboard/rivers')
  return data.rivers || []
}

export async function getTimeSeries(params = {}) {
  const { data } = await api.get('/dashboard/time-series', { params })
  return { series: data.series || [], today: data.today || null }
}

export async function getForecast(params = {}) {
  const { data } = await api.get('/dashboard/forecast', { params })
  return { forecast: data.forecast || [], today: data.today || null }
}

export async function getStations() {
  const { data } = await api.get('/dashboard/stations')
  const stations = dedupeStationsByCode(data.stations || [])
  if (import.meta.env.DEV) console.debug('[SmartRiver] /dashboard/stations:', { count: stations.length })
  return stations
}

export async function getAlerts(params = {}) {
  const { data } = await api.get('/alerts/', { params })
  return data.items || []
}

/** Historical alerts (latest first) and Forecast alerts (earliest first). */
export async function getAlertsByType(params = {}) {
  const { data } = await api.get('/alerts/by-type', { params })
  return {
    historical: data.historical || [],
    forecast: data.forecast || [],
  }
}

/** Persistent SQLite log: anomaly | forecast | historical triggers */
export async function getAlertHistory(params = {}) {
  const { data } = await api.get('/alerts/history', { params })
  return data.items || []
}

export async function resolveAlertHistory(alertId) {
  const { data } = await api.patch(`/alerts/history/${alertId}/resolve`)
  return data
}

/** Active admin-posted warnings (banner) */
export async function getActiveWarnings() {
  const { data } = await api.get('/warnings/active')
  return data.items || []
}

const CANONICAL_STATION_CODES = ['S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07']

/** One row per station_code (S01–S07); merges legacy rows keyed by river name only. */
export function dedupeStationsByCode(stations) {
  const byCode = new Map()
  const riverToCode = {
    'Sungai Klang': 'S01',
    'Sungai Gombak': 'S02',
    'Sungai Pinang': 'S03',
    'Sungai Kulim': 'S04',
    'Sungai Perak': 'S05',
    'Sungai Sarawak': 'S06',
    'Sungai Kinabatangan': 'S07',
  }
  for (const s of stations || []) {
    let code = String(s.station_code || '').trim().toUpperCase()
    if (!CANONICAL_STATION_CODES.includes(code)) {
      const rn = (s.river_name || s.station_name || '').trim()
      code = riverToCode[rn] || code
    }
    if (!code || !CANONICAL_STATION_CODES.includes(code)) continue
    const prev = byCode.get(code)
    const row = {
      ...s,
      station_code: code,
      station_name: (s.river_name || s.station_name || rnFromCode(code)).trim(),
      river_name: (s.river_name || s.station_name || rnFromCode(code)).trim(),
    }
    if (!prev || String(row.last_reading_date || '') >= String(prev.last_reading_date || '')) {
      byCode.set(code, row)
    }
  }
  return [...byCode.values()].sort((a, b) => a.station_code.localeCompare(b.station_code))
}

function rnFromCode(code) {
  const map = {
    S01: 'Sungai Klang',
    S02: 'Sungai Gombak',
    S03: 'Sungai Pinang',
    S04: 'Sungai Kulim',
    S05: 'Sungai Perak',
    S06: 'Sungai Sarawak',
    S07: 'Sungai Kinabatangan',
  }
  return map[code] || code
}

/** Prefer API river_name on each station; fallback for legacy rows. */
export function uniqueRiverNamesFromStations(stations) {
  const out = new Set()
  dedupeStationsByCode(stations).forEach((s) => {
    const n = (s.river_name || '').trim()
    if (n) out.add(n)
  })
  return [...out].sort()
}

export async function getAnomalies(params = {}) {
  const { data } = await api.get('/dashboard/anomalies', { params })
  return data.anomalies || []
}

export async function getWqiData(params = {}) {
  const { data } = await api.get('/dashboard/wqi-data', { params })
  return data.data || []
}

export async function getReadingsTable(params = {}) {
  const { data } = await api.get('/dashboard/readings-table', { params })
  const rows = data.data || []
  if (import.meta.env.DEV) console.debug('[SmartRiver] /dashboard/readings-table:', { params, count: rows.length })
  return rows
}

export async function getReadingsCount(params = {}) {
  const { data } = await api.get('/dashboard/readings-count', { params })
  return data.total ?? 0
}

export async function getYears() {
  const { data } = await api.get('/dashboard/years')
  return data.years || []
}

export async function getCompareSeries(params = {}) {
  const { data } = await api.get('/dashboard/compare-series', { params })
  return data
}

export async function getWqiCalendar(params = {}) {
  const { data } = await api.get('/dashboard/wqi-calendar', { params })
  return data
}

export async function getParameterContribution(params = {}) {
  const { data } = await api.get('/dashboard/parameter-contribution', { params })
  return data
}
