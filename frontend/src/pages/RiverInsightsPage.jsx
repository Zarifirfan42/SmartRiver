/**
 * River insights — comparative trends and WQI calendar heatmap.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import CompareStationsChart from '../components/charts/CompareStationsChart'
import * as dashboardApi from '../api/dashboard'

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

const HM_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
/** GitHub-style: Mon, Wed, Fri beside rows (Sun=0 … Sat=6). */
const HM_DAY_LABELS = ['', 'Mon', '', 'Wed', '', 'Fri', '']

function monthLabelForWeek(year, weekIndex, pad, dim) {
  for (let r = 0; r < 7; r++) {
    const idx = weekIndex * 7 + r
    if (idx < pad) continue
    const dayNum = idx - pad + 1
    if (dayNum < 1 || dayNum > dim) continue
    const d = new Date(year, 0, dayNum)
    if (d.getDate() === 1) return HM_MONTHS[d.getMonth()]
  }
  return ''
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

  if (loading) {
    return <p className="text-surface-500">Loading river insights…</p>
  }

  return (
    <div className="max-w-6xl mx-auto space-y-10">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-900">River insights</h1>
        <p className="text-surface-600 mt-2 text-sm max-w-3xl">
          Compare stations side-by-side and inspect daily WQI patterns on a GitHub-style calendar heatmap
          for all seven rivers (S01–S07).
        </p>
        {err ? <p className="text-amber-700 text-sm mt-2">{err}</p> : null}
      </div>

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
            <div className="inline-flex flex-col">
              {/* Month labels row */}
              <div className="flex pl-9 mb-1">
                {heatGrid.map((_, wi) => {
                  const dim = daysInYear(hmYear)
                  const pad = new Date(hmYear, 0, 1).getDay()
                  const label = monthLabelForWeek(hmYear, wi, pad, dim)
                  return (
                    <div
                      key={`m-${wi}`}
                      className="w-[11px] shrink-0 text-[10px] text-surface-400 leading-none overflow-visible whitespace-nowrap"
                    >
                      {label}
                    </div>
                  )
                })}
              </div>
              <div className="flex gap-1">
                {/* Day-of-week labels (Mon / Wed / Fri) */}
                <div className="flex flex-col gap-0.5 w-8 shrink-0 pt-0">
                  {HM_DAY_LABELS.map((lbl, ri) => (
                    <div
                      key={`d-${ri}`}
                      className="h-2.5 text-[9px] text-surface-400 leading-[10px] text-right pr-1"
                    >
                      {lbl}
                    </div>
                  ))}
                </div>
                {/* Week columns × day rows */}
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
              </div>
            </div>
            <p className="text-[11px] text-surface-500 mt-2 pl-9">
              Columns = weeks (Jan → Dec); rows = Sun → Sat. Month labels align to the first week of each month.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}
