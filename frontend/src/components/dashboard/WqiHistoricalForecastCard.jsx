/**
 * Historical WQI line + ML forecast (dashed) for Dashboard and River Health.
 * Scoped by river and station; forecast is 2026 horizon from /dashboard/forecast.
 */
import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import ForecastChart from '../charts/ForecastChart'
import * as dashboardApi from '../../api/dashboard'

function filterStationsForTrend(stations, riverName) {
  const list = Array.isArray(stations) ? stations : []
  const byKey = new Map()
  for (const s of list) {
    const key = (s.station_code || s.station_name || '').trim()
    if (!key) continue
    if (riverName && String(riverName).trim()) {
      if ((s.river_name || '').trim() !== String(riverName).trim()) continue
    }
    if (!byKey.has(key)) byKey.set(key, s)
  }
  return [...byKey.values()].sort((a, b) =>
    String(a.station_name || a.station_code).localeCompare(String(b.station_name || b.station_code), undefined, {
      sensitivity: 'base',
    }),
  )
}

function stationApiKey(s) {
  return (s.station_code || s.station_name || '').trim()
}

function stationLabel(s) {
  const name = (s.station_name || '').trim()
  const code = (s.station_code || '').trim()
  if (name && code && name !== code) return `${name} (${code})`
  return name || code || 'Station'
}

/**
 * @param {object} props
 * @param {object[]} props.stations - From /dashboard/stations
 * @param {number[]} [props.years] - Optional year list; if omitted, fetched from API
 * @param {number} props.dataRevision - Bump when dataset changes
 * @param {string} props.riverName - River scope when pickRiver is false (e.g. dashboard top-level river)
 * @param {boolean} [props.pickRiver=false] - River Health: show river dropdown and scope chart internally
 */
export default function WqiHistoricalForecastCard({
  stations = [],
  years: yearsProp,
  dataRevision = 0,
  riverName = '',
  pickRiver = false,
}) {
  const [chartRiver, setChartRiver] = useState('')
  const rivers = useMemo(() => dashboardApi.uniqueRiverNamesFromStations(stations), [stations])
  const effectiveRiver = pickRiver ? chartRiver : riverName

  useEffect(() => {
    if (!pickRiver) return
    setChartRiver((r) => r || rivers[0] || '')
  }, [pickRiver, rivers])

  const [internalYears, setInternalYears] = useState([])
  const years = yearsProp?.length ? yearsProp : internalYears

  useEffect(() => {
    if (yearsProp?.length) return
    let cancelled = false
    dashboardApi
      .getYears()
      .then((y) => {
        if (!cancelled) setInternalYears(Array.isArray(y) ? y : [])
      })
      .catch(() => {
        if (!cancelled) setInternalYears([])
      })
    return () => {
      cancelled = true
    }
  }, [dataRevision, yearsProp])

  const trendStationChoices = useMemo(
    () => filterStationsForTrend(stations, effectiveRiver),
    [stations, effectiveRiver],
  )

  const [trendStation, setTrendStation] = useState('')
  const [trendYear, setTrendYear] = useState('')
  const [timeSeries, setTimeSeries] = useState([])
  const [forecastSeries, setForecastSeries] = useState([])
  const [seriesToday, setSeriesToday] = useState(null)

  const [refreshTick, setRefreshTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setRefreshTick((t) => t + 1), 90_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (trendStationChoices.length === 0) {
      setTrendStation('')
      return
    }
    setTrendStation((prev) => {
      if (prev && trendStationChoices.some((s) => stationApiKey(s) === prev)) return prev
      return stationApiKey(trendStationChoices[0])
    })
  }, [trendStationChoices])

  useEffect(() => {
    let cancelled = false
    const params = {
      river_name: effectiveRiver?.trim() ? effectiveRiver : undefined,
      year: trendYear || undefined,
      limit: 2000,
    }
    if (trendStation) params.station_code = trendStation

    Promise.all([
      dashboardApi.getTimeSeries(params),
      dashboardApi.getForecast({
        river_name: effectiveRiver?.trim() ? effectiveRiver : undefined,
        station_code: trendStation || undefined,
        year_from: 2026,
        year_to: 2026,
        limit: 5000,
      }),
    ])
      .then(([tsRes, fcRes]) => {
        if (cancelled) return
        setTimeSeries(Array.isArray(tsRes?.series) ? tsRes.series : [])
        setSeriesToday(tsRes?.today ?? null)
        const fc = fcRes?.forecast ?? []
        setForecastSeries(Array.isArray(fc) ? fc : [])
      })
      .catch(() => {
        if (!cancelled) {
          setTimeSeries([])
          setForecastSeries([])
          setSeriesToday(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [effectiveRiver, trendYear, trendStation, dataRevision, refreshTick])

  const histForChart = useMemo(
    () => timeSeries.map((d) => ({ date: d.date, wqi: d.wqi ?? d.value })),
    [timeSeries],
  )
  const fcForChart = useMemo(
    () => forecastSeries.map((f) => ({ date: f.date, wqi: f.wqi ?? f.value })),
    [forecastSeries],
  )
  const hasAnyPoint = histForChart.length > 0 || fcForChart.length > 0

  return (
    <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-display font-semibold text-surface-800 mb-4">WQI trend &amp; ML forecast</h2>
      <p className="text-sm text-surface-500 mb-4">
        <strong>Historical</strong> line uses readings through the server &quot;today&quot;; <strong>forecast</strong> shows
        daily ML predictions from tomorrow through end of 2026 for the selected river and station. Full-page charting:{' '}
        <Link to="/forecast" className="font-medium text-cyan-700 hover:text-cyan-900 underline">
          Pollution Forecast
        </Link>
        .
      </p>

      <div className="flex flex-wrap items-end gap-4 mb-4">
        {pickRiver && (
          <div>
            <label className="label">River</label>
            <select
              value={chartRiver}
              onChange={(e) => setChartRiver(e.target.value)}
              className="input-field w-auto min-w-[220px]"
              disabled={rivers.length === 0}
            >
              {rivers.length === 0 ? (
                <option value="">No rivers in dataset</option>
              ) : (
                rivers.map((rn) => (
                  <option key={rn} value={rn}>
                    {rn}
                  </option>
                ))
              )}
            </select>
          </div>
        )}
        <div>
          <label className="label">Station</label>
          <select
            value={trendStation}
            onChange={(e) => setTrendStation(e.target.value)}
            className="input-field w-auto min-w-[260px]"
            disabled={trendStationChoices.length === 0}
          >
            {trendStationChoices.length === 0 ? (
              <option value="">No stations for this river</option>
            ) : (
              trendStationChoices.map((s) => {
                const v = stationApiKey(s)
                return (
                  <option key={v} value={v}>
                    {stationLabel(s)}
                  </option>
                )
              })
            )}
          </select>
        </div>
        <div>
          <label className="label">Year (historical)</label>
          <select
            value={trendYear}
            onChange={(e) => setTrendYear(e.target.value)}
            className="input-field w-auto min-w-[120px]"
          >
            <option value="">All</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          className="btn-secondary text-sm"
          onClick={() => setRefreshTick((t) => t + 1)}
        >
          Refresh
        </button>
      </div>

      <p className="text-xs text-surface-500 mb-3">
        {seriesToday
          ? `Historical series through ${seriesToday} (server date). Forecast dates are after that.`
          : ' '}
      </p>

      {hasAnyPoint ? (
        <ForecastChart
          historical={histForChart}
          forecast={fcForChart}
          today={seriesToday}
          viewMode="daily"
          height={320}
        />
      ) : (
        <div className="h-[320px] flex items-center justify-center text-surface-500 text-sm px-4 text-center">
          No historical or forecast points for this selection. Choose another station or ensure the backend has run
          forecast generation.
        </div>
      )}
    </div>
  )
}
