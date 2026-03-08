/**
 * Dashboard API — Summary, time-series, forecast, stations.
 */
import api from './client'

export async function getSummary() {
  const { data } = await api.get('/dashboard/summary')
  return data
}

export async function getTimeSeries(params = {}) {
  const { data } = await api.get('/dashboard/time-series', { params })
  return data.series || []
}

export async function getForecast(params = {}) {
  const { data } = await api.get('/dashboard/forecast', { params })
  return data.forecast || []
}

export async function getStations() {
  const { data } = await api.get('/dashboard/stations')
  return data.stations || []
}

export async function getAlerts(params = {}) {
  const { data } = await api.get('/alerts/', { params })
  return data.items || []
}
