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

/** Format Date for X-axis: "Jan 1", "Jan 2", ... */
function formatDayMonth(date) {
  if (!date || !(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  return `${MONTHS[date.getMonth()]} ${date.getDate()}`
}

/** Add n days to a date. */
function addDays(date, n) {
  const out = new Date(date)
  out.setDate(out.getDate() + n)
  return out
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
  // Normalize and sort historical by date for a continuous timeline (only use rows with valid parsed date)
  const histWithDates = historical
    .map((d) => {
      const dateStr = d.date || d.label
      const parsed = parseDate(dateStr)
      return {
        dateStr,
        date: parsed,
        wqi: d.wqi ?? d.value,
      }
    })
    .filter((x) => x.date != null)
    .sort((a, b) => a.date.getTime() - b.date.getTime())

  const histDates = histWithDates.map((x) => x.date)
  const histValues = histWithDates.map((x) => x.wqi)
  const lastHistDate = histDates.length > 0 ? histDates[histDates.length - 1] : null

  // Forecast values (API may return [{ wqi }, ...] or [number, ...])
  const fcValues = forecast.map((d) => (typeof d === 'number' ? d : d?.wqi ?? null)).filter((v) => v != null)

  // Generate continuous daily dates for forecast: day after last hist (or today if no hist), then +1 each
  const forecastDates = []
  const startDate = lastHistDate || new Date()
  if (fcValues.length > 0) {
    for (let i = 0; i < fcValues.length; i++) {
      forecastDates.push(addDays(startDate, lastHistDate ? i + 1 : i))
    }
  }

  // Continuous timeline: historical labels + forecast labels (daily format)
  const histLabels = histDates.map((d) => formatDayMonth(d))
  const fcLabels = forecastDates.map((d) => formatDayMonth(d))
  const allLabels = [...histLabels, ...fcLabels]

  // Historical dataset: values for history, null for forecast positions
  const histData = [...histValues, ...fcLabels.map(() => null)]

  // Forecast dataset: null until last hist index, then bridge (last hist value) + forecast values so line continues
  const lastVal = histValues.length > 0 ? histValues[histValues.length - 1] : null
  const fcData = [
    ...Array(Math.max(0, histLabels.length - 1)).fill(null),
    ...(histLabels.length > 0 && lastVal != null ? [lastVal] : []),
    ...fcValues,
  ]
  while (fcData.length < allLabels.length) fcData.push(null)
  fcData.length = allLabels.length

  const chartData = {
    labels: allLabels,
    datasets: [
      {
        label: 'Historical Data',
        data: histData,
        borderColor: '#64748b',
        backgroundColor: 'rgba(100, 116, 139, 0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 2,
      },
      {
        label: 'Forecast Prediction',
        data: fcData,
        borderColor: '#0891b2',
        borderDash: [5, 5],
        backgroundColor: 'rgba(6, 182, 212, 0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 2,
      },
    ],
  }

  return (
    <div style={{ height }}>
      <Line data={chartData} options={options} />
    </div>
  )
}
