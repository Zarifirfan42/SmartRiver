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

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' },
    title: {
      display: true,
      text: 'WQI with Anomalies (Abnormal Spike)',
      font: { size: 14 },
    },
  },
  scales: {
    x: {
      title: { display: true, text: 'Date', font: { size: 12 } },
      grid: { display: false },
      ticks: { maxTicksLimit: 12 },
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

/**
 * WQI time series with anomaly points marked clearly (red dots).
 * data: [{ date, wqi, station_code? }]
 * anomalies: [{ date, station_code, wqi, reason }]
 */
export default function WQIAnomalyChart({ data = [], anomalies = [], height = 320 }) {
  const labels = data.map((d) => d.date || d.label)
  const wqiValues = data.map((d) => d.wqi ?? d.value)

  const anomalyKeySet = new Set(
    (anomalies || []).map((a) => `${String(a.date || '').trim()}|${String(a.station_code || '').trim()}`)
  )
  const anomalyByIndex = new Map()
  const anomalyValues = data.map((d, i) => {
    const key = `${String(d.date || '').trim()}|${String(d.station_code || '').trim()}`
    const isAnomaly = anomalyKeySet.has(key)
    if (isAnomaly) {
      const a = (anomalies || []).find(
        (an) => `${String(an.date || '').trim()}|${String(an.station_code || '').trim()}` === key
      )
      if (a) anomalyByIndex.set(i, a)
    }
    return isAnomaly ? (d.wqi ?? d.value) : null
  })

  const chartOptions = {
    ...options,
    plugins: {
      ...options.plugins,
      tooltip: {
        callbacks: {
          label: (context) => {
            const idx = context.dataIndex
            const a = anomalyByIndex.get(idx)
            const isAnomalyDataset = context.dataset.label === 'Anomaly (abnormal spike)'
            if (isAnomalyDataset && a) {
              return [
                `Date: ${a.date || labels[idx] || '—'}`,
                `Station: ${a.station_code || '—'}`,
                `WQI: ${a.wqi != null ? Number(a.wqi).toFixed(1) : '—'}`,
                `Reason: ${a.reason || 'Abnormal spike'}`,
              ]
            }
            return `${context.dataset.label}: ${context.parsed.y}`
          },
        },
      },
    },
  }

  const chartData = {
    labels,
    datasets: [
      {
        label: 'WQI',
        data: wqiValues,
        borderColor: '#0891b2',
        backgroundColor: 'rgba(6, 182, 212, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
      {
        label: 'Anomaly (abnormal spike)',
        data: anomalyValues,
        borderColor: 'transparent',
        backgroundColor: '#dc2626',
        fill: false,
        pointRadius: 6,
        pointHoverRadius: 8,
        pointStyle: 'circle',
        order: 0,
      },
    ],
  }

  return (
    <div style={{ height }}>
      <Line data={chartData} options={chartOptions} />
    </div>
  )
}
