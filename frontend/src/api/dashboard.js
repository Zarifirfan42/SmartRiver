/**
 * Dashboard API — All data from dataset (no hardcoding).
 * Summary, time-series, forecast, stations, anomalies, readings table, years.
 */
import api from './client'

export async function getSummary() {
  const { data } = await api.get('/dashboard/summary')
  return data
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
  const stations = data.stations || []
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
