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

const options = {
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

export default function ForecastChart({ historical = [], forecast = [], height = 280 }) {
  // Normalize historical: parse date, keep wqi
  const histWithDates = historical
    .map((d) => {
      const dateStr = d.date || d.label
      const parsed = parseDate(dateStr)
      return { date: parsed, wqi: d.wqi ?? d.value }
    })
    .filter((x) => x.date != null)
    .sort((a, b) => a.date.getTime() - b.date.getTime())

  // Normalize forecast: parse date, keep wqi
  const fcWithDates = forecast
    .map((d) => {
      const dateStr = d.date || d.label
      const parsed = parseDate(dateStr)
      return { date: parsed, wqi: typeof d === 'number' ? d : (d?.wqi ?? null) }
    })
    .filter((x) => x.date != null && x.wqi != null)
    .sort((a, b) => a.date.getTime() - b.date.getTime())

  // Single chronological timeline (2023 → 2028): merge and dedupe by date string
  const dateToHist = new Map()
  histWithDates.forEach(({ date, wqi }) => dateToHist.set(date.getTime(), { type: 'hist', wqi }))
  const dateToFc = new Map()
  fcWithDates.forEach(({ date, wqi }) => dateToFc.set(date.getTime(), { type: 'fc', wqi }))
  const allTimestamps = [...new Set([...dateToHist.keys(), ...dateToFc.keys()])].sort((a, b) => a - b)
  const allDates = allTimestamps.map((t) => new Date(t))
  const useMonthYear = allDates.length > 12 || (allDates.length > 0 && (allDates[allDates.length - 1].getTime() - allDates[0].getTime()) > 365 * 24 * 60 * 60 * 1000)
  const allLabels = allDates.map((d) => (useMonthYear ? formatMonthYear(d) : formatDayMonth(d)))

  const histData = allTimestamps.map((t) => (dateToHist.has(t) ? dateToHist.get(t).wqi : null))
  const fcData = allTimestamps.map((t) => (dateToFc.has(t) ? dateToFc.get(t).wqi : null))

  const chartData = {
    labels: allLabels,
    datasets: [
      {
        label: 'Historical Data',
        data: histData,
        borderColor: '#475569',
        backgroundColor: 'rgba(71, 85, 105, 0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        spanGaps: true,
      },
      {
        label: 'Forecast Prediction',
        data: fcData,
        borderColor: '#0891b2',
        borderDash: [6, 4],
        backgroundColor: 'rgba(6, 182, 212, 0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        spanGaps: true,
      },
    ],
  }

  return (
    <div style={{ height }}>
      <Line data={chartData} options={options} />
    </div>
  )
}
