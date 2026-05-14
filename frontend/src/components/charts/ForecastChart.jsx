import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Parse date string (YYYY-MM-DD, "Jan 1", "1 Jan", etc.) to Date. Prefer local date for YYYY-MM-DD. */
function parseDate(str) {
  if (!str) return null
  const s = String(str).trim()
  const match = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (match) {
    const [, y, m, d] = match.map(Number)
    const d2 = new Date(y, m - 1, d)
    return Number.isNaN(d2.getTime()) ? null : d2
  }
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? null : d
}

/** Format Date for X-axis: "Jan 2023", "Feb 2023", ... (month + year for long range). */
function formatMonthYear(date) {
  if (!date || !(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  return `${MONTHS[date.getMonth()]} ${date.getFullYear()}`
}

/** Format Date for X-axis: "Jan 1", "Jan 2", ... (short range). */
function formatDayMonth(date) {
  if (!date || !(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  return `${MONTHS[date.getMonth()]} ${date.getDate()}`
}

const baseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      labels: { usePointStyle: true },
    },
    title: {
      display: true,
      text: 'WQI: Historical Data vs Forecast Prediction',
      font: { size: 14 },
    },
  },
  scales: {
    x: {
      title: { display: true, text: 'Date', font: { size: 12 } },
      grid: { display: false },
      ticks: { maxTicksLimit: 20, autoSkip: true, autoSkipPadding: 8 },
    },
    y: {
      title: { display: true, text: 'WQI', font: { size: 12 } },
      min: 0,
      max: 100,
      grid: { color: '#e2e8f0' },
      ticks: { stepSize: 20 },
    },
  },
}

/** YYYY-MM-DD to Date at midnight (local). */
function parseDateOnly(str) {
  if (!str || typeof str !== 'string') return null
  const s = str.trim().slice(0, 10)
  const match = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return null
  const [, y, m, d] = match.map(Number)
  const d2 = new Date(y, m - 1, d)
  return Number.isNaN(d2.getTime()) ? null : d2
}

// Aggregate by granularity: 'daily' | 'monthly' | 'yearly'
function aggregateSeries(entries, mode) {
  if (mode === 'daily') {
    return entries
  }
  const buckets = new Map()
  entries.forEach(({ date, wqi }) => {
    if (!date || Number.isNaN(date.getTime())) return
    const y = date.getFullYear()
    const m = date.getMonth()
    let key
    if (mode === 'monthly') {
      key = `${y}-${String(m + 1).padStart(2, '0')}`
    } else {
      key = `${y}`
    }
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key).push(wqi)
  })
  const out = []
  buckets.forEach((values, key) => {
    const avg = values.reduce((s, v) => s + v, 0) / values.length
    let d
    if (mode === 'monthly') {
      const [y, m] = key.split('-').map(Number)
      d = new Date(y, m - 1, 1)
    } else {
      const y = Number(key)
      d = new Date(y, 0, 1)
    }
    out.push({ date: d, wqi: avg })
  })
  out.sort((a, b) => a.date.getTime() - b.date.getTime())
  return out
}

function aggregateForecastWithCi(entries, mode) {
  if (mode === 'daily') {
    return entries
  }
  const buckets = new Map()
  entries.forEach(({ date, wqi, lo, hi }) => {
    if (!date || Number.isNaN(date.getTime())) return
    const y = date.getFullYear()
    const m = date.getMonth()
    let key
    if (mode === 'monthly') {
      key = `${y}-${String(m + 1).padStart(2, '0')}`
    } else {
      key = `${y}`
    }
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key).push({ wqi, lo, hi })
  })
  const mean = (vals) => {
    const vs = vals.filter((v) => v != null && !Number.isNaN(v))
    if (!vs.length) return null
    return vs.reduce((a, b) => a + b, 0) / vs.length
  }
  const out = []
  buckets.forEach((values, key) => {
    const avgWqi = mean(values.map((v) => v.wqi))
    const avgLo = mean(values.map((v) => v.lo).filter((x) => x != null))
    const avgHi = mean(values.map((v) => v.hi).filter((x) => x != null))
    let d
    if (mode === 'monthly') {
      const [yy, mm] = key.split('-').map(Number)
      d = new Date(yy, mm - 1, 1)
    } else {
      const yy = Number(key)
      d = new Date(yy, 0, 1)
    }
    out.push({ date: d, wqi: avgWqi, lo: avgLo, hi: avgHi })
  })
  out.sort((a, b) => a.date.getTime() - b.date.getTime())
  return out
}

function ciHalfWidth(wqi) {
  const w = Number(wqi)
  if (Number.isNaN(w)) return 6
  return Math.min(12, Math.max(3, 0.08 * Math.max(w, 1)))
}

export default function ForecastChart({ historical = [], forecast = [], height = 280, today: todayStr, viewMode = 'monthly' }) {
  // Classify by today: historical ends at today, forecast starts after today (no overlap).
  const todayDate = todayStr ? parseDateOnly(todayStr) : null

  // Normalize historical: parse date, keep wqi; optionally filter to date <= today
  let histWithDates = historical
    .map((d) => {
      const dateStr = d.date || d.label
      const parsed = parseDate(dateStr)
      return { date: parsed, wqi: d.wqi ?? d.value }
    })
    .filter((x) => x.date != null)
  if (todayDate) histWithDates = histWithDates.filter((x) => x.date.getTime() <= todayDate.getTime())
  histWithDates.sort((a, b) => a.date.getTime() - b.date.getTime())

  // Normalize forecast: parse date, keep wqi + optional CI from API
  let fcWithDates = forecast
    .map((d) => {
      const dateStr = d.date || d.label
      const parsed = parseDate(dateStr)
      const wqi = typeof d === 'number' ? d : (d?.wqi ?? null)
      let lo = d?.wqi_lower ?? d?.wqiLower ?? null
      let hi = d?.wqi_upper ?? d?.wqiUpper ?? null
      if (lo == null && hi == null && wqi != null && !Number.isNaN(Number(wqi))) {
        const half = ciHalfWidth(wqi)
        lo = Math.max(0, Number(wqi) - half)
        hi = Math.min(100, Number(wqi) + half)
      }
      return { date: parsed, wqi, lo, hi }
    })
    .filter((x) => x.date != null && x.wqi != null)
  if (todayDate) fcWithDates = fcWithDates.filter((x) => x.date.getTime() > todayDate.getTime())
  fcWithDates.sort((a, b) => a.date.getTime() - b.date.getTime())

  // Apply aggregation based on view mode and limit number of points
  let histAgg = histWithDates
  let fcAgg = fcWithDates
  if (viewMode === 'monthly') {
    histAgg = aggregateSeries(histWithDates, 'monthly')
    fcAgg = aggregateForecastWithCi(fcWithDates, 'monthly')
    histAgg = histAgg.slice(-36)
    fcAgg = fcAgg.slice(-36)
  } else if (viewMode === 'yearly') {
    histAgg = aggregateSeries(histWithDates, 'yearly')
    fcAgg = aggregateForecastWithCi(fcWithDates, 'yearly')
    histAgg = histAgg.slice(-10)
    fcAgg = fcAgg.slice(-10)
  } else {
    // daily: up to 365 points max (enough for full year)
    histAgg = histWithDates.slice(-365)
    fcAgg = fcWithDates.slice(-365)
  }

  // Single chronological timeline: merge historical + forecast and dedupe by date
  const dateToHist = new Map()
  histAgg.forEach(({ date, wqi }) => dateToHist.set(date.getTime(), { type: 'hist', wqi }))
  const dateToFc = new Map()
  fcAgg.forEach(({ date, wqi, lo, hi }) => dateToFc.set(date.getTime(), { type: 'fc', wqi, lo, hi }))
  const allTimestamps = [...new Set([...dateToHist.keys(), ...dateToFc.keys()])].sort((a, b) => a - b)
  const allDates = allTimestamps.map((t) => new Date(t))
  let allLabels
  if (viewMode === 'daily') {
    allLabels = allDates.map((d) => `${d.getDate().toString().padStart(2, '0')} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`)
  } else if (viewMode === 'monthly') {
    allLabels = allDates.map((d) => formatMonthYear(d))
  } else {
    allLabels = allDates.map((d) => `${d.getFullYear()}`)
  }

  const histData = allTimestamps.map((t) => (dateToHist.has(t) ? dateToHist.get(t).wqi : null))
  const fcData = allTimestamps.map((t) => (dateToFc.has(t) ? dateToFc.get(t).wqi : null))
  const fcLowerData = allTimestamps.map((t) => (dateToFc.has(t) ? dateToFc.get(t).lo : null))
  const fcUpperData = allTimestamps.map((t) => (dateToFc.has(t) ? dateToFc.get(t).hi : null))
  const hasCi = fcLowerData.some((v) => v != null) && fcUpperData.some((v) => v != null)

  const tension = viewMode === 'daily' ? 0.15 : 0.25
  const ciDatasets = hasCi
    ? [
        {
          label: 'Forecast CI lower',
          data: fcLowerData,
          borderColor: 'rgba(79, 70, 229, 0)',
          backgroundColor: 'transparent',
          borderWidth: 0,
          pointRadius: 0,
          fill: false,
          tension,
          spanGaps: false,
          order: 0,
        },
        {
          label: 'Forecast CI upper',
          data: fcUpperData,
          borderColor: 'rgba(79, 70, 229, 0)',
          backgroundColor: 'rgba(79, 70, 229, 0.18)',
          borderWidth: 0,
          pointRadius: 0,
          fill: '-1',
          tension,
          spanGaps: false,
          order: 0,
        },
      ]
    : []

  const chartData = {
    labels: allLabels,
    datasets: [
      ...ciDatasets,
      {
        label: 'Historical Data',
        data: histData,
        borderColor: '#94a3b8',
        backgroundColor: 'rgba(148, 163, 184, 0.16)',
        borderWidth: viewMode === 'daily' ? 1.1 : 1.3,
        fill: viewMode === 'daily',
        tension,
        pointRadius: viewMode === 'daily' ? 1 : 0,
        spanGaps: false,
        order: 2,
      },
      {
        label: 'Forecast Prediction',
        data: fcData,
        borderColor: '#4f46e5',
        borderDash: [],
        backgroundColor: 'rgba(79, 70, 229, 0.12)',
        borderWidth: viewMode === 'daily' ? 3.2 : 2.4,
        fill: false,
        tension,
        pointRadius: viewMode === 'daily' ? 2 : 2,
        spanGaps: false,
        order: 3,
      },
    ],
  }

  const options = {
    ...baseOptions,
    plugins: {
      ...baseOptions.plugins,
      legend: {
        ...baseOptions.plugins.legend,
        labels: {
          ...baseOptions.plugins.legend.labels,
          filter: (item) => item.text !== 'Forecast CI lower' && item.text !== 'Forecast CI upper',
        },
      },
      tooltip: {
        callbacks: {
          title(items) {
            if (!items || items.length === 0) return ''
            return items[0].label
          },
          label(context) {
            const value = context.parsed.y
            if (value == null) return ''
            const w = Number(value)
            let status
            if (w >= 81) status = 'Clean'
            else if (w >= 60) status = 'Slightly Polluted'
            else status = 'Polluted'
            return [`WQI: ${w.toFixed(1)}`, `Status: ${status}`]
          },
        },
      },
    },
    scales: {
      ...baseOptions.scales,
      x: {
        ...baseOptions.scales.x,
        title: {
          display: true,
          text: viewMode === 'daily' ? 'Date' : viewMode === 'monthly' ? 'Month' : 'Year',
          font: { size: 12 },
        },
      },
    },
  }

  return (
    <div style={{ height }}>
      <Line data={chartData} options={options} />
    </div>
  )
}
