/**
 * Task 5 — comparative trends, WQI calendar heatmap, parameter stress, coverage, Sabah/Sarawak placeholders.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'
import CompareStationsChart from '../components/charts/CompareStationsChart'
import * as dashboardApi from '../api/dashboard'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

function daysInYear(year) {
  const y = Number(year)
  const isLeap = (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0
  return isLeap ? 366 : 365
}

/** GitHub-style grid: columns = weeks, rows = Sun–Sat. */
function buildYearHeatGrid(year, cells) {
  const byDate = Object.fromEntries((cells || []).map((c) => [c.date, c]))
  const y = Number(year)
  const dim = daysInYear(y)
  const jan1 = new Date(y, 0, 1)
  const pad = jan1.getDay()
  const ncells = pad + dim
  const nweeks = Math.ceil(ncells / 7)
  const grid = []
  for (let w = 0; w < nweeks; w++) {
    const col = []
    for (let r = 0; r < 7; r++) {
      const idx = w * 7 + r
      if (idx < pad) {
        col.push({ date: null, cell: null })
        continue
      }
      const dayNum = idx - pad + 1
      if (dayNum > dim) {
        col.push({ date: null, cell: null })
        continue
      }
      const d = new Date(y, 0, dayNum)
      const ds = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      col.push({ date: ds, cell: byDate[ds] || { date: ds, wqi: null, status: null } })
    }
    grid.push(col)
  }
  return grid
}

function heatColor(cell) {
  if (!cell || cell.wqi == null) return '#e2e8f0'
  if (cell.status === 'clean') return '#22c55e'
  if (cell.status === 'slightly_polluted') return '#eab308'
  return '#ef4444'
}

export default function RiverInsightsPage() {
  const [stations, setStations] = useState([])
  const [years, setYears] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')

  const [compareSelected, setCompareSelected] = useState(() => new Set())
  const [compareYear, setCompareYear] = useState('')
  const [compareData, setCompareData] = useState(null)
  const [compareLoading, setCompareLoading] = useState(false)

  const [hmStation, setHmStation] = useState('')
  const [hmYear, setHmYear] = useState(new Date().getFullYear())
  const [hmCells, setHmCells] = useState([])
  const [hmLoading, setHmLoading] = useState(false)

  const [pcStation, setPcStation] = useState('')
  const [pcDate, setPcDate] = useState('')
  const [pcData, setPcData] = useState(null)
  const [pcErr, setPcErr] = useState('')
  const [pcLoading, setPcLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([dashboardApi.getStations(), dashboardApi.getYears()])
      .then(([st, ys]) => {
        if (cancelled) return
        setStations(Array.isArray(st) ? st : [])
        setYears(Array.isArray(ys) ? ys : [])
        setErr('')
      })
      .catch(() => {
        if (!cancelled) {
          setStations([])
          setYears([])
          setErr('Could not load stations or years.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const stationsWithData = useMemo(
    () => (stations || []).filter((s) => !s.data_coming_soon && (s.station_code || s.station_name)),
    [stations],
  )

  useEffect(() => {
    if (!hmStation && stationsWithData[0]) setHmStation(stationsWithData[0].station_code || stationsWithData[0].station_name)
  }, [stationsWithData, hmStation])

  const loadHeatmap = useCallback(async () => {
    if (!hmStation) return
    setHmLoading(true)
    try {
      const res = await dashboardApi.getWqiCalendar({ station_code: hmStation, year: hmYear })
      setHmCells(res.cells || [])
    } catch {
      setHmCells([])
    } finally {
      setHmLoading(false)
    }
  }, [hmStation, hmYear])

  useEffect(() => {
    loadHeatmap()
  }, [loadHeatmap])

  const heatGrid = useMemo(() => buildYearHeatGrid(hmYear, hmCells), [hmYear, hmCells])

  const toggleCompare = (code) => {
    const c = String(code || '').trim()
    if (!c) return
    setCompareSelected((prev) => {
      const next = new Set(prev)
      if (next.has(c)) next.delete(c)
      else next.add(c)
      return next
    })
  }

  const runCompare = async () => {
    const codes = [...compareSelected]
    if (codes.length < 2) {
      setCompareData(null)
      return
    }
    setCompareLoading(true)
    try {
      const data = await dashboardApi.getCompareSeries({
        station_codes: codes.join(','),
        year: compareYear ? Number(compareYear) : undefined,
      })
      setCompareData(data)
    } catch {
      setCompareData(null)
    } finally {
      setCompareLoading(false)
    }
  }

  const runParameterChart = async () => {
    setPcErr('')
    setPcData(null)
    if (!pcStation.trim() || !pcDate.trim()) {
      setPcErr('Enter station code and date.')
      return
    }
    setPcLoading(true)
    try {
      const data = await dashboardApi.getParameterContribution({
        station_code: pcStation.trim(),
        date: pcDate.trim().slice(0, 10),
      })
      setPcData(data)
    } catch (e) {
      const d = e?.response?.data?.detail
      const msg = Array.isArray(d) ? d.map((x) => (typeof x === 'string' ? x : x.msg || JSON.stringify(x))).join('; ') : d
      setPcErr(typeof msg === 'string' && msg ? msg : 'No breakdown available for this selection.')
      setPcData(null)
    } finally {
      setPcLoading(false)
    }
  }

  const paramChartData = useMemo(() => {
    if (!pcData?.parameters?.length) return null
    const params = [...pcData.parameters].sort((a, b) => Number(b.contribution_pct) - Number(a.contribution_pct))
    return {
      labels: params.map((p) => p.label),
      datasets: [
        {
          label: 'Relative stress %',
          data: params.map((p) => p.contribution_pct),
          backgroundColor: 'rgba(79, 70, 229, 0.55)',
          borderColor: 'rgba(67, 56, 202, 0.9)',
          borderWidth: 1,
        },
      ],
    }
  }, [pcData])

  const paramOptions = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: pcData ? `Parameter stress · WQI ${pcData.wqi ?? '—'} (${pcData.date})` : 'Parameter contribution',
        font: { size: 14 },
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Share of total stress (%)' },
        min: 0,
        suggestedMax: 100,
        grid: { color: '#e2e8f0' },
      },
      y: { grid: { display: false } },
    },
  }

  if (loading) {
    return <p className="text-surface-500">Loading river insights…</p>
  }

  return (
    <div className="max-w-6xl mx-auto space-y-10">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">River insights</h1>
        <p className="text-surface-600 mt-2 text-sm max-w-3xl">
          Compare stations, inspect daily WQI patterns, see which parameters drove a low score (when chemistry exists in
          SQLite), check data coverage, and browse Sabah/Sarawak placeholders listed as &quot;Data coming soon&quot;.
        </p>
        {err ? <p className="text-amber-700 text-sm mt-2">{err}</p> : null}
      </div>

      {/* Coverage */}
      <section className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-1">Data coverage</h2>
        <p className="text-sm text-surface-500 mb-4">
          Distinct sampling days divided by calendar span (first to last reading). Higher is more continuous history.
        </p>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-surface-500 border-b border-surface-200">
                <th className="py-2 pr-4">Station</th>
                <th className="py-2 pr-4">River</th>
                <th className="py-2 pr-4">Coverage</th>
                <th className="py-2 pr-4">Range</th>
              </tr>
            </thead>
            <tbody>
              {stations.map((s) => {
                const code = s.station_code || s.station_name
                const pct = Number(s.data_coverage_pct ?? 0)
                const coming = Boolean(s.data_coming_soon)
                return (
                  <tr key={code} className="border-b border-surface-100">
                    <td className="py-2 pr-4 font-medium text-surface-800">
                      {code}
                      {coming ? (
                        <span className="ml-2 inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                          Data coming soon
                        </span>
                      ) : null}
                    </td>
                    <td className="py-2 pr-4 text-surface-600">{s.river_name || '—'}</td>
                    <td className="py-2 pr-4 w-48">
                      <div className="flex items-center gap-2">
                        <div className="h-2 flex-1 rounded-full bg-surface-100 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${coming ? 'bg-surface-300' : 'bg-cyan-600'}`}
                            style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                          />
                        </div>
                        <span className="text-xs text-surface-600 tabular-nums w-12 text-right">
                          {coming ? '—' : `${pct}%`}
                        </span>
                      </div>
                    </td>
                    <td className="py-2 pr-4 text-surface-600 text-xs">{s.data_coverage_range_label || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Compare */}
      <section className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-1">Comparative river analysis</h2>
        <p className="text-sm text-surface-500 mb-4">Select two or more stations with uploaded readings, optional year filter.</p>
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="label">Year (optional)</label>
            <select
              className="input-field w-auto min-w-[120px]"
              value={compareYear}
              onChange={(e) => setCompareYear(e.target.value)}
            >
              <option value="">All years</option>
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button type="button" className="btn-primary text-sm" onClick={runCompare} disabled={compareLoading}>
              {compareLoading ? 'Loading…' : 'Load chart'}
            </button>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-52 overflow-y-auto border border-surface-100 rounded-lg p-3 mb-4">
          {stationsWithData.map((s) => {
            const code = s.station_code || s.station_name
            const checked = compareSelected.has(code)
            return (
              <label key={code} className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={checked} onChange={() => toggleCompare(code)} />
                <span>
                  {code}
                  <span className="text-surface-500"> · {s.river_name || ''}</span>
                </span>
              </label>
            )
          })}
        </div>
        <CompareStationsChart compareResult={compareData} height={340} />
      </section>

      {/* Heatmap */}
      <section className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-1">WQI heatmap calendar</h2>
        <p className="text-sm text-surface-500 mb-4">
          Green = clean (WQI ≥ 81), amber = slightly polluted, red = polluted; grey = no reading.
        </p>
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="label">Station</label>
            <select
              className="input-field w-auto min-w-[220px]"
              value={hmStation}
              onChange={(e) => setHmStation(e.target.value)}
            >
              {stationsWithData.map((s) => {
                const code = s.station_code || s.station_name
                return (
                  <option key={code} value={code}>
                    {code} — {s.river_name || ''}
                  </option>
                )
              })}
            </select>
          </div>
          <div>
            <label className="label">Year</label>
            <select
              className="input-field w-auto min-w-[100px]"
              value={hmYear}
              onChange={(e) => setHmYear(Number(e.target.value))}
            >
              {years.length
                ? years.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))
                : [hmYear - 1, hmYear, hmYear + 1].map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
            </select>
          </div>
        </div>
        {hmLoading ? (
          <p className="text-surface-500 text-sm">Loading calendar…</p>
        ) : (
          <div className="overflow-x-auto pb-2">
            <div className="inline-flex gap-0.5">
              {heatGrid.map((col, wi) => (
                <div key={wi} className="flex flex-col gap-0.5">
                  {col.map((slot, ri) => (
                    <div
                      key={`${wi}-${ri}`}
                      title={
                        slot.cell?.date
                          ? `${slot.cell.date}: WQI ${slot.cell.wqi ?? '—'}`
                          : ''
                      }
                      className="w-2.5 h-2.5 rounded-sm shrink-0"
                      style={{ backgroundColor: slot.cell ? heatColor(slot.cell) : 'transparent' }}
                    />
                  ))}
                </div>
              ))}
            </div>
            <p className="text-[11px] text-surface-500 mt-2">
              Columns are weeks (left → right); rows are Sun → Sat. Matches a GitHub-style contribution grid.
            </p>
          </div>
        )}
      </section>

      {/* Parameters */}
      <section className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm">
        <h2 className="font-display font-semibold text-surface-800 mb-1">Parameter contribution</h2>
        <p className="text-sm text-surface-500 mb-4">
          Uses one day&apos;s chemistry from persisted water-quality rows (upload pipeline). Best for diagnosing low WQI
          days.
        </p>
        <div className="flex flex-wrap gap-4 items-end mb-4">
          <div>
            <label className="label">Station code</label>
            <input
              className="input-field w-32"
              value={pcStation}
              onChange={(e) => setPcStation(e.target.value)}
              placeholder="S03"
            />
          </div>
          <div>
            <label className="label">Date</label>
            <input
              className="input-field w-40"
              type="date"
              value={pcDate}
              onChange={(e) => setPcDate(e.target.value)}
            />
          </div>
          <button type="button" className="btn-primary text-sm" onClick={runParameterChart} disabled={pcLoading}>
            {pcLoading ? 'Loading…' : 'Load breakdown'}
          </button>
        </div>
        {pcErr ? <p className="text-amber-700 text-sm mb-3">{pcErr}</p> : null}
        {pcData?.method_note ? <p className="text-xs text-surface-500 mb-2">{pcData.method_note}</p> : null}
        {paramChartData ? (
          <div className="h-72">
            <Bar data={paramChartData} options={paramOptions} />
          </div>
        ) : (
          <p className="text-surface-500 text-sm">Run a query to see the horizontal bar chart.</p>
        )}
      </section>
    </div>
  )
}
